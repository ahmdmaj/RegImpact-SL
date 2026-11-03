import requests
import json

url = "http://localhost:8000/analysis"
headers = {
    "Content-Type": "application/json",
    "X-User-Role": "sme_user"
}

payload = {
    "profile": {
        "business_id": "BIZ-SL-FOOD-RETAIL-001",
        "industry": "food_processing",
        "activity": "food_manufacturing",
        "employee_count": 12,
        "products": [
            {
                "category": "biscuits_and_cookies",
                "prepackaged": True
            }
        ],
        "market": {
            "domestic": True,
            "export_flag": False,
            "b2b_only": False
        },
        "packaged_in_presence_of_purchaser": False,
        "as_at_date": "2026-07-01"
    }
}

resp = requests.post(url, json=payload, headers=headers)
print("Status Code:", resp.status_code)
try:
    data = resp.json()
    with open("scratch/api_analysis_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Total rules evaluated:", data.get("total_rules_evaluated"))
    print("Applicable count:", data.get("applicable_rules_count"))
    print("Conditional rules count:", data.get("conditional_rules_count"))
    print("Not applicable count:", data.get("not_applicable_rules_count"))
    print("Unsupported count:", data.get("unsupported_rules_count"))
    print("Evaluations:")
    for ev in data.get("evaluations", []):
        print(f" - Rule: {ev.get('rule_id')} | Status: {ev.get('status')} | Doc: {ev.get('document_title')} | Gap: {ev.get('coverage_gap')}")
except Exception as e:
    print("Error parsing response:", e, resp.text)
