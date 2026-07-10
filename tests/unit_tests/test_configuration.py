from langgraph.graph.state import StateGraph
from langgraph.pregel import Pregel

from src.agent.graph import builder


def test_builder_is_state_graph() -> None:
    assert isinstance(builder, StateGraph)


def test_compiled_graph_is_pregel() -> None:
    from langgraph.checkpoint.memory import MemorySaver
    graph = builder.compile(checkpointer=MemorySaver())
    assert isinstance(graph, Pregel)
