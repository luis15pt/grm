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
    Fetch rack and device positioning data from NetBox for rack visualization.

    Args:
        site_filter: Filter by datacenter site (e.g., 'CA1')
        gpu_type_filter: Filter by GPU type (e.g., 'H100', 'A100')
        owner_filter: Filter by owner ('Nexgen Cloud' or 'Investors')

    Returns: {
        "racks": [{
            "id": 123,
            "name": "Z01-T23",
            "site": "CA1",
            "u_height": 42,
            "devices": [{
                "hostname": "gpu-h100-001",
                "position": 10,
                "u_height": 4,
                "owner_group": "Nexgen Cloud" | "Investors",
                "gpu_type": "H100",
                "tenant": "Chris Starkey",
                "status": "active" | "decommissioning",
                "nvlinks": true
            }]
        }],
        "summary": {
            "by_owner": {...},
            "by_gpu_type": {...},
            "totals": {...}
        }
    }
    """
    if not NETBOX_URL or not NETBOX_API_KEY:
        print("⚠️ NetBox not configured - cannot fetch rack visualization data")
        return {"racks": [], "summary": {}, "error": "NetBox not configured"}

    headers = {
        'Authorization': f'Token {NETBOX_API_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        # Step 1: Fetch all racks
        racks_url = f"{NETBOX_URL}/api/dcim/racks/"
        racks_params = {'limit': 500}
        if site_filter:
            # NetBox API uses site__name for filtering by site name
            racks_params['site__name'] = site_filter

        print(f"📦 Fetching racks from NetBox with params: {racks_params}")
        racks_response = requests.get(racks_url, headers=headers, params=racks_params, timeout=30)
        if racks_response.status_code != 200:
            print(f"❌ NetBox racks API error: {racks_response.status_code} - {racks_response.text[:200]}")
            # Try without site filter as fallback
            if site_filter:
                print("⚠️ Retrying without site filter...")
                racks_params = {'limit': 500}
                racks_response = requests.get(racks_url, headers=headers, params=racks_params, timeout=30)
                if racks_response.status_code != 200:
                    return {"racks": [], "summary": {}, "error": f"API error: {racks_response.status_code}"}

        racks_data = racks_response.json()
        racks_list = racks_data.get('results', [])

        # If site filter was provided, filter racks by site name client-side as backup
        if site_filter and racks_list:
            racks_list = [r for r in racks_list if r.get('site', {}).get('name') == site_filter]

        print(f"📦 Fetched {len(racks_list)} racks from NetBox")

        # Step 2: Fetch all devices with rack positions
        devices_url = f"{NETBOX_URL}/api/dcim/devices/"
        devices_params = {
            'limit': 1000,
            'has_primary_ip': 'true',  # Only devices with IPs (actual servers)
        }
        if site_filter:
            # NetBox API uses site__name for filtering by site name
            devices_params['site__name'] = site_filter

        all_devices = []
        offset = 0
        print(f"🖥️ Fetching devices from NetBox with params: {devices_params}")
        while True:
            devices_params['offset'] = offset
            devices_response = requests.get(devices_url, headers=headers, params=devices_params, timeout=30)
            if devices_response.status_code != 200:
                print(f"❌ NetBox devices API error: {devices_response.status_code} - {devices_response.text[:200]}")
                # Try without site filter as fallback
                if site_filter and offset == 0:
                    print("⚠️ Retrying devices without site filter...")
                    devices_params.pop('site__name', None)
                    devices_response = requests.get(devices_url, headers=headers, params=devices_params, timeout=30)
                    if devices_response.status_code != 200:
                        break
                else:
                    break

            devices_data = devices_response.json()
            devices_batch = devices_data.get('results', [])
            all_devices.extend(devices_batch)

            if len(devices_batch) < 1000:
                break
            offset += 1000

        # If site filter was provided but API didn't support it, filter client-side
        if site_filter and all_devices:
            original_count = len(all_devices)
            all_devices = [d for d in all_devices if d.get('site', {}).get('name') == site_filter]
            if len(all_devices) != original_count:
                print(f"🔍 Filtered devices by site '{site_filter}': {original_count} -> {len(all_devices)}")

        print(f"🖥️ Fetched {len(all_devices)} devices from NetBox")

        # Step 3: Process devices and organize by rack
        rack_devices = {}  # rack_id -> list of devices
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

        for device in all_devices:
            device_name = device.get('name', '')

            # Extract GPU type from device name or device type
            gpu_type = None
            device_type_name = device.get('device_type', {}).get('model', '') if device.get('device_type') else ''

            # Try to detect GPU type from name patterns
            for gpu in ['H100', 'H200', 'A100', 'A6000', 'L40S', 'L40', 'A40', '4090', '3090']:
                if gpu.lower() in device_name.lower() or gpu.lower() in device_type_name.lower():
                    gpu_type = gpu
                    break

            # Apply GPU type filter
            if gpu_type_filter and gpu_type != gpu_type_filter:
                continue

            # Get tenant and owner information
            tenant_data = device.get('tenant', {})
            tenant_name = tenant_data.get('name', 'Unknown') if tenant_data else 'Unknown'
            owner_group = 'Nexgen Cloud' if tenant_name == 'Chris Starkey' else 'Investors'

            # Apply owner filter
            if owner_filter and owner_group != owner_filter:
                continue

            # Get device status
            status_data = device.get('status', {})
            status = status_data.get('value', 'active') if status_data else 'active'

            # Get custom fields (NVLinks)
            custom_fields = device.get('custom_fields', {})
            nvlinks = custom_fields.get('NVLinks', False) or False

            # Get rack and position info
            rack_data = device.get('rack', {})
            position = device.get('position')
            device_u_height = device.get('device_type', {}).get('u_height', 4) if device.get('device_type') else 4

            device_info = {
                "hostname": device_name,
                "position": position,
                "u_height": device_u_height,
                "owner_group": owner_group,
                "gpu_type": gpu_type,
                "tenant": tenant_name,
                "status": status,
                "nvlinks": nvlinks,
                "netbox_id": device.get('id'),
                "netbox_url": device.get('url')
            }

            # Update summary counters
            summary["totals"]["total_devices"] += 1
            summary["by_owner"][owner_group]["total"] += 1

            if status == 'decommissioning':
                summary["by_owner"][owner_group]["decommissioning"] += 1
                summary["totals"]["for_sale"] += 1
            else:
                summary["by_owner"][owner_group]["active"] += 1

            # GPU type breakdown (only for NexGen devices)
            if gpu_type:
                if gpu_type not in summary["by_gpu_type"]:
                    summary["by_gpu_type"][gpu_type] = {"nexgen": 0, "investors": 0, "decommissioning": 0}

                if owner_group == "Nexgen Cloud":
                    summary["by_gpu_type"][gpu_type]["nexgen"] += 1
                    if status == 'decommissioning':
                        summary["by_gpu_type"][gpu_type]["decommissioning"] += 1
                else:
                    summary["by_gpu_type"][gpu_type]["investors"] += 1

            # Organize by rack
            if rack_data and rack_data.get('id') and position:
                rack_id = rack_data['id']
                if rack_id not in rack_devices:
                    rack_devices[rack_id] = []
                rack_devices[rack_id].append(device_info)
            else:
                unpositioned_devices.append(device_info)

        # Step 4: Build rack visualization structure
        racks_output = []
        for rack in racks_list:
            rack_id = rack.get('id')
            devices_in_rack = rack_devices.get(rack_id, [])

            # Skip empty racks unless they have devices
            if not devices_in_rack:
                continue

            site_info = rack.get('site', {})
            site_name = site_info.get('name', 'Unknown') if site_info else 'Unknown'

            racks_output.append({
                "id": rack_id,
                "name": rack.get('name', f'Rack-{rack_id}'),
                "site": site_name,
                "u_height": rack.get('u_height', 42),
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
