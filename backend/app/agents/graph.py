from langgraph.graph import StateGraph, START, END
from app.agents.state import DevSelectState
from app.agents.agent1_cv_extraction import agent1_cv_extraction
from app.agents.agent2_github_analysis import agent2_github_analysis
from app.agents.agent3_lead_evaluator import agent3_lead_evaluator

def _candidate_field(candidate, name: str):
    if isinstance(candidate, dict):
        return candidate.get(name)
    return getattr(candidate, name, None)


def route_after_agent1(state: DevSelectState) -> str:
    if state.get("error"):
        return END
    candidate = state.get("candidate")
    if candidate and _candidate_field(candidate, "github_url"):
        return "agent_2"
    return "agent_3"

def build_graph(checkpointer):
    workflow = StateGraph(DevSelectState)

    workflow.add_node("agent_1", agent1_cv_extraction)
    workflow.add_node("agent_2", agent2_github_analysis)
    workflow.add_node("agent_3", agent3_lead_evaluator)

    workflow.add_edge(START, "agent_1")

    workflow.add_conditional_edges(
        "agent_1",
        route_after_agent1,
        {
            "agent_2": "agent_2",
            "agent_3": "agent_3",
            END: END,
        },
    )

    workflow.add_edge("agent_2", "agent_3")
    workflow.add_edge("agent_3", END)

    graph = workflow.compile(checkpointer=checkpointer)

    return graph
