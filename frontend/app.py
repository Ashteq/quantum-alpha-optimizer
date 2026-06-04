"""
app.py  —  Quantum-Alpha Portfolio Optimizer  (Streamlit Frontend)
------------------------------------------------------------------
Sends a POST request to the FastAPI backend at http://localhost:8000/optimize
and visualises the optimised portfolio using interactive Plotly charts.

Run with:
    streamlit run app.py --server.port 8501

Author : Quantum-Alpha Team
"""

from __future__ import annotations

import json
import time

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────────────────────────────────────
# Page configuration  (must be the very first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Quantum-Alpha Portfolio Optimizer",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
BACKEND_URL: str = "http://localhost:8000/optimize"
REQUEST_TIMEOUT: int = 300          # QAOA can be slow — generous timeout
DEFAULT_TICKERS: str = "AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA"

# ── Colour palette ────────────────────────────────────────────────────────────
SELECTED_COLOUR = "#00d4ff"
REJECTED_COLOUR = "#1e3a5f"
BG_COLOUR       = "#0a0f1e"
CARD_COLOUR     = "#111827"
ACCENT_COLOUR   = "#7c3aed"
TEXT_COLOUR     = "#e2e8f0"
GREEN_COLOUR    = "#10b981"
RED_COLOUR      = "#ef4444"


# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Courier New', monospace;
        background-color: #0a0f1e;
        color: #e2e8f0;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #0d1424;
        border-right: 1px solid #1e3a5f;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricLabel"]  { color: #94a3b8 !important; font-size: 0.75rem; }
    [data-testid="stMetricValue"]  { color: #00d4ff !important; }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.4rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        font-family: 'Courier New', monospace;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* ── Text inputs ── */
    .stTextInput > div > div > input {
        background-color: #111827;
        border: 1px solid #1e3a5f;
        color: #e2e8f0;
        border-radius: 6px;
        font-family: 'Courier New', monospace;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background-color: #111827 !important;
        color: #94a3b8 !important;
        border: 1px solid #1e3a5f;
        border-radius: 6px;
    }

    /* ── Divider ── */
    hr { border-color: #1e3a5f; }

    /* ── Selected ticker badge ── */
    .ticker-badge {
        display: inline-block;
        background: #0f3460;
        border: 1px solid #00d4ff;
        border-radius: 4px;
        padding: 2px 10px;
        margin: 3px;
        font-size: 0.85rem;
        color: #00d4ff;
        font-weight: 700;
        letter-spacing: 0.06em;
    }
    .ticker-badge-rejected {
        display: inline-block;
        background: #1a1a2e;
        border: 1px solid #334155;
        border-radius: 4px;
        padding: 2px 10px;
        margin: 3px;
        font-size: 0.85rem;
        color: #475569;
        text-decoration: line-through;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — controls
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚛️ Quantum-Alpha")
    st.markdown("*Portfolio Optimizer*")
    st.divider()

    ticker_input: str = st.text_input(
        "📈 Tickers (comma-separated)",
        value=DEFAULT_TICKERS,
        help="Enter 2–10 stock tickers traded on major exchanges.",
    )

    st.markdown("### ⚙️ Solver Parameters")

    risk_factor: float = st.slider(
        "Risk Aversion (q)",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.05,
        help="0 = maximise return; 1 = minimise risk.",
    )

    qaoa_reps: int = st.select_slider(
        "QAOA Depth (p)",
        options=[1, 2, 3],
        value=1,
        help="Higher depth → better approximation but slower runtime.",
    )

    budget_input = st.number_input(
        "Budget (# assets to select)",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="How many assets to include in the final portfolio.",
    )

    st.divider()
    optimise_btn = st.button("🚀 Optimise Portfolio", use_container_width=True)

    st.markdown("---")
    st.caption("Backend → `localhost:8000`")
    st.caption("Frontend → `localhost:8501`")


# ─────────────────────────────────────────────────────────────────────────────
# Main area — hero header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <h1 style="
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #00d4ff 0%, #7c3aed 60%, #2563eb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    ">Quantum-Alpha Portfolio Optimizer</h1>
    <p style="color:#64748b; margin-top:4px; font-size:0.9rem;">
        QAOA-powered binary asset selection via Qiskit · yfinance market data
    </p>
    """,
    unsafe_allow_html=True,
)
st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: parse tickers from input string
# ─────────────────────────────────────────────────────────────────────────────
def parse_tickers(raw: str) -> list[str]:
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Plotly bar chart — binary selection
# ─────────────────────────────────────────────────────────────────────────────
def plot_selection_bar(all_tickers: list[str], selection_vector: list[int]) -> go.Figure:
    """Horizontal bar chart: selected assets (1) vs rejected (0)."""
    colours = [SELECTED_COLOUR if s else REJECTED_COLOUR for s in selection_vector]
    labels  = ["✓ Selected" if s else "✗ Rejected"  for s in selection_vector]

    fig = go.Figure(
        go.Bar(
            x=selection_vector,
            y=all_tickers,
            orientation="h",
            marker_color=colours,
            text=labels,
            textposition="inside",
            textfont=dict(color="white", family="Courier New", size=12),
            hovertemplate="<b>%{y}</b><br>Selected: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Asset Selection (Binary)", font=dict(color=TEXT_COLOUR, size=16)),
        paper_bgcolor=CARD_COLOUR,
        plot_bgcolor=BG_COLOUR,
        font=dict(color=TEXT_COLOUR, family="Courier New"),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[0, 1.3],
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=13)),
        margin=dict(l=10, r=10, t=50, b=10),
        height=max(260, len(all_tickers) * 46),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Plotly pie chart — equal-weight allocation
# ─────────────────────────────────────────────────────────────────────────────
def plot_allocation_pie(asset_details: list[dict]) -> go.Figure:
    tickers = [a["ticker"] for a in asset_details]
    weights = [a["weight"] for a in asset_details]

    fig = go.Figure(
        go.Pie(
            labels=tickers,
            values=weights,
            hole=0.5,
            textinfo="label+percent",
            textfont=dict(color="white", family="Courier New", size=13),
            marker=dict(
                colors=[
                    "#00d4ff", "#7c3aed", "#2563eb", "#10b981",
                    "#f59e0b", "#ef4444", "#ec4899",
                ][:len(tickers)],
                line=dict(color=BG_COLOUR, width=2),
            ),
            hovertemplate="<b>%{label}</b><br>Weight: %{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text="Portfolio Allocation (Equal-Weight)", font=dict(color=TEXT_COLOUR, size=16)),
        paper_bgcolor=CARD_COLOUR,
        font=dict(color=TEXT_COLOUR, family="Courier New"),
        legend=dict(bgcolor=CARD_COLOUR, bordercolor="#1e3a5f"),
        margin=dict(l=10, r=10, t=50, b=10),
        height=360,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Plotly bar chart — expected returns per asset
# ─────────────────────────────────────────────────────────────────────────────
def plot_returns_bar(asset_details: list[dict]) -> go.Figure:
    tickers  = [a["ticker"] for a in asset_details]
    returns  = [round(a["expected_return"] * 100, 2) for a in asset_details]
    colours  = [GREEN_COLOUR if r >= 0 else RED_COLOUR for r in returns]

    fig = go.Figure(
        go.Bar(
            x=tickers,
            y=returns,
            marker_color=colours,
            text=[f"{r:+.1f}%" for r in returns],
            textposition="outside",
            textfont=dict(color=TEXT_COLOUR, family="Courier New", size=12),
            hovertemplate="<b>%{x}</b><br>Expected Return: %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(
            text="Selected Asset — Annualised Expected Return",
            font=dict(color=TEXT_COLOUR, size=16),
        ),
        paper_bgcolor=CARD_COLOUR,
        plot_bgcolor=BG_COLOUR,
        font=dict(color=TEXT_COLOUR, family="Courier New"),
        xaxis=dict(showgrid=False, tickfont=dict(size=13)),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1e3a5f",
            ticksuffix="%",
            zeroline=True,
            zerolinecolor="#334155",
        ),
        margin=dict(l=10, r=10, t=50, b=10),
        height=340,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Optimisation logic — called when button is clicked
# ─────────────────────────────────────────────────────────────────────────────
if optimise_btn:
    tickers = parse_tickers(ticker_input)

    # ── Client-side validation ────────────────────────────────────────────────
    if len(tickers) < 2:
        st.error("⚠️ Please enter at least 2 ticker symbols separated by commas.")
        st.stop()
    if len(tickers) > 10:
        st.error("⚠️ Maximum 10 tickers supported. Please reduce the list.")
        st.stop()

    payload = {
        "tickers": tickers,
        "budget": int(budget_input),
        "risk_factor": risk_factor,
        "qaoa_reps": qaoa_reps,
    }

    # ── Call backend ──────────────────────────────────────────────────────────
    status_placeholder = st.empty()
    with st.spinner("⚛️  Running QAOA optimisation — this may take 30–120 s …"):
        try:
            t0 = time.perf_counter()
            resp = requests.post(
                BACKEND_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            elapsed_client = round(time.perf_counter() - t0, 2)

        except requests.exceptions.ConnectionError:
            st.error(
                "🔌 Cannot reach the backend at `http://localhost:8000`.\n\n"
                "**Make sure the FastAPI server is running:**\n"
                "```\ncd backend && uvicorn main:app --reload --port 8000\n```"
            )
            st.stop()
        except requests.exceptions.Timeout:
            st.error(
                f"⏱️ Request timed out after {REQUEST_TIMEOUT}s. "
                "Try reducing the number of tickers or QAOA depth."
            )
            st.stop()

    # ── HTTP error handling ───────────────────────────────────────────────────
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"Backend error ({resp.status_code}): {detail}")
        st.stop()

    # ── Parse response ────────────────────────────────────────────────────────
    data: dict = resp.json()

    # ─────────────────────────────────────────────────────────────────────────
    # Results UI
    # ─────────────────────────────────────────────────────────────────────────
    st.success(
        f"✅ Optimisation complete in **{data['elapsed_seconds']}s** "
        f"(round-trip: {elapsed_client}s)"
    )

    # ── Selected / rejected ticker badges ─────────────────────────────────────
    selected_set = set(data["selected_tickers"])
    badges = "".join(
        f'<span class="ticker-badge">{t}</span>'
        if t in selected_set
        else f'<span class="ticker-badge-rejected">{t}</span>'
        for t in data["all_tickers"]
    )
    st.markdown(f"<div style='margin-bottom:16px'>{badges}</div>", unsafe_allow_html=True)

    # ── Metric cards ──────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Selected Assets",
            f"{len(data['selected_tickers'])} / {len(data['all_tickers'])}",
        )
    with m2:
        ret_pct = round(data["portfolio_expected_return"] * 100, 2)
        st.metric("Expected Return (ann.)", f"{ret_pct:+.2f}%")
    with m3:
        vol_pct = round(data["portfolio_variance"] ** 0.5 * 100, 2)
        st.metric("Volatility (ann.)", f"{vol_pct:.2f}%")
    with m4:
        st.metric("Sharpe Proxy", f"{data['sharpe_proxy']:.3f}")

    st.divider()

    # ── Charts row 1: selection bar + allocation pie ──────────────────────────
    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        st.plotly_chart(
            plot_selection_bar(data["all_tickers"], data["selection_vector"]),
            use_container_width=True,
        )
    with col_b:
        st.plotly_chart(
            plot_allocation_pie(data["asset_details"]),
            use_container_width=True,
        )

    # ── Charts row 2: returns bar ─────────────────────────────────────────────
    if data["asset_details"]:
        st.plotly_chart(
            plot_returns_bar(data["asset_details"]),
            use_container_width=True,
        )

    # ── Raw JSON expander ─────────────────────────────────────────────────────
    with st.expander("🔬 Raw API Response (debug)"):
        st.json(data)

else:
    # ── Idle state — instructions ─────────────────────────────────────────────
    st.markdown(
        """
        <div style="
            background: #111827;
            border: 1px solid #1e3a5f;
            border-radius: 10px;
            padding: 32px 36px;
            margin-top: 16px;
        ">
        <h3 style="color:#00d4ff; margin-top:0">How to use</h3>
        <ol style="color:#94a3b8; line-height:2">
            <li>Enter 2–10 comma-separated stock tickers in the sidebar (e.g. <code>AAPL, MSFT, GOOGL</code>).</li>
            <li>Adjust the <strong>Risk Aversion</strong> slider and <strong>QAOA depth</strong>.</li>
            <li>Set how many assets you want the algorithm to <strong>select</strong> (Budget).</li>
            <li>Click <strong>🚀 Optimise Portfolio</strong> — the backend will fetch market data and run QAOA.</li>
        </ol>
        <p style="color:#475569; margin-bottom:0; font-size:0.85rem">
            ⚛️ Powered by Qiskit QAOA  ·  📈 yfinance market data  ·  ⚡ FastAPI backend
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
