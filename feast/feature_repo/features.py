from datetime import timedelta
from pathlib import Path

from feast import FeatureView, FeatureService, Field, FileSource
from feast.types import Float64, Int64, String

from entities import customer

# ── Data source ──
# Points to the Parquet file exported from Databricks.
# The event_timestamp_column tells Feast which column represents
# the point-in-time for each feature row. We use pipeline_run_timestamp
# because this is a single-snapshot dataset — every row shares the
# same generation timestamp. In a production sliding-window setup,
# this would be the feature_cutoff_date cast to a timestamp.
PARQUET_PATH = str(
    Path(__file__).resolve().parent.parent.parent / "data" / "churn_feature_dataset.parquet"
)

churn_feature_source = FileSource(
    name="churn_feature_dataset",
    path=PARQUET_PATH,
    timestamp_field="pipeline_run_timestamp",
)

# ── Feature view ──
# Maps all 22 predictive features from the schema document (docs/feature_schema.md).
# Feature names match the Parquet columns exactly — this is the schema contract.
# The target column (churned) and metadata columns are intentionally excluded.
# Feast serves features, not labels. Labels are joined during training.
customer_churn_features = FeatureView(
    name="customer_churn_features",
    entities=[customer],
    schema=[
        # Transactional features (7)
        Field(name="order_count", dtype=Int64),
        Field(name="lifetime_spend", dtype=Float64),
        Field(name="avg_order_value", dtype=Float64),
        Field(name="days_since_last_order", dtype=Int64),
        Field(name="first_to_second_order_days", dtype=Int64),
        Field(name="total_items_purchased", dtype=Int64),
        Field(name="return_rate", dtype=Float64),
        # Behavioral features (6)
        Field(name="total_sessions", dtype=Int64),
        Field(name="session_count_30d", dtype=Int64),
        Field(name="avg_session_depth", dtype=Float64),
        Field(name="browse_to_buy_ratio", dtype=Float64),
        Field(name="cart_abandonment_rate", dtype=Float64),
        Field(name="days_since_last_session", dtype=Int64),
        # Product interaction features (4)
        Field(name="distinct_products_purchased", dtype=Int64),
        Field(name="distinct_categories_purchased", dtype=Int64),
        Field(name="favorite_category", dtype=String),
        Field(name="price_sensitivity_score", dtype=Float64),
        # Demographic features (5)
        Field(name="age", dtype=Int64),
        Field(name="gender", dtype=String),
        Field(name="country", dtype=String),
        Field(name="traffic_source", dtype=String),
        Field(name="account_age_days", dtype=Int64),
    ],
    source=churn_feature_source,
    # TTL controls how stale a feature can be before Feast considers it expired.
    # 365 days is generous for a batch-updated dataset. In production with
    # streaming features, this would be much shorter (hours or minutes).
    ttl=timedelta(days=365),
    online=True,
    description=(
        "Churn prediction features for TheLook e-commerce customers. "
        "22 features across transactional, behavioral, product interaction, "
        "and demographic groups. Schema version v1. "
        "See docs/feature_schema.md for the full contract."
    ),
)

# ── Feature service ──
# Bundles the features needed for churn prediction into a single
# retrievable unit. Training and serving both reference this service
# to ensure they pull the same feature set.
churn_prediction_service = FeatureService(
    name="churn_prediction_service",
    features=[customer_churn_features],
    description=(
        "Feature service for customer churn prediction. "
        "Serves all 22 features from customer_churn_features. "
        "Used by both MLflow training (historical) and serving (online)."
    ),
)
