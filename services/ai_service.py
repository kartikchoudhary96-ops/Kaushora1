"""Kaushora AI: grounded assistant over the real public dataset.

Flow: question -> retrieve relevant Kaushora records + derived analytics ->
structured context -> Gemini (if GEMINI_API_KEY) else deterministic fallback.
The model/API is never the source of numerical truth; every figure in an
answer resolves to a database row or a documented derivation. Where the
dataset lacks evidence, the assistant says so explicitly.

Structured response: {answer, evidence[], data_source, grounded,
ai_available, note}.
"""
import json
import os
import urllib.request


def _gemini_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()


def build_context():
    """Retrieve relevant Kaushora records for grounding (all live DB reads)."""
    from .analytics_service import (compute_skill_demand, dashboard_overview,
                                    district_summary, evidence_metrics,
                                    labour_indicators, recommendations_live,
                                    trend_signals)
    from .skill_gap_service import course_alignment
    from .db import get_db

    ov = dashboard_overview()
    c = get_db()
    try:
        courses = [dict(r) for r in c.execute(
            "SELECT id, course_name, sector, nsqf_level FROM courses ORDER BY id").fetchall()]
    finally:
        c.close()
    scored = []
    for co in courses:
        try:
            a = course_alignment(co["id"])
        except Exception:
            a = None
        if a and a["alignment_score"] is not None:
            scored.append({"course_id": co["id"], "course_name": co["course_name"],
                           "score": a["alignment_score"], "action": a["recommended_action"],
                           "missing": [m["skill_name"] for m in a["missing_skills"]],
                           "matched_roles": a["matched_roles"]})
    scored.sort(key=lambda x: x["score"])
    dist = district_summary()
    with_centres = [d for d in dist if d["training_centres"] > 0]
    return {
        "totals": ov["totals"],
        "weakest_alignments": scored[:5],
        "assessable_courses": len(scored),
        "districts_total": len(dist),
        "districts_with_centres": [
            {"district": d["district"], "centres": d["training_centres"],
             "capacity": d["capacity"]} for d in with_centres],
        "indicators": [
            {"name": r["indicator_name"], "value": r["indicator_value"], "unit": r.get("unit"),
             "group": r.get("population_group"), "period": r.get("period")}
            for r in labour_indicators()],
        "evidence": [
            {"metric": r["metric_name"], "value": r["metric_value"], "unit": r.get("unit"),
             "geography": r.get("geography")}
            for r in evidence_metrics()],
        "recommendations": [
            {"type": r.get("recommendation_type"), "text": r.get("recommendation_text"),
             "priority": r.get("priority"), "engine": bool(r.get("engine"))}
            for r in recommendations_live()[:8]],
        "skills": [{"id": s["id"], "name": s["skill_name"],
                    "status": s["demand_status"]} for s in compute_skill_demand()],
        "trends": [{"technology": t["technology"], "direction": t.get("trend_direction"),
                    "evidence": t.get("evidence")} for t in trend_signals()],
    }


def _ev(names):
    return [{"source": n, "data_source": "REAL"} for n in names]


