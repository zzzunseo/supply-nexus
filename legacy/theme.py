"""Shared visual tokens for the Streamlit UI and Plotly globe."""
TOKENS = {
    "background": "#050B16", "panel": "#0B1526", "border": "#263A50",
    "text": "#E6F0FA", "muted": "#A5B8CC", "cyan": "#4DE5F4",
    "amber": "#FFC66D", "red": "#FF647E", "ocean": "#0A192F",
    "land": "#123B46", "coast": "#32606B", "grid": "#20364B",
    "radius": "14px", "font": "Pretendard, 'Noto Sans KR', sans-serif",
}

# Shared by the Python shell and the WebGL component. Legacy tokens above also
# keep the first Plotly prototype executable through app_plotly.py.
TOKENS.update({
    'background': '#060D17', 'panel': '#0A1422', 'border': '#1D2D40',
    'border_strong': '#30465F', 'text': '#E1ECF6', 'muted': '#9AACBF',
    'cyan': '#56DDEB', 'red': '#FF7186', 'input': '#0D1A2B',
    'selection': '#0C2639', 'hover': '#10243A', 'toggle': '#2785B2',
    'radius': '12px', 'radius_small': '6px',
    'font': "Pretendard, 'Malgun Gothic', 'Noto Sans KR', sans-serif",
    'number_font': "'Cascadia Mono', 'Consolas', monospace",
    'map_glow': '#0C1B30', 'label_bg': '#0A1726D9',
    'danger_bg': '#2B1825', 'danger_border': '#6E3449',
    'land_emission': '#9CC9FF', 'atmosphere': '#3986C6',
    'context_node': '#2D627A', 'context_arc': '#254458',
    'context_red': '#713447', 'arc_start': '#247AAB',
    'context_amber': '#715A37', 'warning_bg': '#2B251C',
    'shadow': '0 8px 28px rgba(0,0,0,.25)',
})


def shell_stylesheet():
    return f"""<style>
    .stApp {{background:{TOKENS['background']};}}
    [data-testid="stHeader"] {{display:none;}}
    .block-container {{padding:0!important;max-width:none!important;}}
    [data-testid="stMainBlockContainer"] {{padding:0!important;max-width:none!important;}}
    [data-testid="stVerticalBlock"] {{gap:0!important;}}
    [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"]) {{margin:0;}}
    footer {{visibility:hidden;}}
    </style>"""


def stylesheet():
    t = TOKENS
    return f"""<style>
    .stApp {{background:{t['background']};color:{t['text']};}}
    html, body, [class*="css"], .stApp {{font-family:{t['font']};}}
    [data-testid="stSidebar"] {{background:{t['panel']};border-right:1px solid {t['border']};}}
    .block-container {{padding-top:2.2rem;padding-bottom:2rem;max-width:1600px;}}
    h1 {{font-size:2.25rem!important;letter-spacing:-.055em;}}
    h2,h3 {{letter-spacing:-.035em;}}
    [data-testid="stMetric"] {{background:{t['panel']};border:1px solid {t['border']};
        border-radius:{t['radius']};padding:18px 22px;}}
    [data-testid="stMetricValue"] {{font-variant-numeric:tabular-nums;color:{t['cyan']};}}
    [data-testid="stCaptionContainer"] {{color:{t['muted']};}}
    [data-testid="stVerticalBlockBorderWrapper"] {{border-radius:{t['radius']};}}
    .eyebrow {{color:{t['cyan']};font-size:.75rem;letter-spacing:.16em;font-weight:700;}}
    .legend {{color:{t['muted']};font-size:.84rem;line-height:1.8;}}
    .legend .normal {{color:{t['cyan']};}} .legend .alert {{color:{t['red']};}}
    .hint {{color:{t['muted']};font-size:.83rem;}}
    </style>"""
