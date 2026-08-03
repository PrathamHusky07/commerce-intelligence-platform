# Feature Schema · Churn Prediction Dataset

**Version:** v1
**Notebook:** `04_feature_engineering.ipynb`
**Table:** `ecommerce.gold.churn_feature_dataset`

---

## 1. Dataset Overview

| Field | Value |
|---|---|
| Prediction task | Binary classification. Will a customer churn? |
| Prediction horizon | 90 days, configurable via `PREDICTION_WINDOW_DAYS` |
| Feature cutoff | `max(orders.created_at) - 90 days` |
| Observation unit | One row per customer (`user_id`) |
| Target | `churned = 1` if zero non-cancelled orders in the label window |
| Row count | 62,000 eligible customers from a base of 100,000 |
| Columns | 22 features, 1 target, 4 metadata |
| Source | TheLook E-Commerce, 7 tables, 3.35M rows |
| Eligibility | At least one non-cancelled order before the cutoff. Customers who never ordered are excluded because churn is undefined for them. |

---

## 2. Pipeline Lineage

BigQuery is exported to Parquet, uploaded to a Databricks Unity Catalog Volume, and ingested into Bronze with ingestion timestamps. Silver cleans, types, and validates the data, applies 13 Delta CHECK constraints, and adds derived columns. Gold aggregates Silver into five business-owned domain tables for analytics.

Feature engineering reads directly from Silver, not Gold. Gold tables aggregate across the full observation period, so using them for features would leak the label. The notebook applies its own temporal cutoff against Silver, computes features from the feature window, generates labels from the label window, and exports both a Delta table and a Parquet snapshot. The Parquet is consumed by Feast, MLflow, and Evidently.

---

## 3. Feature Groups

| Group | Count | Source | What It Captures |
|---|---|---|---|
| Transactional | 7 | `orders_clean`, `order_items_clean` | Spend, frequency, recency. `days_since_last_order` is typically the strongest single churn predictor. |
| Behavioral | 6 | `events_clean` | Browsing intensity, recent engagement, conversion behavior. Non-anonymous events only. |
| Product Interaction | 4 | `order_items_clean`, `products_clean` | Category breadth, product variety, price behavior. |
| Demographic | 5 | `customers_clean` | Time-independent attributes plus tenure. |

---

## 4. Feature Dictionary

### Transactional

| Feature | Type | Nullable | Definition |
|---|---|---|---|
| `order_count` | long | No | Non-cancelled orders before the cutoff |
| `lifetime_spend` | double | No | Sum of `sale_price` on non-cancelled items before the cutoff |
| `avg_order_value` | double | Yes | `lifetime_spend / order_count`, null when spend is zero |
| `days_since_last_order` | int | No | Days from the cutoff back to the most recent non-cancelled order |
| `first_to_second_order_days` | int | Yes | Days between order 1 and order 2, null for single-order customers |
| `total_items_purchased` | long | No | Count of non-cancelled order items before the cutoff |
| `return_rate` | double | Yes | Returned items divided by total items, item-level |

### Behavioral

| Feature | Type | Nullable | Definition |
|---|---|---|---|
| `total_sessions` | long | No | Distinct sessions across all history, zero if no events |
| `session_count_30d` | long | No | Distinct sessions in the 30 days before the cutoff |
| `avg_session_depth` | double | No | Events per session |
| `browse_to_buy_ratio` | double | No | Purchase events divided by product-view events |
| `cart_abandonment_rate` | double | No | 1 minus (purchase events divided by cart events) |
| `days_since_last_session` | int | No | Days since most recent event, sentinel of 360 for customers with no events |

### Product Interaction

| Feature | Type | Nullable | Definition |
|---|---|---|---|
| `distinct_products_purchased` | long | Yes | Count of distinct products in non-cancelled items |
| `distinct_categories_purchased` | long | Yes | Count of distinct categories via the products join |
| `favorite_category` | string | Yes | Category with the highest revenue per customer, revenue-weighted |
| `price_sensitivity_score` | double | Yes | Average discount percentage. Zero variance in TheLook because `sale_price` equals `retail_price`. Retained for design intent, excluded from training. |

### Demographic

| Feature | Type | Nullable | Definition |
|---|---|---|---|
| `age` | long | No | Age at cutoff, range 12 to 70 |
| `gender` | string | No | M or F, encoding deferred to training |
| `country` | string | Yes | Country string, encoding deferred to training |
| `traffic_source` | string | No | Acquisition channel: Search, Organic, Email, Facebook, Display |
| `account_age_days` | int | No | Days from account creation to cutoff |

### Target

| Column | Type | Definition |
|---|---|---|
| `churned` | int | 1 if zero non-cancelled orders in the label window, 0 otherwise |

Class balance is 92.9% churned (57,572) and 7.1% not churned (4,428). The imbalance reflects a 7-plus year customer history against a 90-day prediction window and is handled during training with class weights or threshold tuning.

### Pipeline Metadata

| Column | Type | Purpose |
|---|---|---|
| `feature_cutoff_date` | date | Which temporal snapshot generated these features |
| `prediction_window_days` | int | Churn definition window |
| `feature_version` | string | Schema version for lineage tracking |
| `pipeline_run_timestamp` | timestamp | Dataset creation time |

---

## 5. Null Handling

