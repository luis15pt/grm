#!/usr/bin/env python3
"""Get all GPU devices from NetBox for inventory tracking"""

import requests


def main(
    netbox_api: dict,
    include_inactive: bool = True
) -> dict:
    """Get all GPU devices from NetBox DCIM

    Retrieves all devices with GPU-related tags for complete inventory tracking,
    including out-of-stock and inactive devices.

    Args:
        netbox_api: NetBox API credentials resource
        include_inactive: Include non-active devices (default: True)

    Returns:
        dict: Organized GPU devices with keys:
            - 'active_devices': dict mapping hostname to device info
            - 'non_active_gpu_devices': list of inactive GPU devices
            - 'total_devices': int
            - 'gpu_type_counts': dict of counts by GPU type
    """
    try:
        url = f"{netbox_api['base_url']}/api/dcim/devices/"
        headers = {
            'Authorization': f"Token {netbox_api['api_token']}",
            'Content-Type': 'application/json'
        }

        # Fetch all devices (paginated)
        all_devices = []
        page = 1
        params = {'limit': 1000}

        while True:
            params['offset'] = (page - 1) * 1000
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code != 200:
                raise Exception(f"NetBox API error: {response.status_code}")

            data = response.json()
            devices_batch = data['results']
            all_devices.extend(devices_batch)

            if len(devices_batch) < 1000:
                break
            page += 1

        # GPU-related identifiers
        gpu_tags = [
            'nvidia-h100-pcie', 'nvidia h100 pcie',
            'nvidia-a100-pcie', 'nvidia a100 pcie',
            'nvidia-a100-sxm', 'nvidia a100 sxm',
            'nvidia-h100-sxm', 'nvidia h100 sxm',
            'nvidia-h100-80gb-sxm5', 'nvidia h100 80gb sxm5',
            'nvidia-h200-sxm5', 'nvidia h200 sxm5',
            'nvidia-rtx-4090', 'nvidia rtx 4090',
            'nvidia l40', 'nvidia rtx a6000'
        ]
        gpu_server_roles = ['gpu servers', 'gpu-servers', 'gpu server']

        # GPU type classification
        gpu_type_mapping = {
            'nvidia h100 pcie': 'H100',
            'nvidia h100 80gb sxm5': 'H100-SXM5',
            'nvidia h100 sxm': 'H100-SXM5',
            'nvidia a100 pcie': 'A100',
            'nvidia a100 sxm': 'A100',
            'nvidia l40': 'L40',
            'nvidia rtx a6000': 'RTX-A6000',
            'nvidia h200 sxm5': 'H200-SXM5'
        }

        active_devices = {}
        non_active_gpu_devices = []
        gpu_type_counts = {}

        for device in all_devices:
            device_name = device.get('name', '')
            device_status = device.get('status', {}).get('value', '')
            device_role = device.get('device_role', {}).get('name', '').lower() if device.get('device_role') else ''
            device_tags = [tag.get('name', '').lower() for tag in device.get('tags', [])]

            # Check if device is GPU-related
            is_gpu = any(tag in gpu_tags for tag in device_tags) or any(role in device_role for role in gpu_server_roles)

            if is_gpu:
                # Determine GPU type
                gpu_type = 'Unknown'
                for tag in device_tags:
                    if tag in gpu_type_mapping:
                        gpu_type = gpu_type_mapping[tag]
                        break

                tenant_data = device.get('tenant', {})
                tenant_name = tenant_data.get('name', 'Unknown') if tenant_data else 'Unknown'
                owner_group = 'Nexgen Cloud' if tenant_name == 'Chris Starkey' else 'Investors'

                custom_fields = device.get('custom_fields', {})
                nvlinks = custom_fields.get('NVLinks', False) or False

                device_info = {
                    'name': device_name,
                    'status': device_status,
                    'gpu_type': gpu_type,
                    'tenant': tenant_name,
                    'owner_group': owner_group,
                    'nvlinks': nvlinks,
                    'netbox_device_id': device.get('id'),
                    'netbox_url': device.get('display_url') or device.get('url')
                }

                # Count GPU types
                gpu_type_counts[gpu_type] = gpu_type_counts.get(gpu_type, 0) + 1

                if device_status == 'active':
                    active_devices[device_name] = device_info
                elif include_inactive:
                    non_active_gpu_devices.append(device_info)

        return {
            'active_devices': active_devices,
            'non_active_gpu_devices': non_active_gpu_devices,
            'total_devices': len(all_devices),
            'gpu_type_counts': gpu_type_counts,
            'active_count': len(active_devices),
            'inactive_count': len(non_active_gpu_devices)
        }

    except Exception as e:
        raise Exception(f"Error fetching GPU devices from NetBox: {str(e)}")
