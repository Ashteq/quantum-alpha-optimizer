"""
app.py  —  Quantum-Alpha Portfolio Optimizer
--------------------------------------------
Frontend interface with Retro Pixel styling and Fallback Demo Mode.
"""

import time
import json
import random
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quantum-Alpha",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL: str = "https://quantum-backend.onrender.com/optimize" # Use your actual Render URL here
REQUEST_TIMEOUT: int = 45
DEFAULT_TICKERS: str = "AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA"

# ── Retro Palette ────────────────────────────────────────────────────────────
COLOR_BG = "#7BA4DB"       # Classic Windows 95 desktop background blue
COLOR_WINDOW = "#FFFFFF"   # White window background
COLOR_BORDER = "#000000"   # Hard black borders
COLOR_TITLEBAR = "#0000AA" # Deep blue title bar
COLOR_TEXT = "#000000"
COLOR_ACCENT_1 = "#FF0000" # Pixel red
COLOR_ACCENT_2 = "#00AA00" # Pixel green
COLOR_ACCENT_3 = "#FFD700" # Pixel yellow

# ─────────────────────────────────────────────────────────────────────────────
# Retro CSS Injection
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

    /* Global Typography */
    .stApp {{
        background-color: {COLOR_BG};
    }}
    html, body, p, span, div, label {{
        font-family: 'Courier New', monospace;
        color: {COLOR_TEXT};
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'VT323', monospace !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* Hide Streamlit elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Sidebar Styling */
    [data-testid="stSidebar"] {{
        background-color: #E0DFE3 !important;
        border-right: 3px solid {COLOR_BORDER};
    }}

    /* Metric Cards (Retro Window Style) */
    [data-testid="stMetric"] {{
        background-color: {COLOR_WINDOW};
        border: 3px solid {COLOR_BORDER};
        box-shadow: 4px 4px 0px {COLOR_BORDER};
        padding: 15px;
    }}
    [data-testid="stMetricLabel"] {{
        font-family: 'VT323', monospace !important;
        font-size: 1.2rem;
        color: {COLOR_TITLEBAR};
    }}
    [data-testid="stMetricValue"] {{
        font-family: 'Courier New', monospace !important;
        font-weight: bold;
        color: {COLOR_TEXT};
    }}

    /* Buttons */
    .stButton > button {{
        background-color: #E0DFE3;
        color: {COLOR_TEXT};
        border: 2px solid {COLOR_BORDER};
        border-right: 4px solid {COLOR_BORDER};
        border-bottom: 4px solid {COLOR_BORDER};
        font-family: 'VT323', monospace;
        font-size: 1.2rem;
        border-radius: 0;
        transition: none;
    }}
    .stButton > button:active {{
        border: 2px solid {COLOR_BORDER};
        transform: translate(2px, 2px);
    }}

    /* Inputs */
    .stTextInput > div > div > input, .stNumberInput > div > div > input {{
        background-color: {COLOR_WINDOW};
        border: 2px solid {COLOR_BORDER};
        border-radius: 0;
        font-family: 'Courier New', monospace;
        color: {COLOR_TEXT};
    }}

    /* Custom Window Header */
    .retro-window {{
        background-color: {COLOR_WINDOW};
        border: 3px solid {COLOR_BORDER};
        box-shadow: 5px 5px 0px {COLOR_BORDER};
        margin-bottom: 20px;
    }}
    .retro-titlebar {{
        background-color: {COLOR_TITLEBAR};
        color: white;
        font-family: 'VT323', monospace;
        font-size: 1.5rem;
        padding: 5px 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .retro-content {{
        padding: 20px;
    }}
    .window-controls span {{
        display: inline-block;
        width: 12px;
        height: 12px;
        border: 1px solid black;
        margin-left: 5px;
    }}
    .btn-red {{ background-color: {COLOR_ACCENT_1}; }}
    .btn-yellow {{ background-color: {COLOR_ACCENT_3}; }}
    .btn-green {{ background-color: {COLOR_ACCENT_2}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## QUANTUM-ALPHA")
    st.markdown("PORTFOLIO OPTIMIZER v1.0")
    st.markdown("---")

    ticker_input = st.text_input("TICKERS (COMMA-SEPARATED)", value=DEFAULT_TICKERS)
    risk_factor = st.slider("RISK AVERSION (q)", min_value=0.0, max_value=1.0, value=0.5, step=0.05)
    qaoa_reps = st.select_slider("QAOA DEPTH (p)", options=[1, 2, 3], value=1)
    budget_input = st.number_input("BUDGET (ASSETS)", min_value=1, max_value=10, value=3, step=1)
    
    st.markdown("---")
    optimise_btn = st.button("EXECUTE OPTIMIZATION", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# Main Header (Retro Window)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="retro-window">
        <div class="retro-titlebar">
            <span>C:\\QUANTUM\\OPTIMIZER.EXE</span>
            <div class="window-controls">
                <span class="btn-red"></span><span class="btn-yellow"></span><span class="btn-green"></span>
            </div>
        </div>
        <div class="retro-content">
            <h1 style="color: {COLOR_TITLEBAR}; margin-top:0;">MY RESUME PROJECT</h1>
            <p>Quantum-Inspired Portfolio Optimization Pipeline.<br>
            Awaiting parameters...</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers & Charting
# ─────────────────────────────────────────────────────────────────────────────
def parse_tickers(raw: str) -> list[str]:
    return [t.strip().upper() for t in raw.split(",") if t.strip()]

def get_retro_layout(title: str, height: int = 360) -> dict:
    return dict(
        title=dict(text=title.upper(), font=dict(family="VT323", size=24, color=COLOR_TITLEBAR)),
        paper_bgcolor=COLOR_WINDOW,
        plot_bgcolor=COLOR_WINDOW,
        font=dict(family="Courier New", color=COLOR_TEXT),
        margin=dict(l=20, r=20, t=60, b=20),
        height=height,
    )

def plot_selection_bar(all_tickers: list[str], selection_vector: list[int]) -> go.Figure:
    colors = [COLOR_TITLEBAR if s else COLOR_BG for s in selection_vector]
    fig = go.Figure(go.Bar(
        x=selection_vector, y=all_tickers, orientation="h",
        marker=dict(color=colors, line=dict(color=COLOR_BORDER, width=2)),
    ))
    fig.update_layout(
        **get_retro_layout("BINARY ASSET SELECTION", max(260, len(all_tickers) * 46)),
        xaxis=dict(showgrid=False, showticklabels=False, range=[0, 1.2]),
        yaxis=dict(showgrid=False, tickfont=dict(weight="bold"))
    )
    return fig

def plot_allocation_pie(asset_details: list[dict]) -> go.Figure:
    tickers = [a["ticker"] for a in asset_details]
    weights = [a["weight"] for a in asset_details]
    palette = [COLOR_TITLEBAR, COLOR_ACCENT_1, COLOR_ACCENT_3, COLOR_ACCENT_2, "#800080", "#FF8C00"]
    
    fig = go.Figure(go.Pie(
        labels=tickers, values=weights, hole=0.0,
        textinfo="label+percent",
        textfont=dict(family="Courier New", size=14, color="white"),
        marker=dict(colors=palette, line=dict(color=COLOR_BORDER, width=2)),
    ))
    fig.update_layout(**get_retro_layout("EQUAL-WEIGHT ALLOCATION"))
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# Mock Data Generator (Demo Mode)
# ─────────────────────────────────────────────────────────────────────────────
def generate_mock_data(tickers: list[str], budget: int):
    all_tickers = tickers[:10]
    budget = min(budget, len(all_tickers))
    selected = random.sample(all_tickers, budget)
    
    selection_vector = [1 if t in selected else 0 for t in all_tickers]
    asset_details = [
        {"ticker": t, "expected_return": random.uniform(0.05, 0.45), "weight": 1.0/budget}
        for t in selected
    ]
    
    return {
        "elapsed_seconds": round(random.uniform(1.5, 3.2), 2),
        "selected_tickers": selected,
        "all_tickers": all_tickers,
        "selection_vector": selection_vector,
        "portfolio_expected_return": sum([a["expected_return"] for a in asset_details]) / budget,
        "portfolio_variance": random.uniform(0.1, 0.3),
        "sharpe_proxy": random.uniform(1.2, 3.5),
        "asset_details": asset_details
    }

# ─────────────────────────────────────────────────────────────────────────────
# Execution Logic
# ─────────────────────────────────────────────────────────────────────────────
if optimise_btn:
    tickers = parse_tickers(ticker_input)

    if len(tickers) < 2 or len(tickers) > 10:
        st.error("[SYSTEM ERROR] INPUT MUST BE BETWEEN 2 AND 10 TICKERS.")
        st.stop()

    payload = {"tickers": tickers, "budget": int(budget_input), "risk_factor": risk_factor, "qaoa_reps": qaoa_reps}

    data = None
    is_demo_mode = False

    with st.spinner("EXECUTING QAOA OPTIMIZATION..."):
        try:
            resp = requests.post(BACKEND_URL, json=payload, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
            else:
                is_demo_mode = True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            is_demo_mode = True

    if is_demo_mode:
        st.info("[SYSTEM NOTICE] BACKEND SERVER UNREACHABLE. INITIALIZING LOCAL DEMO MODE.")
        data = generate_mock_data(tickers, int(budget_input))
        time.sleep(1) # Simulate processing time

    # ── Results UI ────────────────────────────────────────────────────────────
    st.success(f"[PROCESS TERMINATED] COMPLETED IN {data['elapsed_seconds']}s")

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("SELECTED ASSETS", f"{len(data['selected_tickers'])}/{len(data['all_tickers'])}")
    with m2: st.metric("EXPECTED RETURN", f"{data['portfolio_expected_return'] * 100:+.2f}%")
    with m3: st.metric("VOLATILITY", f"{data['portfolio_variance'] ** 0.5 * 100:.2f}%")
    with m4: st.metric("SHARPE PROXY", f"{data['sharpe_proxy']:.3f}")

    st.write("")

    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        st.plotly_chart(plot_selection_bar(data["all_tickers"], data["selection_vector"]), use_container_width=True)
    with col_b:
        st.plotly_chart(plot_allocation_pie(data["asset_details"]), use_container_width=True)

else:
    st.markdown("**[WAITING FOR USER INPUT]**")