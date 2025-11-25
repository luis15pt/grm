#!/usr/bin/env python3
"""Add a host to an OpenStack aggregate"""

import openstack
import subprocess


def main(
    openstack_connection: dict,
    hostname: str,
    aggregate_name: str,
    dry_run: bool = False
) -> dict:
    """Add a host to a specific aggregate

    Uses OpenStack CLI for compatibility with existing infrastructure.

    Args:
        openstack_connection: OpenStack credentials resource
        hostname: Hostname to add (e.g., 'gpu-host-001')
        aggregate_name: Target aggregate name (e.g., 'H100-n3', 'A100-n3-spot')
        dry_run: If True, validate but don't execute

    Returns:
        dict: Result with keys 'success', 'message', 'hostname', 'aggregate'
    """
    if dry_run:
        return {
            'success': True,
            'message': f'DRY RUN: Would add {hostname} to aggregate {aggregate_name}',
            'hostname': hostname,
            'aggregate': aggregate_name,
            'dry_run': True
        }

    try:
        # Build OpenStack CLI command
        # Set environment variables for authentication
        import os
        env = os.environ.copy()
        env['OS_AUTH_URL'] = openstack_connection['auth_url']
        env['OS_USERNAME'] = openstack_connection['username']
        env['OS_PASSWORD'] = openstack_connection['password']
        env['OS_PROJECT_NAME'] = openstack_connection['project_name']
        env['OS_USER_DOMAIN_NAME'] = openstack_connection.get('user_domain_name', 'Default')
        env['OS_PROJECT_DOMAIN_NAME'] = openstack_connection.get('project_domain_name', 'Default')
        env['OS_REGION_NAME'] = openstack_connection.get('region_name', 'RegionOne')
        env['OS_INTERFACE'] = openstack_connection.get('interface', 'public')
        env['OS_IDENTITY_API_VERSION'] = openstack_connection.get('identity_api_version', '3')

        command = f"openstack aggregate add host {aggregate_name} {hostname}"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )

        if result.returncode == 0:
            return {
                'success': True,
                'message': f'Successfully added {hostname} to aggregate {aggregate_name}',
                'hostname': hostname,
                'aggregate': aggregate_name,
                'stdout': result.stdout.strip()
            }
        else:
            raise Exception(f"OpenStack CLI failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        raise Exception(f"Command timed out after 30 seconds")
    except Exception as e:
        raise Exception(f"Error adding host to aggregate: {str(e)}")
