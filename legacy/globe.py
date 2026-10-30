"""Orthographic globe, with routes interpolated along great circles."""
import math
import plotly.graph_objects as go
from legacy.theme import TOKENS as T

VIEWS = {"아시아·태평양": (125, 23), "유럽": (20, 35), "북미": (-105, 30), "전체": (125, 20)}


def great_circle(lon1, lat1, lon2, lat2, steps=64):
    """Return shortest surface arc; handle coincident and antipodal endpoints."""
    def vector(lon, lat):
        a, b = math.radians(lon), math.radians(lat)
        return (math.cos(b)*math.cos(a), math.cos(b)*math.sin(a), math.sin(b))
    a, b = vector(lon1, lat1), vector(lon2, lat2)
    dot = max(-1.0, min(1.0, sum(x*y for x, y in zip(a, b))))
    angle = math.acos(dot)
    if angle < 1e-9:
        return [lon1, lon2], [lat1, lat2]
    if abs(math.pi-angle) < 1e-7:
        axis = (0, 0, 1) if abs(a[2]) < .9 else (1, 0, 0)
        tangent = (a[1]*axis[2]-a[2]*axis[1], a[2]*axis[0]-a[0]*axis[2], a[0]*axis[1]-a[1]*axis[0])
        norm = math.sqrt(sum(x*x for x in tangent))
        tangent = tuple(x/norm for x in tangent)
    else:
        tangent = tuple((b[i]-dot*a[i])/math.sin(angle) for i in range(3))
    lons, lats = [], []
    for i in range(steps+1):
        t = angle*i/steps
        p = [math.cos(t)*a[j]+math.sin(t)*tangent[j] for j in range(3)]
        lons.append(math.degrees(math.atan2(p[1], p[0])))
        lats.append(math.degrees(math.atan2(p[2], math.hypot(p[0], p[1]))))
    return lons, lats


def build_globe(nodes, edges, affected, region, show_labels=True, show_grid=True, revision=0):
    lookup = {n['id']: n for n in nodes}
    fig = go.Figure()
    for edge in edges:
        a, b = lookup[edge['from']], lookup[edge['to']]
        blocked = a['id'] in affected or b['id'] in affected
        color = T['red'] if blocked else T['cyan']
        lons, lats = great_circle(a['lon'], a['lat'], b['lon'], b['lat'])
        fig.add_trace(go.Scattergeo(
            lon=lons, lat=lats, mode='lines',
            line=dict(width=2 if blocked else 1.5, color=color, dash='dot' if blocked else 'solid'),
            opacity=.9 if blocked else .65, showlegend=False,
            text=f"{a['name']} → {b['name']}<br>{edge['item']} · {'중단 예시' if blocked else '정상 예시'}",
            hoverinfo='text', name=edge['id'], uid=edge['id'],
        ))
    for blocked, label, color in [(False, '정상 거점', T['cyan']), (True, '중단 거점', T['red'])]:
        group = [n for n in nodes if (n['id'] in affected) == blocked]
        if not group:
            continue
        fig.add_trace(go.Scattergeo(
            lon=[n['lon'] for n in group], lat=[n['lat'] for n in group],
            mode='markers+text' if show_labels else 'markers',
            text=[n['name'] for n in group], textposition='top center',
            textfont=dict(size=11, color=T['text']),
            customdata=[[n['country'], n['role'], '중단 예시' if blocked else '정상 예시'] for n in group],
            hovertemplate='%{text}<br>%{customdata[0]} · %{customdata[1]}<br>%{customdata[2]}<extra></extra>',
            marker=dict(size=10 if blocked else 7, color=color, symbol='x' if blocked else 'circle',
                        line=dict(width=1, color=T['text'])),
            name=label, showlegend=False, uid='affected' if blocked else 'normal',
        ))
    lon, lat = VIEWS[region]
    fig.update_geos(
        projection_type='orthographic', projection_rotation=dict(lon=lon, lat=lat, roll=0),
        projection_scale=.92, scope='world', showframe=False, showocean=True,
        oceancolor=T['ocean'], showland=True, landcolor=T['land'],
        showcoastlines=True, coastlinecolor=T['coast'], coastlinewidth=.7,
        showcountries=True, countrycolor=T['grid'], countrywidth=.4,
        bgcolor='rgba(0,0,0,0)', resolution=110,
        lonaxis=dict(showgrid=show_grid, gridcolor=T['grid'], gridwidth=.5, dtick=30),
        lataxis=dict(showgrid=show_grid, gridcolor=T['grid'], gridwidth=.5, dtick=30),
        uirevision=f'{region}-{revision}',
    )
    fig.update_layout(
        height=620, margin=dict(l=12, r=12, t=12, b=12),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family=T['font'], color=T['text']), dragmode='pan',
        uirevision=f'{region}-{revision}',
        hoverlabel=dict(bgcolor=T['panel'], bordercolor=T['border'], font_color=T['text']),
    )
    return fig
