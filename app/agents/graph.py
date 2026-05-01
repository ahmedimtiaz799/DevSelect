from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config import settings
from app.agents.state import DevSelectState
from app.agents.agent1_cv_extraction import agent1_cv_extraction
from app.agents.agent2_github_analysis import agent2_github_analysis
from app.agents.agent3_lead_evaluator import agent3_lead_evaluator

def route_after_agent1(state: DevSelectState) -> str:
    github_analysis = state.get("github_analysis")
    if github_analysis and github_analysis.scenario in ("ACCESSIBLE", "MULTIPLE_FOUND"):
        return "agent_2"
    return "agent_3"

async def build_graph():
    checkpointer=AsyncPostgresSaver.from_conn_string(
        settings.DATABASE_URL
    )
    await checkpointer.setup()

    workflow=StateGraph(DevSelectState)

    workflow.add_node("agent_1",agent1_cv_extraction)
    workflow.add_node("agent_2",agent2_github_analysis)
    workflow.add_node("agent_3",agent3_lead_evaluator)

    workflow.add_edge(START,"agent_1")

    workflow.add_conditional_edges(
        "agent_1",
        route_after_agent1,
        {
            "agent_2":"agent_2",
            "agent_3":"agent_3",
        },
    )

    workflow.add_edge("agent_2","agent_3")
    workflow.add_edge("agent_3",END)

    graph=workflow.compile(checkpointer=checkpointer)

    return graph

