"""
Page 2 — Business Explorer

v5 — Production Readiness Sprint:
  #5  cliponaxis=False globally to fix all label clipping systemically
  #6  Plotly toolbar: hover-to-show (Plotly default), not always-off
  #7  Shared global CHART_LAYOUT (r=90, t=55) — every chart inherits
  #8  Lollipop rename x-axis, label reference line, fix text positioning
  #9  SLA annotation split into two lines, positioned inside chart area
  #10 Explorer section headings (Business Summary / Evidence / Recommended Action)
  #11 Recommendation card with action-level indicator (severity-driven)
  #12 Editorial consistency across all recommendations (shared component)
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from app.styles import inject_css


# ─────────────────────────────────────────────────────────────────────
# Shared chart layout — every chart inherits, override only when needed.
# #7 — Consistency is underrated: one source of truth for chart styling.
# ─────────────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    margin=dict(l=20, r=90, t=55, b=40),
)
# #6 — Plotly default hover-to-show toolbar. No config override.

# #5 — Applied via fig.update_traces(cliponaxis=False) after every trace update.
# This is the systemic fix for label clipping across every chart on the page.


# ─────────────────────────────────────────────────────────────────────
# Shared UI helpers — used across every domain section.
# #10 — Explorer section headings; #11/#12 — Recommendation card.
# ─────────────────────────────────────────────────────────────────────
def _section_label(text: str):
    """Render a small uppercase section label above each block of content.
    Creates the Business Summary → Evidence → Recommended Action narrative."""
    st.markdown(
        f'<div class="explorer-section-label">{text}</div>',
        unsafe_allow_html=True,
    )


# Action-level presets — severity → (icon, label, css class)
_ACTION_LEVELS = {
    "green":  ("🟢", "No Action Required", "rec-green"),
    "yellow": ("🟡", "Monitor",             "rec-yellow"),
    "orange": ("🟠", "Investigate",         "rec-orange"),
    "red":    ("🔴", "Immediate Action",    "rec-red"),
}


def _render_recommendation(level: str, recommendation: str, business_impact: str):
    """Render a recommendation card with an action-level indicator.

    #11 — Action-level indicator (🟢/🟡/🟠/🔴) driven by signal severity.
    #12 — Consistent structure across all sections:
          [action-level line] → [recommendation, 1-2 sentences] → [business impact]
    """
    icon, label, css_class = _ACTION_LEVELS.get(level, _ACTION_LEVELS["green"])
    st.markdown(
        f"""
        <div class="recommendation-card {css_class}">
            <div class="rec-action-level"><span>{icon}</span><span>{label}</span></div>
            <div class="rec-text">{recommendation}</div>
            <div class="rec-impact">{business_impact}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_period(period) -> str:
    try:
        return period.strftime("%b %Y")
    except Exception:
        s = str(period)
        return s[:7] if len(s) >= 7 else s


