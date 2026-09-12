import json

import streamlit as st

from nodes.hashnode import get_db_connection

st.set_page_config(page_title="Sales Battlecards", page_icon="⚔️", layout="wide")

# The '## Company:' side of links.md — all battlecards are written from this POV.
COMPANY_NAME = "Notion"

_DISPLAY_NAMES = {"clickup": "ClickUp", "coda": "Coda", "airtable": "Airtable"}


def pretty_name(name: str) -> str:
    """'clickup' -> 'ClickUp', 'some-slug' -> 'Some Slug'."""
    return _DISPLAY_NAMES.get(name.lower(), name.replace("-", " ").title())


def parse_json_list(raw: str) -> list:
    """The synthesis node stores JSON arrays — plain strings for strengths/
    weaknesses, dicts of {objection, rebuttal, supporting_fact} for objections.
    Items are kept as-is. If parsing fails, fall back to showing the raw lines
    so the UI never breaks on unexpected db content."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [ln.strip("- ").strip() for ln in str(raw).splitlines() if ln.strip()]
    if isinstance(value, list):
        return value
    return [value]


@st.cache_data(ttl=60)
def load_battlecards() -> dict:
    """Read every battlecard the pipeline wrote to the db."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT competitor_name, strengths, weaknesses, objection_handling, last_updated
            FROM battlecards
            ORDER BY competitor_name
        """).fetchall()
    finally:
        conn.close()

    battlecards = {}
    for name, strengths, weaknesses, objection_handling, last_updated in rows:
        battlecards[name] = {
            "strengths": parse_json_list(strengths),
            "weaknesses": parse_json_list(weaknesses),
            "objection_handling": parse_json_list(objection_handling),
            "last_updated": last_updated,
        }
    return battlecards


def load_competitor_facts(competitor_name: str) -> list[dict]:
    """Per-page extracted facts behind the synthesis (shown as evidence)."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT md_file_path, extracted_facts FROM page_hashes "
            "WHERE entity_type = 'competitor' AND entity_name = ? "
            "ORDER BY md_file_path",
            (competitor_name,),
        ).fetchall()
    finally:
        conn.close()

    pages = []
    for md_path, raw in rows:
        try:
            parsed = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        pages.append({"page": md_path, "facts": parsed})
    return pages


battlecards = load_battlecards()

# --- Sidebar: competitor picker -------------------------------------------------
with st.sidebar:
    st.title("⚔️ Battlecards")
    st.caption(f"Our company: **{COMPANY_NAME}**")
    if st.button("🔄 Refresh"):
        load_battlecards.clear()
        st.rerun()
    st.divider()
    st.subheader("Competitors")

if not battlecards:
    st.sidebar.warning("No battlecards yet.")
    st.warning(
        "The database has no battlecards yet. Generate them first:\n\n"
        "`python main.py`\n\n"
        "Then come back and click **Refresh**."
    )
    st.stop()

selected = st.sidebar.radio(
    "Select competitor",
    options=list(battlecards),
    format_func=pretty_name,
    label_visibility="collapsed",
)

# --- Main panel ------------------------------------------------------------------
card = battlecards[selected]

st.title(f"{COMPANY_NAME} vs {pretty_name(selected)}")
st.caption(f"Battlecard last updated: {card['last_updated']}")

col_strengths, col_weaknesses = st.columns(2)

with col_strengths:
    st.subheader(f"💪 {COMPANY_NAME} strengths")
    if card["strengths"]:
        for point in card["strengths"]:
            st.markdown(f"- ✅ {point}")
    else:
        st.info("No strengths recorded yet.")

with col_weaknesses:
    st.subheader("⚠️ Where they beat us")
    if card["weaknesses"]:
        for point in card["weaknesses"]:
            st.markdown(f"- ⚠️ {point}")
    else:
        st.info("No weaknesses recorded yet.")

st.divider()
st.subheader("🛡️ Objection handling")
if card["objection_handling"]:
    for i, item in enumerate(card["objection_handling"], start=1):
        if isinstance(item, dict):
            # new structured format from the Objection model
            objection = str(item.get("objection") or f"Objection {i}")
            title = objection if len(objection) <= 90 else objection[:89] + "…"
            with st.expander(f"🗣️ “{title}”"):
                st.markdown(f"**Rebuttal:** {item.get('rebuttal', '—')}")
                fact = item.get("supporting_fact")
                if fact:
                    st.markdown(f"> 💡 **Supporting fact:** {fact}")
        else:
            # old plain-string format, kept for backwards compatibility
            with st.expander(f"Objection {i}"):
                st.write(item)
else:
    st.info("No objection-handling talk tracks recorded yet.")

# --- Evidence: the raw facts the synthesis was built from ------------------------
with st.expander("📄 Underlying extracted facts (evidence)"):
    for entry in load_competitor_facts(selected):
        st.markdown(f"**`{entry['page']}`**")
        st.json(entry["facts"], expanded=False)

st.sidebar.divider()
st.sidebar.caption(
    f"{len(battlecards)} competitor(s) in db · update them with `python main.py`"
)