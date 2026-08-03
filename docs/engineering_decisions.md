# Engineering Decisions

This document captures the key architectural choices behind the E-Commerce Intelligence Platform. Each decision is written as a lightweight Architecture Decision Record with the context, the choice, the alternatives considered, and the reasoning.

The goal is to make the "why" behind the system explicit, so that a reader can evaluate the design without having to read the code first.

---

## 1. Medallion Architecture for the Lakehouse

**Context.** The pipeline ingests raw data from BigQuery and needs to serve business analytics, machine learning, and an agent. These consumers have different requirements for cleanliness, structure, and semantics.

**Decision.** Adopt a Bronze, Silver, Gold medallion structure inside Databricks Unity Catalog, with one catalog (`ecommerce`) and three schemas.

**Alternatives considered.** A single flat schema per table, or a raw and curated split. Both were rejected because they collapse the boundary between "what came in" and "what the business owns."

**Rationale.** The medallion pattern gives every layer a clear contract. Bronze preserves the source exactly for lineage and reprocessing. Silver enforces types, constraints, and referential integrity, so downstream consumers do not have to defend against bad data. Gold is business-shaped and business-owned, which is what the ML pipeline and the agent need. This separation also allows the layers to evolve independently.

---

## 2. Domain-Oriented Gold Tables

**Context.** Gold tables can either mirror the operational schema (one table per source entity) or reflect how business teams actually work.

**Decision.** Build five domain-oriented Gold tables, each with a named owner: `customer_360` (Marketing and CRM), `product_performance` (Merchandising), `inventory_health` (Supply Chain), `fulfillment_metrics` (Operations), and `funnel_analytics` (Growth and Product).

**Alternatives considered.** Continuing to mirror source tables at the Gold layer.

**Rationale.** Business teams do not think in normalized schemas. A marketing lead asks about customers, not about the `users` table joined to `orders` joined to `order_items`. Domain tables make the platform legible to the people who use it, and they make the boundary between engineering and the business explicit through ownership.

---

## 3. Features Engineered from Silver, Not Gold

**Context.** Gold tables aggregate across the full observation period, including data that would not have been available at prediction time. Using them for features would leak the label.

**Decision.** Engineer all 22 churn features from Silver tables with an explicit `FEATURE_CUTOFF_DATE` and a 90-day prediction window. Gold tables are never read during feature engineering.

**Alternatives considered.** Building features directly on Gold, which is faster and simpler.

**Rationale.** Label leakage is the single most common failure mode in production ML. If the model sees future information during training, its offline metrics will look strong and its production behavior will collapse. Reading from Silver with a temporal cutoff enforces point-in-time correctness. The 23-user discrepancy caught during validation, and the diagnostic cell preserved in the notebook, demonstrates the discipline this decision requires.

---

## 4. Feast Instead of Databricks Feature Store

**Context.** The platform needs offline features for training and online features for serving. Databricks Feature Store is not available on the Free Edition.

**Decision.** Use open-source Feast with a Parquet offline store and a SQLite online store, both running locally.

**Alternatives considered.** Databricks Feature Store, which would have been the default choice on a paid workspace.

**Rationale.** Feast provides the same API for offline and online features, which prevents training-serving skew at the interface level. It runs locally without a managed service, which keeps the project portable and reproducible on any machine. The pattern also demonstrates the underlying concept, rather than depending on a vendor abstraction that hides how a feature store actually works.

---

## 5. LightGBM as the Production Model

**Context.** Multiple training runs were logged in MLflow across three model families: logistic regression as a baseline, four LightGBM configurations, and four XGBoost configurations.

**Decision.** Register `lgb_0.05lr_31lv_100est` as `ecommerce-churn-model v2` in the MLflow Staging registry. AUC-ROC is 0.7417 with 75.2% recall and 96.2% precision.

**Alternatives considered.** XGBoost, which was tested with equivalent hyperparameter sweeps.

**Rationale.** All four XGBoost runs predicted every customer as churned because the `scale_pos_weight` correction was too aggressive for the imbalance in this dataset. Precision collapsed to the base rate and recall pinned at 1.0, which is a well-known failure mode of over-correction. LightGBM's built-in `is_unbalance` flag produced genuine discrimination. Logistic regression served as a baseline and confirmed that tree models justified their added complexity. Neural networks were intentionally out of scope because the goal was a production-oriented tabular pipeline rather than maximizing predictive performance, and gradient boosted trees remain the strongest default for tabular data at this scale.

---

## 6. Single LangGraph Agent, Not a Multi-Agent System

**Context.** Agentic systems can be built as a single agent with tools, or as a supervisor orchestrating specialist agents with shared state.

**Decision.** Build the AI Business Analyst as a single LangGraph agent with three nodes, one conditional edge, and five tools (`kpi_summary`, `sql_query`, `churn_analysis`, `monitoring_status`, `chart_generator`).

**Alternatives considered.** A multi-agent supervisor pattern with specialist agents for analytics, monitoring, and narration.

**Rationale.** The problem is structured investigation over a bounded set of tables with a deterministic signal layer. A single agent with typed tools solves this cleanly. Multi-agent orchestration adds latency, coordination overhead, and failure modes that are not justified by the problem's complexity. Architecture should match the problem, not the trend. A separate portfolio project uses a multi-agent supervisor pattern where the workflow genuinely requires it.

