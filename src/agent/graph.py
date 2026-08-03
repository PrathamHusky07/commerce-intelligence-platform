"""
LangGraph agent — single agent with conditional branching.

Three nodes, one conditional edge:
  load_signals → route → [investigate] → generate_brief → END

The agent routes conditionally: critical findings → investigate → brief;
no critical findings → brief directly.
"""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_google_vertexai")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*was deprecated.*")

from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


# ── Default LLM configuration ──
DEFAULT_PROJECT_ID = "ecommerce-lakehouse-mlops"
DEFAULT_LOCATION = "us-central1"
DEFAULT_MODEL = "gemini-2.5-flash"


class AgentState(TypedDict):
    signals_text: str
    findings_text: str
    has_critical: bool
    investigation_results: str
    briefing: str
    messages: list


def build_agent(
    signals: list,
    findings: list,
    agent_tools: list,
    project_id: str = DEFAULT_PROJECT_ID,
    location: str = DEFAULT_LOCATION,
    model_name: str = DEFAULT_MODEL,
):
    """
    Build and return the compiled LangGraph agent and the LLM instances.

    Returns:
        (agent, llm, llm_with_tools) — compiled graph, base LLM, tool-bound LLM.
    """
    llm = ChatVertexAI(
        model_name=model_name,
        project=project_id,
        location=location,
        temperature=0.3,
        max_output_tokens=4096,
    )
    llm_with_tools = llm.bind_tools(agent_tools)

    # ── Node: Load Signals ──
    def load_signals_node(state: AgentState) -> AgentState:
        signals_text = "\n".join([s.context for s in signals])

        findings_text_parts = []
        for f in findings:
            findings_text_parts.append(
                f"[{f.severity.upper()} | {f.priority} | confidence={f.confidence:.0%}] {f.title}\n"
                f"  {f.description}\n"
                f"  Evidence: {'; '.join(f.evidence[:3])}\n"
                f"  Action: {f.recommended_action}"
            )
        findings_text = "\n\n".join(findings_text_parts)
        has_critical = any(f.severity in ("critical", "notable") for f in findings)

        return {
            **state,
            "signals_text": signals_text,
            "findings_text": findings_text,
            "has_critical": has_critical,
            "investigation_results": "",
        }

    # ── Node: Investigate ──
    def investigate_node(state: AgentState) -> AgentState:
        actionable = [f for f in findings if f.severity in ("critical", "notable")]
        investigation_prompt = (
            "You are an AI Business Analyst. The following findings need investigation:\n\n"
            + "\n".join([f"- {f.title}: {f.description}" for f in actionable])
            + "\n\nUse the sql_query and churn_analysis tools to investigate the root causes. "
            "Be specific about which segments, categories, or distribution centers are driving these changes. "
            "Provide your analysis in a structured format."
        )
        messages = [
            SystemMessage(content="You are an expert business analyst. Use the provided tools to investigate."),
            HumanMessage(content=investigation_prompt),
        ]
        response = llm_with_tools.invoke(messages)

        investigation_text = ""
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                tool_fn = {t.name: t for t in agent_tools}.get(tc["name"])
                if tool_fn:
                    try:
                        result = tool_fn.invoke(tc["args"])
                        investigation_text += f"\n[Tool: {tc['name']}]\n{result}\n"
                    except Exception as e:
                        investigation_text += f"\n[Tool: {tc['name']}] Error: {e}\n"
        else:
            investigation_text = response.content if hasattr(response, "content") and response.content else ""

        return {**state, "investigation_results": investigation_text}

    # ── Node: Generate Brief ──
    def generate_brief_node(state: AgentState) -> AgentState:
        brief_prompt = f"""You are an AI Business Analyst generating an executive briefing.

BUSINESS SIGNALS:
{state['signals_text']}

KEY FINDINGS:
{state['findings_text']}

{f"INVESTIGATION RESULTS:{chr(10)}{state['investigation_results']}" if state['investigation_results'] else ""}

Generate a structured executive briefing with EXACTLY these 5 sections.
Use Markdown formatting. Be specific — cite numbers from the signals and findings.

STRICT RULES:
- ONLY reference metrics, values, and evidence explicitly provided above.
- Do NOT introduce external explanations, marketing hypotheses, or ungrounded recommendations.
- Every claim must trace to a specific signal or finding listed above.
- If you cannot explain a change from the evidence, say "requires further investigation" rather than guessing.
- For each key finding, explain WHY IT MATTERS by connecting related signals (e.g. revenue up + orders up + users flat = existing customers buying more, not new acquisition).
- After each hypothesis, note what additional data would strengthen or refute it (e.g. "Marketing spend data is unavailable, so acquisition effectiveness cannot be verified").

## Executive Summary
Two to three sentences summarizing the overall business state. Lead with the most important development.

## Business Health
A scoreboard of key metrics with their status (green/yellow/red) and delta values.
Format as a table.

## Key Findings & Hypotheses
The most important findings, ordered by priority (P1 first). Each with:
- What happened (cite the specific metric and delta)
- Why it matters (connect to other signals — what does this combination mean for the business?)
- Hypothesis based ONLY on the evidence above
- Confidence level
- Data limitation: what additional data would help verify

## Model & Monitoring Status
Current state of the ML model and monitoring system.

## Recommended Actions & Open Questions
Three to five specific, actionable recommendations tied to the findings above.
Each recommendation should specify what to investigate and what data to look at.
Plus any open questions that cannot be answered from the current data alone.
"""

        messages = [
            SystemMessage(content=(
                "You are an expert business analyst at a major e-commerce company. "
                "Your job is to synthesize pre-computed business signals and findings "
                "into a clear, actionable executive briefing. "
                "Never compute metrics yourself — only reference what is provided. "
                "Never introduce external knowledge or hypotheses not supported by the evidence. "
                "Write in a professional but direct tone. No filler."
            )),
            HumanMessage(content=brief_prompt),
        ]

        response = llm.invoke(messages)
        briefing = response.content if hasattr(response, "content") and response.content else ""

        return {**state, "briefing": briefing}

    # ── Routing ──
    def route_by_severity(state: AgentState) -> str:
        return "investigate" if state["has_critical"] else "generate_brief"

    # ── Build graph ──
    workflow = StateGraph(AgentState)
    workflow.add_node("load_signals", load_signals_node)
    workflow.add_node("investigate", investigate_node)
    workflow.add_node("generate_brief", generate_brief_node)
    workflow.add_edge(START, "load_signals")
    workflow.add_conditional_edges("load_signals", route_by_severity, {
        "investigate": "investigate",
        "generate_brief": "generate_brief",
    })
    workflow.add_edge("investigate", "generate_brief")
    workflow.add_edge("generate_brief", END)

    agent = workflow.compile()
    return agent, llm, llm_with_tools


