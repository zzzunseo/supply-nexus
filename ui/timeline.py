"""Eight labelled daily process series, with first-shortage markers."""
import plotly.graph_objects as go
from resilience_globe import COLORS


STYLES = [
    ('normal', 'solid', 'circle'),
    ('buffer', 'dash', 'square'),
    ('reduced', 'dot', 'diamond'),
    ('stopped', 'dashdot', 'cross'),
    ('bypass', 'longdash', 'triangle-up'),
    ('normal', 'dot', 'triangle-down'),
    ('reduced', 'dash', 'star'),
    ('bypass', 'dashdot', 'x'),
]


def build_timeline(result):
    figure = go.Figure()
    days = [row['day'] for row in result['timeline']]
    for index, process in enumerate(result['scores']):
        color_key, dash, symbol = STYLES[index % len(STYLES)]
        color = COLORS[color_key]
        values = [row[process] for row in result['timeline']]
        first = result['first_hit'].get(process)
        unsupported = result['scores'][process] is None
        label = process + (' · 미산정' if unsupported else '') + (' *' if process in result.get('incomplete_processes', {}) else '')
        figure.add_trace(go.Scatter(
            x=days, y=values, name=label, legendgroup=process,
            mode='lines+markers', line=dict(color=color, dash=dash, width=1.8),
            marker=dict(symbol=symbol, size=3),
            hovertemplate=label + ' · %{x}일: %{y:.1f}/100<extra></extra>',
        ))
        if first is not None:
            figure.add_trace(go.Scatter(
                x=[first], y=[result['timeline'][first - 1][process]],
                name=f'{process} 첫 소재 부족 {first}일', legendgroup=process,
                showlegend=False, mode='markers',
                marker=dict(color=color, symbol=symbol, size=10, line=dict(color='white', width=1)),
                hovertemplate=f'{process} 첫 소재 부족: {first}일 · %{{y:.1f}}/100<extra></extra>',
            ))
    figure.update_layout(
        height=190, margin=dict(l=32, r=6, t=12, b=65),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#A5CEDD', size=9),
        legend=dict(orientation='h', y=-0.25, yanchor='top', x=0, font=dict(size=9)),
        xaxis=dict( range=[0.5, max(days) + 0.5], gridcolor='#20394E'),
        yaxis=dict(range=[0, 100], tickvals=[0, 50, 100], gridcolor='#20394E'),
        hovermode='closest',
    )
    return figure
