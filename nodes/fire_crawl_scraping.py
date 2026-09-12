import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from state import Stateclass
from dotenv import load_dotenv

from firecrawl import Firecrawl

load_dotenv()

# --- Config ---------------------------------------------------------------

FIRECRAWL_API_KEY = os.environ["FIRECRAWL_API_KEY"]
BASE_DATA_DIR = Path("data")

app = Firecrawl(api_key=FIRECRAWL_API_KEY)


def url_to_filename(url: str) -> str:
    """Turn a URL path into a safe filename, e.g. '/pricing' -> 'pricing.md'."""
    path = urlparse(url).path.strip("/")
    if not path:
        return "homepage.md"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()
    return f"{slug}.md"


def clean_markdown(markdown: str) -> str:
    """Strip lines that are just image markdown (logo strips, decorative
    images) — these add noise without useful text for the LLM stage."""
    lines = markdown.split("\n")
    cleaned = [
        line for line in lines
        if not re.fullmatch(r"(\[?!\[.*?\]\(.*?\)\]?\(.*?\)|!\[.*?\]\(.*?\)\s*)+", line.strip())
    ]
    return "\n".join(cleaned)



LOGIN_WALL_SIGNS = [
    "sign in to see this page", "you're almost there",
    "continue with google", "log in to your account",
    "please log in", "authentication required",
]

def is_junk_content(markdown: str, min_words: int = 100) -> bool:
    """Detect login walls, paywalls, or near-empty scrapes."""
    lower = markdown.lower()
    if any(sign in lower for sign in LOGIN_WALL_SIGNS):
        return True
    return len(markdown.split()) < min_words

def scrape_and_save(url: str, output_dir: Path, max_retries: int = 3) -> bool:
    for attempt in range(1, max_retries + 1):
        try:
            result = app.scrape(url, formats=["markdown"], only_main_content=True)
            markdown = result.get("markdown", "") if isinstance(result, dict) else result.markdown

            if not markdown.strip():
                print(f"  skipped (empty content): {url}")
                return False

            # NEW: reject junk before it's cleaned, saved, or hashed
            if is_junk_content(markdown):
                print(f"  skipped (junk/login-wall): {url}")
                return False

            markdown = clean_markdown(markdown)

            output_dir.mkdir(parents=True, exist_ok=True)
            filepath = output_dir / url_to_filename(url)
            filepath.write_text(markdown, encoding="utf-8")
            print(f"  saved: {filepath}")
            return True

        except Exception as e:
            error_text = str(e).lower()
            is_rate_limit = "rate limit" in error_text or "429" in error_text
            if is_rate_limit and attempt < max_retries:
                print(f"  rate limited on {url} (attempt {attempt}/{max_retries}), waiting 60s...")
                time.sleep(60)
                continue
            print(f"  failed to scrape {url}: {e}")
            return False

    return False

def domain_slug(url: str) -> str:
    """Turn a URL into a clean folder name, e.g. 'https://clickup.com' -> 'clickup-com'."""
    domain = urlparse(url).netloc.replace("www.", "")
    return re.sub(r"[^a-zA-Z0-9]+", "-", domain).strip("-").lower()


# --- Main scraping functions -------------------------------------------------

def scrape_company_info(state: Stateclass) -> dict:
    """Scrape each company link and save as markdown under data/company/."""
    company_links = state.get("company_links")
    if not company_links:
        raise ValueError("Company info links are not set in the state.")

    output_dir = BASE_DATA_DIR / "company"
    saved_count = 0

    for url in company_links:
        print(f"Scraping company page: {url}")
        if scrape_and_save(url, output_dir):
            saved_count += 1
        time.sleep(1)

    print(f"Company scrape done: {saved_count}/{len(company_links)} pages saved.")
    return {"company_Scraping_done": True}


def scrape_competitors_info(state: Stateclass) -> dict:
    """Scrape each competitor's links, saving pages under
    data/competitors/<name-from-links-file>/."""
    competitors_links = state.get("competitors_links", {})
    if not competitors_links:
        raise ValueError("Competitors links are not set in the state.")

    for name, urls in competitors_links.items():
        folder_name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
        output_dir = BASE_DATA_DIR / "competitors" / folder_name
        saved_count = 0

        for url in urls:
            print(f"Scraping {name} page: {url}")
            if scrape_and_save(url, output_dir):
                saved_count += 1
            time.sleep(1)

        print(f"  {name}: {saved_count}/{len(urls)} pages saved.")

    return {"competitors_Scraping_done": True}