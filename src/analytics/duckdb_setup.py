"""
DuckDB data platform integration.

Creates an in-memory DuckDB database and registers Gold table Parquet files
as queryable tables. In production, this would be a Databricks SQL warehouse
or a Spark session — the agent's architecture is identical either way, just
the connection string changes.
"""

import json
from pathlib import Path

import duckdb


def get_connection(
    data_dir: Path = Path("data"),
    evidently_dir: Path = Path("evidently"),
    gold_tables: dict = None,
    predictions_path: Path = None,
    monitoring_path: Path = None,
) -> tuple:
    """
    Initialize DuckDB and register all Gold tables + predictions.

    Returns:
        (con, monitoring_summary) — DuckDB connection and parsed monitoring JSON.
    """
    if gold_tables is None:
        gold_tables = {
            "customer_360":        data_dir / "customer_360.parquet",
            "product_performance": data_dir / "product_performance.parquet",
            "inventory_health":    data_dir / "inventory_health.parquet",
            "fulfillment_metrics": data_dir / "fulfillment_metrics.parquet",
            "funnel_analytics":    data_dir / "funnel_analytics.parquet",
        }

    if predictions_path is None:
        predictions_path = data_dir / "predictions.parquet"
    if monitoring_path is None:
        monitoring_path = evidently_dir / "monitoring_summary.json"

    # ── Verify files ──
    all_paths = list(gold_tables.values()) + [predictions_path, monitoring_path]
    missing = [str(p) for p in all_paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing files: {missing}")

    # ── Initialize DuckDB ──
    con = duckdb.connect(":memory:")

    for table_name, parquet_path in gold_tables.items():
        con.execute(
            f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{parquet_path}')"
        )

    con.execute(
        f"CREATE TABLE predictions AS SELECT * FROM read_parquet('{predictions_path}')"
    )

    # ── Load monitoring summary ──
    with open(monitoring_path) as f:
        monitoring_summary = json.load(f)

    return con, monitoring_summary


def get_table_info(con) -> list:
    """Return list of (table_name, row_count) tuples."""
    tables = con.execute("SHOW TABLES").fetchall()
    info = []
    for t in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        info.append((t[0], count))
    return info
