"""
Deterministic analytics — pure Python and DuckDB.

No LLM. This module computes all business KPIs with period-over-period
comparisons. Every metric is computed from a SQL query that is stored
on the Signal object for reproducibility.
"""

from .models import Signal


# ── Thresholds (importable by other modules) ──
CRITICAL_THRESHOLD = 0.10
WARNING_THRESHOLD = 0.05


def compute_signal(
    metric: str,
    domain: str,
    current: float,
    prior: float,
    query: str = "",
    critical_threshold: float = CRITICAL_THRESHOLD,
    warning_threshold: float = WARNING_THRESHOLD,
) -> Signal:
    """Compute a Signal from current vs prior values with direction-aware severity."""
    if prior == 0:
        delta_pct = 0.0
    else:
        delta_pct = (current - prior) / abs(prior)

    abs_delta = abs(delta_pct)

    if delta_pct > 0.005:
        direction = "up"
    elif delta_pct < -0.005:
        direction = "down"
    else:
        direction = "flat"

    # Direction-aware severity:
    # Large negative changes are critical (something is wrong).
    # Large positive changes are notable (good news, but understand why).
    if abs_delta >= critical_threshold:
        severity = "critical" if direction == "down" else "notable"
    elif abs_delta >= warning_threshold:
        severity = "warning"
    else:
        severity = "normal"

    context = f"{metric}: {current:,.2f} (was {prior:,.2f}), {delta_pct:+.1%} {direction}"
    return Signal(
        metric=metric, domain=domain, current_value=current, prior_value=prior,
        delta_pct=delta_pct, severity=severity, direction=direction,
        context=context, source_query=query,
    )


def run_analytics(con, comparison_type: str = "month_over_month") -> tuple:
    """
    Run all KPI computations against DuckDB and return Signals.

    Returns:
        (signals, current_period, prior_period)
    """
    signals = []

    # ── Determine analysis periods ──
    period_query = """
    SELECT DISTINCT order_month
    FROM fulfillment_metrics
    ORDER BY order_month DESC
    LIMIT 2
    """
    periods = con.execute(period_query).fetchall()
    if len(periods) < 2:
        return signals, None, None

    current_period = periods[0][0]
    prior_period = periods[1][0]

    # ── 1. Revenue ──
    rev_query = """
    SELECT
        SUM(CASE WHEN order_month = ? THEN total_revenue ELSE 0 END) AS current_rev,
        SUM(CASE WHEN order_month = ? THEN total_revenue ELSE 0 END) AS prior_rev
    FROM fulfillment_metrics
    """
    row = con.execute(rev_query, [current_period, prior_period]).fetchone()
    signals.append(compute_signal("Total Revenue", "revenue", row[0] or 0, row[1] or 0, rev_query))

    # ── 2. Orders Fulfilled ──
    orders_query = """
    SELECT
        SUM(CASE WHEN order_month = ? THEN orders_fulfilled ELSE 0 END) AS cur,
        SUM(CASE WHEN order_month = ? THEN orders_fulfilled ELSE 0 END) AS prior
    FROM fulfillment_metrics
    """
    row = con.execute(orders_query, [current_period, prior_period]).fetchone()
    signals.append(compute_signal("Orders Fulfilled", "revenue", row[0] or 0, row[1] or 0, orders_query))

    # ── 3. Active Users ──
    active_query = """
    SELECT
        (SELECT COUNT(DISTINCT user_id) FROM funnel_analytics
         WHERE event_month = ?) AS cur,
        (SELECT COUNT(DISTINCT user_id) FROM funnel_analytics
         WHERE event_month = ?) AS prior
    """
    row = con.execute(active_query, [current_period, prior_period]).fetchone()
    signals.append(compute_signal("Active Users", "customers", row[0] or 0, row[1] or 0, active_query))

    # ── 4. Avg Conversion Rate ──
    conv_query = """
    SELECT
        AVG(CASE WHEN event_month = ? THEN session_to_purchase_rate END) AS cur,
        AVG(CASE WHEN event_month = ? THEN session_to_purchase_rate END) AS prior
    FROM funnel_analytics
    """
    row = con.execute(conv_query, [current_period, prior_period]).fetchone()
    signals.append(compute_signal("Avg Conversion Rate", "conversion", row[0] or 0, row[1] or 0, conv_query))

    # ── 5. Avg Delivery Days ──
    del_query = """
    SELECT
        AVG(CASE WHEN order_month = ? THEN avg_delivery_days END) AS cur,
        AVG(CASE WHEN order_month = ? THEN avg_delivery_days END) AS prior
    FROM fulfillment_metrics
    """
    row = con.execute(del_query, [current_period, prior_period]).fetchone()
    signals.append(compute_signal("Avg Delivery Days", "fulfillment", row[0] or 0, row[1] or 0, del_query))

    # ── 6. On-Time Rate ──
    ot_query = """
    SELECT
        AVG(CASE WHEN order_month = ? THEN on_time_rate END) AS cur,
        AVG(CASE WHEN order_month = ? THEN on_time_rate END) AS prior
    FROM fulfillment_metrics
    """
    row = con.execute(ot_query, [current_period, prior_period]).fetchone()
    signals.append(compute_signal("On-Time Delivery Rate", "fulfillment", row[0] or 0, row[1] or 0, ot_query))

    # ── 7. Dead Stock Rate (point-in-time, no MoM) ──
    dead_query = """
    SELECT
        AVG(CASE WHEN is_dead_stock = true THEN 1.0 ELSE 0.0 END) AS dead_rate,
        COUNT(*) AS total_products
    FROM inventory_health
    """
    row = con.execute(dead_query).fetchone()
    dead_signal = Signal(
        metric="Dead Stock Rate", domain="inventory",
        current_value=row[0] or 0, prior_value=0, delta_pct=0,
        severity="info" if (row[0] or 0) < 0.10 else "warning",
        direction="flat",
        context=f"Dead stock rate: {(row[0] or 0):.1%} across {row[1]:,} products",
        source_query=dead_query,
    )
    signals.append(dead_signal)

    # ── 8. Churn Risk (from inference batch) ──
    churn_query = """
    SELECT
        AVG(churn_probability) AS avg_prob,
        COUNT(CASE WHEN churn_probability > 0.7 THEN 1 END) AS high_risk,
        COUNT(*) AS total
    FROM predictions
    """
    row = con.execute(churn_query).fetchone()
    high_risk_pct = (row[1] or 0) / max(row[2] or 1, 1)
    churn_signal = Signal(
        metric="Churn Risk (Inference Batch)", domain="churn",
        current_value=row[1] or 0, prior_value=row[2] or 0,
        delta_pct=high_risk_pct,
        severity="warning" if high_risk_pct > 0.5 else "normal",
        direction="up" if high_risk_pct > 0.5 else "flat",
        context=(
            f"Churn risk: {row[1] or 0} of {row[2] or 0} customers high-risk "
            f"(prob > 0.7), avg prob {(row[0] or 0):.3f}"
        ),
        source_query=churn_query,
    )
    signals.append(churn_signal)

    return signals, current_period, prior_period
