from feast import Entity, ValueType

# Every feature in this project is keyed on a single customer.
# The user_id column in churn_feature_dataset.parquet is the join key.
customer = Entity(
    name="customer",
    join_keys=["user_id"],
    value_type=ValueType.INT64,
    description="A unique customer in the TheLook e-commerce platform.",
)