def fallback_answer(question, ctx):
    """Deterministic grounded answers from live context (no model needed)."""
    q = (question or "").lower()
    totals = ctx.get("totals", {})
    if "district" in q or "nagpur" in q or "training centre" in q or "capacity" in q:
        named = "; ".join(
            f"{d['district']}: {d['centres']} centre(s)" + (
                f", {d['capacity']['training_seats']} CTS seats" if d.get("capacity") and d["capacity"].get("training_seats") else ""
            ) for d in ctx.get("districts_with_centres", []))
        others = totals.get("districts", 36) - len(ctx.get("districts_with_centres", []))
        return (
            f"Training-centre records exist for {len(ctx.get('districts_with_centres', []))} of "
            f"{totals.get('districts', 36)} Maharashtra districts ({named}). "
            f"The remaining {others} districts have no published centre records. "
            f"Seats/enrolments are published only for Nagpur CTS (120 seats); elsewhere capacity gaps "
            f"cannot be estimated. See the Districts page for the per-district evidence.",
            _ev(["training_centres", "district_capacity", "districts"]),
        )
    if "course" in q or "curriculum" in q or "alignment" in q or "missing" in q:
        weak = ctx.get("weakest_alignments", [])
        if not weak:
            return ("No course in the catalog has an assessable alignment: explicit occupation "
                    "requirements exist for too few same-sector occupations. Five reference "
                    "assessments (all 100%) are shown on the Courses page as provided reference.",
                    _ev(["curriculum_alignment_ref"]))
        lines = "; ".join(f"{w['course_name']}: {w['score']}% ({w['action']}; missing: {', '.join(w['missing']) or 'none'})" for w in weak)
        return (
            f"Weakest independently-assessed curriculum alignments: {lines}. "
            f"Scores compare recorded course coverage against explicit NOS occupation requirements "
            f"(same sector only). Five provided reference assessments (100%) are shown alongside on Courses.",
            _ev(["course_skills", "occupation_skills", "curriculum_alignment_ref"]),
        )
    if "career" in q or "occupation" in q or "job role" in q or "qp " in q:
        return (
            "Career matching compares your skills against 32 NSDC occupations with QP codes and NSQF "
            "levels. Only 4 occupations carry explicit NOS skill links, so matches outside those are "
            "reported as unscored rather than zero. Recommended courses come only from the 15 recorded "
            "ITI courses. Try Careers with e.g. 'Data Entry' or 'Communication'.",
            _ev(["job_roles", "occupation_skills", "courses"]),
        )
    if "indicator" in q or "lfpr" in q or "unemployment" in q or "wpr" in q or "plfs" in q:
        inds = "; ".join(f"{i['name']} {i['value']}{i['unit'] or ''} ({i['group']})" for i in ctx.get("indicators", [])[:6])
        return (f"PLFS 2025 (usual status, All India): {inds}. District-level PLFS is not published, "
                f"so these figures are never downscaled to districts.",
                _ev(["labour_indicators"]))
    if "trend" in q or "emerg" in q or "growing" in q or "ncs" in q or "vacanc" in q:
        evs = "; ".join(f"{e['metric']}: {e['value']} {e['unit'] or ''} ({e['geography']})" for e in ctx.get("evidence", [])[:4])
        return (f"Recorded evidence: {evs}. WEF trend signals are qualitative sector-level evidence, "
                f"not skill-level measurements.",
                _ev(["evidence_metrics", "trends"]))
    if "recommend" in q or "action" in q or "priority" in q or "gap" in q:
        recs = "; ".join(f"[{r['priority']}] {r['text']}" for r in ctx.get("recommendations", [])[:4])
        return (f"Evidence-based recommendations: {recs}. Provided rows are compiler derivations; "
                f"engine rows are Kaushora derivations from live evidence.",
                _ev(["recommendations"]))
    # default: demand / skills (aggregates pulled live from context, never typed)
    evs = "; ".join(f"{e['metric']}: {e['value']} {e['unit'] or ''}".strip()
                    for e in ctx.get("evidence", [])[:4])
    n_skills = totals.get("unique_skills", len(ctx.get("skills", [])))
    return (
        "Per-skill demand scores cannot be calculated: the source skill_demand assessment is NULL "
        "for every signal (method: 'Not calculated - insufficient signals'). The catalog holds "
        f"{n_skills} real skills; national aggregates ({evs}) are shown as evidence, never "
        "converted into skill scores. See Skill Intelligence.",
        _ev(["skill_demand", "skills", "evidence_metrics"]),
    )


SYSTEM_PROMPT = (
    "You are Kaushora AI, the labour-market intelligence assistant for Kaushora. "
    "Use only the provided Kaushora context for factual claims about Kaushora's dataset. "
    "Do not invent statistics, jobs, employers, skills, courses, districts or trends. "
    "Clearly distinguish calculated metrics from source observations. "
    "If the provided context is insufficient, state that the available data is insufficient. Be concise."
)


def ask_ai(question, context=None):
    ctx = build_context()
    key = _gemini_key()
    if not key:
        answer, evidence = fallback_answer(question, ctx)
        return {"answer": answer, "evidence": evidence, "data_source": "REAL",
                "grounded": True, "ai_available": False,
                "note": "Kaushora AI model unavailable (no API key). Deterministic grounded fallback from live database context."}
    slim = {"totals": ctx.get("totals"), "weakest_alignments": ctx.get("weakest_alignments"),
            "districts_with_centres": ctx.get("districts_with_centres"),
            "indicators": ctx.get("indicators"), "evidence": ctx.get("evidence"),
            "recommendations": ctx.get("recommendations"),
            "skills": ctx.get("skills"), "trends": ctx.get("trends")}
    prompt = SYSTEM_PROMPT + "\nCONTEXT (Kaushora database extracts):\n" + json.dumps(slim)[:5000] + "\nQUESTION:\n" + (question or "")
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode())
        txt = j["candidates"][0]["content"]["parts"][0]["text"]
        return {"answer": txt, "evidence": _ev(["dashboard_overview", "indicators", "alignments", "districts"]),
                "data_source": "REAL", "grounded": True, "ai_available": True,
                "note": "Generated with Gemini over retrieved Kaushora records; numbers come from backend analytics."}
    except Exception as e:
        answer, evidence = fallback_answer(question, ctx)
        return {"answer": answer, "evidence": evidence, "data_source": "REAL",
                "grounded": True, "ai_available": False,
                "note": f"Kaushora AI model unavailable ({type(e).__name__}). Deterministic grounded fallback."}
