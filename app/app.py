"""
E-Commerce Intelligence Platform — Streamlit Application

Entry point. Initializes shared state (DuckDB, signals, findings)
once, then delegates to page modules.

Run from project root:
    streamlit run app/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# ── Ensure project root is on sys.path so `src.*` imports work ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Page config (must be first Streamlit call) ──
st.set_page_config(
    page_title="E-Commerce Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Shared state initialization (runs once per session) ──
if "initialized" not in st.session_state:
    from src.analytics import get_connection, run_analytics, generate_findings, generate_suggested_questions

    con, monitoring_summary = get_connection(
        data_dir=PROJECT_ROOT / "data",
        evidently_dir=PROJECT_ROOT / "evidently",
    )

    signals, current_period, prior_period = run_analytics(con)
    findings = generate_findings(signals, con, current_period, prior_period, monitoring_summary)
    suggested_questions = generate_suggested_questions(findings)

    st.session_state.con = con
    st.session_state.monitoring_summary = monitoring_summary
    st.session_state.signals = signals
    st.session_state.findings = findings
    st.session_state.current_period = current_period
    st.session_state.prior_period = prior_period
    st.session_state.suggested_questions = suggested_questions
    st.session_state.project_root = PROJECT_ROOT
    st.session_state.chat_history = []
    st.session_state.initialized = True


# ── Navigation ──
page = st.sidebar.radio(
    "Navigation",
    ["Executive Intelligence", "Business Explorer"],
    label_visibility="collapsed",
)

# ── Check for cross-page navigation via query params ──
params = st.query_params
if params.get("page") == "explorer":
    page = "Business Explorer"

if page == "Executive Intelligence":
    from app.page_executive import render_executive_page
    render_executive_page()
else:
    from app.page_explorer import render_explorer_page
    render_explorer_page()
