"""
Variant Column Settings - Persisted configuration for which aggregate
suffixes should be displayed as separate on-demand variant columns.

Settings are stored in data/variant_settings.json and cached in memory.
Thread-safe for concurrent Flask request handling.
"""

import json
import os
import threading
from datetime import datetime

_settings_lock = threading.Lock()
_settings_cache = None
_settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'variant_settings.json')

DEFAULT_SPLIT_SUFFIXES = ['NVLink', 'Drain', 'Lifeboat']


def _ensure_data_dir():
    data_dir = os.path.dirname(_settings_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)


def get_variant_settings():
    """Return current variant settings, loading from disk or using defaults."""
    global _settings_cache
    with _settings_lock:
        if _settings_cache is not None:
            return _settings_cache
        if os.path.exists(_settings_path):
            try:
                with open(_settings_path, 'r') as f:
                    _settings_cache = json.load(f)
                return _settings_cache
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ Failed to load variant settings: {e}")
        _settings_cache = {
            'split_suffixes': list(DEFAULT_SPLIT_SUFFIXES),
            'updated_at': None
        }
        return _settings_cache


def save_variant_settings(split_suffixes):
    """Save variant settings to disk and update cache."""
    global _settings_cache
    _ensure_data_dir()
    settings = {
        'split_suffixes': split_suffixes,
        'updated_at': datetime.utcnow().isoformat() + 'Z'
    }
    with _settings_lock:
        with open(_settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        _settings_cache = settings
    return settings


def get_split_suffixes():
    """Return just the list of split suffixes."""
    return get_variant_settings().get('split_suffixes', DEFAULT_SPLIT_SUFFIXES)


def clear_settings_cache():
    """Clear the in-memory cache to force reload from disk."""
    global _settings_cache
    with _settings_lock:
        _settings_cache = None
