"""
BigQuery Extraction Script for TheLook E-Commerce Dataset.

Reads all 7 TheLook tables from BigQuery public data and saves
them as Parquet files locally for upload to Databricks.

Authentication: Uses Google Application Default Credentials (ADC).
    Run `gcloud auth application-default login` before executing.

Usage:
    python src/ingestion/bigquery_extract.py
    python src/ingestion/bigquery_extract.py --tables users orders
    python src/ingestion/bigquery_extract.py --format csv
"""

import argparse
import os
import sys
import time

from google.cloud import bigquery

# Add project root to path so config imports work from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.config import BQ_PUBLIC_DATASET, DATA_DIR, GCP_PROJECT_ID, THELOOK_TABLES


def extract_table(client: bigquery.Client, table_name: str, output_dir: str, output_format: str = "parquet") -> dict:
    """
    Extract a single table from BigQuery and save locally.

    Args:
        client: Authenticated BigQuery client.
        table_name: Name of the table in thelook_ecommerce dataset.
        output_dir: Local directory to save the file.
        output_format: 'parquet' or 'csv'.

    Returns:
        dict with table_name, row_count, file_size_mb, duration_seconds.
    """
    full_table = f"{BQ_PUBLIC_DATASET}.{table_name}"
    ext = "parquet" if output_format == "parquet" else "csv"
    output_path = os.path.join(output_dir, f"{table_name}.{ext}")

    print(f"\n{'='*60}")
    print(f"Extracting: {full_table}")
    print(f"Output:     {output_path}")

    start = time.time()

    query = f"SELECT * FROM `{full_table}`"
    df = client.query(query, project=GCP_PROJECT_ID).to_dataframe()

    row_count = len(df)
    print(f"Rows:       {row_count:,}")

    if output_format == "parquet":
        df.to_parquet(output_path, index=False, engine="pyarrow")
    else:
        df.to_csv(output_path, index=False)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    duration = time.time() - start

    print(f"File size:  {file_size_mb:.2f} MB")
    print(f"Duration:   {duration:.1f}s")

    return {
        "table": table_name,
        "rows": row_count,
        "size_mb": round(file_size_mb, 2),
        "duration_s": round(duration, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Extract TheLook E-Commerce data from BigQuery.")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=THELOOK_TABLES,
        help=f"Tables to extract. Default: all ({', '.join(THELOOK_TABLES)})",
    )
    parser.add_argument(
        "--format",
        choices=["parquet", "csv"],
        default="parquet",
        help="Output format. Default: parquet",
    )
    parser.add_argument(
        "--output-dir",
        default=DATA_DIR,
        help=f"Output directory. Default: {DATA_DIR}",
    )
    args = parser.parse_args()

    # Validate table names
    for t in args.tables:
        if t not in THELOOK_TABLES:
            print(f"ERROR: Unknown table '{t}'. Valid tables: {', '.join(THELOOK_TABLES)}")
            sys.exit(1)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize BigQuery client using ADC
    print("Authenticating with Google Cloud (Application Default Credentials)...")
    try:
        client = bigquery.Client(project=GCP_PROJECT_ID)
        print(f"Authenticated. Project: {GCP_PROJECT_ID}")
    except Exception as e:
        print(f"ERROR: Failed to authenticate. Run 'gcloud auth application-default login' first.\n{e}")
        sys.exit(1)

    # Extract each table
    print(f"\nExtracting {len(args.tables)} tables from {BQ_PUBLIC_DATASET}")
    print(f"Output directory: {args.output_dir}")
    print(f"Format: {args.format}")

    results = []
    total_start = time.time()

    for table_name in args.tables:
        result = extract_table(client, table_name, args.output_dir, args.format)
        results.append(result)

    total_duration = time.time() - total_start

    # Print summary
    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"{'Table':<25} {'Rows':>12} {'Size (MB)':>12} {'Time (s)':>10}")
    print(f"{'-'*25} {'-'*12} {'-'*12} {'-'*10}")

    total_rows = 0
    total_size = 0.0
    for r in results:
        print(f"{r['table']:<25} {r['rows']:>12,} {r['size_mb']:>12.2f} {r['duration_s']:>10.1f}")
        total_rows += r["rows"]
        total_size += r["size_mb"]

    print(f"{'-'*25} {'-'*12} {'-'*12} {'-'*10}")
    print(f"{'TOTAL':<25} {total_rows:>12,} {total_size:>12.2f} {total_duration:>10.1f}")
    print(f"\nAll files saved to: {args.output_dir}")
    print(f"Next step: Upload these files to Databricks Volume at /Volumes/ecommerce/bronze/raw_data/")


if __name__ == "__main__":
    main()
