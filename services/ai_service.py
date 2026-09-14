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


def build_context(student_id=None, entity=None, entity_id=None):
    """Retrieve relevant Kaushora records for grounding (all live DB reads).

    When student_id is supplied, includes that student's profile + analysis.
    When entity/entity_id supplied (skill/occupation/course/district), includes
    that entity's observed records.
    """
    from .analytics_service import (compute_skill_demand, dashboard_overview,
                                    district_summary, evidence_metrics,
                                    labour_indicators, recommendations_live,
                                    trend_signals, vacancy_evidence)
    from .skill_gap_service import course_alignment
    from .db import get_db

    ov = dashboard_overview()
    vac = vacancy_evidence()
    c = get_db()
    try:
        courses = [dict(r) for r in c.execute(
            "SELECT id, course_name, sector, nsqf_level FROM courses ORDER BY id").fetchall()]
        employer_ev = [dict(r) for r in c.execute("SELECT * FROM employer_evidence").fetchall()]
        skill_gaps = [dict(r) for r in c.execute("SELECT * FROM district_skill_gaps WHERE demand_signal IS NOT NULL").fetchall()]
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
    ctx = {
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
        "employer_evidence": [
            {"finding": r["finding"], "source": r["source"], "year": r.get("year"),
             "sample_size": r.get("sample_size")}
            for r in employer_ev if r.get("finding")],
        "skill_gaps": [
            {"sector": r.get("demand_signal"), "source": r.get("evidence_sources")}
            for r in skill_gaps],
        "recommendations": [
            {"type": r.get("recommendation_type"), "text": r.get("recommendation_text"),
             "priority": r.get("priority"), "engine": bool(r.get("engine"))}
            for r in recommendations_live()[:8]],
        "skills": [{"id": s["id"], "name": s["skill_name"],
                    "status": s["demand_status"], "score": s.get("demand_score")} for s in compute_skill_demand()],
        "trends": [{"technology": t["technology"], "direction": t.get("trend_direction"),
                    "evidence": t.get("evidence")} for t in trend_signals()],
        "vacancy": {
            "total": vac.get("total", 0),
            "maharashtra": vac.get("maharashtra", 0),
            "top_skills": vac.get("top_skills", [])[:5],
            "by_sector": vac.get("by_sector", [])[:5],
            "source": vac.get("source", ""),
            "period": vac.get("period", ""),
        },
    }
    # Student-specific context (when on My Student Dashboard / Career Detail)
    if student_id:
        try:
            from .student_service import get_student_analysis
            an = get_student_analysis(int(student_id))
            if an:
                ctx["student"] = {
                    "profile": {k: an["profile"].get(k) for k in ("id", "status", "district_name", "state_name", "goal", "skills", "interests", "preferences", "education_level")},
                    "top_matches": [{"occupation": m["occupation_name"], "score": m["score"], "label": m["label"], "coverage": m["coverage"]} for m in an.get("career_matches", [])[:3]],
                    "prioritized_gaps": an.get("prioritized_gaps", [])[:3],
                    "next_actions": an.get("next_actions", [])[:3],
                }
        except Exception:
            pass
    # Entity-specific context (skill/occupation/course/district pages)
    if entity and entity_id:
        try:
            c2 = get_db()
            try:
                if entity == "skill":
                    r = c2.execute("SELECT id, skill_name, skill_category FROM skills WHERE id=?", (entity_id,)).fetchone()
                    if r:
                        ctx["entity"] = {"type": "skill", "id": r["id"], "name": r["skill_name"], "category": r["skill_category"]}
                        # Add job postings citing this skill
                        jp_rows = c2.execute(
                            "SELECT job_title, state, city, sector, employment_type FROM job_postings "
                            "WHERE skill_ids LIKE ? ORDER BY scraped_at DESC LIMIT 10",
                            (f"%{entity_id}%",)
                        ).fetchall()
                        ctx["entity"]["job_postings"] = [{"title": j["job_title"], "state": j["state"],
                                                          "city": j["city"], "sector": j["sector"],
                                                          "type": j["employment_type"]} for j in jp_rows]
                        ctx["entity"]["posting_count"] = c2.execute(
                            "SELECT COUNT(*) c FROM job_postings WHERE skill_ids LIKE ?",
                            (f"%{entity_id}%",)
                        ).fetchone()["c"]
                elif entity == "occupation":
                    r = c2.execute("SELECT role_id, job_title, qp_code FROM job_roles WHERE role_id=?", (entity_id,)).fetchone()
                    if r:
                        ctx["entity"] = {"type": "occupation", "id": r["role_id"], "name": r["job_title"], "qp": r["qp_code"]}
                        # Add job postings for this occupation's skills
                        skill_ids = c2.execute(
                            "SELECT skill_id FROM occupation_skills WHERE occupation_id=?",
                            (entity_id,)
                        ).fetchall()
                        if skill_ids:
                            like_clause = " OR ".join(["skill_ids LIKE ?"] * len(skill_ids))
                            params = [f"%{s['skill_id']}%" for s in skill_ids]
                            jp_rows = c2.execute(
                                f"SELECT job_title, state, city, sector FROM job_postings "
                                f"WHERE {like_clause} ORDER BY scraped_at DESC LIMIT 10",
                                params
                            ).fetchall()
                            ctx["entity"]["job_postings"] = [{"title": j["job_title"], "state": j["state"],
                                                              "city": j["city"], "sector": j["sector"]} for j in jp_rows]
                            ctx["entity"]["posting_count"] = c2.execute(
                                f"SELECT COUNT(DISTINCT id) c FROM job_postings WHERE {like_clause}",
                                params
                            ).fetchone()["c"]
                elif entity == "course":
                    r = c2.execute("SELECT id, course_name, sector FROM courses WHERE id=?", (entity_id,)).fetchone()
                    if r: ctx["entity"] = {"type": "course", "id": r["id"], "name": r["course_name"], "sector": r["sector"]}
                elif entity == "district":
                    r = c2.execute("SELECT district_id, district_name, district_code FROM districts WHERE district_id=?", (entity_id,)).fetchone()
                    if r:
                        ctx["entity"] = {"type": "district", "id": r["district_id"], "name": r["district_name"]}
                        jp_rows = c2.execute(
                            "SELECT job_title, state, city, sector FROM job_postings "
                            "WHERE state LIKE ? OR city LIKE ? ORDER BY scraped_at DESC LIMIT 10",
                            (f"%{r['district_name']}%", f"%{r['district_name']}%")
                        ).fetchall()
                        ctx["entity"]["job_postings"] = [{"title": j["job_title"], "state": j["state"],
                                                          "city": j["city"], "sector": j["sector"]} for j in jp_rows]
            finally:
                c2.close()
        except Exception:
            pass
    return ctx


