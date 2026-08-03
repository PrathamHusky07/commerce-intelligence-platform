"""
Finding detection and generation.

Evaluates which Signals deserve executive attention. Builds structured
Findings with confidence scores, evidence trails, and priority labels.
The LLM will reason over these — it never computes them.
"""

from .models import Finding


def _compute_priority(severity: str, confidence: float) -> str:
    """Derive P1/P2/P3 priority from severity and confidence."""
    if severity == "critical":
        return "P1"
    if severity == "notable" and confidence >= 0.8:
        return "P1"
    if severity in ("notable", "warning") and confidence >= 0.6:
        return "P2"
    return "P3"


def generate_findings(
    signals: list,
    con,
    current_period,
    prior_period,
    monitoring_summary: dict,
) -> list:
    """
    Analyze signals, detect anomalies, and produce evidence-backed Findings.

    Args:
        signals: List of Signal objects from run_analytics().
        con: DuckDB connection.
        current_period: Current analysis period.
        prior_period: Prior analysis period.
        monitoring_summary: Parsed monitoring_summary.json dict.

    Returns:
        List of Finding objects sorted by priority (P1 first).
    """
    findings = []

    # ── Collect actionable signals (critical or notable) and warnings ──
    actionable_signals = [s for s in signals if s.severity in ("critical", "notable")]
    warning_signals = [s for s in signals if s.severity == "warning"]

    # ── For each actionable signal, investigate deeper ──
    for sig in actionable_signals:
        evidence = [sig.context]
        drill_query = ""

        if sig.domain == "revenue":
            drill_query = f"""
            SELECT distribution_center_name, total_revenue,
                   orders_fulfilled
            FROM fulfillment_metrics
            WHERE order_month = '{current_period}'
            ORDER BY total_revenue DESC
            LIMIT 5
            """
            rows = con.execute(drill_query).fetchall()
            for r in rows:
                evidence.append(f"  DC '{r[0]}': ${r[1]:,.0f} revenue, {r[2]:,} orders")

        elif sig.domain == "customers":
            drill_query = """
            SELECT traffic_source, COUNT(*) AS users,
                   AVG(order_count) AS avg_orders
            FROM customer_360
            GROUP BY traffic_source
            ORDER BY users DESC
            """
            rows = con.execute(drill_query).fetchall()
            for r in rows:
                evidence.append(f"  Source '{r[0]}': {r[1]:,} users, avg {r[2]:.1f} orders")

        elif sig.domain == "conversion":
            drill_query = f"""
            SELECT event_month, AVG(session_to_purchase_rate) AS avg_conv,
                   COUNT(DISTINCT user_id) AS users
            FROM funnel_analytics
            GROUP BY event_month
            ORDER BY event_month DESC
            LIMIT 6
            """
            rows = con.execute(drill_query).fetchall()
            for r in rows:
                evidence.append(f"  {r[0]}: conv={r[1]:.4f}, users={r[2]:,}")

        elif sig.domain == "fulfillment":
            drill_query = f"""
            SELECT distribution_center_name,
                   AVG(avg_delivery_days) AS avg_del,
                   AVG(on_time_rate) AS avg_ot
            FROM fulfillment_metrics
            WHERE order_month = '{current_period}'
            GROUP BY distribution_center_name
            ORDER BY avg_del DESC
            LIMIT 5
            """
            rows = con.execute(drill_query).fetchall()
            for r in rows:
                evidence.append(f"  DC '{r[0]}': {r[1]:.1f} days avg, {r[2]:.1%} on-time")

        # ── Compute confidence from corroborating signals ──
        domain_signals = [s for s in signals if s.domain == sig.domain]
        corroborating = [s for s in domain_signals if s.severity in ("critical", "notable", "warning")]
        confidence = min(len(corroborating) / max(len(domain_signals), 1), 1.0)
        if len(evidence) > 2:
            confidence = min(confidence + 0.2, 1.0)

        priority = _compute_priority(sig.severity, confidence)

        findings.append(Finding(
            title=f"{sig.metric} — {sig.direction.upper()} {abs(sig.delta_pct):.1%}",
            description=f"{sig.metric} moved {sig.delta_pct:+.1%} from {prior_period} to {current_period}.",
            confidence=round(confidence, 2),
            severity=sig.severity,
            priority=priority,
            evidence=evidence,
            source_query=drill_query or sig.source_query,
            recommended_action=f"Investigate {sig.metric.lower()} drivers in the {sig.domain} domain.",
        ))

    # ── Add warning-level findings ──
    for sig in warning_signals:
        findings.append(Finding(
            title=f"{sig.metric} — {sig.direction.upper()} {abs(sig.delta_pct):.1%}",
            description=sig.context,
            confidence=0.6,
            severity="warning",
            priority=_compute_priority("warning", 0.6),
            evidence=[sig.context],
            source_query=sig.source_query,
            recommended_action=f"Monitor {sig.metric.lower()} trend over the next period.",
        ))

    # ── Add monitoring finding (always present) ──
    mon = monitoring_summary
    mon_severity = "warning" if mon.get("prediction_drift_detected") else "normal"

    mon_flags = [
        mon.get("data_drift_detected", False),
        mon.get("prediction_drift_detected", False),
        mon.get("model_degraded", False),
    ]
    flags_raised = sum(1 for f in mon_flags if f)
    mon_confidence = round(0.7 + (flags_raised * 0.1), 2)

    findings.append(Finding(
        title="ML Model Monitoring Status",
        description=(
            f"Data drift: {mon.get('features_drifted', 0)}/{mon.get('features_tested', 0)} features. "
            f"Prediction drift: {'YES' if mon.get('prediction_drift_detected') else 'No'}. "
            f"Model degradation: {'YES' if mon.get('model_degraded') else 'No'}. "
            f"Recommendation: {mon.get('recommendation', 'N/A')}."
        ),
        confidence=mon_confidence,
        severity=mon_severity,
        priority=_compute_priority(mon_severity, mon_confidence),
        evidence=[
            f"Feature drift: {mon.get('features_drifted')}/{mon.get('features_tested')} features drifted",
            f"Prediction drift: {mon.get('prediction_drift_method')} = {mon.get('prediction_drift_score')} (threshold: {mon.get('prediction_drift_threshold')})",
            f"AUC: {mon.get('auc_ref')} → {mon.get('auc_cur')} (drop: {mon.get('auc_drop_pct')}%)",
            f"Recommendation: {mon.get('recommendation')}",
        ],
        source_query="SELECT * FROM monitoring_summary.json",
        recommended_action="Investigate prediction drift source before retraining.",
    ))

    # ── Sort by priority: P1 first, then P2, then P3 ──
    priority_order = {"P1": 0, "P2": 1, "P3": 2}
    findings.sort(key=lambda f: priority_order.get(f.priority, 9))

    return findings


