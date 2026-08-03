"""
Shared CSS for the E-Commerce Intelligence Platform.

v5 — Production Readiness Sprint (12 fixes):
  #1  Fix Dead Stock / Churn <span class="prior"> rendering (was <div>)
  #3  Key Findings hierarchy: bold title heading, indented sub-points
  #4  Supporting data as HTML table (not raw text)
  #5  Explorer section headings (Business Summary / Evidence / Recommended Action)
  #11 Recommendation card with action-level indicators
  #12 Editorial consistency (shared component, consistent voice)
"""


def inject_css():
    """Inject shared CSS into the Streamlit page."""
    import streamlit as st

    st.markdown("""
    <style>
    /* ── Global ── */
    .block-container { padding-top: 1rem; max-width: 1200px; }
    section[data-testid="stSidebar"] { background: #0B1426; }
    section[data-testid="stSidebar"] .stRadio label { color: #CBD5E1; font-size: 0.95rem; }

    /* ── Header bar ── */
    .header-bar {
        background: linear-gradient(135deg, #0B1426 0%, #1E293B 100%);
        padding: 1.5rem 2rem 1.25rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.75rem;
    }
    .header-top-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 0.75rem;
    }
    .header-bar .platform-name {
        color: #94A3B8;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 0 0 0.3rem 0;
    }
    .header-bar h1 {
        color: #F8FAFC;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.01em;
    }
    .header-bar .subtitle {
        color: #94A3B8;
        font-size: 0.85rem;
        margin: 0.35rem 0 0 0;
    }
    .header-bar .brief-timestamp {
        color: #64748B;
        font-size: 0.78rem;
        margin: 0.3rem 0 0 0;
    }
    .header-badges {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .header-badge {
        padding: 0.3rem 0.75rem;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        cursor: pointer;
        text-decoration: none;
        transition: opacity 0.15s;
    }
    .header-badge:hover { opacity: 0.85; }
    .badge-green { background: #064E3B; color: #6EE7B7; }
    .badge-amber { background: #78350F; color: #FCD34D; }
    .badge-red   { background: #7F1D1D; color: #FCA5A5; }
    .badge-blue  { background: #1E3A5F; color: #93C5FD; }
    .badge-slate { background: #1E293B; color: #94A3B8; }

    /* ── #1 — Layer labels above KPI rows ── */
    .kpi-layer-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin: 1.25rem 0 0.5rem 0;
    }
    .kpi-layer-label:first-child { margin-top: 0; }

    /* ── KPI cards — uniform height, flex layout ── */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.1rem 1.25rem;
        text-align: left;
        height: 135px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    }
    .kpi-card .label {
        color: #64748B;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }
    .kpi-card .value {
        font-size: 1.45rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.1;
        margin-bottom: 0.3rem;
    }
    .kpi-card .delta {
        font-size: 0.82rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        display: inline-block;
    }
    .kpi-card .prior {
        font-size: 0.72rem;
        color: #94A3B8;
        margin-top: 0.25rem;
        display: block;
    }
    .delta-up   { background: #ECFDF5; color: #059669; }
    .delta-down-good { background: #ECFDF5; color: #059669; }
    .delta-down-bad  { background: #FEF2F2; color: #DC2626; }
    .delta-flat { background: #F1F5F9; color: #64748B; }

    /* ── Snapshot items ── */
    .snapshot-item {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.75rem 1rem;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        min-height: 64px;
    }
    .snapshot-icon { font-size: 1.3rem; line-height: 1; }
    .snapshot-label {
        font-size: 0.72rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .snapshot-status { font-size: 0.88rem; font-weight: 700; }
    .status-green  { color: #059669; }
    .status-amber  { color: #D97706; }
    .status-red    { color: #DC2626; }

    /* ── Priority badges ── */
    .priority-badge {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-right: 0.5rem;
    }
    .priority-p1-positive { background: #D1FAE5; color: #065F46; }
    .priority-p1-negative { background: #FEE2E2; color: #991B1B; }
    .priority-p2 { background: #FEF3C7; color: #92400E; }
    .priority-p3 { background: #F1F5F9; color: #475569; }

    /* ── Finding cards ── */
    .finding-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563EB;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .finding-card.p1-positive { border-left-color: #059669; }
    .finding-card.p1-negative { border-left-color: #DC2626; }
    .finding-card.p2 { border-left-color: #D97706; }
    .finding-card.p3 { border-left-color: #64748B; }
    .finding-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.5rem;
    }
    .finding-desc {
        color: #475569;
        font-size: 0.88rem;
        margin-bottom: 0.5rem;
        line-height: 1.5;
    }
    .finding-impact {
        font-size: 0.84rem;
        color: #1E293B;
        font-style: italic;
        padding: 0.5rem 0.75rem;
        margin: 0.5rem 0 0.75rem 0;
        border-radius: 0 4px 4px 0;
    }
    .finding-card.p1-positive .finding-impact { border-left: 3px solid #059669; background: #F0FDF4; }
    .finding-card.p1-negative .finding-impact { border-left: 3px solid #DC2626; background: #FFF5F5; }
    .finding-card.p2 .finding-impact { border-left: 3px solid #D97706; background: #FFFBEB; }
    .finding-card.p3 .finding-impact { border-left: 3px solid #64748B; background: #F8FAFC; }
    .finding-evidence {
        font-size: 0.82rem;
        color: #64748B;
        line-height: 1.6;
        margin-bottom: 0.5rem;
    }
    .finding-evidence ul { margin: 0.25rem 0 0 1.2rem; padding: 0; }
    .finding-evidence li { margin-bottom: 0.2rem; }
    .finding-meta {
        display: flex;
        gap: 1.25rem;
        font-size: 0.78rem;
        color: #94A3B8;
        flex-wrap: wrap;
        align-items: center;
    }
    .evidence-badge {
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .evidence-strong  { background: #ECFDF5; color: #059669; }
    .evidence-moderate { background: #FEF3C7; color: #92400E; }
    .evidence-limited  { background: #FEF2F2; color: #991B1B; }

    /* ── Section headers ── */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0F172A;
        margin: 2.25rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E2E8F0;
    }

    /* ── Insight callout ── */
    .insight-callout {
        background: #F0F9FF;
        border-left: 3px solid #2563EB;
        padding: 0.6rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.88rem;
        color: #1E293B;
        border-radius: 0 6px 6px 0;
        line-height: 1.5;
    }

    /* ── #5 — Explorer section labels (Business Summary / Evidence / Recommended Action) ── */
    .explorer-section-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748B;
        margin: 1.75rem 0 0.5rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #E2E8F0;
    }
    .explorer-section-label:first-of-type { margin-top: 0.5rem; }

    /* ── #11 #12 — Recommendation card with action-level indicators ── */
    .recommendation-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #64748B;
        padding: 1rem 1.25rem;
        margin-top: 0.5rem;
        font-size: 0.9rem;
        color: #1E293B;
        border-radius: 0 6px 6px 0;
        line-height: 1.55;
    }
    .recommendation-card .rec-action-level {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.55rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .recommendation-card .rec-text {
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    .recommendation-card .rec-impact {
        font-size: 0.82rem;
        color: #475569;
        font-style: italic;
        padding-top: 0.5rem;
        border-top: 1px solid #E2E8F0;
    }
    /* Action-level variants */
    .rec-green   { border-left-color: #059669; background: #F0FDF4; }
    .rec-green  .rec-action-level { color: #065F46; }
    .rec-yellow  { border-left-color: #CA8A04; background: #FEFCE8; }
    .rec-yellow .rec-action-level { color: #854D0E; }
    .rec-orange  { border-left-color: #EA580C; background: #FFF7ED; }
    .rec-orange .rec-action-level { color: #9A3412; }
    .rec-red     { border-left-color: #DC2626; background: #FEF2F2; }
    .rec-red    .rec-action-level { color: #991B1B; }

    /* ── Briefing container ── */
    .briefing-container {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 2rem 2.25rem;
        margin-top: 0.5rem;
        color: #1E293B;
        line-height: 1.7;
        font-size: 0.92rem;
    }
    .briefing-container h2 {
        color: #0F172A;
        font-size: 1.2rem;
        margin-top: 1.75rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #E2E8F0;
    }
    .briefing-container h2:first-child { margin-top: 0; }
    .briefing-container h3 {
        color: #1E293B;
        font-size: 1.05rem;
        margin-top: 1.25rem;
        margin-bottom: 0.5rem;
    }
    .briefing-container table {
        width: 100%;
        border-collapse: collapse;
        margin: 0.75rem 0;
        font-size: 0.88rem;
    }
    .briefing-container th, .briefing-container td {
        padding: 0.5rem 0.75rem;
        border: 1px solid #E2E8F0;
        text-align: left;
    }
    .briefing-container th { background: #F8FAFC; font-weight: 600; color: #0F172A; }
    .briefing-container td.cell-green { background: #D1FAE5; color: #065F46; font-weight: 600; }
    .briefing-container td.cell-red   { background: #FEE2E2; color: #991B1B; font-weight: 600; }
    .briefing-container td.cell-amber { background: #FEF3C7; color: #92400E; font-weight: 600; }
    .briefing-container td.cell-flat  { background: #F1F5F9; color: #64748B; }
    .briefing-container ul { margin: 0.5rem 0 0.5rem 1.5rem; }
    .briefing-container li { margin-bottom: 0.4rem; }
    /* #3 — Key Findings hierarchy: finding title stands alone, sub-points indented */
    .briefing-container .finding-heading {
        font-size: 1rem;
        font-weight: 700;
        color: #0F172A;
        margin: 1.6rem 0 0.35rem 0;
        padding: 0;
    }
    .briefing-container .finding-heading:first-child { margin-top: 0.5rem; }
    .briefing-container .finding-sublabel {
        font-size: 0.85rem;
        font-weight: 600;
        color: #475569;
        margin: 0.6rem 0 0.2rem 0.25rem;
    }
    .briefing-container .finding-sublist {
        margin: 0.1rem 0 0.4rem 1.75rem;
        padding: 0;
    }
    .briefing-container .finding-sublist li {
        margin-bottom: 0.3rem;
        color: #334155;
        font-size: 0.88rem;
    }

    /* ── #5 — Chat response: styled section headings ── */
    .chat-response {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.9rem;
        color: #1E293B;
        line-height: 1.6;
    }
    .chat-response .chat-section-label {
        font-size: 0.82rem;
        font-weight: 700;
        color: #059669;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin: 1rem 0 0.3rem 0;
    }
    .chat-response .chat-section-label:first-child { margin-top: 0; }
    .chat-response pre {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        font-size: 0.82rem;
        overflow-x: auto;
        white-space: pre;
        margin-top: 0.5rem;
    }
    /* #4 — Supporting Data as a real table */
    .chat-response table {
        width: 100%;
        border-collapse: collapse;
        margin: 0.5rem 0 0.25rem 0;
        font-size: 0.85rem;
    }
    .chat-response th, .chat-response td {
        padding: 0.5rem 0.75rem;
        border: 1px solid #E2E8F0;
        text-align: left;
    }
    .chat-response th {
        background: #F8FAFC;
        font-weight: 600;
        color: #0F172A;
        text-transform: none;
    }
    .chat-response td.num { text-align: right; font-variant-numeric: tabular-nums; }

    /* ── Context banner ── */
    .context-banner {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        padding: 0.7rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.85rem;
        color: #1E40AF;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .context-banner strong { color: #1E3A8A; }

    /* ── Explore link ── */
    .explore-link {
        font-size: 0.8rem;
        color: #2563EB;
        text-decoration: none;
        font-weight: 600;
    }
    .explore-link:hover { text-decoration: underline; }

    /* ── Churn definition note ── */
    .definition-note {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-radius: 6px;
        padding: 0.5rem 0.85rem;
        font-size: 0.82rem;
        color: #92400E;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
