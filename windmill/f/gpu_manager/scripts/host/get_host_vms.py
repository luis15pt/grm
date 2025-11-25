#!/usr/bin/env python3
"""Get VMs running on a specific host"""

import openstack


def main(
    openstack_connection: dict,
    hostname: str
) -> list:
    """Get list of VMs running on a specific compute host

    Returns detailed information about each VM including name, status,
    flavor, image, project, and user.

    Args:
        openstack_connection: OpenStack credentials resource
        hostname: Compute host to query (e.g., 'gpu-host-001')

    Returns:
        list: List of VM dictionaries with keys:
            - Name, Status, ID, Created, Updated, Flavor, Image, Project, User
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

        vm_list = []
        for server in servers:
            flavor_info = getattr(server, 'flavor', {})
            image_info = getattr(server, 'image', {})

            vm_info = {
                'Name': server.name,
                'Status': server.status,
                'ID': server.id,
                'Created': getattr(server, 'created', 'N/A'),
                'Updated': getattr(server, 'updated', 'N/A'),
                'Flavor': flavor_info.get('original_name', 'N/A') if isinstance(flavor_info, dict) else 'N/A',
                'Image': image_info.get('name', 'N/A') if isinstance(image_info, dict) else 'N/A',
                'Project': getattr(server, 'project_id', 'N/A'),
                'User': getattr(server, 'user_id', 'N/A')
            }
            vm_list.append(vm_info)

        return vm_list

    except Exception as e:
        raise Exception(f"Error getting VMs for host {hostname}: {str(e)}")
