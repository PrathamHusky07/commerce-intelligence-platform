"""
Page 1 — Executive Intelligence

v5 — Production Readiness Sprint:
  #1  Fix Dead Stock / Churn KPI card <span class="prior"> (was <div>)
  #3  Key Findings hierarchy in briefing — bold title as heading,
      sub-points (Hypothesis, Confidence, Evidence) indented beneath
  #4  Supporting Data renders as HTML table (not raw text dump)
"""

import glob
import re
from pathlib import Path

import streamlit as st

from app.styles import inject_css


def _fmt_period(period) -> str:
    """Format a period value as 'Jun 2026'."""
    try:
        return period.strftime("%b %Y")
    except Exception:
        s = str(period)
        return s[:7] if len(s) >= 7 else s


def _fmt_dc(text: str) -> str:
    """Remove 'DC ' prefix from distribution center names."""
    return text.replace("DC '", "'").replace("DC '", "'")


def _is_positive_finding(finding) -> bool:
    """Determine if a finding represents a positive business development."""
    return finding.severity == "notable" and "up" in finding.title.lower()


def _render_header():
    """Render the top status bar."""
    findings = st.session_state.findings
    current = st.session_state.current_period
    prior = st.session_state.prior_period
    mon = st.session_state.monitoring_summary

    p1_findings = [f for f in findings if f.priority == "P1"]
    p1_count = len(p1_findings)
    p2_count = sum(1 for f in findings if f.priority == "P2")

    all_p1_positive = all(_is_positive_finding(f) for f in p1_findings) if p1_findings else True

    if p1_count > 0:
        if all_p1_positive:
            findings_badge = (
                f'<a href="#key-findings" class="header-badge badge-green" style="text-decoration:none;">'
                f'{p1_count} Key Development{"s" if p1_count > 1 else ""}</a>'
            )
        else:
            findings_badge = (
                f'<a href="#key-findings" class="header-badge badge-red" style="text-decoration:none;">'
                f'{p1_count} Critical Risk{"s" if p1_count > 1 else ""}</a>'
            )
    elif p2_count > 0:
        findings_badge = (
            f'<a href="#key-findings" class="header-badge badge-amber" style="text-decoration:none;">'
            f'{p2_count} Item{"s" if p2_count > 1 else ""} to Review</a>'
        )
    else:
        findings_badge = '<span class="header-badge badge-green">All Clear</span>'

    if mon.get("prediction_drift_detected") or mon.get("model_degraded"):
        mon_badge = '<a href="#key-findings" class="header-badge badge-amber" style="text-decoration:none;">Model Health: Attention Required</a>'
    else:
        mon_badge = '<span class="header-badge badge-green">Model Health: Stable</span>'

    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    brief_path = reports_dir / "executive_brief.md"
    brief_ts = ""
    if brief_path.exists():
        for line in brief_path.read_text(encoding="utf-8").splitlines()[:10]:
            if line.startswith("**Generated:**"):
                brief_ts = line.replace("**Generated:**", "").strip()
                break
    ts_line = f'<p class="brief-timestamp">Latest brief: {brief_ts}</p>' if brief_ts else ""

    period_str = f"{_fmt_period(prior)} → {_fmt_period(current)}"

    st.markdown(f"""
    <div class="header-bar">
        <div class="header-top-row">
            <div>
                <p class="platform-name">E-Commerce Intelligence Platform</p>
                <h1>Executive Intelligence</h1>
                <p class="subtitle">Analysis period: {period_str} · Month-over-month</p>
                {ts_line}
            </div>
            <div class="header-badges">
                {findings_badge}
                {mon_badge}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_executive_snapshot():
    """Render the 5-second executive glance."""
    signals = st.session_state.signals
    findings = st.session_state.findings
    mon = st.session_state.monitoring_summary

    def _signal_status(metric_name):
        sig = next((s for s in signals if s.metric == metric_name), None)
        if not sig:
            return "—", "status-green", "🟢"
        if sig.severity == "critical":
            return "Declining", "status-red", "🔴"
        if sig.severity == "notable":
            return ("Strong Growth", "status-green", "📈") if sig.direction == "up" else ("Notable Change", "status-amber", "🟡")
        if sig.severity == "warning":
            return "Watch", "status-amber", "🟡"
        return "Stable", "status-green", "🟢"

    rev_label, rev_class, rev_icon = _signal_status("Total Revenue")
    orders_label, orders_class, orders_icon = _signal_status("Orders Fulfilled")

    del_sig = next((s for s in signals if s.metric == "Avg Delivery Days"), None)
    ot_sig = next((s for s in signals if s.metric == "On-Time Delivery Rate"), None)
    if del_sig and del_sig.severity in ("critical", "warning"):
        ops_label, ops_class, ops_icon = "Degrading", "status-red", "🔴"
    elif ot_sig and ot_sig.current_value >= 0.95:
        ops_label, ops_class, ops_icon = "Stable", "status-green", "🟢"
    else:
        ops_label, ops_class, ops_icon = "Watch", "status-amber", "🟡"

    if mon.get("prediction_drift_detected") and mon.get("model_degraded"):
        model_label, model_class, model_icon = "Degraded", "status-red", "🔴"
    elif mon.get("prediction_drift_detected") or mon.get("model_degraded"):
        model_label, model_class, model_icon = "Attention Required", "status-amber", "🟡"
    else:
        model_label, model_class, model_icon = "Healthy", "status-green", "🟢"

    has_critical_negative = any(f.severity == "critical" and f.priority == "P1" and not _is_positive_finding(f) for f in findings)
    if has_critical_negative:
        biz_label, biz_class, biz_icon = "At Risk", "status-red", "🔴"
    else:
        biz_label, biz_class, biz_icon = "Healthy", "status-green", "🟢"

    items = [
        ("Business", biz_icon, biz_label, biz_class),
        ("Revenue", rev_icon, rev_label, rev_class),
        ("Orders", orders_icon, orders_label, orders_class),
        ("Operations", ops_icon, ops_label, ops_class),
        ("Model", model_icon, model_label, model_class),
    ]

    # #1 — Layer label above snapshot row
    st.markdown('<div class="kpi-layer-label">Business Status</div>', unsafe_allow_html=True)
    cols = st.columns(len(items))
    for i, (label, icon, status, cls) in enumerate(items):
        with cols[i]:
            st.markdown(f"""
            <div class="snapshot-item">
                <span class="snapshot-icon">{icon}</span>
                <div>
                    <div class="snapshot-label">{label}</div>
                    <div class="snapshot-status {cls}">{status}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


def _render_kpi_cards():
    """Render KPI cards — #1 (layer gaps), #2 (fix Dead Stock/Churn prior rendering)."""
    signals = st.session_state.signals

    cards = []
    for s in signals:
        # Format values
        if s.metric in ("Total Revenue",):
            val_str = f"${s.current_value:,.0f}"
            prior_str = f"Previous: ${s.prior_value:,.0f}"
        elif s.metric in ("Avg Conversion Rate", "On-Time Delivery Rate"):
            val_str = f"{s.current_value:.1%}" if s.current_value < 2 else f"{s.current_value:,.2f}"
            prior_str = f"Previous: {s.prior_value:.1%}" if s.prior_value < 2 else f"Previous: {s.prior_value:,.2f}"
        elif s.metric in ("Avg Delivery Days",):
            val_str = f"{s.current_value:.1f}d"
            prior_str = f"Previous: {s.prior_value:.1f}d"
        elif s.metric.startswith("Churn"):
            val_str = f"{int(s.current_value)} / {int(s.prior_value)}"
            # #2 — Plain text, no HTML that could break
            prior_str = "high-risk / total scored"
        elif s.metric == "Dead Stock Rate":
            val_str = f"{s.current_value:.1%}"
            # #2 — Plain text, no HTML that could break
            prior_str = "current snapshot"
        else:
            val_str = f"{s.current_value:,.0f}"
            prior_str = f"Previous: {s.prior_value:,.0f}"

        # Delta calculation
        if s.metric in ("Dead Stock Rate", "Churn Risk (Inference Batch)"):
            # #2 — These have no delta, just show value
            delta_str = ""
            delta_class = ""
        elif s.delta_pct == 0:
            delta_class = "delta-flat"
            delta_str = "—"
        elif s.direction == "up":
            delta_class = "delta-down-bad" if s.metric in ("Avg Delivery Days",) else "delta-up"
            delta_str = f"↑ {abs(s.delta_pct):.1%}"
        elif s.direction == "down":
            delta_class = "delta-down-good" if s.metric in ("Avg Delivery Days",) else "delta-down-bad"
            delta_str = f"↓ {abs(s.delta_pct):.1%}"
        else:
            actual = abs(s.delta_pct)
            if actual > 0.0001:
                arrow = "↑" if s.delta_pct > 0 else "↓"
                delta_str = f"{arrow} {actual:.1%}"
                delta_class = "delta-flat"
            else:
                delta_str = "—"
                delta_class = "delta-flat"

        label = s.metric.replace("(Inference Batch)", "").strip()
        delta_html = f'<span class="delta {delta_class}">{delta_str}</span>' if delta_str else ""
        # #1 — <span> renders reliably in nested contexts; CSS makes it display:block
        prior_html = f'<span class="prior">{prior_str}</span>'

        cards.append((label, val_str, delta_html, prior_html))

    # #1 — Render with layer labels and gaps
    row1 = cards[:4]
    row2 = cards[4:]

    st.markdown('<div class="kpi-layer-label">Business KPIs</div>', unsafe_allow_html=True)
    cols = st.columns(len(row1))
    for i, (label, val, delta, prior) in enumerate(row1):
        with cols[i]:
            st.markdown(f"""
            <div class="kpi-card">
                <div>
                    <div class="label">{label}</div>
                    <div class="value">{val}</div>
                </div>
                <div>
                    {delta}
                    {prior}
                </div>
            </div>
            """, unsafe_allow_html=True)

    if row2:
        st.markdown('<div class="kpi-layer-label">Operations &amp; Model</div>', unsafe_allow_html=True)
        cols2 = st.columns(len(row2))
        for i, (label, val, delta, prior) in enumerate(row2):
            with cols2[i]:
                st.markdown(f"""
                <div class="kpi-card">
                    <div>
                        <div class="label">{label}</div>
                        <div class="value">{val}</div>
                    </div>
                    <div>
                        {delta}
                        {prior}
                    </div>
                </div>
                """, unsafe_allow_html=True)


def _derive_business_impact(finding, signals) -> str:
    """Derive an observational business impact statement. #6 — no em dashes."""
    title_lower = finding.title.lower()
    signals_dict = {s.metric: s for s in signals}

    if "revenue" in title_lower:
        rev = signals_dict.get("Total Revenue")
        orders = signals_dict.get("Orders Fulfilled")
        users = signals_dict.get("Active Users")
        if rev and orders and users:
            if rev.direction == "up" and orders.direction == "up":
                if abs(users.delta_pct) < 0.05:
                    return (
                        "Revenue and fulfilled orders increased together while user growth "
                        "remained modest, indicating improved commercial performance from "
                        "the existing customer base during the reporting period."
                    )
                return (
                    "Revenue and order volume moved in the same direction, "
                    "suggesting broad-based commercial activity change."
                )
            if rev.direction == "down":
                return "Revenue decline may affect downstream planning. Further segmentation is needed."

    if "orders" in title_lower:
        orders = signals_dict.get("Orders Fulfilled")
        rev = signals_dict.get("Total Revenue")
        if orders and rev and orders.direction == "up" and rev.direction == "up":
            return "Order volume growth coincided with revenue growth, indicating consistent demand across the reporting period."

    if "monitoring" in title_lower or "model" in title_lower:
        return "Model monitoring flagged conditions that may reduce confidence in future churn predictions if left unaddressed."

    if "delivery" in title_lower or "fulfillment" in title_lower:
        return "Fulfillment performance changes directly affect customer satisfaction and may influence repeat purchase behavior."

    if "dead stock" in title_lower or "inventory" in title_lower:
        return "Inventory health affects carrying costs and capital allocation. Dead stock represents tied-up capital with no recent sales velocity."

    if "churn" in title_lower:
        return "Elevated churn risk in the inference batch may indicate a segment requiring re-engagement before the predicted window closes."

    return ""


def _render_findings():
    """Render priority-ordered finding cards. #6 — no em dashes in monitoring text."""
    findings = st.session_state.findings
    signals = st.session_state.signals

    st.markdown('<div class="section-header" id="key-findings">Key Findings</div>', unsafe_allow_html=True)

    for f in findings:
        is_positive = _is_positive_finding(f)
        is_monitoring = "monitoring" in f.title.lower() or "model" in f.title.lower()

        if f.priority == "P1":
            card_class = "p1-positive" if is_positive else "p1-negative"
            p_class = "priority-p1-positive" if is_positive else "priority-p1-negative"
            p_label = "Opportunity" if is_positive else "Critical"
        elif f.priority == "P2":
            card_class = "p2"
            p_class = "priority-p2"
            p_label = "Review"
        else:
            card_class = "p3"
            p_class = "priority-p3"
            p_label = "Monitor"

        if f.confidence >= 0.8:
            ev_label, ev_class = "Strong", "evidence-strong"
        elif f.confidence >= 0.6:
            ev_label, ev_class = "Moderate", "evidence-moderate"
        else:
            ev_label, ev_class = "Limited", "evidence-limited"

        desc = f.description
        for attr in ("current_period", "prior_period"):
            val = getattr(st.session_state, attr, None)
            if val:
                desc = desc.replace(str(val), _fmt_period(val))
        desc = _fmt_dc(desc)

        # #6 #11 — Monitoring finding: business language, no jargon, no em dashes
        if is_monitoring:
            mon = st.session_state.monitoring_summary
            drift_detected = mon.get("prediction_drift_detected", False)
            model_degraded = mon.get("model_degraded", False)

            if drift_detected and not model_degraded:
                desc = (
                    "Prediction behavior has shifted compared to the training period. "
                    f"Current business impact appears low, model accuracy remains stable "
                    f"(less than {abs(float(mon.get('auc_drop_pct', 0))):.1f}% change). "
                    "If drift continues, customer churn predictions may become less reliable "
                    "over the coming weeks."
                )
            elif model_degraded:
                desc = (
                    "The churn prediction model has degraded. Prediction accuracy has dropped "
                    "and outputs should be treated with lower confidence until the model is retrained."
                )
            else:
                desc = "All monitoring checks passed. The churn prediction model is operating within expected parameters."

        impact_text = _derive_business_impact(f, signals)
        impact_html = f'<div class="finding-impact">{impact_text}</div>' if impact_text else ""

        evidence_items = ""
        for ev in f.evidence[:4]:
            ev_clean = _fmt_dc(ev)
            evidence_items += f"<li>{ev_clean}</li>"
        evidence_html = f'<div class="finding-evidence"><ul>{evidence_items}</ul></div>' if evidence_items else ""

        domain_map = {
            "revenue": "revenue", "customers": "customers",
            "fulfillment": "fulfillment", "inventory": "inventory",
            "churn": "customers", "monitoring": "customers",
        }
        explore_domain = ""
        for key in domain_map:
            if key in f.title.lower() or key in f.recommended_action.lower():
                explore_domain = domain_map[key]
                break

        explore_html = ""
        if explore_domain:
            ctx = f"{f.priority} — {f.title}".replace(" ", "+")
            explore_html = f'<a class="explore-link" href="?page=explorer&domain={explore_domain}&context={ctx}">Explore →</a>'

        st.markdown(f"""
        <div class="finding-card {card_class}">
            <div class="finding-title">
                <span class="priority-badge {p_class}">{p_label}</span>
                {f.title}
            </div>
            <div class="finding-desc">{desc}</div>
            {impact_html}
            {evidence_html}
            <div class="finding-meta">
                <span>Evidence: <span class="evidence-badge {ev_class}">{ev_label}</span></span>
                <span>Action: {f.recommended_action}</span>
                {explore_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if is_monitoring:
            mon = st.session_state.monitoring_summary
            with st.expander("Technical details", expanded=False):
                st.markdown(
                    f"- **Data drift:** {mon.get('features_drifted', 0)}/{mon.get('features_tested', 0)} features drifted\n"
                    f"- **Prediction drift:** {mon.get('prediction_drift_method', 'N/A')} = {mon.get('prediction_drift_score', 'N/A')} "
                    f"(threshold: {mon.get('prediction_drift_threshold', 'N/A')})\n"
                    f"- **AUC:** {mon.get('auc_ref', 'N/A')} → {mon.get('auc_cur', 'N/A')} "
                    f"(drop: {mon.get('auc_drop_pct', 'N/A')}%)\n"
                    f"- **Recommendation:** {mon.get('recommendation', 'N/A')}"
                )


def _render_briefing():
    """Render the executive briefing. #3 — strip Status column. #9 — finding hierarchy."""
    st.markdown('<div class="section-header">Executive Briefing</div>', unsafe_allow_html=True)

    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    brief_files = sorted(glob.glob(str(reports_dir / "executive_brief*.md")), reverse=True)

    if brief_files:
        latest_path = Path(brief_files[0])
        briefing_text = latest_path.read_text(encoding="utf-8")

        if len(brief_files) > 1:
            with st.expander("📅 Briefing history", expanded=False):
                selected = st.selectbox(
                    "Select a past briefing:",
                    brief_files,
                    format_func=lambda x: Path(x).stem.replace("executive_brief", "Brief").replace("_", " "),
                    label_visibility="collapsed",
                )
                if selected != brief_files[0]:
                    briefing_text = Path(selected).read_text(encoding="utf-8")

        lines = briefing_text.split("\n")
        content_start = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                content_start = i
                break
        clean_text = "\n".join(lines[content_start:])

        st.markdown(f'<div class="briefing-container">{_md_to_html(clean_text)}</div>', unsafe_allow_html=True)
    else:
        st.info("No executive briefing has been generated yet. Run the agent notebook first.")


def _md_to_html(md_text: str) -> str:
    """Markdown-to-HTML. #3 — strip Status column from header AND data rows.
    #9 — Key Findings hierarchy: bold title line, sub-points indented."""

    html_lines = []
    in_table = False
    in_list = False
    table_headers = []
    status_col_idx = -1  # #3 — track the Status column index

    for line in md_text.split("\n"):
        stripped = line.strip()

        # Table rows
        if "|" in stripped and not stripped.startswith("#"):
            cols = [c.strip() for c in stripped.split("|") if c.strip()]
            if all(c.replace("-", "").replace(":", "") == "" for c in cols):
                continue  # separator row
            if not in_table:
                html_lines.append("<table>")
                in_table = True
                table_headers = [c.lower() for c in cols]
                # #3 — Find Status column index
                status_col_idx = -1
                for idx, h in enumerate(table_headers):
                    if h == "status":
                        status_col_idx = idx
                        break
                # Build header row, skipping Status
                header_cells = []
                for idx, c in enumerate(cols):
                    if idx == status_col_idx:
                        continue
                    header_cells.append(f"<th>{c}</th>")
                html_lines.append("<tr>" + "".join(header_cells) + "</tr>")
            else:
                cells = []
                for j, c in enumerate(cols):
                    # #3 — Skip Status column entirely
                    if j == status_col_idx:
                        continue
                    cell_class = ""
                    if j < len(table_headers) and table_headers[j] in ("change", "delta", "% change"):
                        if c.startswith("+") or c.startswith("↑"):
                            cell_class = ' class="cell-green"'
                        elif c.startswith("-") or c.startswith("↓"):
                            cell_class = ' class="cell-red"'
                        elif c in ("N/A", "—"):
                            cell_class = ' class="cell-amber"'
                        else:
                            cell_class = ' class="cell-flat"'
                    cells.append(f"<td{cell_class}>{c}</td>")
                html_lines.append("<tr>" + "".join(cells) + "</tr>")
            continue
        elif in_table:
            html_lines.append("</table>")
            in_table = False
            table_headers = []
            status_col_idx = -1

        # #3 — Key Findings hierarchy detection
        # The LLM emits finding titles as "- **Title**" (bullet + entirely bold, no colon inside)
        # and sub-points as "- **Hypothesis:** text" or "**Hypothesis:**" then plain text.
        # Rewrite these into a proper heading + indented sub-list structure.

        # Standalone bold (not a bullet): "**Some finding title.**"
        bold_only_match = re.match(r'^\*\*(.+?)\*\*\.?$', stripped)
        if bold_only_match and not stripped.startswith("- ") and not stripped.startswith("* "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            title_text = bold_only_match.group(1)
            html_lines.append(f'<div class="finding-heading">{title_text}</div>')
            continue

        # Bulleted line where the ENTIRE content is bold (no colon inside) → finding title
        bullet_bold_title = re.match(r'^[-*]\s+\*\*([^:]+?)\*\*\.?$', stripped)
        if bullet_bold_title:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            title_text = bullet_bold_title.group(1)
            html_lines.append(f'<div class="finding-heading">{title_text}</div>')
            continue

        # Bulleted line starting with a bold LABEL followed by a colon → sub-point
        # e.g. "- **Hypothesis:** Driven by..." or "- **Confidence:** 100%"
        bullet_sublabel = re.match(r'^[-*]\s+\*\*([A-Za-z][A-Za-z ]+?):\*\*\s*(.*)$', stripped)
        if bullet_sublabel:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            label = bullet_sublabel.group(1).strip()
            content = bullet_sublabel.group(2).strip()
            html_lines.append(f'<div class="finding-sublabel">{label}</div>')
            if content:
                content_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                html_lines.append(
                    f'<ul class="finding-sublist"><li>{content_html}</li></ul>'
                )
            continue

        # Nested list items (2+ space indent)
        if stripped.startswith("  - ") or stripped.startswith("  * ") or stripped.startswith("    - "):
            content = stripped.lstrip(" -*")
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f"<li style='margin-left:1.5rem'>{content}</li>")
            continue

        # Regular list items (fallback for lists not matching the finding patterns above)
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            content = stripped[2:]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f"<li>{content}</li>")
            continue
        elif in_list and stripped == "":
            html_lines.append("</ul>")
            in_list = False

        # Headers
        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped:
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_lines.append(f"<p>{content}</p>")

    if in_table:
        html_lines.append("</table>")
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _is_number_like(cell: str) -> bool:
    """Return True if a table cell looks like a number (int, float, currency, percentage)."""
    s = cell.strip().replace(",", "").replace("$", "").replace("%", "").replace("+", "").replace("-", "")
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def _render_markdown_table(table_lines: list) -> str:
    """Convert a list of pipe-delimited markdown table lines into styled HTML table.
    Uses .num class for right-aligned numeric cells."""
    if len(table_lines) < 2:
        return ""

    def parse_row(line):
        # Strip leading/trailing pipe, then split
        parts = line.strip().strip("|").split("|")
        return [p.strip() for p in parts]

    header_cells = parse_row(table_lines[0])
    # table_lines[1] is the separator like |---|:---:|---:|
    data_rows = [parse_row(line) for line in table_lines[2:] if line.strip()]

    # Determine which columns are numeric (majority of cells number-like)
    num_cols = len(header_cells)
    numeric_flags = []
    for j in range(num_cols):
        col_vals = [row[j] for row in data_rows if j < len(row)]
        if col_vals and sum(1 for v in col_vals if _is_number_like(v)) >= len(col_vals) * 0.6:
            numeric_flags.append(True)
        else:
            numeric_flags.append(False)

    html = ["<table>"]
    html.append("<tr>" + "".join(f"<th>{h}</th>" for h in header_cells) + "</tr>")
    for row in data_rows:
        cells = []
        for j, cell in enumerate(row):
            cls = ' class="num"' if j < len(numeric_flags) and numeric_flags[j] else ""
            cells.append(f"<td{cls}>{cell}</td>")
        html.append("<tr>" + "".join(cells) + "</tr>")
    html.append("</table>")
    return "\n".join(html)


def _is_table_line(line: str) -> bool:
    """Detect a pipe-delimited markdown table row (at least 2 pipes)."""
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def _is_separator_line(line: str) -> bool:
    """Detect a markdown table separator: |---|:---:|---:|"""
    s = line.strip().strip("|")
    if not s:
        return False
    parts = [p.strip() for p in s.split("|")]
    return all(re.match(r"^:?-+:?$", p) for p in parts if p)


def _format_chat_html(raw_text: str) -> str:
    """Convert raw markdown chat response to styled HTML.

    #4 — Detects pipe-delimited markdown tables (from to_markdown() output)
         and renders them as styled HTML tables. Handles tables both inside
         and outside code blocks.
    Also converts **Answer**, **Why It Matters** into styled section labels,
    and code blocks into <pre> tags. Fixes ```</div> leak.
    """

    # Remove any leaked HTML tags from code block boundaries
    raw_text = raw_text.replace("```</div>", "```")
    raw_text = raw_text.replace('```"', '```')

    lines = raw_text.split("\n")
    html_parts = []
    in_code = False
    code_buffer = []  # accumulate lines while in code block, to check for embedded tables

    def flush_code_buffer():
        """Flush accumulated code-block content. If it contains a markdown table,
        render the table part as HTML and any non-table lines as <pre>."""
        if not code_buffer:
            return

        # Find contiguous table lines
        table_start = None
        for idx, ln in enumerate(code_buffer):
            if _is_table_line(ln) and idx + 1 < len(code_buffer) and _is_separator_line(code_buffer[idx + 1]):
                table_start = idx
                break

        if table_start is None:
            # No table detected — render as normal <pre>
            html_parts.append("<pre>")
            html_parts.extend(code_buffer)
            html_parts.append("</pre>")
        else:
            # Non-table lines before table (if any) go in a <pre>
            pre_lines = code_buffer[:table_start]
            if any(l.strip() for l in pre_lines):
                html_parts.append("<pre>")
                html_parts.extend(pre_lines)
                html_parts.append("</pre>")

            # Collect table lines: header + separator + data rows until non-table line
            table_lines = [code_buffer[table_start], code_buffer[table_start + 1]]
            i = table_start + 2
            while i < len(code_buffer) and _is_table_line(code_buffer[i]):
                table_lines.append(code_buffer[i])
                i += 1
            html_parts.append(_render_markdown_table(table_lines))

            # Non-table trailing lines
            trailing = code_buffer[i:]
            if any(l.strip() for l in trailing):
                html_parts.append("<pre>")
                html_parts.extend(trailing)
                html_parts.append("</pre>")

        code_buffer.clear()

    # First pass: also detect standalone (non-code-block) tables at the top level
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Code block boundaries
        if stripped.startswith("```"):
            if in_code:
                flush_code_buffer()
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_buffer.append(line)
            i += 1
            continue

        # Standalone table (outside code block): header row followed by separator row
        if _is_table_line(stripped) and i + 1 < len(lines) and _is_separator_line(lines[i + 1]):
            table_lines = [stripped, lines[i + 1].strip()]
            j = i + 2
            while j < len(lines) and _is_table_line(lines[j].strip()):
                table_lines.append(lines[j].strip())
                j += 1
            html_parts.append(_render_markdown_table(table_lines))
            i = j
            continue

        # Section headings — **Answer**, **Why It Matters**, etc.
        heading_match = re.match(r'^\*\*(.+?)\*\*:?\s*$', stripped)
        if heading_match:
            label = heading_match.group(1)
            html_parts.append(f'<div class="chat-section-label">{label}</div>')
            i += 1
            continue

        # Full-line bold as heading
        if stripped.startswith("**") and stripped.endswith("**") and stripped.count("**") == 2:
            label = stripped.strip("*").strip(":").strip()
            html_parts.append(f'<div class="chat-section-label">{label}</div>')
            i += 1
            continue

        # Separator
        if stripped == "---":
            html_parts.append("<hr style='border:none; border-top:1px solid #E2E8F0; margin:0.75rem 0;'>")
            i += 1
            continue

        # Regular text
        if stripped:
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_parts.append(f"<p style='margin:0.3rem 0;'>{content}</p>")
        i += 1

    if in_code:
        flush_code_buffer()

    return "\n".join(html_parts)


def _render_followup():
    """Render suggested follow-up buttons and interactive chat.
    #7 — 'Suggested Questions (click to investigate)'
    #5 — Chat responses rendered as styled HTML."""
    st.markdown('<div class="section-header">Follow-Up</div>', unsafe_allow_html=True)

    suggested = st.session_state.suggested_questions

    # #7 — Clean label format
    st.markdown("**Suggested Questions** (click to investigate)")
    cols = st.columns(min(len(suggested), 3))
    for i, (question, domain) in enumerate(suggested):
        with cols[i % len(cols)]:
            if st.button(f"🔍 {question}", key=f"suggest_{i}", use_container_width=True):
                st.session_state.pending_question = question

    user_question = st.chat_input("Ask a follow-up question about the findings...")

    question_to_process = None
    if user_question:
        question_to_process = user_question
    elif "pending_question" in st.session_state:
        question_to_process = st.session_state.pending_question
        del st.session_state.pending_question

    if question_to_process:
        st.session_state.chat_history.append({"role": "user", "content": question_to_process})

        with st.spinner("Investigating..."):
            from src.agent import create_tools, build_agent, ask_followup

            if "agent_tools" not in st.session_state:
                project_root = st.session_state.get("project_root", Path(__file__).resolve().parent.parent)
                tools = create_tools(
                    st.session_state.signals,
                    st.session_state.findings,
                    st.session_state.con,
                    st.session_state.monitoring_summary,
                    charts_dir=project_root / "reports" / "charts",
                )
                _, llm, llm_with_tools = build_agent(
                    st.session_state.signals,
                    st.session_state.findings,
                    tools,
                )
                st.session_state.agent_tools = tools
                st.session_state.llm = llm
                st.session_state.llm_with_tools = llm_with_tools

            answer = ask_followup(
                question_to_process,
                st.session_state.llm,
                st.session_state.llm_with_tools,
                st.session_state.agent_tools,
                st.session_state.con,
                st.session_state.findings,
            )

        st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # #5 — Render chat with styled HTML
    if st.session_state.chat_history:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                styled_html = _format_chat_html(msg["content"])
                st.markdown(f'<div class="chat-response">{styled_html}</div>', unsafe_allow_html=True)


def render_executive_page():
    """Main render function."""
    inject_css()
    _render_header()
    _render_executive_snapshot()
    _render_kpi_cards()
    _render_findings()
    _render_briefing()
    _render_followup()
