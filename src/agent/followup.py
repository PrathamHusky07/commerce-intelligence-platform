"""
Interactive follow-up Q&A — Mode 2.

v5 — Production Readiness Sprint:
  #2  Type-guard response.content when it's a list of content blocks (Gemini)
  #4  Supporting data returned as markdown table (from to_markdown()),
      rendered by _format_chat_html as an HTML <table>
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage


TABLE_SCHEMAS = """
AVAILABLE TABLES AND THEIR EXACT COLUMN NAMES:

customer_360: user_id, first_name, last_name, email, age, gender (values: M, F),
  country, state, city, traffic_source (values: Search, Organic, Facebook, Email, Display),
  account_created_at, order_count, lifetime_spend, avg_order_value,
  avg_item_sale_price, total_items_purchased, distinct_products_purchased, return_rate,
  favorite_category, first_order_at, last_order_at, days_since_last_order,
  first_to_second_order_days, total_sessions, session_count_30d, days_since_last_session,
  avg_session_depth, browse_to_buy_ratio, cart_abandonment_rate

product_performance: product_id, name, brand, category, department (values: Men, Women),
  sku, cost, retail_price, base_margin, distribution_center_id, units_sold,
  total_revenue, avg_selling_price, unique_buyers, units_returned, return_rate,
  total_units_received, units_in_stock, sell_through_rate, avg_days_to_sell,
  total_margin, margin_pct, category_revenue_rank, first_sold_at, last_sold_at

inventory_health: product_id, name, brand, category, distribution_center_id,
  distribution_center_name, total_units_received, units_sold, units_in_stock,
  avg_unit_cost, stock_value, turnover_rate, avg_days_to_sell, days_of_supply,
  daily_sell_rate, last_sale_at, days_since_last_sale,
  is_dead_stock (boolean: true/false), reorder_signal (boolean: true/false),
  oldest_unsold_received_at

fulfillment_metrics: distribution_center_id, distribution_center_name, order_month,
  orders_fulfilled, items_fulfilled, avg_delivery_days, median_delivery_days,
  avg_ship_days, on_time_deliveries, total_deliveries, on_time_rate, returned_items,
  return_rate, total_revenue

funnel_analytics: user_id, event_month, sessions, total_events, avg_session_depth,
  home_events, department_events, product_view_events, cart_events, purchase_events,
  cancel_events, session_to_purchase_rate, cart_to_purchase_rate, browse_depth,
  sessions_mom_change, first_event_at, last_event_at

predictions: user_id, churn_probability (float 0-1),
  predicted_label (integer: 1=churned, 0=not churned),
  prediction_timestamp, model_name, model_version
"""


def _build_findings_context(findings) -> str:
    context = "\nCURRENT FINDINGS FROM THE EXECUTIVE BRIEFING:\n"
    for f in findings:
        context += f"- [{f.severity.upper()}] {f.title}: {f.description}\n"
        context += f"  Evidence: {'; '.join(f.evidence[:3])}\n"
    return context


def _normalize_content(content) -> str:
    """#2 — Normalize LLM response content to a plain string.

    Gemini via LangChain can return `.content` as either:
      - a plain string (most common)
      - a list of content blocks: [{"type": "text", "text": "..."}, ...]
      - a list of strings (rare, but possible)

    This helper flattens all cases to a single string, preventing the
    TypeError: sequence item 0: expected str instance, list found
    that crashes `"\\n".join(output_parts)` downstream.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content") or ""
                if text:
                    parts.append(str(text))
            else:
                # Unknown block type — coerce safely
                parts.append(str(block))
        return "\n".join(parts)
    # Any other type — coerce to string safely
    return str(content)


