"""Durable representative assumptions for the main dashboard's detour switches."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

from .logistics import validate_route_settings
from resilience_logistics import default_detours


PROFILE_PATH = Path(__file__).resolve().parents[1] / 'data' / 'quick_detour_profiles.json'


def default_quick_profiles(network):
    profiles = default_detours()
    for cp, profile in profiles.items():
        # Enough shared scenario capacity for the per-route 50% assumption,
        # even when optional registered material scopes are activated later.
        route_count = sum(cp in route['via'] for route in network['logistics_routes'].values())
        profile['capacity_units'] = route_count * profile['max_fraction']
    return profiles


def validate_profiles(network, profiles):
    if not isinstance(profiles, dict) or set(profiles) != set(network['port_detours']):
        raise ValueError('보통값의 항만 목록이 현재 모델과 다릅니다.')
    if any(not isinstance(profile, dict) for profile in profiles.values()):
        raise ValueError('항만별 보통값 형식이 잘못되었습니다.')
    validate_route_settings(dict(network, port_detours=profiles))
    if any(profile['enabled'] is not False for profile in profiles.values()):
        raise ValueError('보통값 파일에는 우회 사용 상태를 저장하지 않습니다.')
    return profiles


def read_profiles(network, path=PROFILE_PATH):
    path = Path(path)
    if not path.exists():
        return default_quick_profiles(network)
    if path.stat().st_size > 100_000:
        raise ValueError('보통값 파일 크기가 너무 큽니다.')
    payload = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(payload, dict) or set(payload) != {'schema_version', 'profiles'}
            or type(payload['schema_version']) is not int or payload['schema_version'] != 1):
        raise ValueError('지원하지 않는 보통값 파일 형식입니다.')
    return validate_profiles(network, payload['profiles'])


def write_profiles(network, profiles, path=PROFILE_PATH):
    validate_profiles(network, profiles)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(dict(schema_version=1, profiles=profiles), ensure_ascii=False, indent=2)
    fd, temporary = tempfile.mkstemp(prefix='quick-detours-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_profile(network, cp, values, path=PROFILE_PATH):
    if cp not in network['port_detours']:
        raise ValueError('등록되지 않은 항만입니다.')
    profiles = read_profiles(network, path)
    profiles[cp] = dict(deepcopy(values), enabled=False)
    write_profiles(network, profiles, path)
    return profiles


def quick_setting(current, profile, enabled):
    """On loads the saved assumption. Off preserves numeric values for inspection."""
    if type(enabled) is not bool:
        raise ValueError('우회 스위치 상태가 잘못되었습니다.')
    return dict(deepcopy(profile if enabled else current), enabled=enabled)
