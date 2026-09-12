from state import Stateclass
import re
from pathlib import Path

COMPANY_HEADER = re.compile(r"^##\s*Company\s*:?\s*(.*)$", re.IGNORECASE)
COMPETITOR_HEADER = re.compile(r"^##\s*Competitor\s*:\s*(.+)$", re.IGNORECASE)


def parse_links_file(filepath: str = "links.md") -> dict:
    """
    Parse a links.md file structured like:

        ## Company: Notion
        https://www.notion.com
        https://www.notion.com/pricing

        ## Competitor: ClickUp
        https://www.clickup.com
        https://www.clickup.com/pricing

    Returns:
        {
            "company": ["https://www.notion.com", ...],
            "competitors": {
                "ClickUp": ["https://www.clickup.com", ...],
                "Coda": [...],
            }
        }
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"{filepath} not found — create it with '## Company:' and "
            f"'## Competitor: <name>' section headers, one URL per line."
        )

    company_links: list[str] = []
    competitors: dict[str, list[str]] = {}

    mode = None            # "company" | "competitor" | None
    current_competitor = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line:
            continue  # blank lines are just visual spacing, skip

        company_match = COMPANY_HEADER.match(line)
        if company_match:
            mode = "company"
            current_competitor = None
            continue

        competitor_match = COMPETITOR_HEADER.match(line)
        if competitor_match:
            mode = "competitor"
            current_competitor = competitor_match.group(1).strip()
            competitors.setdefault(current_competitor, [])
            continue

        # Anything else is treated as a URL line, assigned to whatever
        # section we're currently inside.
        if mode == "company":
            company_links.append(line)
        elif mode == "competitor" and current_competitor:
            competitors[current_competitor].append(line)
        else:
            print(f"  WARNING: ignoring line outside any '## Company' or "
                  f"'## Competitor:' section: {line!r}")

    if not company_links:
        print("  WARNING: no company URLs found under '## Company:' section")
    if not competitors:
        print("  WARNING: no competitor sections found")

    return {"company": company_links, "competitors": competitors}




def get_company_info_link(state: Stateclass) -> dict:
    """Load the company's URLs from links.md."""
    parsed = parse_links_file("links.md")
    company_links = parsed["company"]
    state["company_links"] = company_links
    return {"company_links": company_links}


def get_competitors_links(state: Stateclass) -> dict:
    """Load each competitor's URLs (grouped by name) from links.md."""
    parsed = parse_links_file("links.md")
    competitors_links = parsed["competitors"]  # dict[str, list[str]]
    state["competitors_links"] = competitors_links
    return {"competitors_links": competitors_links}