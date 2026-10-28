"""Test script to verify Task 2 & Task 3 through the live deployed backend at http://localhost:8000."""
import json
import urllib.request

def test_deployed_analysis():
    payload = {
        "as_at_date": "2026-10-01",
        "business_name": "Lanka Sea Harvests",
        "business_scale": "SMALL",
        "annual_revenue_lkr": 15000000,
        "employee_count": 12,
        "products": [
            {
                "product_name": "Frozen Raw Headless Prawns",
                "category": "SEAFOOD",
                "ingredients": ["Prawns", "Water"],
                "additives": ["Tartrazine"],
                "packaging_type": "POLYETHYLENE_POUCH",
                "target_market": "DOMESTIC",
            }
        ]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/analysis",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            print(f"HTTP Status: {status}")
            print(f"Body keys: {list(body.keys())}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return
    except Exception as e:
        print(f"Connection error: {e}")
        return

    print("\n--- SUMMARY COUNTS ---")
    print(f"Total rules evaluated: {body.get('total_rules_evaluated')}")
    print(f"Applicable rules count: {body.get('applicable_rules_count')}")
    print(f"Conditional rules count: {body.get('conditional_rules_count')}")
    print(f"Not applicable rules count: {body.get('not_applicable_rules_count')}")
    print(f"Unsupported rules count: {body.get('unsupported_rules_count')}")
    print(f"Missing data count: {body.get('conditional_missing_data_count')}")

    print("\n--- EVALUATIONS ---")
    evals = body.get("evaluations", [])
    print(f"Total evaluations: {len(evals)}")
    for ev in evals:
        print(f"  Rule: {ev.get('rule_id')} | Status: {ev.get('status')} | Outcome: {ev.get('outcome_type')}")
        print(f"    Reason: {ev.get('reason')}")
        print(f"    Source: {ev.get('source_citation')}")
        print(f"    Doc ID: {ev.get('document_id')} | Title: {ev.get('document_title')} | Page: {ev.get('page_number')}")
        print(f"    Coverage gap: {ev.get('coverage_gap')} | Review status: {ev.get('review_status')}")
        if ev.get("missing_fields"):
            print(f"    Missing fields: {ev.get('missing_fields')}")
        if ev.get("counterfactuals"):
            print(f"    Counterfactuals: {ev.get('counterfactuals')}")

    print("\n--- ACTION CHECKLIST ---")
    for item in body.get("action_checklist", []):
        print(f"  Item: {item}")

    print("\n--- NARRATIVE SUMMARY ---")
    print(f"Summary: {body.get('narrative_summary')[:200]}...")

if __name__ == "__main__":
    test_deployed_analysis()
