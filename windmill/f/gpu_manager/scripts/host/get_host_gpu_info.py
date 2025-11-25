#!/usr/bin/env python3
"""Get GPU usage information for a host"""

import re
import openstack


def extract_gpu_count_from_flavor(flavor_name):
    """Extract GPU count from flavor name like 'n3-H100x8'"""
    if not flavor_name or flavor_name == 'N/A':
        return 0
    match = re.search(r'x(\d+)', flavor_name)
    return int(match.group(1)) if match else 0


def main(
    openstack_connection: dict,
    hostname: str
) -> dict:
    """Get GPU usage information for a specific compute host

    Calculates total GPU usage by summing GPU counts from all VM flavors.

    Args:
        openstack_connection: OpenStack credentials resource
        hostname: Compute host to query (e.g., 'gpu-host-001')

    Returns:
        dict: GPU usage information with keys:
            - 'gpu_used': int (total GPUs in use)
            - 'gpu_capacity': int (total GPU capacity, usually 8 or 10)
            - 'vm_count': int (number of VMs)
            - 'gpu_usage_ratio': str (e.g., '6/8')
    """
    try:
        conn = openstack.connect(
            auth_url=openstack_connection['auth_url'],
            username=openstack_connection['username'],
            password=openstack_connection['password'],
            project_name=openstack_connection['project_name'],
            user_domain_name=openstack_connection.get('user_domain_name', 'Default'),
            project_domain_name=openstack_connection.get('project_domain_name', 'Default'),
            region_name=openstack_connection.get('region_name', 'RegionOne')
        )

        try:
            servers = list(conn.compute.servers(host=hostname, all_projects=True))
        except:
            servers = list(conn.compute.servers(host=hostname))

        # Calculate total GPU usage from VM flavors
        total_gpu_used = 0
        for server in servers:
            flavor_info = getattr(server, 'flavor', {})
            flavor_name = flavor_info.get('original_name', 'N/A') if isinstance(flavor_info, dict) else 'N/A'
            gpu_count = extract_gpu_count_from_flavor(flavor_name)
            total_gpu_used += gpu_count

        # Determine GPU capacity (10 for A4000, 8 for others)
        host_gpu_capacity = 10 if 'A4000' in hostname else 8

        return {
            'gpu_used': total_gpu_used,
            'gpu_capacity': host_gpu_capacity,
            'vm_count': len(servers),
            'gpu_usage_ratio': f"{total_gpu_used}/{host_gpu_capacity}"
        }

    except Exception as e:
        # Return default on error
        return {
            'gpu_used': 0,
            'gpu_capacity': 8,
            'vm_count': 0,
            'gpu_usage_ratio': "0/8"
        }
