from pydantic import BaseModel, Field
from typing import Optional
import json
import time
import hashlib
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from state import Stateclass
from nodes.hashnode import get_db_connection
from langchain_openai import ChatOpenAI

import os
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini",
                 api_key = os.getenv("OPENAI_API_KEY"),
                  temperature=0
                  )


class PricingTier(BaseModel):
    name: str = Field(description="Exact plan name as shown on the page, e.g. 'Business', 'Pro'")
    price: str = Field(
        description="Exact price and billing unit as stated, e.g. '$20/user/month (billed annually)'. "
                     "If pricing is 'Contact us' or custom, use that exact phrase — don't guess a number."
    )
    key_features: list[str] = Field(
        default_factory=list,
        description="Specific named features or limits tied to this tier, e.g. 'SAML SSO', "
                     "'Unlimited automation runs', '250 guest seats'. Avoid vague summaries "
                     "like 'advanced security' — name the actual feature."
    )

class PageFacts(BaseModel):
    pricing_tiers: list[PricingTier] = Field(default_factory=list)
    product_features: list[str] = Field(
        default_factory=list,
        description="Concrete, named product capabilities mentioned on the page — specific "
                     "feature names, integrations, or limits (e.g. 'Gantt charts', 'API access', "
                     "'connects to Slack and GitHub'). Do not include generic marketing phrases "
                     "like 'powerful collaboration' or 'seamless workflows' — skip a feature "
                     "entirely if the page only describes it vaguely."
    )
    positioning_statement: Optional[str] = Field(
        default=None,
        description="The company's own stated positioning, as close to verbatim as possible. "
                     "This is expected to be marketing language — keep it faithful to the source, "
                     "don't sharpen or reword it."
    )
    target_customer: Optional[str] = Field(
        default=None,
        description="Who the page states this product is for, as stated — company size, "
                     "role, or industry if mentioned (e.g. 'small business teams', "
                     "'enterprise IT departments'). Use null if not explicitly stated."
    )


structured_llm = llm.with_structured_output(PageFacts)


import tiktoken  # or use Groq/Anthropic's token counting if you switch providers

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


def truncate_to_relevant_content(markdown: str, max_tokens: int = 6000) -> str:
    """If a page is unusually long, keep the content most likely to matter
    (start of the page, where pricing/hero/positioning usually live) rather
    than blindly cutting mid-sentence at the token limit."""
    if count_tokens(markdown) <= max_tokens:
        return markdown

    # crude but effective: take proportional chunks from start and middle,
    # since pricing tables and feature lists tend to front-load
    words = markdown.split()
    keep_words = int(len(words) * (max_tokens / count_tokens(markdown)))
    return " ".join(words[:keep_words])

def extract_facts_from_page(markdown: str) -> dict | None:
    """Single-page extraction using native structured output — no manual
    JSON parsing, no retry-on-parse-failure needed."""
    content = truncate_to_relevant_content(markdown, max_tokens=6000)
    try:
        result: PageFacts = structured_llm.invoke(
            "Extract structured facts from this webpage for a sales battlecard.\n"
            "Prioritize concrete, specific details over general marketing language — "
            "named features, exact prices, stated limits or numbers. If a section of "
            "the page is purely vague marketing copy with no concrete detail, it's fine "
            "to leave the corresponding field empty rather than paraphrasing fluff.\n\n"
            f"Page content:\n{content}"
        )
        return result.model_dump()
    except Exception as e:
        print(f"  extraction failed: {e}")
        return None



def extract_pages_node(state: Stateclass) -> dict:
    """Process each page in pages_to_extract: one page, one LLM call,
    write results + hash to the db."""
    pages_to_extract = state.get("pages_to_extract", [])
    conn = get_db_connection()
    extracted_count = 0

    for page in pages_to_extract:
        print(f"Extracting: {page['md_file_path']}")
        markdown = Path(page["md_file_path"]).read_text(encoding="utf-8")

        facts = extract_facts_from_page(markdown)
        if facts is None:
            continue  # don't update the db — we'll retry this page next run since hash won't match

        facts_json = json.dumps(facts, sort_keys=True)
        facts_hash = hashlib.sha256(facts_json.encode("utf-8")).hexdigest()

        conn.execute("""
            INSERT INTO page_hashes (entity_type, entity_name, page_url, md_file_path,
                                      raw_hash, facts_hash, extracted_facts, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (entity_type, entity_name, page_url)
            DO UPDATE SET raw_hash=excluded.raw_hash, facts_hash=excluded.facts_hash,
                          extracted_facts=excluded.extracted_facts, last_updated=CURRENT_TIMESTAMP
        """, (page["entity_type"], page["entity_name"], page["md_file_path"], page["md_file_path"],
              page["new_hash"], facts_hash, facts_json))
        conn.commit()
        extracted_count += 1
        time.sleep(1)  # basic pacing, same reasoning as your scrape rate-limiting

    conn.close()
    print(f"Extraction done: {extracted_count}/{len(pages_to_extract)} pages processed.")
    return {"extraction_done": True}