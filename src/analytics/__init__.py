"""
Analytics package — deterministic business intelligence.

No LLM. Pure Python and DuckDB.

Usage:
    from src.analytics import (
        Signal, Finding, ExecutiveBrief,
        get_connection, get_table_info,
        run_analytics,
        generate_findings, generate_suggested_questions,
    )
"""

from .models import Signal, Finding, ExecutiveBrief
from .duckdb_setup import get_connection, get_table_info
from .signals import run_analytics, compute_signal, CRITICAL_THRESHOLD, WARNING_THRESHOLD
from .findings import generate_findings, generate_suggested_questions
