#!/usr/bin/env python3
"""Find which aggregate a host currently belongs to"""

import openstack


def main(
    openstack_connection: dict,
    hostname: str
) -> dict:
    """Find the current aggregate for a specific host

    Scans all aggregates to find which one contains the hostname.

    Args:
        openstack_connection: OpenStack credentials resource
        hostname: Hostname to search for (e.g., 'gpu-host-001')

    Returns:
        dict: Result with keys 'hostname', 'aggregate', 'found'
            Returns None for 'aggregate' if host not found in any aggregate
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
            region_name=openstack_connection.get('region_name', 'RegionOne')
        )

        # Scan all aggregates for the hostname (early termination)
        for agg in conn.compute.aggregates():
            if hostname in (agg.hosts or []):
                return {
                    'hostname': hostname,
                    'aggregate': agg.name,
                    'found': True
                }

        return {
            'hostname': hostname,
            'aggregate': None,
            'found': False
        }

    except Exception as e:
        raise Exception(f"Error finding aggregate for hostname {hostname}: {str(e)}")
