#!/usr/bin/env python3
"""Get status of a Hyperstack VM"""

import requests


def main(
    hyperstack_api: dict,
    vm_id: str
) -> dict:
    """Get current status of a Hyperstack VM

    Args:
        hyperstack_api: Hyperstack API credentials resource
        vm_id: VM identifier to check

    Returns:
        dict: VM status information with keys:
            - 'vm_id': str
            - 'name': str
            - 'status': str (e.g., 'ACTIVE', 'BUILD', 'ERROR')
            - 'power_state': str
            - 'ip_address': str (if available)
            - 'flavor': str
            - 'created_at': str
    """
    try:
        base_url = hyperstack_api.get('base_url', 'https://api.hyperstack.cloud/v1')
        api_key = hyperstack_api['api_key']

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # Get VM details
        response = requests.get(
            f'{base_url}/virtual-machines/{vm_id}',
            headers=headers,
            timeout=30
        )

        if response.status_code == 404:
            raise ValueError(f"VM {vm_id} not found")
        elif response.status_code != 200:
            raise Exception(f"Hyperstack API error {response.status_code}: {response.text}")

        result = response.json()
        vm_data = result.get('virtual_machine', result)

        return {
            'vm_id': vm_data.get('id', vm_id),
            'name': vm_data.get('name'),
            'status': vm_data.get('status'),
            'power_state': vm_data.get('power_state'),
            'ip_address': vm_data.get('floating_ip', {}).get('address'),
            'flavor': vm_data.get('flavor', {}).get('name') if isinstance(vm_data.get('flavor'), dict) else vm_data.get('flavor'),
            'created_at': vm_data.get('created_at'),
            'updated_at': vm_data.get('updated_at')
        }

    except Exception as e:
        raise Exception(f"Error getting VM status: {str(e)}")