def run_briefing(agent, findings, current_period, prior_period,
                 comparison_type="month_over_month", model_name=DEFAULT_MODEL,
                 reports_dir: Path = Path("reports")) -> str:
    """
    Run the agent and save the executive brief to a markdown file.

    Returns:
        The briefing text.
    """
    reports_dir.mkdir(exist_ok=True)

    initial_state = {
        "signals_text": "",
        "findings_text": "",
        "has_critical": False,
        "investigation_results": "",
        "briefing": "",
        "messages": [],
    }

    result = agent.invoke(initial_state)
    briefing_text = result["briefing"]

    # ── Save with metadata header ──
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"# Executive Briefing — E-Commerce Intelligence Platform\n\n"
        f"**Generated:** {ts}\n"
        f"**Analysis Period:** {prior_period} → {current_period} ({comparison_type})\n"
        f"**Model:** {model_name}\n"
        f"**Findings:** {len(findings)} "
        f"({sum(1 for f in findings if f.priority == 'P1')} P1, "
        f"{sum(1 for f in findings if f.priority == 'P2')} P2, "
        f"{sum(1 for f in findings if f.priority == 'P3')} P3)\n\n"
        f"---\n\n"
    )

    brief_path = reports_dir / "executive_brief.md"
    brief_path.write_text(header + briefing_text, encoding="utf-8")

    return briefing_text