def _render_header():
    current = st.session_state.current_period
    prior = st.session_state.prior_period
    period_str = f"{_fmt_period(prior)} → {_fmt_period(current)}"

    st.markdown(f"""
    <div class="header-bar">
        <div class="header-top-row">
            <div>
                <p class="platform-name">E-Commerce Intelligence Platform</p>
                <h1>Business Explorer</h1>
                <p class="subtitle">Investigate and verify · {period_str}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_kpi_cards():
    signals = st.session_state.signals

    display_metrics = [
        ("Total Revenue", "$", 0),
        ("Orders Fulfilled", "", 0),
        ("Active Users", "", 0),
        ("Avg Delivery Days", "", 1),
        ("On-Time Delivery Rate", "", 1),
    ]

    cols = st.columns(len(display_metrics))
    for i, (metric_name, prefix, decimals) in enumerate(display_metrics):
        sig = next((s for s in signals if s.metric == metric_name), None)
        if not sig:
            continue

        if prefix == "$":
            val_str = f"${sig.current_value:,.{decimals}f}"
        elif sig.current_value < 2 and metric_name in ("On-Time Delivery Rate",):
            val_str = f"{sig.current_value:.1%}"
        else:
            val_str = f"{sig.current_value:,.{decimals}f}"

        actual_delta = abs(sig.delta_pct)
        if actual_delta < 0.0001:
            delta_str = "—"
            delta_class = "delta-flat"
        elif sig.delta_pct > 0:
            delta_str = f"↑ {actual_delta:.1%}"
            delta_class = "delta-down-bad" if metric_name in ("Avg Delivery Days",) else "delta-up"
        else:
            delta_str = f"↓ {actual_delta:.1%}"
            delta_class = "delta-down-good" if metric_name in ("Avg Delivery Days",) else "delta-down-bad"

        with cols[i]:
            st.markdown(f"""
            <div class="kpi-card">
                <div>
                    <div class="label">{metric_name}</div>
                    <div class="value">{val_str}</div>
                </div>
                <span class="delta {delta_class}">{delta_str}</span>
            </div>
            """, unsafe_allow_html=True)


def _render_context_banner():
    params = st.query_params
    context = params.get("context", "")
    if context:
        context_text = context.replace("+", " ")
        st.markdown(f"""
        <div class="context-banner">
            <span>📌</span>
            <span>Opened from: <strong>{context_text}</strong></span>
        </div>
        """, unsafe_allow_html=True)


def render_explorer_page():
    inject_css()
    _render_header()
    _render_context_banner()
    _render_kpi_cards()

    con = st.session_state.con

    default_domain = st.query_params.get("domain", "revenue")
    domain_options = [
        "Revenue & Growth",
        "Customer Retention",
        "Product Portfolio",
        "Operations & SLA",
        "Inventory Actions",
    ]
    domain_map = {
        "revenue": "Revenue & Growth", "customers": "Customer Retention",
        "churn": "Customer Retention", "fulfillment": "Operations & SLA",
        "inventory": "Inventory Actions", "monitoring": "Revenue & Growth",
    }
    default_idx = 0
    mapped = domain_map.get(default_domain, "Revenue & Growth")
    if mapped in domain_options:
        default_idx = domain_options.index(mapped)

    selected_domain = st.selectbox("Explore domain:", domain_options, index=default_idx)
    st.markdown("---")

    if selected_domain == "Revenue & Growth":
        _render_revenue_section(con)
    elif selected_domain == "Customer Retention":
        _render_customers_section(con)
    elif selected_domain == "Product Portfolio":
        _render_products_section(con)
    elif selected_domain == "Operations & SLA":
        _render_fulfillment_section(con)
    elif selected_domain == "Inventory Actions":
        _render_inventory_section(con)


def _render_revenue_section(con):
    """Revenue & Growth. Narrative flow: Business Summary → Evidence → Recommended Action."""
    signals = st.session_state.signals
    rev_sig = next((s for s in signals if s.metric == "Total Revenue"), None)
    orders_sig = next((s for s in signals if s.metric == "Orders Fulfilled"), None)

    # ── Business Summary ──
    _section_label("Business Summary")
    if rev_sig and orders_sig:
        st.markdown(f"""
        <div class="insight-callout">
            Revenue grew <strong>{abs(rev_sig.delta_pct):.1%}</strong> month-over-month to
            <strong>${rev_sig.current_value:,.0f}</strong>, driven by a
            <strong>{abs(orders_sig.delta_pct):.1%}</strong> increase in fulfilled orders.
            Growth was broad-based across all distribution centers.
        </div>
        """, unsafe_allow_html=True)

    # ── Evidence ──
    _section_label("Evidence")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Monthly Revenue Trend**")
        df = con.execute("""
            SELECT order_month, SUM(total_revenue) AS revenue
            FROM fulfillment_metrics
            GROUP BY order_month ORDER BY order_month
        """).fetchdf()
        df["order_month"] = df["order_month"].astype(str).str[:7]
        df_recent = df.tail(12)

        fig = px.line(df_recent, x="order_month", y="revenue",
                      labels={"order_month": "Month", "revenue": "Revenue ($)"}, markers=True)
        fig.update_traces(line_color="#2563EB", marker_size=6,
                          texttemplate="%{y:$,.0f}", textposition="top center",
                          textfont_size=8, mode="lines+markers+text",
                          cliponaxis=False)  # #5
        fig.update_layout(height=380, yaxis_tickformat="$,.0f", xaxis_tickangle=-45,
                          yaxis_rangemode="tozero", **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)  # #6 — default toolbar

    with col2:
        st.markdown("**Revenue by Distribution Center** (current period)")
        df = con.execute("""
            SELECT distribution_center_name, SUM(total_revenue) AS revenue
            FROM fulfillment_metrics
            WHERE order_month = (SELECT MAX(order_month) FROM fulfillment_metrics)
            GROUP BY distribution_center_name ORDER BY revenue DESC
        """).fetchdf()
        fig = px.bar(df, x="revenue", y="distribution_center_name", orientation="h",
                     labels={"distribution_center_name": "", "revenue": "Revenue ($)"},
                     text="revenue")
        fig.update_traces(marker_color="#2563EB", texttemplate="$%{x:,.0f}", textposition="outside",
                          textfont_size=9, cliponaxis=False)  # #5
        fig.update_layout(height=380, xaxis_tickformat="$,.0f", yaxis_autorange="reversed", **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)  # #6

    # ── Recommended Action ──
    _section_label("Recommended Action")
    top_dcs = con.execute("""
        SELECT distribution_center_name, SUM(total_revenue) AS rev
        FROM fulfillment_metrics
        WHERE order_month = (SELECT MAX(order_month) FROM fulfillment_metrics)
        GROUP BY distribution_center_name ORDER BY rev DESC LIMIT 3
    """).fetchdf()
    top_names = ", ".join(top_dcs["distribution_center_name"].tolist())

    # #11 — Action level driven by revenue signal severity
    if rev_sig and rev_sig.severity == "notable" and rev_sig.direction == "up":
        level = "green"
    elif rev_sig and rev_sig.severity == "critical":
        level = "orange"
    else:
        level = "yellow"

    _render_recommendation(
        level=level,
        recommendation=(
            f"Sustain the current growth trajectory. Continue allocating marketing spend toward "
            f"top-performing centers ({top_names}), and verify conversion rates before increasing "
            f"the overall acquisition budget."
        ),
        business_impact=(
            "Broad-based revenue growth across all fulfillment centers indicates healthy demand "
            "rather than a single-center anomaly."
        ),
    )


def _render_customers_section(con):
    """Customer Retention. Narrative flow: Business Summary → Evidence → Recommended Action."""
    # Get churn stats up front so summary + recommendation can reference the same numbers
    churn_stats = con.execute("""
        SELECT COUNT(*) AS total,
               COUNT(CASE WHEN churn_probability > 0.7 THEN 1 END) AS high_risk
        FROM predictions
    """).fetchone()
    high_risk_count = churn_stats[1] if churn_stats else 0
    total_scored = churn_stats[0] if churn_stats else 0
    high_risk_pct = (high_risk_count / max(total_scored, 1)) if total_scored else 0

    # ── Business Summary ──
    _section_label("Business Summary")
    st.markdown(f"""
    <div class="insight-callout">
        <strong>{high_risk_count:,}</strong> of <strong>{total_scored:,}</strong> scored customers
        ({high_risk_pct:.1%}) are predicted to churn within the next 90 days.
    </div>
    """, unsafe_allow_html=True)

    # Churn definition explainer (glossary-style, separate from summary)
    st.markdown("""
    <div class="definition-note">
        <strong>Churn</strong> = customers predicted to make no purchase within the next 90 days.
        The model considers signals like days since last purchase, order frequency, and
        average order value to estimate risk. A probability above 0.7 is classified as high-risk.
    </div>
    """, unsafe_allow_html=True)

    # ── Evidence ──
    _section_label("Evidence")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Churn Probability Distribution**")
        df = con.execute("SELECT churn_probability FROM predictions").fetchdf()
        fig = px.histogram(df, x="churn_probability", nbins=30,
                           labels={"churn_probability": "Churn Probability"})
        fig.update_traces(marker_color="#DC2626", marker_line_width=0.5, marker_line_color="#991B1B",
                          cliponaxis=False)  # #5
        fig.add_vline(x=0.7, line_dash="dash", line_color="#0F172A",
                      annotation_text="High-risk threshold (0.7)")
        fig.update_layout(height=350, showlegend=False, yaxis_title="Customers", **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)  # #6

    with col2:
        st.markdown("**High-Risk Churn by Traffic Source**")
        df = con.execute("""
            SELECT c.traffic_source, COUNT(*) AS high_risk_customers
            FROM predictions p JOIN customer_360 c ON p.user_id = c.user_id
            WHERE p.churn_probability > 0.7
            GROUP BY c.traffic_source ORDER BY high_risk_customers DESC
        """).fetchdf()
        fig = px.pie(df, values="high_risk_customers", names="traffic_source", hole=0.4)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=350, showlegend=False, **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)  # #6

    st.markdown("**Customer Segments by Traffic Source**")
    df = con.execute("""
        SELECT traffic_source, COUNT(*) AS customers,
               ROUND(AVG(order_count), 2) AS avg_orders,
               ROUND(AVG(lifetime_spend), 2) AS avg_spend,
               ROUND(AVG(return_rate) * 100, 2) AS avg_return_rate_pct
        FROM customer_360 WHERE order_count > 0
        GROUP BY traffic_source ORDER BY customers DESC
    """).fetchdf()
    df.columns = ["Traffic Source", "Customers", "Avg Orders", "Avg Spend ($)", "Avg Return Rate (%)"]
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Avg Spend ($)": st.column_config.NumberColumn(format="$%.2f"),
                     "Avg Return Rate (%)": st.column_config.NumberColumn(format="%.2f%%"),
                 })

    # ── Recommended Action ──
    _section_label("Recommended Action")
    top_churn_source = con.execute("""
        SELECT c.traffic_source, COUNT(*) AS cnt
        FROM predictions p JOIN customer_360 c ON p.user_id = c.user_id
        WHERE p.churn_probability > 0.7
        GROUP BY c.traffic_source ORDER BY cnt DESC LIMIT 1
    """).fetchone()
    source_name = top_churn_source[0] if top_churn_source else "Search"

    # #11 — Action level driven by the size of the high-risk cohort
    if high_risk_pct >= 0.5:
        level = "orange"
    elif high_risk_pct >= 0.3:
        level = "yellow"
    else:
        level = "green"

    _render_recommendation(
        level=level,
        recommendation=(
            f"Prioritize re-engagement for the {source_name} traffic segment, which contributes "
            f"the largest share of predicted churn. Launch targeted campaigns before the 90-day "
            f"prediction window closes for the highest-probability customers."
        ),
        business_impact=(
            f"Retaining even a fraction of the {high_risk_count:,} high-risk customers preserves "
            "downstream revenue at a lower cost than net-new acquisition."
        ),
    )


def _render_products_section(con):
    """Product Portfolio. Narrative flow: Business Summary → Evidence → Recommended Action."""
    top_cat = con.execute("""
        SELECT category, SUM(total_revenue) AS revenue
        FROM product_performance GROUP BY category ORDER BY revenue DESC LIMIT 1
    """).fetchone()

    # ── Business Summary ──
    _section_label("Business Summary")
    if top_cat:
        st.markdown(f"""
        <div class="insight-callout">
            <strong>{top_cat[0]}</strong> leads all categories with
            <strong>${top_cat[1]:,.0f}</strong> in total revenue.
        </div>
        """, unsafe_allow_html=True)

    # ── Evidence ──
    _section_label("Evidence")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Top 10 Categories by Revenue**")
        df = con.execute("""
            SELECT category, SUM(total_revenue) AS revenue
            FROM product_performance GROUP BY category ORDER BY revenue DESC LIMIT 10
        """).fetchdf()
        fig = px.bar(df, x="revenue", y="category", orientation="h",
                     labels={"category": "", "revenue": "Revenue ($)"},
                     text="revenue")
        fig.update_traces(marker_color="#2563EB", texttemplate="$%{x:,.0f}", textposition="outside",
                          textfont_size=9, cliponaxis=False)  # #5
        fig.update_layout(height=400, xaxis_tickformat="$,.0f", yaxis_autorange="reversed", **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)  # #6

    with col2:
        # #9 — Lollipop: rename x-axis, label reference line explicitly,
        # position labels dynamically (above dots above mean, below dots below mean)
        st.markdown("**Return Rate by Category** (top 10 by volume)")
        df = con.execute("""
            SELECT category, SUM(units_sold) AS units,
                   ROUND(AVG(return_rate) * 100, 2) AS avg_return_rate_pct
            FROM product_performance WHERE units_sold > 0
            GROUP BY category ORDER BY units DESC LIMIT 10
        """).fetchdf()
        # Sort ascending → highest return rate at top of chart (Plotly renders y-axis bottom-up)
        df = df.sort_values("avg_return_rate_pct", ascending=True)

        overall_avg = df["avg_return_rate_pct"].mean()

        # Build lollipop chart
        fig = go.Figure()

        # Horizontal segments from average to each dot
        for _, row in df.iterrows():
            fig.add_shape(
                type="line",
                x0=overall_avg, x1=row["avg_return_rate_pct"],
                y0=row["category"], y1=row["category"],
                line=dict(color="#D97706", width=2),
            )

        # Dots colored by direction (red = worse than average, green = better)
        colors = ["#DC2626" if v > overall_avg else "#059669" for v in df["avg_return_rate_pct"]]

        # #9 — Dynamic text positioning: above the dot if above the mean,
        # below the dot if below the mean → labels never overlap the mean line.
        text_positions = [
            "top center" if v > overall_avg else "bottom center"
            for v in df["avg_return_rate_pct"]
        ]

        fig.add_trace(go.Scatter(
            x=df["avg_return_rate_pct"],
            y=df["category"],
            mode="markers+text",
            marker=dict(size=12, color=colors),
            text=[f"{v:.1f}%" for v in df["avg_return_rate_pct"]],
            textposition=text_positions,
            textfont=dict(size=10),
            showlegend=False,
            cliponaxis=False,  # #5
        ))

        # #9 — Reference line: explicitly labeled "Category Portfolio Average"
        fig.add_vline(
            x=overall_avg, line_dash="dash", line_color="#475569",
            annotation_text=f"Category Portfolio Average ({overall_avg:.1f}%)",
            annotation_font_color="#475569",
            annotation_position="top",
        )

        fig.update_layout(
            height=420,
            # #9 — Rename x-axis to be self-explanatory
            xaxis_title="Return Rate (Category vs Portfolio Average)",
            yaxis_title="",
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig, use_container_width=True)  # #6

        # #9 — One-line reading key so the color coding is instantly clear
        st.markdown(
            "<div style='font-size:0.78rem; color:#64748B; margin-top:-0.5rem;'>"
            "🔴 Above portfolio average (investigate) &nbsp;&nbsp; "
            "🟢 Below portfolio average (healthy)"
            "</div>",
            unsafe_allow_html=True,
        )

    dept = st.selectbox("Filter by department:", ["All", "Men", "Women"])
    where = "" if dept == "All" else f"WHERE department = '{dept}'"

    st.markdown(f"**Top Products by Revenue** ({dept})")
    df = con.execute(f"""
        SELECT name, category, brand, units_sold,
               ROUND(total_revenue, 2) AS total_revenue,
               ROUND(margin_pct * 100, 1) AS margin_pct
        FROM product_performance {where} ORDER BY total_revenue DESC LIMIT 15
    """).fetchdf()
    df.columns = ["Product", "Category", "Brand", "Units Sold", "Revenue ($)", "Margin (%)"]
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Revenue ($)": st.column_config.NumberColumn(format="$%.2f"),
                     "Margin (%)": st.column_config.NumberColumn(format="%.1f%%"),
                 })

    # ── Recommended Action ──
    _section_label("Recommended Action")
    # #11 — Check whether any category is significantly above portfolio average
    above_avg_rows = con.execute("""
        SELECT category, ROUND(AVG(return_rate) * 100, 2) AS avg_rate
        FROM product_performance WHERE units_sold > 0
        GROUP BY category
    """).fetchdf()
    overall_avg_rate = above_avg_rows["avg_rate"].mean() if not above_avg_rows.empty else 0
    outliers = above_avg_rows[above_avg_rows["avg_rate"] > overall_avg_rate + 2.0]
    level = "yellow" if len(outliers) > 0 else "green"

    top_name = top_cat[0] if top_cat else "the top category"
    _render_recommendation(
        level=level,
        recommendation=(
            f"Sustain the merchandising strategy that positioned {top_name} as the revenue leader. "
            f"Investigate categories with return rates significantly above the portfolio average "
            f"({overall_avg_rate:.1f}%) before adjusting inventory allocation for the next cycle."
        ),
        business_impact=(
            "Return-rate outliers indicate either quality issues or a category-fit mismatch. "
            "Both erode margin and should be diagnosed before scaling procurement."
        ),
    )


def _render_fulfillment_section(con):
    """Operations & SLA. #12 — remove Delivery Days Trend."""
    """Operations & SLA. Narrative flow: Business Summary → Evidence → Recommended Action."""
    signals = st.session_state.signals
    del_sig = next((s for s in signals if s.metric == "Avg Delivery Days"), None)
    ot_sig = next((s for s in signals if s.metric == "On-Time Delivery Rate"), None)

    # ── Business Summary ──
    _section_label("Business Summary")
    if del_sig and ot_sig:
        st.markdown(f"""
        <div class="insight-callout">
            Average delivery time is <strong>{del_sig.current_value:.1f} days</strong>
            ({abs(del_sig.delta_pct):.1%} {'improvement' if del_sig.direction == 'down' else 'increase'} MoM).
            On-time delivery rate is <strong>{ot_sig.current_value:.1%}</strong>, well above the 5-day SLA target.
        </div>
        """, unsafe_allow_html=True)

    # ── Evidence ──
    _section_label("Evidence")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Avg Delivery Days by Fulfillment Center** (current period)")
        df = con.execute("""
            SELECT distribution_center_name, avg_delivery_days
            FROM fulfillment_metrics
            WHERE order_month = (SELECT MAX(order_month) FROM fulfillment_metrics)
            ORDER BY avg_delivery_days DESC
        """).fetchdf()

        fig = px.bar(df, x="avg_delivery_days", y="distribution_center_name", orientation="h",
                     labels={"distribution_center_name": "", "avg_delivery_days": "Avg Delivery Days"},
                     text="avg_delivery_days")
        fig.update_traces(marker_color="#2563EB", texttemplate="%{x:.1f}d", textposition="outside",
                          textfont_size=9, cliponaxis=False)  # #5

        # #10 — SLA annotation: two-line label, positioned inside chart area
        fig.add_vline(
            x=5.0,
            line_dash="dash",
            line_color="#DC2626",
            annotation_text="SLA Target<br>(5 days)",
            annotation_font_color="#DC2626",
            annotation_font_size=10,
            annotation_position="top left",
        )
        fig.update_layout(
            height=400,
            yaxis_autorange="reversed",
            # Extend x-axis so the SLA line has visual breathing room to the right
            xaxis_range=[0, 6.5],
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig, use_container_width=True)  # #6

    with col2:
        st.markdown("**On-Time Rate by Fulfillment Center** (current period)")
        df = con.execute("""
            SELECT distribution_center_name AS "Fulfillment Center",
                   ROUND(on_time_rate * 100, 1) AS "On-Time Rate (%)",
                   on_time_deliveries AS "On-Time Deliveries",
                   total_deliveries AS "Total Deliveries"
            FROM fulfillment_metrics
            WHERE order_month = (SELECT MAX(order_month) FROM fulfillment_metrics)
            ORDER BY on_time_rate ASC
        """).fetchdf()
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "On-Time Rate (%)": st.column_config.NumberColumn(format="%.1f%%"),
                     })

    # ── Recommended Action ──
    _section_label("Recommended Action")
    # #11 — Action level: if all DCs are under SLA, no action; otherwise investigate
    max_days_row = con.execute("""
        SELECT MAX(avg_delivery_days) AS max_days
        FROM fulfillment_metrics
        WHERE order_month = (SELECT MAX(order_month) FROM fulfillment_metrics)
    """).fetchone()
    max_days = max_days_row[0] if max_days_row and max_days_row[0] is not None else 0

    if max_days >= 5.0:
        level = "orange"
    elif max_days >= 4.0:
        level = "yellow"
    else:
        level = "green"

    _render_recommendation(
        level=level,
        recommendation=(
            "Sustain current operational cadence. All fulfillment centers are operating within "
            "the 5-day SLA target. Continue monitoring seasonal volume spikes that could compress "
            "the buffer during peak periods."
        ),
        business_impact=(
            f"Current headroom to SLA (max observed: {max_days:.1f} days) means routine volume "
            "growth can be absorbed without operational escalation."
        ),
    )


