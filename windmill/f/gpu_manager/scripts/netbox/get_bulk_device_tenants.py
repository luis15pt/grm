#!/usr/bin/env python3
"""Get tenant information from NetBox for multiple devices in bulk"""

import requests


def main(
    netbox_api: dict,
    hostnames: list
) -> dict:
    """Get tenant and owner information for multiple devices efficiently

    Fetches all devices from NetBox and maps tenant info to requested hostnames.
    More efficient than individual lookups.

    Args:
        netbox_api: NetBox API credentials resource
        hostnames: List of device hostnames to lookup

    Returns:
        dict: Mapping of hostname to tenant information
            {
                'hostname1': {'tenant': '...', 'owner_group': '...', 'nvlinks': bool, ...},
                'hostname2': {...},
                ...
            }
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
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                raise Exception(f"NetBox API error: {response.status_code}")

            data = response.json()
            devices_batch = data['results']
            all_devices.extend(devices_batch)

            # Stop if we got less than full page
            if len(devices_batch) < 1000:
                break
            page += 1

        # Build mapping for requested hostnames
        device_map = {}
        hostnames_set = set(hostnames)

        for device in all_devices:
            device_name = device.get('name')
            if device_name in hostnames_set:
                tenant_data = device.get('tenant', {})
                tenant_name = tenant_data.get('name', 'Unknown') if tenant_data else 'Unknown'
                owner_group = 'Nexgen Cloud' if tenant_name == 'Chris Starkey' else 'Investors'

                custom_fields = device.get('custom_fields', {})
                nvlinks = custom_fields.get('NVLinks', False)
                if nvlinks is None:
                    nvlinks = False

                device_map[device_name] = {
                    'tenant': tenant_name,
                    'owner_group': owner_group,
                    'nvlinks': nvlinks,
                    'netbox_device_id': device.get('id'),
                    'netbox_url': device.get('display_url') or device.get('url')
                }

        # Fill in defaults for devices not found
        default_result = {
            'tenant': 'Unknown',
            'owner_group': 'Investors',
            'nvlinks': False,
            'netbox_device_id': None,
            'netbox_url': None
        }

        for hostname in hostnames:
            if hostname not in device_map:
                device_map[hostname] = default_result

        return device_map

    except Exception as e:
        raise Exception(f"Error performing bulk NetBox lookup: {str(e)}")
