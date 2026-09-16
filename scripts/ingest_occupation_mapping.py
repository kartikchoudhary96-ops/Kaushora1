"""Problem #2 importer: DeepSeek occupation->QP->NOS->skill research.

Reads data/raw/kaushora_occupation_mapping/*.csv (staged exact copies).
Validates schemas, dupes, URLs, vocabs, occupation matching (by NAME, never
by research OCC_ IDs), skill equivalence, source/QP/NOS cross-refs.
Then imports in ONE transaction (rollback on failure):
  sources DSRC_001..033 | occupation_nos (65) | nos_competencies (63) |
  occupation_skills exact-equivalence rows (5) | new_skill_candidates (25) |
  skill_aliases resolvable (1) + candidate_aliases (6) |
  job_roles.qp_code/qp_name overwrite to research codes (logged) |
  qualifications sync + backfill | ingestion_runs audit row.
Idempotent: research-owned rows are DELETE+INSERT; existing 10
occupation_skills rows and all non-DSRC data are never touched.
Usage: python scripts/ingest_occupation_mapping.py [--validate-only]
"""
import csv
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PKG = BASE / "data" / "raw" / "kaushora_occupation_mapping"
DB = BASE / "database" / "kaushora.db"

# Research SK_ -> Kaushora SKL exact semantic equivalence (curated, verified
# against skills table at runtime; every distinct research skill must appear
# in EXACT or POSSIBLE, else validation fails).
SK_EXACT = {
    "SK_QUALITY": "SKL008",
    "SK_DATAENTRY": "SKL011",
    "SK_SECURITYMGMT": "SKL016",
    "SK_WAREHOUSEOPS": "SKL015",
    "SK_WEBDEV": "SKL012",
}
SK_POSSIBLE = {
    "SK_SAFETY": "SKL010",
    "SK_SOLAR": "SKL027",
    "SK_MILKING": "SKL017",
    "SK_ANIMALFEED": "SKL017",
    "SK_BBS": "SKL018",
    "SK_REBAR": "SKL018",
    "SK_DESIGNTOOLS": "SKL013",
    "SK_PROGRAMMING": "SKL012",
}
# PWD-adapted QP -> originating QP (from research notes; never primary).
PWD_ORIGIN = {
    "PWD/CON/Q0602": "CON/Q0602",
    "PWD/BWS/Q0102": "BWS/Q0102",
    "PWD/AGR/Q4101": "AGR/Q4101",
}
QP_STATUS_MAP = {"CURRENT": "Active", "RETIRED": "Retired"}


def norm(s):
    s = (s or "").casefold().strip()
    for ch in ["\u2013", "\u2014", "\ufffd", "_"]:
        s = s.replace(ch, "-" if ch != "_" else " ")
    return re.sub(r"\s+", " ", s).strip()


