#!/usr/bin/env python3
"""Get hosts in an OpenStack aggregate"""

import openstack


def main(
    openstack_connection: dict,
    aggregate_name: str
) -> list:
    """Get list of hosts in a specific aggregate

    Args:
        openstack_connection: OpenStack credentials resource
        aggregate_name: Name of the aggregate (e.g., 'H100-n3', 'A100-n3-spot')

    Returns:
        list: List of hostname strings in the aggregate
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

        # Find aggregate by name
        aggregates = list(conn.compute.aggregates())
        for agg in aggregates:
            if agg.name == aggregate_name:
                return agg.hosts or []

        raise ValueError(f"Aggregate '{aggregate_name}' not found")

    except Exception as e:
        raise Exception(f"Error getting hosts for aggregate {aggregate_name}: {str(e)}")
