#!/usr/bin/env python3
"""
Centralized NetBox utilities for header construction and branch management.
Supports the NetBox Branching plugin for querying data from different branches.
"""

import os
import requests

# NetBox configuration
NETBOX_URL = os.getenv('NETBOX_URL')
NETBOX_API_KEY = os.getenv('NETBOX_API_KEY')

# Global default branch (None = main/production)
_global_default_branch = None


def set_global_default_branch(branch_schema_id=None):
    """
    Set the global default branch for all NetBox API calls.

    Args:
        branch_schema_id: 8-char alphanumeric branch schema ID, or None for main branch
    """
    global _global_default_branch
    _global_default_branch = branch_schema_id
    print(f"🌿 NetBox global default branch set to: {branch_schema_id or 'Main (Production)'}")


def get_global_default_branch():
    """
    Get the current global default branch.

    Returns:
        Branch schema ID or None for main branch
    """
    return _global_default_branch


def build_netbox_headers(branch_override=None):
    """
    Build NetBox API headers with optional branch header.

    Priority: branch_override > global_default > None (main)

    Args:
        branch_override: Specific branch to use, overrides global default

    Returns:
        dict: Headers for NetBox API requests
    """
    headers = {
        'Authorization': f'Token {NETBOX_API_KEY}',
        'Content-Type': 'application/json'
    }

    # Determine which branch to use (priority: override > global default)
    branch = branch_override if branch_override is not None else _global_default_branch

    if branch:
        headers['X-NetBox-Branch'] = branch

    return headers


def get_cache_key_suffix(branch=None):
    """
    Get a cache key suffix for branch-aware caching.

    Args:
        branch: Branch schema ID, or None to use global default

    Returns:
        str: Cache key suffix (empty string for main branch, "_branch_<id>" otherwise)
    """
    # Use provided branch or fall back to global default
    effective_branch = branch if branch is not None else _global_default_branch

    if effective_branch:
        return f"_branch_{effective_branch}"
    return ""


def list_available_branches():
    """
    List all available NetBox branches from the branching plugin.

    Returns:
        list: List of branch objects with id, name, schema_id, status, etc.
    """
    if not NETBOX_URL or not NETBOX_API_KEY:
        return []

    try:
        # Branch CRUD operations don't need the X-NetBox-Branch header
        headers = {
            'Authorization': f'Token {NETBOX_API_KEY}',
            'Content-Type': 'application/json'
        }

        url = f"{NETBOX_URL}/api/plugins/branching/branches/"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            branches = data.get('results', [])

            # Format branch data for API response
            formatted_branches = []
            for branch in branches:
                formatted_branches.append({
                    'id': branch.get('id'),
                    'name': branch.get('name'),
                    'schema_id': branch.get('schema_id'),  # 8-char ID used in header
                    'status': branch.get('status', {}).get('value', 'unknown') if isinstance(branch.get('status'), dict) else branch.get('status', 'unknown'),
                    'status_label': branch.get('status', {}).get('label', 'Unknown') if isinstance(branch.get('status'), dict) else branch.get('status', 'Unknown'),
                    'description': branch.get('description', ''),
                    'created': branch.get('created'),
                    'last_updated': branch.get('last_updated'),
                    'owner': branch.get('owner', {}).get('username') if branch.get('owner') else None
                })

            return formatted_branches
        elif response.status_code == 404:
            # Branching plugin not installed
            print("⚠️ NetBox branching plugin not installed or endpoint not available")
            return []
        else:
            print(f"❌ Failed to list NetBox branches: HTTP {response.status_code}")
            return []

    except requests.exceptions.Timeout:
        print("❌ Timeout while listing NetBox branches")
        return []
    except Exception as e:
        print(f"❌ Error listing NetBox branches: {e}")
        return []


def validate_branch(schema_id):
    """
    Validate that a branch schema ID exists and is accessible.

    Args:
        schema_id: 8-char alphanumeric branch schema ID

    Returns:
        dict: Branch info if valid, None otherwise
    """
    if not schema_id:
        return {'valid': True, 'name': 'Main (Production)', 'schema_id': None}

    branches = list_available_branches()
    for branch in branches:
        if branch.get('schema_id') == schema_id:
            return {'valid': True, **branch}

    return None


def is_branching_available():
    """
    Check if the NetBox branching plugin is available.

    Returns:
        bool: True if branching plugin is installed and accessible
    """
    if not NETBOX_URL or not NETBOX_API_KEY:
        return False

    try:
        headers = {
            'Authorization': f'Token {NETBOX_API_KEY}',
            'Content-Type': 'application/json'
        }

        url = f"{NETBOX_URL}/api/plugins/branching/branches/"
        response = requests.get(url, headers=headers, timeout=5)

        return response.status_code == 200

    except Exception:
        return False


def get_branch_info():
    """
    Get information about the current branch configuration.

    Returns:
        dict: Current branch configuration info
    """
    return {
        'global_default_branch': _global_default_branch,
        'global_default_name': 'Main (Production)' if not _global_default_branch else None,
        'branching_available': is_branching_available()
    }
