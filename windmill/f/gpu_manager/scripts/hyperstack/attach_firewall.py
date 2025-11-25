#!/usr/bin/env python3
"""Attach firewall rules to Hyperstack VM"""

import requests


def main(
    hyperstack_api: dict,
    vm_id: str,
    gpu_type: str = None,
    firewall_id: str = None
) -> dict:
    """Attach firewall rules to a Hyperstack VM

    Args:
        hyperstack_api: Hyperstack API credentials resource
        vm_id: VM identifier to attach firewall to
        gpu_type: GPU type (e.g., 'H100') - looks up firewall ID from mapping
        firewall_id: Explicit firewall ID (overrides gpu_type lookup)

    Returns:
        dict: Attachment result with keys:
            - 'success': bool
            - 'vm_id': str
            - 'firewall_id': str
            - 'message': str
    """
    try:
        base_url = hyperstack_api.get('base_url', 'https://api.hyperstack.cloud/v1')
        api_key = hyperstack_api['api_key']

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # Determine firewall ID
        if not firewall_id and gpu_type:
            firewall_map = hyperstack_api.get('firewall_id_map', {})
            firewall_id = firewall_map.get(gpu_type)
            if not firewall_id:
                raise ValueError(f"No firewall mapping found for GPU type: {gpu_type}")
        elif not firewall_id:
            raise ValueError("Either gpu_type or firewall_id must be provided")

        # Attach firewall
        payload = {
            'firewall_id': firewall_id
        }

        response = requests.post(
            f'{base_url}/virtual-machines/{vm_id}/firewall',
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code not in [200, 201, 202]:
            raise Exception(f"Hyperstack API error {response.status_code}: {response.text}")

        return {
            'success': True,
            'vm_id': vm_id,
            'firewall_id': firewall_id,
            'message': f'Firewall {firewall_id} attached to VM {vm_id}'
        }

    except Exception as e:
        raise Exception(f"Error attaching firewall: {str(e)}")
