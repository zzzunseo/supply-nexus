"""Simulation boundary and independent one-at-a-time assumption comparisons."""
from copy import deepcopy
import streamlit as st
from simulation.resilience import calculate_supply_shock
from simulation.reporting import period_bottleneck, score_view
from .state import scopes_from_state


def calculate_current(network):
    return calculate_supply_shock(
        network,
        deepcopy(st.session_state.rr_events),
        st.session_state.rr_days,
        st.session_state.rr_inventory,
        st.session_state.rr_bypass,
        scopes_from_state(),
    )


@st.cache_data(show_spinner=False, max_entries=32)
def calculate_sensitivity(network, events, observation_days, use_inventory, use_bypass, scopes):
    """Scale active-node assumptions, with every other input held constant.

    Inventory is bounded to 365 days and bypass limits to 100%, matching engine
    validation. Shared reserve capacity and qualification/ramp times stay fixed.
    Period mean is the mean of daily bottleneck indices, not mean production.
    """
    variants = [
        ('기준', None, 1.0),
        ('재고 ×0.5', 'inventory_days', 0.5),
        ('재고 ×1.5', 'inventory_days', 1.5),
        ('우회 ×0.5', 'alt_capacity', 0.5),
        ('우회 ×1.5', 'alt_capacity', 1.5),
    ]
    active_scopes = {'core', *scopes}
    rows = []
    for label, field, factor in variants:
        variant = deepcopy(network)
        if field:
            upper = 365.0 if field == 'inventory_days' else 1.0
            for key, node in variant['nodes'].items():
                if node.get('scope', 'core') in active_scopes:
                    node[field] = min(upper, float(node[field]) * factor)
                    if field == 'inventory_days' and key in variant.get('route_settings', {}):
                        setting = variant['route_settings'][key]
                        setting['inventory_days'] = min(upper, float(setting['inventory_days']) * factor)
        result = calculate_supply_shock(
            variant, deepcopy(events), observation_days, use_inventory, use_bypass, scopes
        )
        average = sum(min(row[p] for p in result['scores'] if row[p] is not None) for row in result['timeline']) / observation_days
        mean_view = score_view(result, 'mean')
        rows.append(dict(label=label, overall=result['overall'], average=average,
                         mean_overall=mean_view['overall'], mean_average=period_bottleneck(mean_view)))
    for row in rows:
        row['delta'] = row['overall'] - rows[0]['overall']
        row['average_delta'] = row['average'] - rows[0]['average']
        row['mean_delta'] = row['mean_overall'] - rows[0]['mean_overall']
        row['mean_average_delta'] = row['mean_average'] - rows[0]['mean_average']
    return rows