| Category | Features | Fill Strategy |
|---|---|---|
| Structurally undefined | `avg_order_value`, `first_to_second_order_days`, `return_rate` | Left null. Downstream models handle missingness through split rules or imputation. |
| Absence of activity | `total_sessions`, `session_count_30d`, `avg_session_depth`, `browse_to_buy_ratio`, `cart_abandonment_rate` | Filled with 0. Zero is the correct representation of "did not happen." |
| Sentinel required | `days_since_last_session` | Filled with 360, four times the prediction window, to signal "never engaged" without breaking numeric scale. |
| Processing lag edge case | `distinct_products_purchased`, `distinct_categories_purchased`, `favorite_category`, `price_sensitivity_score` | Left null for the 23 customers whose orders are pre-cutoff but whose items are post-cutoff by one to four days. |

---

## 6. Leakage Prevention

Label leakage is the most common silent failure in production ML. Three mechanisms prevent it:

**Read from Silver, not Gold.** Silver preserves row-level data with timestamps intact. Gold aggregates across the full observation window and would include information from after the cutoff.

**Independent timestamp validation.** The notebook re-queries source tables with the feature filters and confirms the maximum timestamp is strictly before the cutoff.

| Source | Max Timestamp in Features | Cutoff |
|---|---|---|
| `orders_clean` | 2026-04-16 23:56:14 | 2026-04-17 |
| `order_items_clean` | 2026-04-16 23:50:03 | 2026-04-17 |
| `events_clean` | 2026-04-16 23:59:25 | 2026-04-17 |

**Separate label generation.** Labels come from an independent query against the label window and share no intermediate DataFrames with features.

---

## 7. Feature Decisions

**`price_sensitivity_score` retained with zero variance.** TheLook has no discounts, so the feature is universally 0. It stays in the schema because the design is correct for any real dataset with promotions. Training excludes it explicitly.

**Categorical encoding deferred to training.** `gender`, `country`, `traffic_source`, and `favorite_category` remain as strings. Encoding depends on the algorithm and is decided in the training notebook. This keeps the feature dataset algorithm-agnostic.

**Favorite category by revenue, not frequency.** A customer who buys one $500 jacket and three $10 pairs of socks has "Outerwear" as their favorite category, not "Socks." Revenue reflects the economic relationship better than frequency.

**Left join for 23 processing-lag customers.** These customers placed orders before the cutoff, but the item records were written one to four days after. Left join with `fillna` keeps them in the dataset at zero spend rather than dropping them silently.

---

## 8. Feature Statistics

Point-in-time distribution snapshot from the v1 generation run. These serve as the reference baseline for Evidently drift detection.

| Feature | Mean | Median | P95 | Min | Max |
|---|---|---|---|---|---|
| `order_count` | 1.42 | 1 | 3 | 1 | 4 |
| `lifetime_spend` | 123.20 | 79.99 | 368.95 | 0.00 | 1,722.93 |
| `avg_order_value` | 86.53 | 60.58 | 239.99 | 1.50 | 1,149.99 |
| `days_since_last_order` | 612.04 | 441 | 1,766 | 1 | 2,657 |
| `total_sessions` | 2.26 | 2 | 5 | 1 | 12 |
| `session_count_30d` | 0.10 | 0 | 1 | 0 | 8 |
| `price_sensitivity_score` | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `account_age_days` | 1,394.75 | 1,409 | 2,541 | 4 | 2,662 |

Most customers are single-purchase (median `order_count` = 1), long-inactive (median `days_since_last_order` = 441), and minimally engaged (median `session_count_30d` = 0). This matches the 92.9% churn rate and reflects a typical e-commerce long tail.

---

## 9. Schema Freeze

Schema is frozen at v1. Any change to feature names, types, or semantics requires a version bump and coordinated updates to all downstream consumers. The `feature_version` metadata column lets multiple schema versions coexist during migration.

| Consumer | Contract |
|---|---|
| Feast | Feature views mirror these names and types exactly. Entity key is `user_id`. |
| MLflow training | Reads features from Feast's historical API. Drops `price_sensitivity_score` and metadata columns before training. |
| MLflow serving | Pulls online features from Feast for a given `user_id`. |
| Evidently | Compares production distributions against the baselines in Section 8. |
| AI Analyst Agent | Consumes churn predictions produced from this schema. |

---

## 10. Assumptions and Limitations

TheLook is a synthetic dataset from Google's Looker team. It is structurally realistic but not real transaction data. The project prioritizes engineering architecture over model accuracy, and the pipeline would apply directly to real e-commerce data.

Sale price equals retail price for every item, so `price_sensitivity_score` has zero variance and cannot demonstrate promotional signal.

Clickstream data is a static historical table, not a live stream. Features like `session_count_30d` are computed in batch. A production system would compute them from Kafka or Redpanda into Feast's online store in near real time.

The dataset produces one feature cutoff and one label set. A production system would use sliding-window training across multiple cutoffs. `PREDICTION_WINDOW_DAYS` and `FEATURE_CUTOFF` are configurable to support this.

The 92.9% churn rate reflects seven-plus years of customer history against a 90-day window. A live e-commerce platform with active marketing typically sees 15 to 40%.

Twenty-three of the 62,000 customers have orders before the cutoff but items after it. They are retained with zero spend metrics rather than dropped.

---

## 11. Future Enhancements

Features that would strengthen the model on richer data but are not supported by TheLook:

**Inter-purchase interval variance.** Standard deviation of gaps between orders. Sparse in TheLook because most customers order once.

**Session recency decay.** Exponential decay on session counts so recent sessions weigh more. Requires denser clickstream data.

**Discount utilization rate.** Fraction of purchases made on discount. Not computable because `sale_price` equals `retail_price` throughout.

**Brand loyalty concentration.** Herfindahl index of spend across brands. Sparse in TheLook due to the low repeat-purchase rate.
