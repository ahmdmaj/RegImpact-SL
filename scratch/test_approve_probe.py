import urllib.request
import urllib.error
import json

base_url = "http://localhost:8000"

roles = [
    ("No Header", None),
    ("admin", "admin"),
    ("reviewer", "reviewer"),
    ("sme_user", "sme_user"),
]

rule_id = "RULE-SUGAR-2494-06-RED"

print(f"=== TESTING APPROVE PERMISSION ON {rule_id} ===")
for label, role in roles:
    headers = {"Content-Type": "application/json"}
    if role is not None:
        headers["X-User-Role"] = role
    
    # We send an empty or test payload
    payload = json.dumps({
        "reviewer_id": "test_auditor",
        "reviewer_role": "PRIMARY_ANNOTATOR",
        "rationale": "Audit test probe"
    }).encode('utf-8')
    
    # We will test with a dummy nonexistent rule ID first so we don't accidentally approve a real rule!
    test_rule = "RULE-AUDIT-PROBE-NONEXISTENT"
    req = urllib.request.Request(f"{base_url}/admin/reviews/{test_rule}/approve", data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"  [{label.ljust(12)}] Status: {response.status}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        try:
            ej = json.loads(err_body)
            detail = ej.get('detail')
        except Exception:
            detail = err_body[:50]
        print(f"  [{label.ljust(12)}] Status: {e.code} | detail: {detail}")
    except Exception as e:
        print(f"  [{label.ljust(12)}] Error: {e}")