def generate_suggested_questions(findings: list) -> list:
    """
    Generate follow-up questions from findings — purely programmatic, no LLM.

    Returns:
        List of (question_text, domain) tuples.
    """
    questions = []
    seen_domains = set()

    for f in findings:
        if f.severity in ("critical", "notable"):
            if "revenue" in f.title.lower() and "revenue" not in seen_domains:
                questions.append((
                    "Which product categories drove the revenue change?",
                    "revenue",
                ))
                seen_domains.add("revenue")
            if "orders" in f.title.lower() and "orders" not in seen_domains:
                questions.append((
                    "Which distribution centers drove order growth?",
                    "revenue",
                ))
                seen_domains.add("orders")
            if "user" in f.title.lower() and "customers" not in seen_domains:
                questions.append((
                    "Which traffic sources contributed the most new users?",
                    "customers",
                ))
                seen_domains.add("customers")

        if f.severity == "warning":
            if "churn" in f.title.lower() and "churn" not in seen_domains:
                questions.append((
                    "What percentage of high-risk churn customers came from each traffic source?",
                    "churn",
                ))
                seen_domains.add("churn")
            if "monitoring" in f.title.lower() and "monitoring" not in seen_domains:
                questions.append((
                    "What is the current model AUC and drift status?",
                    "monitoring",
                ))
                seen_domains.add("monitoring")
            if "dead stock" in f.description.lower() and "inventory" not in seen_domains:
                questions.append((
                    "Which product categories have the highest dead stock rates?",
                    "inventory",
                ))
                seen_domains.add("inventory")

    # ── Always include at least one if none were generated ──
    if not questions:
        questions.append((
            "Show me the top 5 product categories by revenue.",
            "revenue",
        ))

    return questions[:5]  # cap at 5
