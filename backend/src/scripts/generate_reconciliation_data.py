import sys
import hashlib
import json
from pathlib import Path

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import SourceDocumentORM, ClauseORM, RuleORM

raw_dir = Path("backend/data/raw_sources")
files = sorted([f for f in raw_dir.iterdir() if f.is_file() and f.name != ".gitkeep"])

print(f"Total physical files: {len(files)}")

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# Map file to DB record if any
file_to_db = {}
with session_scope() as db:
    docs = db.query(SourceDocumentORM).all()
    for d in docs:
        clauses = db.query(ClauseORM).filter_by(document_id=d.id).all()
        rules = (
            db.query(RuleORM)
            .join(ClauseORM, RuleORM.clause_id == ClauseORM.clause_id)
            .filter(ClauseORM.document_id == d.id)
            .all()
        )
        # Match by file_path or sha256_hash
        file_to_db[d.id] = {
            "doc": d,
            "clauses": len(clauses),
            "rules": len(rules)
        }

print(f"Total DB records: {len(file_to_db)}")
