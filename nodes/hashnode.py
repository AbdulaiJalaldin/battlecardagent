import hashlib
import sqlite3
from pathlib import Path
from state import Stateclass

DB_PATH = "battlecard.db"
BASE_DATA_DIR = Path("data")


def hash_page(markdown: str) -> str:
    """Deterministic hash of a page's full content."""
    normalized = "\n".join(ln.strip() for ln in markdown.split("\n") if ln.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS page_hashes (
            entity_type TEXT NOT NULL,      -- 'company' or 'competitor'
            entity_name TEXT NOT NULL,      -- 'Notion', 'ClickUp', etc.
            page_url TEXT NOT NULL,
            md_file_path TEXT NOT NULL,
            raw_hash TEXT NOT NULL,
            facts_hash TEXT,
            extracted_facts TEXT,           -- JSON blob, filled in by the LLM extraction node
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (entity_type, entity_name, page_url)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS battlecards (
            competitor_name TEXT PRIMARY KEY,
            strengths TEXT,
            weaknesses TEXT,
            objection_handling TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return conn


def hash_scraped_pages(state: Stateclass) -> dict:
    """Walk every saved .md file, hash it, and compare against the stored
    hash for that page. Returns a list of pages that are new or changed
    and therefore need LLM extraction."""
    conn = get_db_connection()
    pages_to_extract = []

    # Company pages
    company_dir = BASE_DATA_DIR / "company"
    if company_dir.exists():
        for md_file in company_dir.glob("*.md"):
            _check_and_queue(conn, "company", "self", md_file, pages_to_extract)

    # Competitor pages — one subfolder per competitor
    competitors_dir = BASE_DATA_DIR / "competitors"
    if competitors_dir.exists():
        for competitor_folder in competitors_dir.iterdir():
            if competitor_folder.is_dir():
                for md_file in competitor_folder.glob("*.md"):
                    _check_and_queue(conn, "competitor", competitor_folder.name, md_file, pages_to_extract)

    conn.close()
    print(f"Hashing done: {len(pages_to_extract)} page(s) new or changed, need extraction.")
    return {"pages_to_extract": pages_to_extract}


def _check_and_queue(conn, entity_type: str, entity_name: str, md_file: Path, pages_to_extract: list):
    markdown = md_file.read_text(encoding="utf-8")
    new_hash = hash_page(markdown)

    row = conn.execute(
        "SELECT raw_hash FROM page_hashes WHERE entity_type=? AND entity_name=? AND page_url=?",
        (entity_type, entity_name, str(md_file))
    ).fetchone()

    if row is None:
        print(f"  new page: {md_file}")
        pages_to_extract.append({"entity_type": entity_type, "entity_name": entity_name,
                                  "md_file_path": str(md_file), "new_hash": new_hash})
    elif row[0] != new_hash:
        print(f"  changed: {md_file}")
        pages_to_extract.append({"entity_type": entity_type, "entity_name": entity_name,
                                  "md_file_path": str(md_file), "new_hash": new_hash})
    else:
        print(f"  unchanged, skipping: {md_file}")