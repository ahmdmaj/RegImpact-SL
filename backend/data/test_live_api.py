import json
import urllib.request

payload = {
    "business_profile": {
        "business_id": "BIZ-REAL-001",
        "activity": "food_manufacturing",
        "products": [{"category": "spices", "prepackaged": True}],
        "packaged_in_presence_of_purchaser": False,
        "market": {"b2b_only": False},
    },
    "as_at_date": "2026-07-15",
    "clause_ids": ["RULE-FCAU-REAL-2026-REG-2"],
}

req = urllib.request.Request(
    "http://localhost:8000/analysis",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req) as resp:
    status_code = resp.status
    data = json.loads(resp.read().decode("utf-8"))

print("Status Code:", status_code)
print("Total evaluated:", data["total_rules_evaluated"])
print("Applicable:", data["applicable_rules_count"])
print("Conditional (Total):", data["conditional_rules_count"])
print("Conditional (Missing Data):", data.get("conditional_missing_data_count", 0))
print("Conditional (Rule Precondition):", data.get("conditional_rule_count", 0))
print("Evaluation Details:")
for ev in data["evaluations"]:
    print(f"  Rule: {ev['rule_id']}")
    print(f"  Clause: {ev['clause']}")
    print(f"  Status: {ev['status']}")
    print(f"  Document Title: {ev['document_title']}")
    print(f"  Document ID: {ev['document_id']}")
    print(f"  Page: {ev['page_number']}")
    print(f"  Offsets: [{ev['char_start']}, {ev['char_end']}]")
    print(f"  Review Status: {ev['review_status']}")
    print(f"  Reason: {ev['reason']}")
    print(f"  Trace items: {len(ev['evaluation_trace'])}")
