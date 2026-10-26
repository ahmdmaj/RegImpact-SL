import json
from pathlib import Path

with open("backend/data/quarantine/doc_inventory_audit.json", encoding="utf-8") as f:
    docs = json.load(f)

print(f"{'DOCUMENT ID':38s} | {'SIZE':7s} | {'CLASS':30s} | {'CLS':3s} | {'EMB':3s} | {'TITLE':30s}")
print("-" * 125)
for d in docs:
    did = d["id"]
    sz = str(d["actual_size"])
    cl = d["classification"]
    cls_cnt = str(d["clause_count"])
    emb_cnt = str(d["verified_embs"])
    title = d["title"][:28]
    print(f"{did:38s} | {sz:7s} | {cl:30s} | {cls_cnt:3s} | {emb_cnt:3s} | {title:30s}")
