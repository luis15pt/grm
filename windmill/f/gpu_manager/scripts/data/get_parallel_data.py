#!/usr/bin/env python3
"""Collect GPU data from all sources in parallel (master data collection script)"""

import re
from concurrent.futures import ThreadPoolExecutor
import wmill


def main(
    openstack_connection: dict,
    netbox_api: dict
) -> dict:
    """Collect all GPU infrastructure data using parallel agents

    This is the master data collection function that:
    1. Discovers GPU aggregates from OpenStack
    2. Gets all devices from NetBox
    3. Collects host/VM/GPU information
    4. Organizes data by GPU type and pool (on-demand, spot, runpod, contract)

    Designed to replace the complex parallel_agents.py module.
    Windmill's native caching and job queue handle optimization.

    Args:
        openstack_connection: OpenStack credentials resource
        netbox_api: NetBox API credentials resource

    Returns:
        dict: Complete GPU infrastructure data organized by GPU type:
            {
                'H100': {
                    'config': {'ondemand_variants': [...], 'spot': '...', 'runpod': '...'},
                    'hosts': [{hostname, aggregate, tenant_info, vm_count, gpu_info}, ...],
                    'summary': {total_hosts, total_vms, total_gpu_used, total_gpu_capacity}
                },
                'A100': {...},
                'outofstock': {...},  # Non-active GPU devices from NetBox
                ...
            }
    """
    try:
        # Step 1: Discover GPU aggregates using existing script
        aggregates_data = wmill.run_script_sync(
            path="f/gpu_manager/scripts/openstack/discover_gpu_aggregates",
            args={"openstack_connection": openstack_connection}
        )

        # Step 2: Get all GPU devices from NetBox
        netbox_devices_data = wmill.run_script_sync(
            path="f/gpu_manager/scripts/netbox/get_all_gpu_devices",
            args={"netbox_api": netbox_api, "include_inactive": True}
        )

        # Step 3: For each GPU type, get hosts and their details
        organized_data = {}

        for gpu_type, config in aggregates_data.items():
            # Collect all hosts for this GPU type
            all_hosts = []

            # Get hosts from each pool type
            for variant in config.get('ondemand_variants', []):
                hosts = wmill.run_script_sync(
                    path="f/gpu_manager/scripts/openstack/get_aggregate_hosts",
                    args={
                        "openstack_connection": openstack_connection,
                        "aggregate_name": variant['aggregate']
                    }
                )
                for hostname in hosts:
                    all_hosts.append({
                        'hostname': hostname,
                        'aggregate': variant['aggregate'],
                        'pool_type': 'ondemand',
                        'variant': variant['variant']
                    })

            # Spot hosts
            if config.get('spot'):
                hosts = wmill.run_script_sync(
                    path="f/gpu_manager/scripts/openstack/get_aggregate_hosts",
                    args={
                        "openstack_connection": openstack_connection,
                        "aggregate_name": config['spot']
                    }
                )
                for hostname in hosts:
                    all_hosts.append({
                        'hostname': hostname,
                        'aggregate': config['spot'],
                        'pool_type': 'spot'
                    })

            # RunPod hosts
            if config.get('runpod'):
                hosts = wmill.run_script_sync(
                    path="f/gpu_manager/scripts/openstack/get_aggregate_hosts",
                    args={
                        "openstack_connection": openstack_connection,
                        "aggregate_name": config['runpod']
                    }
                )
                for hostname in hosts:
                    all_hosts.append({
                        'hostname': hostname,
                        'aggregate': config['runpod'],
                        'pool_type': 'runpod'
                    })

            # Contract hosts
            for contract in config.get('contracts', []):
                hosts = wmill.run_script_sync(
                    path="f/gpu_manager/scripts/openstack/get_aggregate_hosts",
                    args={
                        "openstack_connection": openstack_connection,
                        "aggregate_name": contract['aggregate']
                    }
                )
                for hostname in hosts:
                    all_hosts.append({
                        'hostname': hostname,
                        'aggregate': contract['aggregate'],
                        'pool_type': 'contract',
                        'contract_name': contract['name']
                    })

            # Step 4: Enrich host data with NetBox tenant info and VM/GPU counts
            # Get tenant info for all hostnames in bulk
            hostnames = [h['hostname'] for h in all_hosts]

            if hostnames:
                tenant_data = wmill.run_script_sync(
                    path="f/gpu_manager/scripts/netbox/get_bulk_device_tenants",
                    args={
                        "netbox_api": netbox_api,
                        "hostnames": hostnames
                    }
                )

                # Enrich each host with tenant and compute info
                for host in all_hosts:
                    hostname = host['hostname']
                    host['tenant_info'] = tenant_data.get(hostname, {
                        'tenant': 'Unknown',
                        'owner_group': 'Investors',
                        'nvlinks': False
                    })

                    # Get VM count and GPU info (these are lightweight queries)
                    vm_count = wmill.run_script_sync(
                        path="f/gpu_manager/scripts/host/get_host_vm_count",
                        args={
                            "openstack_connection": openstack_connection,
                            "hostname": hostname
                        }
                    )
                    host['vm_count'] = vm_count

                    gpu_info = wmill.run_script_sync(
                        path="f/gpu_manager/scripts/host/get_host_gpu_info",
                        args={
                            "openstack_connection": openstack_connection,
                            "hostname": hostname
                        }
                    )
                    host['gpu_info'] = gpu_info

            # Calculate summary statistics
            total_hosts = len(all_hosts)
            total_vms = sum(h.get('vm_count', 0) for h in all_hosts)
            total_gpu_used = sum(h.get('gpu_info', {}).get('gpu_used', 0) for h in all_hosts)
            total_gpu_capacity = sum(h.get('gpu_info', {}).get('gpu_capacity', 8) for h in all_hosts)

            organized_data[gpu_type] = {
                'config': config,
                'hosts': all_hosts,
                'device_count': total_hosts,
                'summary': {
                    'total_hosts': total_hosts,
                    'total_vms': total_vms,
                    'total_gpu_used': total_gpu_used,
                    'total_gpu_capacity': total_gpu_capacity,
                    'gpu_usage_ratio': f"{total_gpu_used}/{total_gpu_capacity}"
                }
            }

        # Step 5: Add out-of-stock devices
        organized_data['outofstock'] = {
            'hosts': netbox_devices_data.get('non_active_gpu_devices', []),
            'device_count': len(netbox_devices_data.get('non_active_gpu_devices', [])),
            'name': 'Out of Stock'
        }

        return organized_data

    except Exception as e:
        raise Exception(f"Error collecting parallel data: {str(e)}")
