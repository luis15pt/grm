#!/usr/bin/env python3

import re
from datetime import datetime

def extract_gpu_count_from_flavor(flavor_name):
    """Extract GPU count from flavor name like 'n3-RTX-A6000x8' or 'n3-RTX-A6000x1-spot'"""
    if not flavor_name or flavor_name == 'N/A':
        return 0
    
    # Pattern to match GPU count from flavor names like n3-RTX-A6000x8, n3-RTX-A6000x1-spot
    match = re.search(r'x(\d+)', flavor_name)
    if match:
        return int(match.group(1))
    return 0

def is_spot_flavor(flavor_name):
    """Check if a flavor is a spot flavor - name ends with '-spot' like 'n3-RTX-A6000x1-spot'

    Anything we can't positively identify as spot counts as on-demand, so a host is
    never reported as ready to sell on missing or malformed flavor data.
    """
    if not flavor_name or flavor_name == 'N/A':
        return False

    return str(flavor_name).strip().lower().endswith('-spot')

class CaseInsensitiveDict(dict):
    """Dict whose string-key lookups ignore case.

    NetBox and OpenStack don't always agree on hostname casing. A plain dict
    lookup silently misses, and the host then reads as "not in any aggregate"
    with zero VMs and zero GPUs. Keys are stored normalized; original_key()
    returns the casing the source actually reported.
    """

    def __init__(self, data=None):
        super().__init__()
        self._original_keys = {}
        if data:
            for key, value in data.items():
                self[key] = value

    @staticmethod
    def _norm(key):
        return key.lower() if isinstance(key, str) else key

    def __setitem__(self, key, value):
        normalized = self._norm(key)
        self._original_keys[normalized] = key
        super().__setitem__(normalized, value)

    def __getitem__(self, key):
        return super().__getitem__(self._norm(key))

    def __contains__(self, key):
        return super().__contains__(self._norm(key))

    def get(self, key, default=None):
        return super().get(self._norm(key), default)

    def original_key(self, key, default=None):
        """Return the key as originally stored (e.g. OpenStack's own casing)"""
        return self._original_keys.get(self._norm(key), default)


class CaseInsensitiveSet(set):
    """Set of strings whose membership test ignores case.

    Original strings are preserved for iteration and display - only `in` is
    case-insensitive.
    """

    def __init__(self, iterable=None):
        super().__init__(iterable or [])
        self._normalized = {self._norm(value) for value in self}

    @staticmethod
    def _norm(value):
        return value.lower() if isinstance(value, str) else value

    def add(self, value):
        super().add(value)
        self._normalized.add(self._norm(value))

    def update(self, *others):
        for other in others:
            for value in other:
                self.add(value)

    def __contains__(self, value):
        return self._norm(value) in self._normalized


def get_gpu_type_from_aggregate(aggregate_name):
    """Extract GPU type from aggregate name like 'RTX-A6000-n3-runpod' -> 'RTX-A6000'"""
    if not aggregate_name:
        return None
    
    match = re.match(r'^([A-Z0-9-]+)-n3', aggregate_name)
    if match:
        return match.group(1)
    return None

def get_gpu_count_from_hostname(hostname):
    """Determine GPU count from hostname - A4000 hosts have 10, others have 8"""
    if 'A4000' in hostname:
        return 10
    return 8

def mask_api_key(api_key, prefix=""):
    """Mask API key for display purposes"""
    if not api_key:
        return "***_KEY"
    
    if len(api_key) <= 8:
        return "***_KEY"
    
    return f"{api_key[:4]}***{api_key[-4:]}"

# Global command log storage (will be moved here from app.py)
command_log = []

def log_command(command, result, execution_type='executed'):
    """Log command execution with timestamp and result"""
    global command_log
    
    log_entry = {
        'id': len(command_log) + 1,
        'timestamp': datetime.now().isoformat(),
        'command': command,
        'type': execution_type,
        'success': result.get('success', False),
        'stdout': result.get('stdout', ''),
        'stderr': result.get('stderr', ''),
        'returncode': result.get('returncode', -1)
    }
    
    command_log.append(log_entry)
    
    # Keep only last 100 entries
    if len(command_log) > 100:
        command_log = command_log[-100:]