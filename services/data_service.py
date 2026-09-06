"""Skill normalization against the real-evidence catalog.

Maps free-text skill phrases (candidate input, NCO related_skills,
employer free text) to canonical skill ids via exact alias/slug match
first, then token-containment matching. Name-based matches are
approximate and must be labelled as such by callers.
"""
import re
from .db import get_db

MANUAL_ALIASES = {
    "programming": "SK-JSD-01",
    "programming fundamentals": "SK-JSD-01",
    "python": "SK-JSD-01",
    "java": "SK-JSD-01",
    "coding": "SK-JSD-01",
    "database management": "SK-JSD-02",
    "sql": "SK-JSD-02",
    "databases": "SK-JSD-02",
    "data modelling": "SK-JSD-02",
    "software testing": "SK-JSD-03",
    "testing": "SK-JSD-03",
    "test cases": "SK-JSD-03",
    "technical documentation": "SK-JSD-04",
    "documentation": "SK-JSD-04",
    "data entry operations": "SK-DEO-01",
    "data entry": "SK-DEO-01",
    "quality checking": "SK-DEO-02",
    "patient care assistance": "SK-GDA-01",
    "patient care": "SK-GDA-01",
    "sanitation and hygiene": "SK-GDA-02",
    "sanitation": "SK-GDA-02",
    "hygiene": "SK-GDA-02",
    "communication and interpersonal skills": "SK-GDA-03",
    "communication": "SK-GDA-03",
    "customer service": "SK-GDA-03",
}


def tokens(s):
    return set(re.findall(r"[a-z]+", (s or "").lower()))


def normalize_skill_name(name: str):
    if not name:
        return None
    key = re.sub(r"\s+", " ", name.strip().lower())
    if key in MANUAL_ALIASES:
        return MANUAL_ALIASES[key]
    try:
        c = get_db()
        try:
            r = c.execute("SELECT id FROM skills WHERE lower(skill_name)=?", (key,)).fetchone()
            if r:
                return r["id"]
            r = c.execute(
                "SELECT id FROM skills WHERE normalized_skill_name=?",
                (re.sub(r"\s+", "_", key),),
            ).fetchone()
            if r:
                return r["id"]
            r = c.execute("SELECT skill_id FROM skill_aliases WHERE alias=?", (key,)).fetchone()
            if r:
                return r["skill_id"]
        finally:
            c.close()
    except Exception:
        pass
    return None


def skill_ids_for_phrase(phrase, skills):
    """Map one free-text phrase to skill ids by token containment.

    `skills`: {id: {"skill_name":..., "normalized_skill_name":...}}.
    Match when either token set contains the other (single generic tokens
    like 'data' alone do not match). Returns list of ids (may be empty).
    """
    pt = tokens(phrase)
    if not pt:
        return []
    hits = []
    for sid, s in skills.items():
        st = tokens(s.get("normalized_skill_name") or "") | tokens(s.get("skill_name") or "")
        st.discard("and")
        pt2 = set(pt)
        pt2.discard("and")
        if not st or not pt2:
            continue
        # containment either way: phrase names the skill, or the skill
        # name covers the phrase (e.g. "documentation" -> Technical Documentation)
        if st <= pt2 or pt2 <= st:
            hits.append(sid)
    return hits


def split_ids(s):
    if not s:
        return []
    return [x.strip() for x in str(s).split(",") if x.strip()]