def _extract_sql_from_malformed(response) -> str:
    metadata = getattr(response, "response_metadata", {})
    finish_msg = metadata.get("finish_message", "")
    if "sql_query" in finish_msg and "query=" in finish_msg:
        match = re.search(r"query=['\"](.+?)['\"]\\)", finish_msg, re.DOTALL)
        if not match:
            match = re.search(r"query=\'\'\'(.*?)\'\'\'", finish_msg, re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""


def _summarize_result(question: str, result_text: str, llm, findings_context: str) -> str:
    """Ask the LLM to produce a structured analyst-style summary.
    #6 — Prompt instructs the LLM to avoid em dashes."""
    summary_prompt = (
        f"You are a senior business analyst at a major e-commerce company.\n\n"
        f"Question: {question}\n\n"
        f"SQL Result:\n{result_text}\n\n"
        f"Write a structured executive-friendly response with EXACTLY this format:\n\n"
        f"**Answer**\n"
        f"One to three sentences with the key insight. Lead with the most important finding. "
        f"Cite specific numbers from the result.\n\n"
        f"**Why It Matters**\n"
        f"One to two sentences connecting this to the broader business context or executive briefing findings.\n\n"
        f"WRITING RULES:\n"
        f"- Do NOT include the raw data table.\n"
        f"- Do NOT invent numbers not in the result.\n"
        f"- Do NOT say 'based on the data' or 'according to the results'.\n"
        f"- Do NOT use em dashes (—). Use commas, periods, or semicolons instead.\n"
        f"- Write in natural business English. No filler words.\n\n"
        f"CURRENT FINDINGS:\n{findings_context}"
    )
    try:
        response = llm.invoke([
            SystemMessage(content=(
                "You are a senior business analyst. Write concise, executive-friendly summaries. "
                "Use a professional tone. Cite numbers from the provided data only. "
                "Follow the exact format requested: Answer paragraph, then Why It Matters paragraph. "
                "Never use em dashes. Use commas, periods, or semicolons instead."
            )),
            HumanMessage(content=summary_prompt),
        ])
        # #2 — Normalize content (handles str, list of blocks, etc.)
        summary = _normalize_content(getattr(response, "content", None))
        if summary:
            return (
                f"{summary}\n\n"
                f"---\n\n"
                f"**Supporting Data**\n\n"
                f"```\n{result_text}\n```"
            )
        return f"```\n{result_text}\n```"
    except Exception:
        return f"```\n{result_text}\n```"


def ask_followup(question: str, llm, llm_with_tools, agent_tools, con, findings) -> str:
    """Ask the agent a follow-up question grounded in the briefing context."""
    findings_context = _build_findings_context(findings)

    messages = [
        SystemMessage(content=(
            "You are a senior business analyst at a major e-commerce company. "
            "An executive briefing was just generated. The user is asking a follow-up question. "
            "Use the sql_query tool to query the data and answer the question.\n\n"
            "IMPORTANT RULES:\n"
            "- Use ONLY the exact column names listed in the schema below.\n"
            "- Write simple, correct SQL. Prefer straightforward queries over CTEs.\n"
            "- LIMIT results to at most 10 rows.\n"
            "- If the exact question cannot be answered with the available data, "
            "explain why briefly and then offer the closest available information "
            "by querying what IS available. Never just say 'I cannot determine'.\n"
            "- Use a professional, concise tone.\n"
            f"{TABLE_SCHEMAS}\n"
            f"{findings_context}"
        )),
        HumanMessage(content=f"Question: {question}"),
    ]

    response = llm_with_tools.invoke(messages)

    raw_result = ""
    output_parts = []

    # #2 — Always normalize response.content, since Gemini sometimes returns a list of blocks
    content_str = _normalize_content(getattr(response, "content", None))
    if content_str.strip():
        output_parts.append(content_str)

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            tool_fn = {t.name: t for t in agent_tools}.get(tc["name"])
            if tool_fn:
                try:
                    result = tool_fn.invoke(tc["args"])
                    raw_result = result
                    output_parts.append(f"\n{result}")
                except Exception:
                    output_parts.append(
                        "\n\nI wasn't able to retrieve this data. "
                        "Please try rephrasing the question or explore the relevant "
                        "section in the Business Explorer page."
                    )

    if not output_parts or (len(output_parts) == 1 and not output_parts[0].strip()):
        extracted_sql = _extract_sql_from_malformed(response)
        if extracted_sql:
            try:
                result_df = con.execute(extracted_sql).fetchdf()
                if not result_df.empty:
                    total = len(result_df)
                    display_df = result_df.head(10)
                    # #4 — markdown table so _format_chat_html renders it as HTML <table>
                    raw_result = display_df.to_markdown(
                        index=False,
                        floatfmt=",.2f",
                    )
                    if total > 10:
                        raw_result += f"\n\n(Showing top 10 of {total} rows)"
                    output_parts = [raw_result]
                else:
                    output_parts = ["The query returned no results for this question."]
            except Exception:
                output_parts = [
                    "I wasn't able to retrieve this data with the generated query. "
                    "Please try rephrasing the question or explore the relevant "
                    "section in the Business Explorer page."
                ]
        else:
            # #2 — Normalize content again for the fallback path
            fallback = _normalize_content(getattr(response, "content", ""))
            if fallback and len(fallback.strip()) > 10:
                output_parts = [fallback]
            else:
                output_parts = [
                    "I wasn't able to generate a query for this question. "
                    "Please try rephrasing it or explore the relevant "
                    "section in the Business Explorer page."
                ]

    # #2 — Every element in output_parts is now a string; join is safe
    raw_output = "\n".join(output_parts)
    if raw_result and "Error" not in raw_result and "no results" not in raw_result.lower():
        return _summarize_result(question, raw_result, llm, findings_context)
    return raw_output
