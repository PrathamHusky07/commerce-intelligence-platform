"""
Configuration for the E-Commerce Lakehouse MLOps project.

Loads environment variables and defines dataset/catalog constants.
Uses Google Application Default Credentials (ADC) — no service account JSON keys.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# GCP Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ecommerce-lakehouse-mlops")
BQ_PUBLIC_DATASET = "bigquery-public-data.thelook_ecommerce"

# TheLook E-Commerce tables to extract
THELOOK_TABLES = [
    "users",
    "orders",
    "order_items",
    "products",
    "inventory_items",
    "distribution_centers",
    "events",
]

# Local paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Databricks Unity Catalog paths
DATABRICKS_CATALOG = "ecommerce"
DATABRICKS_BRONZE_SCHEMA = "bronze"
DATABRICKS_SILVER_SCHEMA = "silver"
DATABRICKS_GOLD_SCHEMA = "gold"
DATABRICKS_VOLUME_PATH = f"/Volumes/{DATABRICKS_CATALOG}/{DATABRICKS_BRONZE_SCHEMA}/raw_data"
