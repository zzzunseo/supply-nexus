"""Non-mutating active issue edits. Same-target application remains in the engine."""
from copy import deepcopy


def _check_index(events, index):
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(events):
        raise ValueError('이슈를 다시 선택하세요.')


def delete_issue(events, index):
    _check_index(events, index)
    updated = deepcopy(events)
    del updated[index]
    return updated


def change_issue_duration(events, index, days):
    _check_index(events, index)
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
        raise ValueError('이슈 기간은 1~365 사이의 정수 일수여야 합니다.')
    updated = deepcopy(events)
    updated[index]['days'] = days
    return updated
