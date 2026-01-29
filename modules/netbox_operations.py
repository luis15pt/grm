#!/usr/bin/env python3

import requests
import os

# NetBox configuration
NETBOX_URL = os.getenv('NETBOX_URL')
NETBOX_API_KEY = os.getenv('NETBOX_API_KEY')

# Cache for NetBox tenant lookups to avoid repeated API calls
_tenant_cache = {}

def get_netbox_tenants_bulk(hostnames):
    """Get tenant information from NetBox for multiple hostnames at once"""
    global _tenant_cache
    
    # Return default if NetBox is not configured
    if not NETBOX_URL or not NETBOX_API_KEY:
        print("⚠️ NetBox not configured - using default tenant")
        default_result = {'tenant': 'Unknown', 'owner_group': 'Investors', 'nvlinks': False, 'netbox_device_id': None, 'netbox_url': None}
        return {hostname: default_result for hostname in hostnames}
    
    # Check cache first and separate cached vs uncached hostnames
    cached_results = {}
    uncached_hostnames = []
    
    for hostname in hostnames:
        if hostname in _tenant_cache:
            cached_results[hostname] = _tenant_cache[hostname]
        else:
            uncached_hostnames.append(hostname)
    
    # If all hostnames are cached, return cached results
    if not uncached_hostnames:
        return cached_results
    
    # Bulk query NetBox for uncached hostnames
    bulk_results = {}
    try:
        url = f"{NETBOX_URL}/api/dcim/devices/"
        headers = {
            'Authorization': f'Token {NETBOX_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # NetBox API supports filtering by multiple names using name__in
        # But since that might not work, we'll paginate through all results
        params = {'limit': 1000}  # Get up to 1000 devices per page
        
        all_devices = []
        page = 1
        
        while True:
            params['offset'] = (page - 1) * 1000
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                all_devices.extend(data['results'])
                
                # If we got less than 1000 results, we're done
                if len(data['results']) < 1000:
                    break
                page += 1
            else:
                print(f"❌ NetBox API error: {response.status_code}")
                break
        
        # Create a mapping of device name to tenant info
        device_map = {}
        for i, device in enumerate(all_devices):
            device_name = device.get('name')
            if device_name in uncached_hostnames:
                tenant_data = device.get('tenant', {})
                tenant_name = tenant_data.get('name', 'Unknown') if tenant_data else 'Unknown'
                owner_group = 'Nexgen Cloud' if tenant_name == 'Chris Starkey' else 'Investors'
                
                # Get NVLinks custom field
                custom_fields = device.get('custom_fields', {})
                nvlinks = custom_fields.get('NVLinks', False)
                # Convert None to False for boolean consistency
                if nvlinks is None:
                    nvlinks = False
                
                result = {
                    'tenant': tenant_name,
                    'owner_group': owner_group,
                    'nvlinks': nvlinks,
                    'netbox_device_id': device.get('id'),
                    'netbox_url': device.get('display_url') or device.get('url')
                }
                
                device_map[device_name] = result
                _tenant_cache[device_name] = result
        
        # Fill in results for uncached hostnames
        for hostname in uncached_hostnames:
            if hostname in device_map:
                bulk_results[hostname] = device_map[hostname]
                print(f"✅ NetBox lookup for {hostname}: {device_map[hostname]['tenant']} -> {device_map[hostname]['owner_group']}")
            else:
                # Device not found in NetBox, use default
                default_result = {'tenant': 'Unknown', 'owner_group': 'Investors', 'nvlinks': False, 'netbox_device_id': None, 'netbox_url': None}
                bulk_results[hostname] = default_result
                _tenant_cache[hostname] = default_result
                print(f"⚠️ Device {hostname} not found in NetBox")
        
        print(f"📊 Bulk NetBox lookup completed: {len(bulk_results)} new devices processed")
        
    except Exception as e:
        print(f"❌ NetBox bulk lookup failed: {e}")
        # Fall back to default for all uncached hostnames
        default_result = {'tenant': 'Unknown', 'owner_group': 'Investors', 'nvlinks': False, 'netbox_device_id': None, 'netbox_url': None}
        for hostname in uncached_hostnames:
            bulk_results[hostname] = default_result
            _tenant_cache[hostname] = default_result
    
    # Merge cached and bulk results
    return {**cached_results, **bulk_results}

def get_netbox_tenant(hostname):
    """Get tenant information from NetBox for a single hostname (wrapper for backward compatibility)"""
    return get_netbox_tenants_bulk([hostname])[hostname]


def get_rack_visualization_data(site_filter=None, gpu_type_filter=None, owner_filter=None):
    """
    Get rack visualization data using parallel agents as the single source of truth.
    All data including rack_position and u_height comes from parallel agents.

    Args:
        site_filter: Filter by datacenter site (e.g., 'Enovum')
        gpu_type_filter: Filter by GPU type (e.g., 'H100', 'A100')
        owner_filter: Filter by owner ('Nexgen Cloud' or 'Investors')

    Returns: {
        "racks": [{
            "id": "rack-name",
            "name": "Z01-427",
            "site": "Enovum",
            "u_height": 42,
            "devices": [{...}]
        }],
        "summary": {...}
    }
    """
    # Import here to avoid circular imports
    from modules.parallel_agents import get_all_data_parallel

    try:
        # Step 1: Get all device data from parallel agents (single source of truth)
        print(f"🔄 Loading rack visualization data from parallel agents...")
        parallel_data = get_all_data_parallel()

        # Collect all hosts from all GPU types
        all_hosts = []
        for gpu_type_key, gpu_data in parallel_data.items():
            if gpu_type_key.startswith('_'):
                continue  # Skip internal keys
            hosts = gpu_data.get('hosts', [])
            for host in hosts:
                # Add gpu_type to host data if not present
                if 'gpu_type' not in host or not host.get('gpu_type'):
                    host['gpu_type'] = gpu_type_key
                all_hosts.append(host)

        print(f"📊 Loaded {len(all_hosts)} hosts from parallel agents")

        # Step 2: Apply filters
        filtered_hosts = []
        for host in all_hosts:
            # Site filter
            if site_filter and host.get('site') != site_filter:
                continue

            # GPU type filter
            if gpu_type_filter and host.get('gpu_type') != gpu_type_filter:
                continue

            # Owner filter
            if owner_filter and host.get('owner_group') != owner_filter:
                continue

            filtered_hosts.append(host)

        print(f"🔍 After filters: {len(filtered_hosts)} hosts (site={site_filter}, gpu={gpu_type_filter}, owner={owner_filter})")

        # Step 3: Organize devices by rack
        rack_devices = {}  # rack_name -> {'site': str, 'devices': []}
        unpositioned_devices = []

        # Summary counters
        summary = {
            "by_owner": {
                "Nexgen Cloud": {"total": 0, "active": 0, "decommissioning": 0},
                "Investors": {"total": 0, "active": 0, "decommissioning": 0}
            },
            "by_gpu_type": {},
            "totals": {
                "total_devices": 0,
                "total_racks": 0,
                "for_sale": 0
            }
        }

        for host in filtered_hosts:
            hostname = host.get('hostname') or host.get('name', '')
            rack_name = host.get('rack', 'Unknown')
            site = host.get('site', 'Unknown')
            gpu_type = host.get('gpu_type', 'Unknown')
            owner_group = host.get('owner_group', 'Investors')
            tenant = host.get('tenant', 'Unknown')
            status = host.get('status', 'active')
            nvlinks = host.get('nvlinks', False)

            # Get position and u_height directly from parallel agents data
            position = host.get('rack_position')
            u_height = host.get('u_height', 4)

            device_info = {
                "hostname": hostname,
                "position": position,
                "u_height": u_height,
                "owner_group": owner_group,
                "gpu_type": gpu_type,
                "tenant": tenant,
                "status": status,
                "nvlinks": nvlinks,
                "netbox_id": host.get('netbox_device_id'),
                "netbox_url": host.get('netbox_url'),
                "vm_count": host.get('vm_count', 0),
                "gpu_used": host.get('gpu_used', 0),
                "gpu_capacity": host.get('gpu_capacity', 8)
            }

            # Update summary counters
            summary["totals"]["total_devices"] += 1

            if owner_group in summary["by_owner"]:
                summary["by_owner"][owner_group]["total"] += 1
                if status == 'decommissioning':
                    summary["by_owner"][owner_group]["decommissioning"] += 1
                    summary["totals"]["for_sale"] += 1
                else:
                    summary["by_owner"][owner_group]["active"] += 1

            # GPU type breakdown
            if gpu_type:
                if gpu_type not in summary["by_gpu_type"]:
                    summary["by_gpu_type"][gpu_type] = {"nexgen": 0, "investors": 0, "decommissioning": 0}

                if owner_group == "Nexgen Cloud":
                    summary["by_gpu_type"][gpu_type]["nexgen"] += 1
                    if status == 'decommissioning':
                        summary["by_gpu_type"][gpu_type]["decommissioning"] += 1
                else:
                    summary["by_gpu_type"][gpu_type]["investors"] += 1

            # Organize by rack name (from parallel agents data)
            if rack_name and rack_name != 'Unknown' and position:
                if rack_name not in rack_devices:
                    rack_devices[rack_name] = {'site': site, 'devices': []}
                rack_devices[rack_name]['devices'].append(device_info)
            else:
                unpositioned_devices.append(device_info)

        # Step 5: Build rack visualization structure
        racks_output = []
        for rack_name, rack_info in rack_devices.items():
            devices_in_rack = rack_info['devices']

            racks_output.append({
                "id": rack_name,
                "name": rack_name,
                "site": rack_info['site'],
                "u_height": 42,  # Default rack height
                "devices": sorted(devices_in_rack, key=lambda d: d['position'] or 0, reverse=True)
            })

        # Sort racks by name
        racks_output.sort(key=lambda r: r['name'])

        summary["totals"]["total_racks"] = len(racks_output)

        # Add unpositioned devices section if any
        if unpositioned_devices:
            racks_output.append({
                "id": "unpositioned",
                "name": "Unpositioned",
                "site": site_filter or "All",
                "u_height": 42,
                "devices": unpositioned_devices,
                "is_virtual": True
            })

        print(f"✅ Rack visualization data ready: {len(racks_output)} racks, {summary['totals']['total_devices']} devices")

        return {
            "racks": racks_output,
            "summary": summary,
            "filters": {
                "site": site_filter,
                "gpu_type": gpu_type_filter,
                "owner": owner_filter
            }
        }

    except Exception as e:
        print(f"❌ Error fetching rack visualization data: {e}")
        import traceback
        traceback.print_exc()
        return {"racks": [], "summary": {}, "error": str(e)}
