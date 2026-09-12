from langgraph.graph import StateGraph, START, END
from nodes.gathering_information_node import get_company_info_link, get_competitors_links
from nodes.fire_crawl_scraping import scrape_company_info, scrape_competitors_info
from state import Stateclass
from nodes.hashnode import hash_scraped_pages
from nodes.extraction_node import extract_pages_node
from nodes.synthesis_node import synthesize_battlecards


graph = StateGraph(Stateclass)

graph.add_node("get_company_info_link",get_company_info_link)
graph.add_node("get_competitors_links",get_competitors_links)
graph.add_node("scrape_company_info",scrape_company_info)
graph.add_node("scrape_competitors_info",scrape_competitors_info)
graph.add_node("hash_scraped_pages", hash_scraped_pages)
graph.add_node("extract_pages_node", extract_pages_node)
graph.add_node("synthesize_battlecards", synthesize_battlecards)

graph.add_edge(START, "get_company_info_link")
graph.add_edge("get_company_info_link", "get_competitors_links")
graph.add_edge("get_competitors_links", "scrape_company_info")
graph.add_edge("scrape_company_info", "scrape_competitors_info")
graph.add_edge("scrape_competitors_info", "hash_scraped_pages")
graph.add_edge("hash_scraped_pages", "extract_pages_node")
graph.add_edge("extract_pages_node", "synthesize_battlecards")
graph.add_edge("synthesize_battlecards", END)

workflow=graph.compile()

if __name__ == "__main__":
    result = workflow.invoke({"company_id": "12345"})
    
