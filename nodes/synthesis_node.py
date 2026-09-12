import json

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




class Objection(BaseModel):
    objection: str = Field(
        description="The actual pushback a prospect would say out loud, in their words, "
                     "e.g. 'Airtable has way better data modeling than you.'"
    )
    rebuttal: str = Field(
        description="A specific, concrete response a rep can say back — must reference "
                     "an actual feature, number, or capability, not a vague adjective."
    )
    supporting_fact: str = Field(
        description="The specific fact from our extracted data that backs this rebuttal — "
                     "quote or closely paraphrase it, don't invent anything not in the source data."
    )

class CompetitiveAnalysis(BaseModel):
    strengths: list[str] = Field(description="Where we clearly beat the competitor — specific, not vague")
    weaknesses: list[str] = Field(description="Where the competitor clearly beats us — specific, not vague")
    objections: list[Objection] = Field(description="Real objections paired with grounded rebuttals")

synthesis_llm = llm.with_structured_output(CompetitiveAnalysis)

SYNTHESIS_PROMPT = """You are a competitive intelligence analyst producing a sales battlecard.

Rules:
1. Every claim (strength, weakness, or rebuttal) must be SPECIFIC — cite an actual feature,
   price, limit, or capability from the facts below. Never use vague adjectives alone
   ("more flexible", "more mature", "better reputation") without a concrete detail attached.
   Bad: "Airtable has more flexible data modeling."
   Good: "Airtable supports custom field types and linked records across bases; Notion's
   databases are simpler relation/rollup only."
2. Objections must be phrased as something a REAL PROSPECT would say out loud, not a
   restated feature list. Bad: "Objection: Airtable has automation." Good: "Objection:
   'Airtable's automations don't have run limits like yours do.'"
3. Only use facts present in the data below. If you don't have enough information to make
   a specific claim, leave it out rather than inventing or generalizing.

Our company facts:
{company_facts}

Competitor ({competitor_name}) facts:
{competitor_facts}
"""


def synthesize_battlecards(state: Stateclass) -> dict:
    """For each competitor, read all extracted facts from the db and
    generate strengths/weaknesses/objection-handling, then write the
    result back to the db for Streamlit to read directly."""
    conn = get_db_connection()

    company_rows = conn.execute(
        "SELECT extracted_facts FROM page_hashes WHERE entity_type='company'"
    ).fetchall()
    company_facts = [json.loads(r[0]) for r in company_rows if r[0]]

    competitor_names = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT entity_name FROM page_hashes WHERE entity_type='competitor'"
        ).fetchall()
    ]

    for name in competitor_names:
        competitor_rows = conn.execute(
            "SELECT extracted_facts FROM page_hashes WHERE entity_type='competitor' AND entity_name=?",
            (name,)
        ).fetchall()
        competitor_facts = [json.loads(r[0]) for r in competitor_rows if r[0]]

        prompt = SYNTHESIS_PROMPT.format(
            company_facts=json.dumps(company_facts, indent=2),
            competitor_name=name,
            competitor_facts=json.dumps(competitor_facts, indent=2),
        )

        try:
            analysis: CompetitiveAnalysis = synthesis_llm.invoke(prompt)
        except Exception as e:
            print(f"  synthesis failed for {name}: {e}")
            continue

        conn.execute("""
            INSERT INTO battlecards (competitor_name, strengths, weaknesses, objection_handling, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (competitor_name)
            DO UPDATE SET strengths=excluded.strengths, weaknesses=excluded.weaknesses,
                          objection_handling=excluded.objection_handling, last_updated=CURRENT_TIMESTAMP
        """, (name, json.dumps(analysis.strengths), json.dumps(analysis.weaknesses),
              json.dumps([o.model_dump() for o in analysis.objections])))
        conn.commit()
        print(f"  battlecard updated: {name}")

    conn.close()
    return {"synthesis_done": True}