"""
Agent tool definitions.

Five tools that the LangGraph agent can invoke. None of these tools
perform analytics — the analytics are pre-computed. The tools provide
access to pre-computed results and enable follow-up investigation.

v5 — Production Readiness Sprint:
  #4  sql_query returns a markdown table (via to_markdown()) so the
      UI can render it as a real HTML table instead of raw text.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from langchain_core.tools import tool


def create_tools(signals, findings, con, monitoring_summary, charts_dir: Path = Path("reports/charts")):
    """
    Create the 5 agent tools with the given context.

    The tools close over the provided signals, findings, connection, and
    monitoring data. This avoids global state.

    Returns:
        List of 5 LangChain tool objects.
    """
    charts_dir.mkdir(parents=True, exist_ok=True)

    @tool
    def kpi_summary() -> str:
        """Return the pre-computed business KPI signals and findings.
        Call this first to understand the current business state."""
        lines = ["=== KPI SIGNALS ===\n"]
        for s in signals:
            status = "CRITICAL" if s.severity == "critical" else "WARNING" if s.severity == "warning" else "OK"
            lines.append(f"[{status}] {s.context}")
        lines.append("\n=== KEY FINDINGS ===\n")
        for f in findings:
            lines.append(f"[{f.severity.upper()} | {f.priority} | confidence={f.confidence:.0%}] {f.title}")
            lines.append(f"  {f.description}")
            if f.recommended_action:
                lines.append(f"  → Action: {f.recommended_action}")
        return "\n".join(lines)

    @tool
    def sql_query(query: str) -> str:
        """Execute a SQL query against the Gold tables in DuckDB.
        Available tables: customer_360, product_performance, inventory_health,
        fulfillment_metrics, funnel_analytics, predictions.
        Return the results as a formatted table.
        Use this for follow-up investigations to drill into specific metrics."""
        try:
            result = con.execute(query).fetchdf()
            if result.empty:
                return "Query returned no results."

            total_rows = len(result)
            # Cap at 10 rows for context-window and readability discipline
            display_df = result.head(10)
            # #4 — Return as a markdown table so the UI renders as an HTML <table>
            formatted = display_df.to_markdown(
                index=False,
                floatfmt=",.2f",
            )

            if total_rows > 10:
                formatted += f"\n\n(Showing top 10 of {total_rows} rows)"

            return formatted
        except Exception:
            return "Query could not be executed. Please try a simpler query."

    @tool
    def churn_analysis() -> str:
        """Return churn prediction analysis from the latest inference batch.
        Includes probability distribution, high-risk segments, and key statistics."""
        stats = con.execute("""
            SELECT
                COUNT(*) AS total_customers,
                AVG(churn_probability) AS avg_probability,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY churn_probability) AS median_probability,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY churn_probability) AS p90_probability,
                COUNT(CASE WHEN churn_probability > 0.7 THEN 1 END) AS high_risk_count,
                COUNT(CASE WHEN churn_probability > 0.9 THEN 1 END) AS very_high_risk_count
            FROM predictions
        """).fetchone()

        return (
            f"Churn Analysis (inference batch of {stats[0]:,} customers):\n"
            f"  Avg probability:     {stats[1]:.4f}\n"
            f"  Median probability:  {stats[2]:.4f}\n"
            f"  P90 probability:     {stats[3]:.4f}\n"
            f"  High risk (>0.7):    {stats[4]:,} ({stats[4]/stats[0]:.1%})\n"
            f"  Very high risk (>0.9): {stats[5]:,} ({stats[5]/stats[0]:.1%})"
        )

    @tool
    def monitoring_status() -> str:
        """Return the Evidently AI monitoring summary.
        Includes data drift, prediction drift, model quality, and recommendation."""
        m = monitoring_summary
        return (
            f"Model Monitoring Status (as of {m.get('timestamp', 'unknown')}):\n"
            f"  Data drift:        {'DETECTED' if m.get('data_drift_detected') else 'None'} "
            f"({m.get('features_drifted', 0)}/{m.get('features_tested', 0)} features)\n"
            f"  Prediction drift:  {'DETECTED' if m.get('prediction_drift_detected') else 'None'} "
            f"({m.get('prediction_drift_method', 'N/A')} = {m.get('prediction_drift_score', 'N/A')}, "
            f"threshold = {m.get('prediction_drift_threshold', 'N/A')})\n"
            f"  Model quality:     AUC {m.get('auc_ref', 'N/A')} → {m.get('auc_cur', 'N/A')} "
            f"(drop: {m.get('auc_drop_pct', 'N/A')}%)\n"
            f"  Recommendation:    {m.get('recommendation', 'N/A')}"
        )

    @tool
    def chart_generator(chart_type: str, title: str, data_query: str) -> str:
        """Generate a matplotlib chart from a SQL query and save it.
        Args:
            chart_type: 'bar', 'line', or 'pie'
            title: Chart title
            data_query: SQL query that returns 2 columns (label, value)
        Returns: Path to the saved chart image."""
        try:
            df = con.execute(data_query).fetchdf()
            if df.empty:
                return "No data to chart."

            fig, ax = plt.subplots(figsize=(10, 6))
            cols = df.columns.tolist()

            if chart_type == "bar":
                ax.bar(df[cols[0]].astype(str), df[cols[1]], color="#4A90D9")
            elif chart_type == "line":
                ax.plot(df[cols[0]].astype(str), df[cols[1]], marker="o", color="#4A90D9")
            elif chart_type == "pie":
                ax.pie(df[cols[1]], labels=df[cols[0]].astype(str), autopct="%1.1f%%")
            else:
                return f"Unknown chart type: {chart_type}"

            ax.set_title(title, fontsize=14, fontweight="bold")
            if chart_type != "pie":
                ax.tick_params(axis="x", rotation=45)
                ax.set_ylabel(cols[1])
            plt.tight_layout()

            safe_title = title.lower().replace(" ", "_")[:40]
            chart_path = charts_dir / f"{safe_title}.png"
            fig.savefig(chart_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return f"Chart saved: {chart_path}"
        except Exception as e:
            return f"Chart error: {e}"

    return [kpi_summary, sql_query, churn_analysis, monitoring_status, chart_generator]
