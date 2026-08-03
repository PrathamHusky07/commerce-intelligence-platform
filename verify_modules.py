"""
Module verification script.

Run from project root: python verify_modules.py

Tests that all extracted modules import correctly and produce the same
results as the notebook. Does NOT call the LLM — only tests the
deterministic analytics layer.
"""

import sys
from pathlib import Path

print("=" * 60)
print("  MODULE VERIFICATION")
print("=" * 60)

errors = []

# ── 1. Test imports ──
print("\n1. Testing imports...")

try:
    from src.analytics.models import Signal, Finding, ExecutiveBrief
    print("   ✓ src.analytics.models")
except Exception as e:
    errors.append(f"models import: {e}")
    print(f"   ✗ src.analytics.models: {e}")

try:
    from src.analytics.duckdb_setup import get_connection, get_table_info
    print("   ✓ src.analytics.duckdb_setup")
except Exception as e:
    errors.append(f"duckdb_setup import: {e}")
    print(f"   ✗ src.analytics.duckdb_setup: {e}")

try:
    from src.analytics.signals import run_analytics, compute_signal
    print("   ✓ src.analytics.signals")
except Exception as e:
    errors.append(f"signals import: {e}")
    print(f"   ✗ src.analytics.signals: {e}")

try:
    from src.analytics.findings import generate_findings, generate_suggested_questions
    print("   ✓ src.analytics.findings")
except Exception as e:
    errors.append(f"findings import: {e}")
    print(f"   ✗ src.analytics.findings: {e}")

try:
    from src.agent.tools import create_tools
    print("   ✓ src.agent.tools")
except Exception as e:
    errors.append(f"agent tools import: {e}")
    print(f"   ✗ src.agent.tools: {e}")

try:
    from src.agent.graph import build_agent, run_briefing, AgentState
    print("   ✓ src.agent.graph")
except Exception as e:
    errors.append(f"agent graph import: {e}")
    print(f"   ✗ src.agent.graph: {e}")

try:
    from src.agent.followup import ask_followup, TABLE_SCHEMAS
    print("   ✓ src.agent.followup")
except Exception as e:
    errors.append(f"agent followup import: {e}")
    print(f"   ✗ src.agent.followup: {e}")

# ── Package-level imports ──
try:
    from src.analytics import Signal, Finding, get_connection, run_analytics, generate_findings
    print("   ✓ src.analytics (package)")
except Exception as e:
    errors.append(f"analytics package: {e}")
    print(f"   ✗ src.analytics (package): {e}")

try:
    from src.agent import create_tools, build_agent, run_briefing, ask_followup
    print("   ✓ src.agent (package)")
except Exception as e:
    errors.append(f"agent package: {e}")
    print(f"   ✗ src.agent (package): {e}")

if errors:
    print(f"\n✗ {len(errors)} import errors. Fix these before proceeding.")
    sys.exit(1)

print("\n   All imports passed.")

# ── 2. Test DuckDB setup ──
print("\n2. Testing DuckDB setup...")

con, monitoring_summary = get_connection()
table_info = get_table_info(con)

expected = {
    "customer_360": 100_000,
    "fulfillment_metrics": 903,
    "funnel_analytics": 124_082,
    "inventory_health": 29_036,
    "predictions": 1_000,
    "product_performance": 29_120,
}

for name, count in table_info:
    exp = expected.get(name)
    status = "✓" if exp and count == exp else "✗"
    print(f"   {status} {name:25s} → {count:>10,} rows (expected {exp:,})")
    if exp and count != exp:
        errors.append(f"{name}: got {count}, expected {exp}")

print(f"   Monitoring recommendation: {monitoring_summary['recommendation']}")

# ── 3. Test signal computation ──
print("\n3. Testing signal computation...")

signals, current_period, prior_period = run_analytics(con)

print(f"   Periods: {prior_period} → {current_period}")
print(f"   Signals computed: {len(signals)}")

for s in signals:
    icons = {"critical": "🔴", "notable": "📈", "warning": "🟡", "normal": "🟢", "info": "ℹ️"}
    icon = icons.get(s.severity, "⚪")
    print(f"   {icon} {s.context}")

if len(signals) != 8:
    errors.append(f"Expected 8 signals, got {len(signals)}")

# ── 4. Test findings generation ──
print("\n4. Testing findings generation...")

findings = generate_findings(signals, con, current_period, prior_period, monitoring_summary)

print(f"   Findings generated: {len(findings)}")
for f in findings:
    print(f"   [{f.priority}] [{f.severity.upper()} | {f.confidence:.0%}] {f.title}")

# Verify priority field exists and is valid
for f in findings:
    if f.priority not in ("P1", "P2", "P3"):
        errors.append(f"Invalid priority '{f.priority}' on finding '{f.title}'")

# Verify sorted by priority
priorities = [f.priority for f in findings]
if priorities != sorted(priorities):
    errors.append(f"Findings not sorted by priority: {priorities}")

# ── 5. Test suggested questions ──
print("\n5. Testing suggested questions...")

questions = generate_suggested_questions(findings)
print(f"   Generated {len(questions)} suggested follow-up questions:")
for q, domain in questions:
    print(f"   • [{domain}] {q}")

# ── 6. Test tool creation (no LLM call) ──
print("\n6. Testing tool creation...")

tools = create_tools(signals, findings, con, monitoring_summary)
print(f"   Created {len(tools)} tools: {[t.name for t in tools]}")

if len(tools) != 5:
    errors.append(f"Expected 5 tools, got {len(tools)}")

# ── 7. Verify Finding has priority field ──
print("\n7. Verifying Finding dataclass has priority field...")
test_finding = Finding(
    title="Test", description="Test", confidence=0.9,
    severity="notable", priority="P1",
)
print(f"   ✓ Finding.priority = {test_finding.priority}")

# ── Summary ──
print("\n" + "=" * 60)
if errors:
    print(f"  ✗ FAILED — {len(errors)} errors:")
    for e in errors:
        print(f"    • {e}")
    sys.exit(1)
else:
    print("  ✓ ALL CHECKS PASSED")
    print()
    print("  Modules are ready. Streamlit can import from:")
    print("    from src.analytics import get_connection, run_analytics, generate_findings")
    print("    from src.agent import create_tools, build_agent, run_briefing, ask_followup")
print("=" * 60)
