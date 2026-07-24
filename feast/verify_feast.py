"""
Feast Feature Store — End-to-End Verification

Run from the repo root:
    python feast/verify_feast.py

This script:
  1. Applies the feature repo (registers entities, views, services)
  2. Materializes features into the SQLite online store
  3. Retrieves historical features (training path)
  4. Retrieves online features (serving path)
  5. Prints summary statistics to confirm everything works

If all 4 steps succeed, the feature store is ready for MLflow training.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Feast needs to be run from the feature_repo directory so it can
# find feature_store.yaml. We add it to the path and chdir.
REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURE_REPO = Path(__file__).resolve().parent / "feature_repo"
DATA_DIR = REPO_ROOT / "data"

sys.path.insert(0, str(FEATURE_REPO))

import os
os.chdir(FEATURE_REPO)

from feast import FeatureStore

# Import the objects we need to register explicitly (Feast 0.64+ API)
from entities import customer
from features import churn_feature_source, customer_churn_features, churn_prediction_service

# ── Step 0: Load the Parquet to get timestamps and user_ids ──
parquet_path = DATA_DIR / "churn_feature_dataset.parquet"
print("=" * 60)
print("  FEAST VERIFICATION")
print("=" * 60)
print(f"\n  Parquet: {parquet_path}")

raw_df = pd.read_parquet(parquet_path)
print(f"  Rows:    {len(raw_df):,}")
print(f"  Columns: {list(raw_df.columns)}")

# ── Step 1: Apply the feature repo ──
print(f"\n{'─' * 60}")
print("  Step 1: Applying feature repository...")
store = FeatureStore(repo_path=str(FEATURE_REPO))

# Feast 0.64+ requires explicit object registration.
store.apply([customer, churn_feature_source, customer_churn_features, churn_prediction_service])
print("  ✓ Feature repo applied successfully.")
print(f"    Registry: {FEATURE_REPO.parent / 'registry.db'}")

# ── Step 2: Materialize to the online store ──
print(f"\n{'─' * 60}")
print("  Step 2: Materializing features to online store...")

# Materialize window: from well before the data to now.
# The pipeline_run_timestamp in the data is the event timestamp.
start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
end_date = datetime.now(timezone.utc)

store.materialize(start_date=start_date, end_date=end_date)
print("  ✓ Materialization complete.")
print(f"    Online store: {FEATURE_REPO.parent / 'online_store.db'}")

# ── Step 3: Historical feature retrieval (training path) ──
print(f"\n{'─' * 60}")
print("  Step 3: Testing historical feature retrieval (training path)...")

# Create an entity DataFrame — this is what MLflow training would pass.
# We take 5 sample customers and ask Feast for their features at a
# specific point in time (the pipeline_run_timestamp from the data).
sample_users = raw_df["user_id"].head(5).tolist()
event_ts = raw_df["pipeline_run_timestamp"].iloc[0]

# Ensure timestamp is timezone-aware
if event_ts.tzinfo is None:
    event_ts = event_ts.tz_localize("UTC")

entity_df = pd.DataFrame({
    "user_id": sample_users,
    "event_timestamp": [event_ts] * len(sample_users),
})

historical_features = store.get_historical_features(
    entity_df=entity_df,
    features=store.get_feature_service("churn_prediction_service"),
).to_df()

print(f"  ✓ Historical retrieval returned {len(historical_features)} rows, "
      f"{len(historical_features.columns)} columns")
print(f"    Columns: {list(historical_features.columns)}")
print(f"\n  Sample (first 2 rows):")
print(historical_features.head(2).to_string(index=False))

assert len(historical_features) == 5, f"Expected 5 rows, got {len(historical_features)}"

# ── Step 4: Online feature retrieval (serving path) ──
print(f"\n{'─' * 60}")
print("  Step 4: Testing online feature retrieval (serving path)...")

# This simulates what the MLflow serving endpoint would do:
# given a user_id, pull their latest features from the online store.
online_features = store.get_online_features(
    features=store.get_feature_service("churn_prediction_service"),
    entity_rows=[{"user_id": uid} for uid in sample_users],
).to_dict()

print(f"  ✓ Online retrieval returned features for {len(online_features['user_id'])} customers")
print(f"    Features retrieved: {list(online_features.keys())}")
print(f"\n  Sample (first customer):")
for key, values in online_features.items():
    print(f"    {key}: {values[0]}")

assert len(online_features["user_id"]) == 5, f"Expected 5 customers, got {len(online_features['user_id'])}"

# ── Summary ──
print(f"\n{'=' * 60}")
print("  ALL VERIFICATION STEPS PASSED")
print("=" * 60)
print(f"  Entity:          customer (user_id)")
print(f"  Feature view:    customer_churn_features (22 features)")
print(f"  Feature service: churn_prediction_service")
print(f"  Offline store:   FileSource (Parquet)")
print(f"  Online store:    SQLite")
print(f"  Registry:        {FEATURE_REPO.parent / 'registry.db'}")
print(f"  Online DB:       {FEATURE_REPO.parent / 'online_store.db'}")
print(f"\n  The feature store is ready for MLflow training.")
print(f"  Next: use get_historical_features() in the training notebook")
print(f"        to build the training set from Feast.")
print("=" * 60)
