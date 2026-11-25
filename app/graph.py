"""LangGraph workflows.

build_graph()           -> terminal version: classify -> draft -> approve (send / draft / skip) -> label
build_analysis_graph()  -> UI version: classify -> draft (approval UI mein hoti hai)
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.classifier import MailAnalysis, analyze_mail
from app.drafter import draft_reply
from app.gmail_client import create_draft, mark_processed, reply_address, send_reply


# ---- STATE: ek mail ke saath graph mein ghoomne wala data ----
class AgentState(TypedDict, total=False):
    mail: dict
    analysis: MailAnalysis
    reply: str
    decision: str  # "send" / "draft" / "skip"
    draft_id: str
    sent_id: str


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
    """Human-in-the-loop: tum decide karti ho ke reply bhejni hai, draft karni hai ya chhodni hai."""
    print("\n  --- Draft reply ---")
    print(f"  To: {reply_address(state['mail'])}")
    print()
    print(state["reply"])
    print("  -------------------")
    while True:
        ans = input("  [s] Send abhi  |  [d] Sirf draft save  |  [n] Skip : ").strip().lower()
        if ans == "s":
            # Bhejne se pehle ek aakhri confirmation (galti se send na ho)
            sure = input("  Pakka bhejni hai? (y/n): ").strip().lower()
            if sure == "y":
                return {"decision": "send"}
            print("  Send cancel. Dobara chuno.")
        elif ans == "d":
            return {"decision": "draft"}
        elif ans == "n":
            return {"decision": "skip"}
        else:
            print("  s, d ya n likho.")


def send_node(state: AgentState):
    """TOOL node: reply asli mein bhejo (sirf approval ke baad yahan pohanchta hai)."""
    sent_id = send_reply(state["mail"], state["reply"])
    print(f"  [Mail BHEJ di gayi, id: {sent_id}]")
    return {"sent_id": sent_id}


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
    # decision: "send" / "draft" / "skip"
    return state.get("decision", "skip")


# ---- GRAPH 1: terminal version ----
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("classify", classify_node)
    g.add_node("draft", draft_node)
    g.add_node("approve", approve_node)
    g.add_node("send", send_node)
    g.add_node("save", save_node)
    g.add_node("label", label_node)

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route_after_classify, {"draft": "draft", "skip": "label"})
    g.add_edge("draft", "approve")
    g.add_conditional_edges(
        "approve",
        route_after_approve,
        {"send": "send", "draft": "save", "skip": "label"},
    )
    g.add_edge("send", "label")
    g.add_edge("save", "label")
    g.add_edge("label", END)

    return g.compile()


# ---- GRAPH 2: UI version (approval + save + label UI ke buttons se hota hai) ----
def build_analysis_graph():
    g = StateGraph(AgentState)

    g.add_node("classify", classify_node)
    g.add_node("draft", draft_node)

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route_after_classify, {"draft": "draft", "skip": END})
    g.add_edge("draft", END)

    return g.compile()