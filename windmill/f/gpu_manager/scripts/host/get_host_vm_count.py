#!/usr/bin/env python3
"""Get VM count for a specific host"""

import openstack


def main(
    openstack_connection: dict,
    hostname: str
) -> int:
    """Get count of VMs running on a specific compute host

    Faster than get_host_vms when you only need the count.

    Args:
        openstack_connection: OpenStack credentials resource
        hostname: Compute host to query (e.g., 'gpu-host-001')

    Returns:
        int: Number of VMs running on the host
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
            return len(servers)
        except:
            servers = list(conn.compute.servers(host=hostname))
            return len(servers)

    except Exception as e:
        raise Exception(f"Error getting VM count for host {hostname}: {str(e)}")
