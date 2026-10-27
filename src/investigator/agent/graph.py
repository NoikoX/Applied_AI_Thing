"""The agent as a LangGraph state machine.

    START -> plan -> retrieve -> grade --(gap found, hops left)--> retrieve
                                   \\--(enough, or out of hops)--> extract -> answer -> END

LangGraph runs the nodes, passes the state between them and follows the
conditional edge; the nodes themselves are plain functions in nodes.py.
"""

from functools import partial

from langgraph.graph import END, START, StateGraph

from investigator.agent.nodes import (
    Deps,
    answer_node,
    extract_node,
    grade_node,
    plan_node,
    retrieve_node,
    route_after_grade,
)
from investigator.agent.state import AgentState
from investigator.rag.schemas import RAGAnswer


def build_graph(deps: Deps):
    graph = StateGraph(AgentState)
    graph.add_node("plan", partial(plan_node, deps=deps))
    graph.add_node("retrieve", partial(retrieve_node, deps=deps))
    graph.add_node("grade", partial(grade_node, deps=deps))
    graph.add_node("extract", partial(extract_node, deps=deps))
    graph.add_node("answer", partial(answer_node, deps=deps))

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "grade")
    graph.add_conditional_edges(
        "grade",
        partial(route_after_grade, deps=deps),
        {"retrieve": "retrieve", "extract": "extract"},
    )
    graph.add_edge("extract", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


class InvestigationAgent:
    """Same interface as BaselineRAG, so evaluation and the API can swap them."""

    def __init__(self, deps: Deps):
        self.graph = build_graph(deps)

    def answer(self, question: str) -> RAGAnswer:
        return self.graph.invoke({"question": question})["result"]
