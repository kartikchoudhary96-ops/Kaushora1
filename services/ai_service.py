"""Kaushora AI: optional Gemini layer. Never source of truth for numbers.
Flow: analytics context -> prompt -> Gemini (if key) else structured fallback.
"""
import json
import os
import urllib.request


def _gemini_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()


def fallback_answer(question, context):
    q = (question or "").lower()
    tops = (context or {}).get("top_skills", [])[:5]
    named = [t for t in tops if t.get("demand_score") is not None]
    if named:
        names = ", ".join([f"{t['skill_name']} ({t['demand_score']})" for t in named])
        ds = f"higher-demand skills include: {names}."
    else:
        names = ", ".join([t["skill_name"] for t in tops]) or "see Skill Intelligence"
        ds = (
            "no demand scores can be calculated from the current dataset "
            f"(no job-demand or employer records), so I cannot rank skills by demand. Catalogued skills: {names}."
        )
    if "district" in q or "capacity" in q or "gap" in q:
        return "No district-level demand or capacity records exist in the current dataset, so district gaps cannot be estimated. See the Districts page."
    if "course" in q or "curriculum" in q or "missing" in q:
        return (
            "Course analysis compares each Qualification Pack curriculum against NCO role "
            f"requirements. {ds} Open Courses -> Analyze for the evidence."
        )
    if "career" in q or "learn" in q or "skill" in q or "demand" in q:
        return f"Based on the Real Evidence Dataset (NCO 2015, Qualification Packs, WEF reports), {ds} See Skill Intelligence for sources."
    if "trend" in q or "emerg" in q or "growing" in q:
        trends = (context or {}).get("actions", [])
        t = next((a for a in trends if a.get("type") == "trend"), None)
        if t:
            return f"Sector-level signal: {t['title']} — {t.get('reason', '')}"
    return (
        f"Kaushora AI is temporarily unavailable (no API key or offline). {ds} "
        "Use Dashboard/Skills/Districts pages for the underlying records."
    )


def ask_ai(question, context=None):
    key = _gemini_key()
    context = context or {}
    if not key:
        return {
            "answer": fallback_answer(question, context),
            "ai_available": False,
            "note": "Kaushora AI is temporarily unavailable (no API key). Showing structured fallback.",
        }
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    # keep context small & numeric-safe: instruct not to invent stats
    slim = {
        "top_skills": context.get("top_skills", [])[:6],
        "totals": context.get("totals", {}),
        "actions": context.get("actions", [])[:5],
    }
    prompt = (
        "You are Kaushora AI, a labour-market assistant. Use ONLY the numbers in CONTEXT. "
        "Never invent statistics. If evidence is insufficient, say so. Be concise.\nCONTEXT:\n"
        + json.dumps(slim)[:4000]
        + "\nQUESTION:\n"
        + (question or "")
    )
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode())
        txt = j["candidates"][0]["content"]["parts"][0]["text"]
        return {"answer": txt, "ai_available": True, "note": "Generated with Gemini; numbers come from backend analytics."}
    except Exception as e:
        return {
            "answer": fallback_answer(question, context),
            "ai_available": False,
            "note": f"Kaushora AI is temporarily unavailable ({type(e).__name__}). Showing structured fallback.",
        }