def read_csv(name):
    """Returns (rows, rejected). Rows with a field count != header are rejected
    (never repaired: shifting research columns would fabricate alignment)."""
    with open(PKG / name, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows, rejected = [], []
        for lineno, fields in enumerate(reader, start=2):
            if len(fields) != len(header):
                rejected.append({"file": name, "line": lineno,
                                 "reason": f"field count {len(fields)} != header {len(header)}",
                                 "raw": ",".join(fields)[:300]})
                continue
            rows.append(dict(zip(header, fields)))
    return rows, rejected


def validate(existing):
    """existing: dict of live-DB lookup sets. Returns (errors, warnings, ctx)."""
    errors, warnings = [], []
    src, rej_src = read_csv("source_registry.csv")
    nos, rej_nos = read_csv("occupation_nos.csv")
    comp, rej_comp = read_csv("nos_competencies.csv")
    maps, rej_maps = read_csv("occupation_skills.csv")
    aliases, rej_alias = read_csv("skill_aliases.csv")
    rejected = rej_src + rej_nos + rej_comp + rej_maps + rej_alias
    for rj in rejected:
        warnings.append(f"REJECTED ROW {rj['file']}:{rj['line']} ({rj['reason']})")

    def need(rows, cols, label):
        got = set(rows[0].keys()) if rows else set()
        for col in cols:
            if col not in got:
                errors.append(f"{label}: missing column {col}")

    need(src, ["source_id", "organization", "source_title", "url", "publication_year",
               "accessed_date", "source_status", "official_or_secondary"], "source_registry")
    need(nos, ["occupation_id", "occupation_name", "qp_code", "qp_title", "sector_skill_council",
               "nsqf_level", "qp_status", "nos_code", "nos_title", "nos_status", "source_id",
               "source_url", "publication_year", "observed_or_derived", "confidence"], "occupation_nos")
    need(comp, ["competency_id", "qp_code", "nos_code", "nos_title", "competency_text",
                "source_id", "source_url", "evidence_type", "observed_or_derived",
                "confidence"], "nos_competencies")
    need(maps, ["occupation_id", "occupation_name", "qp_code", "nos_code", "skill_id",
                "skill_name", "original_competency", "mapping_method", "mapping_source",
                "source_id", "source_url", "confidence", "observed_or_derived",
                "mapping_explanation"], "occupation_skills")
    need(aliases, ["alias", "canonical_skill_name", "canonical_skill_id", "source_id",
                   "confidence"], "skill_aliases")
    if errors:
        return errors, warnings, {}

    def dupes(rows, key, label):
        seen, d = set(), set()
        for r in rows:
            k = r[key]
            if k in seen:
                d.add(k)
            seen.add(k)
        if d:
            errors.append(f"{label}: duplicate {key}: {sorted(d)}")

    dupes(src, "source_id", "source_registry")
    dupes(comp, "competency_id", "nos_competencies")
    # NOTE: the same NOS code legitimately recurs across QPs (e.g. BWS/N0201 in
    # two beauty QPs), so nos_code uniqueness is NOT required. Grain is
    # (research occupation, nos_code), checked below.
    # (occupation,nos) grain check
    seen = set()
    for r in nos:
        k = (r["occupation_id"], r["nos_code"])
        if k in seen:
            errors.append(f"occupation_nos: duplicate pair {k}")
        seen.add(k)

    url_re = re.compile(r"^https?://\S+$")
    for label, rows in (("source_registry", src), ("occupation_nos", nos),
                        ("nos_competencies", comp), ("occupation_skills", maps)):
        col = "url" if label == "source_registry" else "source_url"
        for r in rows:
            if not url_re.match((r[col] or "").strip()):
                errors.append(f"{label}: malformed URL {r[col]!r}")

    for r in nos:
        if r["confidence"] not in ("HIGH", "MEDIUM"):
            errors.append(f"occupation_nos: bad confidence {r['confidence']!r}")
        if r["observed_or_derived"] != "OBSERVED":
            errors.append("occupation_nos: expected OBSERVED, got %r" % r["observed_or_derived"])
        if r["qp_status"] not in ("CURRENT", "RETIRED"):
            errors.append(f"occupation_nos: bad qp_status {r['qp_status']!r}")
    for r in comp:
        if r["confidence"] not in ("HIGH", "MEDIUM"):
            errors.append(f"nos_competencies: bad confidence {r['confidence']!r}")
        if r["observed_or_derived"] != "OBSERVED":
            errors.append("nos_competencies: expected OBSERVED")
    for r in maps:
        if r["confidence"] not in ("HIGH", "MEDIUM"):
            errors.append(f"occupation_skills: bad confidence {r['confidence']!r}")
        if r["observed_or_derived"] != "DERIVED":
            errors.append("occupation_skills: expected DERIVED")
    reg_ids = {r["source_id"] for r in src}
    for label, rows in (("occupation_nos", nos), ("nos_competencies", comp),
                        ("occupation_skills", maps), ("skill_aliases", aliases)):
        for r in rows:
            if r["source_id"] not in reg_ids:
                errors.append(f"{label}: unknown source_id {r['source_id']}")

    # Occupation matching by NAME against live job_roles
    role_by_norm = {}
    for rid, title in existing["roles"]:
        role_by_norm.setdefault(norm(title), []).append((rid, title))
    occ_match, occ_class = {}, {}
    for r in nos:
        key = (r["occupation_id"], r["occupation_name"])
        if key in occ_match:
            continue
        hits = role_by_norm.get(norm(r["occupation_name"]), [])
        if len(hits) == 1:
            occ_match[key] = hits[0][0]
            occ_class[key] = ("EXACT_MATCH"
                              if r["occupation_name"].strip().casefold() == hits[0][1].strip().casefold()
                              else "NORMALIZED_MATCH")
        elif len(hits) > 1:
            errors.append(f"occupation_nos: AMBIGUOUS match for {r['occupation_name']!r}: {hits}")
            occ_class[key] = "AMBIGUOUS"
        else:
            errors.append(f"occupation_nos: UNMATCHED {r['occupation_id']} {r['occupation_name']!r}")
            occ_class[key] = "UNMATCHED"

    # Skill classification completeness
    distinct_sk = {(r["skill_id"], r["skill_name"]) for r in maps}
    for sid, sname in sorted(distinct_sk):
        if sid not in SK_EXACT and sid not in SK_POSSIBLE:
            warnings.append(f"skill {sid} ({sname}): no SKL equivalence -> NEW_SKILL_CANDIDATE")
    for sid, skl in list(SK_EXACT.items()) + list(SK_POSSIBLE.items()):
        if skl not in existing["skill_ids"]:
            errors.append(f"equivalence map: {sid} -> unknown skill {skl}")

    # Cross-refs: map rows must cite a researched (occupation,nos)
    nos_pairs = {(r["occupation_id"], r["nos_code"]) for r in nos}
    for r in maps:
        if (r["occupation_id"], r["nos_code"]) not in nos_pairs:
            warnings.append(f"occupation_skills: {(r['occupation_id'], r['nos_code'])} not in occupation_nos")
    # competency QP/NOS coverage
    qp_nos = {(r["qp_code"], r["nos_code"]) for r in nos}
    for r in comp:
        if (r["qp_code"], r["nos_code"]) not in qp_nos:
            warnings.append(f"nos_competencies: {r['competency_id']} QP/NOS not in occupation_nos")

    # Conflicts with existing occupation_skills PKs
    for r in maps:
        sid = r["skill_id"]
        if sid in SK_EXACT:
            occ_key = (r["occupation_id"], r["occupation_name"])
            role_id = occ_match.get(occ_key)
            if role_id and (role_id, SK_EXACT[sid]) in existing["occ_skill_pks"]:
                errors.append(f"CONFLICT: ({role_id}, {SK_EXACT[sid]}) already in occupation_skills")

    # Alias collisions (case-insensitive) + resolvability + confidence.
    # Only HIGH-confidence aliases resolving to a canonical SKL are imported;
    # MEDIUM/context-dependent ones are staged for review (never auto-aliased).
    existing_alias = {a.lower() for a in existing["aliases"]}
    for r in aliases:
        skl = SK_EXACT.get(r["canonical_skill_id"])
        if r["alias"].strip().lower() in existing_alias:
            warnings.append(f"skill_aliases: alias {r['alias']!r} already exists -> will skip")
        elif not skl:
            warnings.append(f"skill_aliases: {r['alias']!r} points to candidate skill -> staged")
        elif r["confidence"] != "HIGH":
            warnings.append(f"skill_aliases: {r['alias']!r} is {r['confidence']} confidence -> staged")

    # Source namespace: DSRC_ must not collide
    for r in src:
        if ("DSRC_" + r["source_id"].replace("SRC_", "")) in existing["source_ids"]:
            errors.append(f"source namespace collision for {r['source_id']}")

    ctx = {"src": src, "nos": nos, "comp": comp, "maps": maps, "aliases": aliases,
           "occ_match": occ_match, "occ_class": occ_class, "rejected": rejected}
    return errors, warnings, ctx


def run_import(conn, ctx):
    c = conn.cursor()
    stats = {"rejected": 0}
    dsrc_of = {}
    for r in ctx["src"]:
        dsrc = "DSRC_" + r["source_id"].replace("SRC_", "")
        dsrc_of[r["source_id"]] = dsrc
    # 1. sources: UPDATE-or-INSERT (never DELETE: qualifications rows added by
    # this import reference DSRC sources via FK).
    for r in ctx["src"]:
        n = c.execute("""UPDATE sources SET source_name=?, organization=?, dataset_name=?,
          dataset_description=?, source_url=?, publication_date=?, retrieval_date=?,
          geographic_coverage=?, data_type=?, source_status=?, data_source=?
          WHERE source_id=?""",
            (r["source_title"], r["organization"], r["source_title"],
             r.get("relevance", ""), r["url"], r["publication_year"], r["accessed_date"],
             r.get("geographic_scope", ""), "NSDC Qualification Pack",
             r["source_status"], "REAL", dsrc_of[r["source_id"]])).rowcount
        if not n:
            c.execute("""INSERT INTO sources (source_id, source_name, organization, dataset_name,
              dataset_description, source_url, publication_date, retrieval_date, coverage_start,
              coverage_end, geographic_coverage, data_type, source_status, data_source)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (dsrc_of[r["source_id"]], r["source_title"], r["organization"], r["source_title"],
                 r.get("relevance", ""), r["url"], r["publication_year"], r["accessed_date"],
                 None, None, r.get("geographic_scope", ""), "NSDC Qualification Pack",
                 r["source_status"], "REAL"))
    # 2. occupation_nos (full replace of research rows)
    c.execute("DELETE FROM occupation_nos")
    qp_of_occ, title_of_occ, nsqf_of_occ, src_of_occ = {}, {}, {}, {}
    for r in ctx["nos"]:
        role_id = ctx["occ_match"][(r["occupation_id"], r["occupation_name"])]
        eff_qp = PWD_ORIGIN.get(r["qp_code"], r["qp_code"])
        c.execute("""INSERT INTO occupation_nos (occupation_id, research_occupation_id,
          occupation_name, qp_code, qp_title, originating_qp_code, sector_skill_council,
          nsqf_level, qp_status, nos_code, nos_title, nos_status, source_id, source_url,
          publication_year, observed_or_derived, confidence, notes, data_source)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (role_id, r["occupation_id"], r["occupation_name"], r["qp_code"], r["qp_title"],
             PWD_ORIGIN.get(r["qp_code"]), r["sector_skill_council"], r["nsqf_level"],
             r["qp_status"], r["nos_code"], r["nos_title"], r["nos_status"],
             dsrc_of[r["source_id"]], r["source_url"],
             int(r["publication_year"]) if (r["publication_year"] or "").isdigit() else None,
             r["observed_or_derived"], r["confidence"], r.get("notes", ""), "REAL"))
        qp_of_occ.setdefault(role_id, (r["qp_code"], r["qp_title"], r["qp_status"]))
        title_of_occ.setdefault(role_id, r["occupation_name"])
        nsqf_of_occ.setdefault(role_id, r["nsqf_level"])
        src_of_occ.setdefault(role_id, dsrc_of[r["source_id"]])
    # 3. competencies (full replace)
    c.execute("DELETE FROM nos_competencies")
    for r in ctx["comp"]:
        c.execute("""INSERT INTO nos_competencies (competency_id, qp_code, nos_code, nos_title,
          competency_text, knowledge_text, performance_text, source_id, source_url,
          evidence_type, observed_or_derived, confidence, notes, data_source)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["competency_id"], r["qp_code"], r["nos_code"], r["nos_title"],
             r["competency_text"], r.get("knowledge_text", ""), r.get("performance_text", ""),
             dsrc_of[r["source_id"]], r["source_url"], r.get("evidence_type", ""),
             r["observed_or_derived"], r["confidence"], r.get("notes", ""), "REAL"))
    # 4. occupation_skills: exact-equivalence rows only; replace prior DSRC rows
    c.execute("DELETE FROM occupation_skills WHERE source_id LIKE 'DSRC\\_%' ESCAPE '\\'")
    n_links = 0
    for r in ctx["maps"]:
        if r["skill_id"] not in SK_EXACT:
            continue
        role_id = ctx["occ_match"][(r["occupation_id"], r["occupation_name"])]
        review = "pending" if r["confidence"] == "MEDIUM" else None
        c.execute("""INSERT INTO occupation_skills (occupation_id, skill_id, importance,
          competency_type, nos_code, source_id, data_source, qp_code, mapping_method,
          mapping_source, source_url, confidence, observed_or_derived, evidence_text,
          review_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (role_id, SK_EXACT[r["skill_id"]], "High", "NOS-derived", r["nos_code"],
             dsrc_of[r["source_id"]], "REAL", PWD_ORIGIN.get(r["qp_code"], r["qp_code"]),
             r["mapping_method"], r["mapping_source"], r["source_url"], r["confidence"],
             r["observed_or_derived"], r["mapping_explanation"], review))
        n_links += 1
    # 5. candidates staging (full replace)
    c.execute("DELETE FROM new_skill_candidates")
    n_cand = 0
    for r in ctx["maps"]:
        if r["skill_id"] in SK_EXACT:
            continue
        role_id = ctx["occ_match"][(r["occupation_id"], r["occupation_name"])]
        cls = "POSSIBLE_DUPLICATE" if r["skill_id"] in SK_POSSIBLE else "NEW_SKILL_CANDIDATE"
        c.execute("""INSERT INTO new_skill_candidates (candidate_skill_id, skill_name,
          occupation_id, qp_code, nos_code, original_competency, mapping_explanation,
          classification, possible_skl_match, confidence, source_id, source_url,
          review_status, notes, data_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["skill_id"], r["skill_name"], role_id,
             PWD_ORIGIN.get(r["qp_code"], r["qp_code"]), r["nos_code"],
             r["original_competency"], r["mapping_explanation"], cls,
             SK_POSSIBLE.get(r["skill_id"]), r["confidence"], dsrc_of[r["source_id"]],
             r["source_url"], "pending", r.get("notes", ""), "REAL"))
        n_cand += 1
    # 6. aliases: resolvable+non-colliding -> skill_aliases; rest -> candidate_aliases
    c.execute("DELETE FROM candidate_aliases")
    n_alias, n_calias = 0, 0
    existing_alias = {x[0].lower() for x in
                      c.execute("SELECT alias FROM skill_aliases").fetchall()}
    for r in ctx["aliases"]:
        skl = SK_EXACT.get(r["canonical_skill_id"])
        if (skl and r["confidence"] == "HIGH"
                and r["alias"].strip().lower() not in existing_alias):
            c.execute("INSERT OR IGNORE INTO skill_aliases (alias, skill_id) VALUES (?,?)",
                      (r["alias"].strip().lower(), skl))
            n_alias += 1
            existing_alias.add(r["alias"].strip().lower())
        else:
            c.execute("""INSERT OR REPLACE INTO candidate_aliases (alias, candidate_skill_id,
              source_context, mapping_basis, source_id, confidence, review_status, notes,
              data_source) VALUES (?,?,?,?,?,?,?,?,?)""",
                (r["alias"], r["canonical_skill_id"], r.get("source_context", ""),
                 r.get("mapping_basis", ""), dsrc_of[r["source_id"]], r["confidence"],
                 "pending", r.get("notes", ""), "REAL"))
            n_calias += 1
    # 7. job_roles qp_code/qp_name overwrite (approved), old values logged
    qp_changes = []
    for role_id, (qp, title, _st) in qp_of_occ.items():
        eff = PWD_ORIGIN.get(qp, qp)
        cur = c.execute("SELECT qp_code, qp_name FROM job_roles WHERE role_id=?",
                        (role_id,)).fetchone()
        if cur and (cur[0] != eff or (cur[1] or "") != (title or "")):
            qp_changes.append(f"{role_id}: {cur[0]}/{cur[1]} -> {eff}/{title}")
            c.execute("UPDATE job_roles SET qp_code=?, qp_name=? WHERE role_id=?",
                      (eff, title, role_id))
    # 8. qualifications sync + backfill
    q_changes, q_added = [], 0
    maxn = 0
    for (qid,) in c.execute("SELECT qualification_id FROM qualifications").fetchall():
        m = re.match(r"QUA(\d+)", qid or "")
        if m:
            maxn = max(maxn, int(m.group(1)))
    for role_id, (qp, title, st) in qp_of_occ.items():
        eff = PWD_ORIGIN.get(qp, qp)
        qst = QP_STATUS_MAP.get(st, st)
        row = c.execute("SELECT qualification_id, qp_code, qualification_status FROM qualifications"
                        " WHERE occupation_id=?", (role_id,)).fetchone()
        if row:
            if row[1] != eff or row[2] != qst:
                q_changes.append(f"{row[0]}: {row[1]}/{row[2]} -> {eff}/{qst}")
                c.execute("UPDATE qualifications SET qp_code=?, qualification_status=? "
                          "WHERE qualification_id=?", (eff, qst, row[0]))
        else:
            maxn += 1
            c.execute("""INSERT INTO qualifications (qualification_id, qualification_name,
              qp_code, occupation_id, nsqf_level, qualification_status, source_id,
              data_source) VALUES (?,?,?,?,?,?,?,?)""",
                (f"QUA{maxn:03d}", title_of_occ[role_id], eff, role_id,
                 nsqf_of_occ[role_id], qst, src_of_occ[role_id], "REAL"))
            q_added += 1
    stats.update({"sources": len(ctx["src"]), "nos_rows": len(ctx["nos"]),
                  "competencies": len(ctx["comp"]), "links": n_links,
                  "candidates": n_cand, "aliases": n_alias,
                  "candidate_aliases": n_calias, "qp_changes": qp_changes,
                  "qual_changes": q_changes, "qual_added": q_added})
    return stats


def main():
    validate_only = "--validate-only" in sys.argv
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        existing = {
            "roles": [(r[0], r[1]) for r in
                      c.execute("SELECT role_id, job_title FROM job_roles").fetchall()],
            "skill_ids": {r[0] for r in c.execute("SELECT id FROM skills").fetchall()},
            "occ_skill_pks": {(r[0], r[1]) for r in
                              c.execute("SELECT occupation_id, skill_id FROM occupation_skills"
                                        " WHERE source_id NOT LIKE 'DSRC\\_%' ESCAPE '\\'").fetchall()},
            "aliases": [r[0] for r in c.execute("SELECT alias FROM skill_aliases").fetchall()],
            "source_ids": {r[0] for r in
                           c.execute("SELECT source_id FROM sources"
                                     " WHERE source_id NOT LIKE 'DSRC\\_%' ESCAPE '\\'").fetchall()},
        }
    finally:
        conn.close()
    errors, warnings, ctx = validate(existing)
    print(f"validation: {len(errors)} errors, {len(warnings)} warnings")
    for w in warnings:
        print(f"  WARNING: {w}")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print("VALIDATION FAILED - database untouched")
        raise SystemExit(1)
    n_occ = len({k[0] for k in ctx["occ_match"]})
    classes = {}
    for v in ctx["occ_class"].values():
        classes[v] = classes.get(v, 0) + 1
    print(f"occupations matched: {n_occ}/33 research IDs -> {len(set(ctx['occ_match'].values()))} Kaushora roles; {classes}")
    print(f"mappings: {len(ctx['maps'])} rows; exact-equivalence skills: "
          f"{sum(1 for r in ctx['maps'] if r['skill_id'] in SK_EXACT)}; staged: "
          f"{sum(1 for r in ctx['maps'] if r['skill_id'] not in SK_EXACT)}")
    if validate_only:
        print("validate-only: database untouched")
        return 0
    conn = sqlite3.connect(DB)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN")
        stats = run_import(conn, ctx)
        warn_txt = "\n".join(warnings[:50])
        if stats["qp_changes"]:
            warn_txt += "\nQP_OVERWRITES(job_roles):\n" + "\n".join(stats["qp_changes"])
        if stats["qual_changes"]:
            warn_txt += "\nQUAL_UPDATES:\n" + "\n".join(stats["qual_changes"])
        conn.execute("""INSERT INTO ingestion_runs (dataset_file, records_imported,
          records_rejected, warnings, status) VALUES (?,?,?,?,?)""",
            ("data/raw/kaushora_occupation_mapping/", sum([
                stats["sources"], stats["nos_rows"], stats["competencies"],
                stats["links"], stats["candidates"], stats["aliases"],
                stats["candidate_aliases"]]) + len(stats["qp_changes"]) + stats["qual_added"],
             len(ctx["rejected"]), warn_txt[:4000], "success"))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("=== IMPORT COMPLETE ===")
    for k, v in stats.items():
        if isinstance(v, list):
            print(f"{k}: {len(v)}")
            for line in v:
                print(f"  {line}")
        else:
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
