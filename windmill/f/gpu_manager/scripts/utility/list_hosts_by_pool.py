#!/usr/bin/env python3
"""List all hosts organized by GPU type and pool"""

import wmill


def main(
    openstack_connection: dict,
    netbox_api: dict,
    gpu_type: str = None,
    pool_type: str = None,
    owner_filter: str = None
) -> dict:
    """List hosts organized by GPU type and pool with optional filtering

    Args:
        openstack_connection: OpenStack credentials resource
        netbox_api: NetBox API credentials resource
        gpu_type: Filter by GPU type (e.g., 'H100', 'A100') - optional
        pool_type: Filter by pool (e.g., 'spot', 'ondemand', 'runpod', 'contract') - optional
        owner_filter: Filter by owner group ('Investors' or 'Nexgen Cloud') - optional

    Returns:
        dict: Hosts organized by GPU type and pool:
            {
                'H100': {
                    'ondemand': [list of hosts],
                    'spot': [list of hosts],
                    'runpod': [list of hosts]
                },
                'A100': {...},
                'summary': {total counts}
            }
    """
    try:
        # Get all data
        all_data = wmill.run_script_sync(
            path="f/gpu_manager/scripts/data/get_parallel_data",
            args={
                "openstack_connection": openstack_connection,
                "netbox_api": netbox_api
            }
        )

        result = {}
        summary = {
            'total_hosts': 0,
            'by_gpu_type': {},
            'by_pool_type': {},
            'by_owner': {}
        }

        # Process each GPU type
        for gt, gpu_data in all_data.items():
            if gt == 'outofstock':
                continue

            # Skip if GPU type filter doesn't match
            if gpu_type and gt != gpu_type:
                continue

            if gt not in result:
                result[gt] = {
                    'ondemand': [],
                    'spot': [],
                    'runpod': [],
                    'contract': []
                }

            # Process hosts
            for host in gpu_data.get('hosts', []):
                pool = host.get('pool_type', 'unknown')

                # Apply filters
                if pool_type and pool != pool_type:
                    continue

                owner = host.get('tenant_info', {}).get('owner_group', 'Unknown')
                if owner_filter and owner != owner_filter:
                    continue

                # Add to result
                if pool in result[gt]:
                    result[gt][pool].append(host)

                # Update summary
                summary['total_hosts'] += 1
                summary['by_gpu_type'][gt] = summary['by_gpu_type'].get(gt, 0) + 1
                summary['by_pool_type'][pool] = summary['by_pool_type'].get(pool, 0) + 1
                summary['by_owner'][owner] = summary['by_owner'].get(owner, 0) + 1

        result['summary'] = summary

        return result

    except Exception as e:
        raise Exception(f"Error listing hosts: {str(e)}")
