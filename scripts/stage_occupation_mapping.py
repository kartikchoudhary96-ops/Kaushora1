"""Stage Problem #2 DeepSeek research CSVs (read-only copy, exact bytes).

Copies the 5 located research files from Downloads into
data/raw/kaushora_occupation_mapping/ under canonical names.
Writes _KAUSHORA_STAGING_MANIFEST.json (Kaushora-generated audit file,
NOT part of the research package) recording provenance + missing docs.
No database access. No transformation of research content.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DEST = BASE / "data" / "raw" / "kaushora_occupation_mapping"
DOWN = Path.home() / "Downloads"

FILES = {
    "deepseek_csv_20260916_16efa4.txt": "source_registry.csv",
    "deepseek_csv_20260916_2d5c19.txt": "occupation_nos.csv",
    "deepseek_csv_20260916_683a0d.txt": "nos_competencies.csv",
    "deepseek_csv_20260916_95ee78.txt": "occupation_skills.csv",
    "deepseek_csv_20260916_5b40f2.txt": "skill_aliases.csv",
}

MISSING_DOCS = ["README.md", "data_dictionary.md", "methodology.md", "validation_report.md"]


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    staged = []
    for src_name, canon in FILES.items():
        src = DOWN / src_name
        if not src.exists():
            raise SystemExit(f"MISSING SOURCE FILE: {src}")
        raw = src.read_bytes()
        (DEST / canon).write_bytes(raw)
        rows = raw.decode("utf-8-sig").strip().splitlines()
        staged.append({
            "canonical_name": canon,
            "original_filename": src_name,
            "original_path": str(src),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "lines_including_header": len(rows),
            "data_rows": len(rows) - 1,
            "header": rows[0] if rows else "",
        })
        print(f"staged {canon}: {len(rows)-1} data rows (from {src_name})")
    manifest = {
        "_generated_by": "Kaushora scripts/stage_occupation_mapping.py (NOT part of the DeepSeek research package)",
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "package": "Problem #2 occupation->QP->NOS->skill research (DeepSeek, 2026-09-16 batch)",
        "files": staged,
        "missing_research_docs": MISSING_DOCS,
        "note": "Content bytes are exact copies. Canonical .csv names are renames only, no transformation.",
    }
    (DEST / "_KAUSHORA_STAGING_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest written: {DEST / '_KAUSHORA_STAGING_MANIFEST.json'}")
    print(f"missing docs (not fabricated): {', '.join(MISSING_DOCS)}")


if __name__ == "__main__":
    main()
