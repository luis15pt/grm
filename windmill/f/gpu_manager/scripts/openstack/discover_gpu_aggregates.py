#!/usr/bin/env python3
"""Discover GPU aggregates from OpenStack with variant support"""

import re
import openstack


def main(
    openstack_connection: dict,
    force_refresh: bool = False
) -> dict:
    """Dynamically discover GPU aggregates from OpenStack

    Discovers and categorizes GPU aggregates including:
    - On-demand variants (with/without NVLink)
    - Spot instances
    - RunPod instances
    - Contract hardware

    Args:
        openstack_connection: OpenStack credentials resource
        force_refresh: Force cache refresh (Note: Windmill provides native caching)

    Returns:
        dict: GPU aggregates organized by type with structure:
            {
                'H100': {
                    'ondemand': 'H100-n3',
                    'ondemand_variants': [{'aggregate': 'H100-n3', 'variant': 'H100-n3'}, ...],
                    'spot': 'H100-n3-spot',
                    'runpod': 'H100-n3-runpod',
                    'contracts': [{'aggregate': 'Contract-AI2C-24xH100', 'name': '...'}]
                },
                ...
            }
    """
    try:
        # Connect to OpenStack
        conn = openstack.connect(
            auth_url=openstack_connection['auth_url'],
            username=openstack_connection['username'],
            password=openstack_connection['password'],
            project_name=openstack_connection['project_name'],
            user_domain_name=openstack_connection.get('user_domain_name', 'Default'),
            project_domain_name=openstack_connection.get('project_domain_name', 'Default'),
            region_name=openstack_connection.get('region_name', 'RegionOne'),
            interface=openstack_connection.get('interface', 'public'),
            identity_api_version=openstack_connection.get('identity_api_version', '3')
        )

        aggregates = list(conn.compute.aggregates())
        gpu_aggregates = {}

        for agg in aggregates:
            # Pattern 1: Regular GPU aggregates: GPU-TYPE-n3[-suffix]
            match = re.match(r'^([A-Z0-9-]+)-n3(-NVLink)?(-spot|-runpod)?$', agg.name)
            if match:
                gpu_type = match.group(1)
                nvlink_suffix = match.group(2)  # -NVLink or None
                pool_suffix = match.group(3)   # -spot, -runpod, or None

                if gpu_type not in gpu_aggregates:
                    gpu_aggregates[gpu_type] = {
                        'ondemand_variants': [],
                        'spot': None,
                        'runpod': None,
                        'contracts': []
                    }

                if pool_suffix == '-spot':
                    gpu_aggregates[gpu_type]['spot'] = agg.name
                elif pool_suffix == '-runpod':
                    gpu_aggregates[gpu_type]['runpod'] = agg.name
                else:
                    # No pool suffix = on-demand variant
                    variant_display = f"{gpu_type}-n3{nvlink_suffix or ''}"
                    gpu_aggregates[gpu_type]['ondemand_variants'].append({
                        'aggregate': agg.name,
                        'variant': variant_display
                    })

            # Pattern 2: Contract aggregates: Contract-* or contract-*
            contract_match = re.match(r'^[Cc]ontract-([^-]+)', agg.name)
            if contract_match:
                # Extract GPU type from contract aggregate name
                gpu_type = None
                for possible_gpu in ['H200-SXM5', 'H100-SXM5', 'A100', 'H100', 'RTX-A6000', 'L40', 'A4000']:
                    if possible_gpu in agg.name:
                        gpu_type = possible_gpu
                        break

                # Try patterns like 24xA100, 8xH100, etc.
                if not gpu_type:
                    suffix_match = re.search(r'\d+x([A-Z0-9-]+)', agg.name)
                    if suffix_match:
                        gpu_type = suffix_match.group(1)

                # Default fallback
                if not gpu_type:
                    gpu_type = 'A100'

                if gpu_type not in gpu_aggregates:
                    gpu_aggregates[gpu_type] = {
                        'ondemand_variants': [],
                        'spot': None,
                        'runpod': None,
                        'contracts': []
                    }

                gpu_aggregates[gpu_type]['contracts'].append({
                    'aggregate': agg.name,
                    'name': agg.name
                })

        # Convert to final format
        result = {}
        for gpu_type, data in gpu_aggregates.items():
            if data['ondemand_variants'] or data['contracts']:
                result[gpu_type] = {
                    'ondemand': data['ondemand_variants'][0]['aggregate'] if data['ondemand_variants'] else None,
                    'ondemand_variants': data['ondemand_variants'],
                    'spot': data['spot'],
                    'runpod': data['runpod'],
                    'contracts': data['contracts']
                }

        return result

    except Exception as e:
        raise Exception(f"Error discovering aggregates: {str(e)}")
