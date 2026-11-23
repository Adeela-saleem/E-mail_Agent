"""LangGraph workflow: classify -> (draft -> approve -> save) -> label, with conditional routing."""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.classifier import MailAnalysis, analyze_mail
from app.drafter import draft_reply
from app.gmail_client import create_draft, mark_processed


# ---- STATE: ek mail ke saath graph mein ghoomne wala data ----
class AgentState(TypedDict, total=False):
    mail: dict
    analysis: MailAnalysis
    reply: str
    approved: bool
    draft_id: str


# ---- NODES: har node ek kaam karta hai aur state ka hissa update karta hai ----
def classify_node(state: AgentState):
    analysis = analyze_mail(state["mail"])
    print(f"  Category: {analysis.category} | Needs reply: {analysis.needs_reply}")
    print(f"  Summary : {analysis.summary}")
    return {"analysis": analysis}


def draft_node(state: AgentState):
    reply = draft_reply(state["mail"], state["analysis"])
    return {"reply": reply}


def approve_node(state: AgentState):
    print("\n  --- Draft reply ---")
    print(state["reply"])
    print("  -------------------")
    ans = input("  Gmail Drafts mein save karun? (y/n): ")
    return {"approved": ans.strip().lower() == "y"}


def save_node(state: AgentState):
    draft_id = create_draft(state["mail"], state["reply"])
    print(f"  [Draft save ho gaya, id: {draft_id}]")
    return {"draft_id": draft_id}


def label_node(state: AgentState):
    """TOOL node: mail par AI-Processed label lagao (har raaste ke end par chalta hai)."""
    mark_processed(state["mail"]["id"])
    print("  [Label lag gaya: AI-Processed]")
    return {}


# ---- CONDITIONAL EDGES: yahan agent "decide" karta hai agla kadam ----
def route_after_classify(state: AgentState) -> str:
    return "draft" if state["analysis"].needs_reply else "skip"


def route_after_approve(state: AgentState) -> str:
    return "save" if state.get("approved") else "skip"


# ---- GRAPH BANAO ----
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("classify", classify_node)
    g.add_node("draft", draft_node)
    g.add_node("approve", approve_node)
    g.add_node("save", save_node)
    g.add_node("label", label_node)

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route_after_classify, {"draft": "draft", "skip": "label"})
    g.add_edge("draft", "approve")
    g.add_conditional_edges("approve", route_after_approve, {"save": "save", "skip": "label"})
    g.add_edge("save", "label")
    g.add_edge("label", END)

    return g.compile()