def _render_inventory_section(con):
    """Inventory Actions. Narrative flow: Business Summary → Evidence → Recommended Action."""
    dead_info = con.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN is_dead_stock THEN 1 ELSE 0 END) AS dead,
               SUM(CASE WHEN reorder_signal THEN 1 ELSE 0 END) AS reorder
        FROM inventory_health
    """).fetchone()
    dead_pct = (dead_info[1] / max(dead_info[0], 1)) * 100 if dead_info else 0

    # ── Business Summary ──
    _section_label("Business Summary")
    if dead_info:
        st.markdown(f"""
        <div class="insight-callout">
            <strong>{dead_info[2]}</strong> products require replenishment.
            Dead stock rate is <strong>{dead_pct:.1f}%</strong> across {dead_info[0]:,} tracked items.
        </div>
        """, unsafe_allow_html=True)

    # ── Evidence ──
    _section_label("Evidence")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Dead Stock by Category** (top 10, sorted by rate)")
        df = con.execute("""
            SELECT category, COUNT(*) AS total_products,
                   SUM(CASE WHEN is_dead_stock THEN 1 ELSE 0 END) AS dead_stock,
                   ROUND(AVG(CASE WHEN is_dead_stock THEN 1.0 ELSE 0.0 END) * 100, 1) AS dead_pct
            FROM inventory_health GROUP BY category ORDER BY dead_pct DESC LIMIT 10
        """).fetchdf()
        fig = px.bar(df, x="dead_pct", y="category", orientation="h",
                     labels={"category": "", "dead_pct": "Dead Stock (%)"},
                     text="dead_pct")
        fig.update_traces(marker_color="#DC2626", texttemplate="%{x:.1f}%", textposition="outside",
                          textfont_size=9, cliponaxis=False)  # #5
        # Extend axis so outside labels have breathing room
        if not df.empty:
            max_val = float(df["dead_pct"].max())
            fig.update_layout(xaxis_range=[0, max_val * 1.18])
        fig.update_layout(height=400, yaxis_autorange="reversed", **CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)  # #6

    with col2:
        st.markdown("**Reorder Signals by Category** (sorted by count)")
        df = con.execute("""
            SELECT category,
                   SUM(CASE WHEN reorder_signal THEN 1 ELSE 0 END) AS reorder_count,
                   COUNT(*) AS total
            FROM inventory_health GROUP BY category
            HAVING SUM(CASE WHEN reorder_signal THEN 1 ELSE 0 END) > 0
            ORDER BY reorder_count DESC LIMIT 10
        """).fetchdf()
        if not df.empty:
            fig = px.bar(df, x="reorder_count", y="category", orientation="h",
                         labels={"category": "", "reorder_count": "Products Needing Reorder"},
                         text="reorder_count")
            fig.update_traces(marker_color="#D97706", texttemplate="%{x}", textposition="outside",
                              textfont_size=9, cliponaxis=False)  # #5
            max_val = float(df["reorder_count"].max())
            fig.update_layout(xaxis_range=[0, max_val * 1.2], height=400,
                              yaxis_autorange="reversed", **CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)  # #6
        else:
            st.info("No reorder signals currently active.")

    st.markdown("**Inventory Health Overview by Fulfillment Center**")
    df = con.execute("""
        SELECT distribution_center_name AS "Fulfillment Center",
               COUNT(*) AS "Products",
               ROUND(SUM(stock_value), 2) AS "Stock Value ($)",
               ROUND(AVG(turnover_rate), 3) AS "Avg Turnover",
               SUM(CASE WHEN is_dead_stock THEN 1 ELSE 0 END) AS "Dead Stock",
               SUM(CASE WHEN reorder_signal THEN 1 ELSE 0 END) AS "Reorder Signals"
        FROM inventory_health GROUP BY distribution_center_name
        ORDER BY "Stock Value ($)" DESC
    """).fetchdf()
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "Stock Value ($)": st.column_config.NumberColumn(format="$%,.2f"),
                     "Avg Turnover": st.column_config.NumberColumn(format="%.3f"),
                 })

    # ── Recommended Action ──
    _section_label("Recommended Action")
    top_reorder = con.execute("""
        SELECT category, SUM(CASE WHEN reorder_signal THEN 1 ELSE 0 END) AS cnt
        FROM inventory_health GROUP BY category ORDER BY cnt DESC LIMIT 2
    """).fetchdf()

    reorder_total = dead_info[2] if dead_info else 0
    # #11 — Action level driven by scale of reorder need and dead-stock rate
    if reorder_total >= 50 or dead_pct >= 15:
        level = "orange"
    elif reorder_total > 0 or dead_pct >= 8:
        level = "yellow"
    else:
        level = "green"

    if not top_reorder.empty and reorder_total > 0:
        top_cats = " and ".join(top_reorder["category"].tolist())
        recommendation = (
            f"Prioritize replenishment for {top_cats}, which account for the largest share of "
            f"active reorder signals. Dead stock remains within acceptable thresholds "
            f"({dead_pct:.1f}%) across all categories."
        )
    else:
        recommendation = (
            "Sustain current replenishment cadence. No active reorder signals require immediate "
            f"procurement action, and dead stock ({dead_pct:.1f}%) is within acceptable thresholds."
        )

    _render_recommendation(
        level=level,
        recommendation=recommendation,
        business_impact=(
            "Timely replenishment protects service levels for high-velocity categories, while "
            "controlled dead stock keeps working capital available for higher-turnover SKUs."
        ),
    )