def _ev(names):
    return [{"source": n, "data_source": "REAL"} for n in names]


def fallback_answer(question, ctx):
    """Deterministic grounded answers from live context (no model needed)."""
    q = (question or "").lower()
    totals = ctx.get("totals", {})
    # Student-specific shortcuts (highest priority when student context present)
    student = ctx.get("student")
    if student and any(k in q for k in ("my profile", "my skills", "my gaps", "my career", "what should i learn", "why was this career", "what skills am i missing")):
        prof = student.get("profile", {})
        gaps = student.get("prioritized_gaps", [])
        nxt = student.get("next_actions", [])
        matches = student.get("top_matches", [])
        if "what should i learn" in q or "what skills am i missing" in q:
            if not gaps:
                return ("You have no prioritized gaps for your top matches — your current skills cover the required explicit NOS links.", _ev(["student_analysis"]))
            g = gaps[0]
            return (f"Top gap for you is {g['skill_name']} ({g['skill_id']}). " + (f"Next action: {nxt[0]['action']} — {nxt[0]['reason']}" if nxt else ""),
                    _ev(["student_analysis", "occupation_skills"]))
        if "why was this career" in q or "why was this occupation" in q:
            if matches:
                m = matches[0]
                return (f"Top match {m['occupation']} ({m['score']}% {m['label']}, {m['coverage']}% coverage) was chosen for your status {prof.get('status')} and interests {', '.join(prof.get('interests', [])[:2])}. See Career Matches for the full why.",
                        _ev(["student_analysis"]))
        # general student summary
        return (f"Profile #{prof.get('id')} — {prof.get('status')} in {prof.get('district_name') or '—'}. "
                f"Top match: {matches[0]['occupation'] if matches else 'none'} "
                f"({matches[0]['label'] if matches else ''}). Gaps: {', '.join(g['skill_name'] for g in gaps[:2]) or 'none'}.",
                _ev(["student_analysis"]))
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
        vac = ctx.get("vacancy", {})
        vac_note = f" {vac['total']} real job postings from Role Radar provide vacancy evidence." if vac.get("total", 0) > 0 else ""
        return (
            "Career matching compares your skills against 33 NSDC occupations with QP codes and NSQF "
            "levels (including CNC Operator from NCO 2015). Only 4 occupations carry explicit NOS skill links, "
            f"so matches outside those are reported as unscored rather than zero.{vac_note} "
            "5 state-level sector skill gaps (NSDC 2013) and 5 employer survey findings are available as evidence. "
            "Try Careers with e.g. 'Data Entry' or 'Communication'.",
            _ev(["job_roles", "occupation_skills", "courses", "job_postings"]),
        )
    if "indicator" in q or "lfpr" in q or "unemployment" in q or "wpr" in q or "plfs" in q:
        inds = "; ".join(f"{i['name']} {i['value']}{i['unit'] or ''} ({i['group']})" for i in ctx.get("indicators", [])[:6])
        return (f"PLFS 2025 (usual status, All India): {inds}. District-level PLFS is not published, "
                f"so these figures are never downscaled to districts.",
                _ev(["labour_indicators"]))
    if "trend" in q or "emerg" in q or "growing" in q or "ncs" in q or "vacanc" in q:
        vac = ctx.get("vacancy", {})
        if vac.get("total", 0) > 0:
            top_sk = "; ".join(f"{s['skill_name']} ({s['c']} postings)" for s in vac.get("top_skills", [])[:5])
            top_sect = "; ".join(f"{s['sector']} ({s['c']})" for s in vac.get("by_sector", [])[:4])
            return (
                f"Job market intelligence from {vac['total']} real LinkedIn postings ({vac['source']}, {vac['period']}): "
                f"{vac['maharashtra']} in Maharashtra. Top demanded skills: {top_sk}. "
                f"Top sectors: {top_sect}. WEF trend signals are qualitative sector-level evidence.",
                _ev(["job_postings", "job_posting_skills", "evidence_metrics"]),
            )
        evs = "; ".join(f"{e['metric']}: {e['value']} {e['unit'] or ''} ({e['geography']})" for e in ctx.get("evidence", [])[:4])
        return (f"Recorded evidence: {evs}. No job posting microdata available yet.",
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
    vac = ctx.get("vacancy", {})
    vac_txt = f" {vac.get('total', 0)} real job postings provide vacancy evidence." if vac.get("total", 0) > 0 else ""
    demand_skills = [s for s in ctx.get("skills", []) if s.get("score") is not None]
    if demand_skills:
        demand_list = "; ".join(f"{s['name']}: {s['score']}% ({s['status']})" for s in demand_skills[:5])
        return (
            f"Of {n_skills} skills in the catalog, {len(demand_skills)} have observed demand signals from WEF/NASSCOM: "
            f"{demand_list}. The remaining {n_skills - len(demand_skills)} skills have insufficient source evidence for demand scoring.{vac_txt} "
            f"National aggregates ({evs}) are shown as evidence, never converted into skill scores. See Skill Intelligence.",
            _ev(["skill_demand", "skills", "evidence_metrics", "job_postings"]),
        )
    return (
        "Per-skill demand scores cannot be calculated: the source skill_demand assessment is NULL "
        "for every signal. The catalog holds "
        f"{n_skills} real skills; national aggregates ({evs}) are shown as evidence, never "
        f"converted into skill scores.{vac_txt} See Skill Intelligence.",
        _ev(["skill_demand", "skills", "evidence_metrics", "job_postings"]),
    )


SYSTEM_PROMPT = (
    "You are Kaushora AI, the labour-market intelligence assistant for Kaushora. "
    "Use only the provided Kaushora context for factual claims about Kaushora's dataset. "
    "Do not invent statistics, jobs, employers, skills, courses, districts or trends. "
    "Clearly distinguish calculated metrics from source observations. "
    "If the provided context is insufficient, state that the available data is insufficient. Be concise."
)


def ask_ai(question, context=None, student_id=None, entity=None, entity_id=None):
    # context param kept for backward compat (ignored — build_context is source of truth)
    ctx = build_context(student_id=student_id, entity=entity, entity_id=entity_id)
    # also merge any caller-supplied context (e.g. legacy tests)
    if context and isinstance(context, dict):
        ctx.update({k: v for k, v in context.items() if k not in ctx})
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
