#!/usr/bin/env python3

import requests
import os
import time

# NetBox configuration
NETBOX_URL = os.getenv('NETBOX_URL')
NETBOX_API_KEY = os.getenv('NETBOX_API_KEY')

# Import NetBox utilities for branch-aware API calls
from .netbox_utils import build_netbox_headers, get_cache_key_suffix

# Cache for NetBox out of stock devices to avoid repeated API calls
# Now a dict keyed by branch suffix for branch-aware caching
_outofstock_cache = {}  # key: branch_suffix -> list of devices
_cache_ttl = 300  # 5 minutes cache TTL
_last_cache_time = {}  # key: branch_suffix -> timestamp

def get_netbox_non_active_devices(branch=None):
    """Get devices from NetBox that are not in active status

    Args:
        branch: Optional NetBox branch schema ID (uses global default if not provided)
    """
    global _outofstock_cache, _last_cache_time

    # Get cache key suffix for branch-aware caching
    cache_suffix = get_cache_key_suffix(branch)

    # Check cache first
    current_time = time.time()
    last_time = _last_cache_time.get(cache_suffix, 0)
    if current_time - last_time < _cache_ttl and cache_suffix in _outofstock_cache:
        cached_data = _outofstock_cache[cache_suffix]
        print(f"✅ Using cached NetBox out-of-stock data ({len(cached_data)} devices)")
        return cached_data

    # Return empty if NetBox is not configured
    if not NETBOX_URL or not NETBOX_API_KEY:
        print("⚠️ NetBox not configured - returning empty out-of-stock list")
        return []

    try:
        print("🔍 Querying NetBox for non-active GPU devices...")

        url = f"{NETBOX_URL}/api/dcim/devices/"
        headers = build_netbox_headers(branch)
        
        # Query for devices with non-active status and GPU tags
        # Status values: active, offline, planned, staged, failed, inventory, decommissioning
        non_active_statuses = ['offline', 'planned', 'staged', 'failed', 'inventory', 'decommissioning']
        gpu_tags = ['nvidia-h100-pcie', 'nvidia-a100-pcie', 'nvidia-a100-sxm', 'nvidia-h100-sxm', 'nvidia-rtx-4090']
        
        all_devices = []
        
        # Query for each non-active status to get all failed/offline devices
        for status in non_active_statuses:
            for gpu_tag in gpu_tags:
                params = {
                    'tag': gpu_tag,
                    'status': status,
                    'limit': 1000  # Get up to 1000 devices per query
                }
                
                try:
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        devices = data.get('results', [])
                        
                        if devices:
                            print(f"📋 Found {len(devices)} devices with status '{status}' and tag '{gpu_tag}'")
                            all_devices.extend(devices)
                    else:
                        print(f"⚠️ NetBox API error for {status}/{gpu_tag}: {response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ Error querying NetBox for {status}/{gpu_tag}: {e}")
                    continue
        
        # Remove duplicates (device might have multiple GPU tags)
        unique_devices = {}
        for device in all_devices:
            device_id = device.get('id')
            if device_id not in unique_devices:
                unique_devices[device_id] = device
        
        processed_devices = []
        
        # Process each unique device
        for device in unique_devices.values():
            device_name = device.get('name')
            if not device_name:
                continue
                
            # Extract device information
            device_info = {
                'name': device_name,
                'hostname': device_name,  # For consistency with other columns
                'status': device.get('status', {}).get('value', 'unknown'),
                'status_label': device.get('status', {}).get('label', 'Unknown'),
                'aggregate': 'unknown',  # Will be filled from custom fields
                'tenant': 'Unknown',
                'owner_group': 'Unknown',
                'nvlinks': False,
                'gpu_used': 0,
                'gpu_capacity': 8,  # Assume 8 GPUs per failed device
                'gpu_usage_ratio': '0/8',
                'site': device.get('site', {}).get('name', 'Unknown') if device.get('site') else 'Unknown',
                'rack': device.get('rack', {}).get('name', 'Unknown') if device.get('rack') else 'Unknown'
            }
            
            # Extract custom fields
            custom_fields = device.get('custom_fields', {})
            if custom_fields:
                # Get aggregate from custom fields
                aggregate = custom_fields.get('Aggregates')
                if aggregate:
                    device_info['aggregate'] = aggregate
                
                # Get NVLinks info
                nvlinks = custom_fields.get('NVLinks')
                if nvlinks is not None:
                    device_info['nvlinks'] = bool(nvlinks)
            
            # Extract tenant information
            tenant_data = device.get('tenant')
            if tenant_data:
                tenant_name = tenant_data.get('name', 'Unknown')
                device_info['tenant'] = tenant_name
                # Set owner group based on tenant (using same logic as netbox_operations.py)
                device_info['owner_group'] = 'Nexgen Cloud' if tenant_name == 'Chris Starkey' else 'Investors'
            
            # Extract tags for additional GPU type information
            tags = device.get('tags', [])
            gpu_type_tags = []
            for tag in tags:
                tag_name = tag.get('name', '').lower()
                if 'nvidia' in tag_name or 'gpu' in tag_name:
                    gpu_type_tags.append(tag.get('name'))
            
            if gpu_type_tags:
                device_info['gpu_tags'] = gpu_type_tags
            
            processed_devices.append(device_info)

        # Update cache with branch-aware key
        _outofstock_cache[cache_suffix] = processed_devices
        _last_cache_time[cache_suffix] = current_time
        
        print(f"✅ NetBox out-of-stock query completed: {len(processed_devices)} non-active GPU devices found")
        
        # Log summary by status
        status_counts = {}
        for device in processed_devices:
            status = device['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            status_summary = ', '.join([f"{status}: {count}" for status, count in status_counts.items()])
            print(f"📊 Status breakdown: {status_summary}")
        
        return processed_devices
        
    except Exception as e:
        print(f"❌ NetBox out-of-stock query failed: {e}")
        return []

def clear_outofstock_cache(branch=None):
    """Clear the out-of-stock devices cache

    Args:
        branch: Optional branch to clear. If None, clears all branch caches.
    """
    global _outofstock_cache, _last_cache_time

    if branch is None:
        # Clear all caches
        total_entries = sum(len(v) for v in _outofstock_cache.values())
        _outofstock_cache = {}
        _last_cache_time = {}
        print(f"🗑️ Cleared all NetBox out-of-stock caches: {total_entries} entries removed")
        return total_entries
    else:
        # Clear specific branch cache
        cache_suffix = get_cache_key_suffix(branch)
        cache_size = len(_outofstock_cache.get(cache_suffix, []))
        _outofstock_cache.pop(cache_suffix, None)
        _last_cache_time.pop(cache_suffix, None)
        print(f"🗑️ Cleared NetBox out-of-stock cache for branch {branch or 'main'}: {cache_size} entries removed")
        return cache_size

def get_outofstock_cache_stats(branch=None):
    """Get cache statistics for monitoring

    Args:
        branch: Optional branch to get stats for. If None, returns stats for all branches.
    """
    global _outofstock_cache, _last_cache_time, _cache_ttl

    current_time = time.time()

    if branch is None:
        # Return stats for all branches
        stats = {}
        for cache_suffix, devices in _outofstock_cache.items():
            last_time = _last_cache_time.get(cache_suffix, 0)
            cache_age = current_time - last_time
            branch_name = cache_suffix.replace('_branch_', '') if cache_suffix else 'main'
            stats[branch_name] = {
                'cached_devices': len(devices),
                'cache_age_seconds': round(cache_age, 1),
                'cache_ttl_seconds': _cache_ttl,
                'is_expired': cache_age > _cache_ttl,
                'last_update': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_time)) if last_time > 0 else 'Never'
            }
        return stats
    else:
        # Return stats for specific branch
        cache_suffix = get_cache_key_suffix(branch)
        last_time = _last_cache_time.get(cache_suffix, 0)
        cache_age = current_time - last_time

        return {
            'cached_devices': len(_outofstock_cache.get(cache_suffix, [])),
            'cache_age_seconds': round(cache_age, 1),
            'cache_ttl_seconds': _cache_ttl,
            'is_expired': cache_age > _cache_ttl,
            'last_update': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_time)) if last_time > 0 else 'Never'
        }