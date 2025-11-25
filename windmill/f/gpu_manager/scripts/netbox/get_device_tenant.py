#!/usr/bin/env python3
"""Get tenant information from NetBox for a device"""

import requests


def main(
    netbox_api: dict,
    hostname: str
) -> dict:
    """Get tenant and owner information for a specific device

    Queries NetBox DCIM API to retrieve tenant assignment and owner group.
    Owner groups: 'Nexgen Cloud' (Chris Starkey tenant) or 'Investors' (all others).

    Args:
        netbox_api: NetBox API credentials resource
        hostname: Device hostname to lookup

    Returns:
        dict: Device tenant information with keys:
            - 'tenant': str (tenant name or 'Unknown')
            - 'owner_group': str ('Nexgen Cloud' or 'Investors')
            - 'nvlinks': bool (NVLinks custom field)
            - 'netbox_device_id': int (device ID)
            - 'netbox_url': str (device URL)
    """
    try:
        url = f"{netbox_api['base_url']}/api/dcim/devices/"
        headers = {
            'Authorization': f"Token {netbox_api['api_token']}",
            'Content-Type': 'application/json'
        }

        # Search for device by name
        params = {'name': hostname, 'limit': 1}
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            raise Exception(f"NetBox API error: {response.status_code}")

        data = response.json()
        results = data.get('results', [])

        if not results:
            # Device not found - return default
            return {
                'tenant': 'Unknown',
                'owner_group': 'Investors',
                'nvlinks': False,
                'netbox_device_id': None,
                'netbox_url': None
            }

        device = results[0]
        tenant_data = device.get('tenant', {})
        tenant_name = tenant_data.get('name', 'Unknown') if tenant_data else 'Unknown'

        # Determine owner group
        owner_group = 'Nexgen Cloud' if tenant_name == 'Chris Starkey' else 'Investors'

        # Get NVLinks custom field
        custom_fields = device.get('custom_fields', {})
        nvlinks = custom_fields.get('NVLinks', False)
        if nvlinks is None:
            nvlinks = False

        return {
            'tenant': tenant_name,
            'owner_group': owner_group,
            'nvlinks': nvlinks,
            'netbox_device_id': device.get('id'),
            'netbox_url': device.get('display_url') or device.get('url')
        }

    except Exception as e:
        raise Exception(f"Error looking up device {hostname} in NetBox: {str(e)}")
