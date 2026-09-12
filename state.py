from typing import TypedDict

class Stateclass(TypedDict):
    """State of the application."""
    company_id: str
    company_links: list[str]
    competitors_links: list[str]
    company_Scraping_done: bool
    competitors_Scraping_done: bool
    pages_to_extract: list[dict]
    extraction_done:bool
    synthesis_done: bool