---

## 7. The LLM Never Computes Metrics

**Context.** Text-to-SQL agents are popular, and it is tempting to let the LLM generate arbitrary SQL against the data. That path produces inconsistent numbers, hallucinated aggregations, and results that cannot be reproduced.

**Decision.** All metrics, comparisons, and severity classifications are computed in Python and DuckDB before the LLM sees them. The LLM receives structured `Signal` and `Finding` objects and generates narrative around them. The `sql_query` tool exists only for interactive follow-up, and its output is always summarized by a second, controlled prompt.

**Alternatives considered.** Standard Text-to-SQL with the LLM writing queries and interpreting results end to end.

**Rationale.** Executives cannot make decisions on numbers that change between runs. Deterministic computation guarantees reproducibility. The LLM then does what it is genuinely good at, which is synthesis and language, rather than arithmetic. This separation is also what makes the platform auditable, because every claim in the briefing traces back to a pre-computed signal.

---

## 8. DuckDB for the Local Analytics Engine

**Context.** The agent and the Streamlit application need low-latency SQL over the Gold Parquet files. Databricks Free Edition has no SQL warehouse endpoint that a local application can call.

**Decision.** Use DuckDB embedded in the Python process, reading Gold Parquet snapshots directly.

**Alternatives considered.** PostgreSQL, SQLite, or an in-memory pandas approach.

**Rationale.** DuckDB is designed exactly for this workload. It reads Parquet without a load step, joins across files at high speed, and runs in the same process as the application without a separate service. PostgreSQL would introduce an additional service to provision and manage for a local deployment. SQLite lacks the analytical query performance the signals layer needs. Pandas would work for a subset of the queries but not for the aggregations and window functions the analytics engine relies on. In a production deployment the connection string would point at a warehouse rather than local files, and the query logic would be unchanged.

---

## 9. Gemini 2.5 Flash on Vertex AI with Application Default Credentials

**Context.** The agent needs an LLM for narrative synthesis and interactive follow-up. Two access paths exist for Gemini models, one through the public API with a key and one through Vertex AI with Google Cloud authentication.

**Decision.** Use `gemini-2.5-flash` through `ChatVertexAI` with Application Default Credentials. No API keys are ever stored.

**Alternatives considered.** The public Gemini API with a stored key, or `ChatGoogleGenerativeAI` with a service account JSON file. An earlier iteration used `gemini-2.5-flash-lite`, which was swapped out after it failed on SQL tool calls with common table expressions.

**Rationale.** ADC removes credential files from the developer machine and from the repository. It is the pattern Google recommends and the one production systems use. Vertex AI also provides the enterprise auth surface that a real deployment would rely on. Flash was chosen over Flash Lite because tool calling with more complex SQL was more reliable, and the cost difference is negligible at portfolio scale.

---

## 10. Streamlit Community Cloud for Public Deployment

**Context.** A portfolio project needs a public URL that a hiring manager can click, without infrastructure for the reviewer to run.

**Decision.** Deploy the application to Streamlit Community Cloud at `ecom-ai-intelligence.streamlit.app`, with only the runtime Gold Parquet files committed to the repository. Pipeline inputs stay out of Git.

**Alternatives considered.** A cloud VM with a self-hosted Streamlit process, Hugging Face Spaces, or Fly.io.

**Rationale.** Streamlit Community Cloud gives the shortest path from a GitHub commit to a live URL. The deployed application is intentionally decoupled from the data pipeline: the pipeline generates versioned Parquet artifacts, and the application consumes immutable outputs. This separation matches the storytelling of the project, since the analytics engine is deterministic and self-contained, so it can serve from local artifacts, while the LLM features run locally where Google credentials are available. The `.gitignore` was configured to include only the Parquet files the application actually reads at runtime, keeping the repository small while still deploying with real data.

---

## 11. Application Reads Local Parquet Snapshots, Not Databricks Directly

**Context.** The Streamlit application needs to read Gold-layer data at runtime. It could query Databricks directly through a SQL endpoint, or it could read local Parquet snapshots exported from Databricks.

**Decision.** Export Gold tables as Parquet snapshots to `data/`, commit the runtime files to the repository, and read them locally through DuckDB.

**Alternatives considered.** A live connection from the application to Databricks through a SQL warehouse, using the Databricks SDK or JDBC driver.

**Rationale.** The pipeline layer and the application layer serve different purposes and should be decoupled. The pipeline generates trusted analytical artifacts. The application consumes those artifacts as immutable inputs. Reading from local Parquet also removes a runtime dependency, so the deployed application does not fail when Databricks is unreachable, credentials expire, or a SQL warehouse is paused. Startup is faster because there is no cold-start on a remote engine. Streamlit Community Cloud, which runs the deployment, cannot hold Databricks credentials without introducing a secrets management pattern that adds no value at portfolio scale. In production the same separation applies, with the export step writing to object storage and the application reading from a versioned prefix rather than a live warehouse.

---

## Notes on Scope

Several capabilities are deliberately out of scope. Streaming ingestion, orchestration through Airflow or Databricks Workflows, containerization, model registry approval gates, and a managed online feature store are all production-scale concerns that would replace equivalent components in this design. The Production Considerations section of the README describes how each layer would evolve. Keeping those out of the current implementation was a scoping choice, not an oversight.
