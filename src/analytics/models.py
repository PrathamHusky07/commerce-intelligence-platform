"""
Domain models for the AI Business Analyst pipeline.

Signal  → A single KPI measurement with period-over-period comparison.
Finding → An anomaly or pattern promoted to executive attention.
ExecutiveBrief → The final structured output the LLM generates.

These are the typed interfaces between deterministic analytics and
the LangGraph agent. Every finding carries its own evidence and the
SQL query that produced it, so any claim in the executive brief is
reproducible.
"""

from dataclasses import dataclass, field


@dataclass
class Signal:
    """A single KPI measurement with period-over-period comparison."""
    metric: str
    domain: str                  # e.g. "revenue", "customers", "fulfillment"
    current_value: float
    prior_value: float
    delta_pct: float             # percentage change (signed)
    severity: str                # "critical", "warning", "normal", "notable", "info"
    direction: str               # "up", "down", "flat"
    context: str                 # human-readable one-liner
    source_query: str = ""       # the DuckDB SQL that produced this


@dataclass
class Finding:
    """An anomaly or noteworthy pattern that deserves executive attention."""
    title: str
    description: str
    confidence: float            # 0.0–1.0, computed from corroborating evidence
    severity: str                # "critical", "notable", "warning", "info"
    priority: str = "P3"         # P1 (act now), P2 (investigate), P3 (monitor)
    evidence: list = field(default_factory=list)
    source_query: str = ""       # reproducible SQL
    recommended_action: str = ""


@dataclass
class ExecutiveBrief:
    """The final structured output the LLM generates."""
    executive_summary: str = ""
    business_health: str = ""
    key_findings: str = ""
    model_health: str = ""
    recommended_actions: str = ""
    generated_at: str = ""
