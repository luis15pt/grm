#!/usr/bin/env python3
"""Deploy a VM on Hyperstack (RunPod platform)"""

import requests
import json


def main(
    hyperstack_api: dict,
    hostname: str,
    flavor_id: str,
    image_id: str = None,
    network_id: str = None,
    assign_floating_ip: bool = True
) -> dict:
    """Deploy a new VM on Hyperstack/RunPod platform

    Args:
        hyperstack_api: Hyperstack API credentials resource
        hostname: Name for the new VM
        flavor_id: Flavor/instance type ID (e.g., 'n3-H100x8')
        image_id: Image ID (defaults to hyperstack_api.default_image_id)
        network_id: Network ID (defaults to hyperstack_api.default_network_id)
        assign_floating_ip: Whether to assign floating IP (default: True)

    Returns:
        dict: Deployment result with keys:
            - 'success': bool
            - 'vm_id': str (VM identifier)
            - 'vm_name': str
            - 'status': str
            - 'ip_address': str (if floating IP assigned)
    """
    try:
        base_url = hyperstack_api.get('base_url', 'https://api.hyperstack.cloud/v1')
        api_key = hyperstack_api['api_key']

        # Use defaults from resource if not provided
        if not image_id:
            image_id = hyperstack_api.get('default_image_id', 'ubuntu-22.04')
        if not network_id:
            network_id = hyperstack_api.get('default_network_id')

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # Prepare VM creation payload
        payload = {
            'name': hostname,
            'flavor': flavor_id,
            'image': image_id,
            'assign_floating_ip': assign_floating_ip
        }

        if network_id:
            payload['network'] = network_id

        # Create VM
        response = requests.post(
            f'{base_url}/virtual-machines',
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code not in [200, 201, 202]:
            raise Exception(f"Hyperstack API error {response.status_code}: {response.text}")

        result = response.json()
        vm_data = result.get('virtual_machine', result)

        return {
            'success': True,
            'vm_id': vm_data.get('id'),
            'vm_name': vm_data.get('name', hostname),
            'status': vm_data.get('status', 'creating'),
            'flavor': flavor_id,
            'image': image_id,
            'ip_address': vm_data.get('floating_ip', {}).get('address') if assign_floating_ip else None,
            'created_at': vm_data.get('created_at')
        }

    except Exception as e:
        raise Exception(f"Error deploying VM on Hyperstack: {str(e)}")
