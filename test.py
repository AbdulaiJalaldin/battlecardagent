from langgraph.graph import StateGraph, START, END
from state import Stateclass
from nodes.hashnode import hash_scraped_pages
from nodes.extraction_node import extract_pages_node
from nodes.synthesis_node import synthesize_battlecards


# A separate, smaller graph for iterating on extraction/synthesis only —
# assumes data/ already has scraped .md files from a previous full run.
test_graph = StateGraph(Stateclass)

test_graph.add_node("hash_scraped_pages", hash_scraped_pages)
test_graph.add_node("extract_pages_node", extract_pages_node)
test_graph.add_node("synthesize_battlecards", synthesize_battlecards)

test_graph.add_edge(START, "hash_scraped_pages")
test_graph.add_edge("hash_scraped_pages", "extract_pages_node")
test_graph.add_edge("extract_pages_node", "synthesize_battlecards")
test_graph.add_edge("synthesize_battlecards", END)

test_workflow = test_graph.compile()

if __name__ == "__main__":
    result = test_workflow.invoke({"company_id": "12345"})