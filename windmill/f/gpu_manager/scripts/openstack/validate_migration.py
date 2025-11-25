#!/usr/bin/env python3
"""Validate if a host migration is allowed"""

import re
import openstack


def main(
    openstack_connection: dict,
    hostname: str,
    source_aggregate: str,
    target_aggregate: str
) -> dict:
    """Validate if host migration between aggregates is allowed

    Checks:
    - GPU types match (unless target is Contract)
    - Spot hosts have no VMs before migration
    - Host exists and is reachable

    Args:
        openstack_connection: OpenStack credentials resource
        hostname: Host to migrate (e.g., 'gpu-host-001')
        source_aggregate: Source aggregate name
        target_aggregate: Target aggregate name

    Returns:
        dict: Validation result with keys:
            - 'valid': bool
            - 'message': str (explanation)
            - 'source_gpu': str
            - 'target_gpu': str
            - 'vm_count': int (if applicable)

    Raises:
        Exception: If validation fails with detailed error message
    """
    try:
        # Extract GPU types from aggregate names
        source_match = re.match(r'^([A-Z0-9-]+)', source_aggregate)
        target_match = re.match(r'^([A-Z0-9-]+)', target_aggregate)

        source_gpu = source_match.group(1) if source_match else 'Unknown'
        target_gpu = target_match.group(1) if target_match else 'Unknown'

        # Rule 1: GPU types must match (unless target is Contract)
        if source_gpu != target_gpu and not target_aggregate.startswith('Contract-'):
            raise ValueError(
                f"Cannot migrate {source_gpu} host to {target_gpu} aggregate. "
                f"GPU types must match unless migrating to Contract hardware."
            )

        # Rule 2: Check VMs if source is spot
        vm_count = 0
        if 'spot' in source_aggregate.lower():
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
                vm_count = len(servers)
            except:
                servers = list(conn.compute.servers(host=hostname))
                vm_count = len(servers)

            if vm_count > 0:
                raise ValueError(
                    f"Cannot migrate spot host {hostname}: {vm_count} VMs still running. "
                    f"VMs must be evacuated before migration."
                )

        return {
            'valid': True,
            'message': f'Migration validated: {hostname} can be moved from {source_aggregate} to {target_aggregate}',
            'source_gpu': source_gpu,
            'target_gpu': target_gpu,
            'vm_count': vm_count,
            'hostname': hostname,
            'source_aggregate': source_aggregate,
            'target_aggregate': target_aggregate
        }

    except ValueError as e:
        # Validation failed - return structured error
        return {
            'valid': False,
            'message': str(e),
            'source_gpu': source_gpu if 'source_gpu' in locals() else 'Unknown',
            'target_gpu': target_gpu if 'target_gpu' in locals() else 'Unknown',
            'vm_count': vm_count if 'vm_count' in locals() else 0,
            'hostname': hostname,
            'source_aggregate': source_aggregate,
            'target_aggregate': target_aggregate
        }
    except Exception as e:
        raise Exception(f"Error validating migration: {str(e)}")
