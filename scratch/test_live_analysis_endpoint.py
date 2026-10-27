"""End-to-end verification of POST /analysis using live PostgreSQL and corrected RAG pipeline."""

import os
import sys

# Force live PostgreSQL and sentence-transformers
os.environ["DATABASE_URL"] = "postgresql://regimpact:regimpact@localhost:5432/regimpact"
os.environ["EMBEDDING_PROVIDER"] = "sentence-transformers"
os.environ["EMBEDDING_MODEL"] = "BAAI/bge-base-en-v1.5"
os.environ["EMBEDDING_DIMENSION"] = "768"

sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.src.main import app

def main():
    client = TestClient(app)
    
    # 1. Health check
    res_health = client.get("/health")
    print("Health response:", res_health.status_code, res_health.json())
    assert res_health.status_code == 200

    # 2. Open-inquiry Analysis for Seafood Processor
    payload = {
        "business_profile": {
            "business_id": "BIZ-SEAFOOD-PROD-01",
            "activity": "food_manufacturing",
            "industry": "food_and_beverage",
            "products": [
                {
                    "name": "Frozen Raw Prawns and Fish Fillets",
                    "category": "fish",
                    "prepackaged": True,
                }
            ],
            "production_capacity": {"value": 150.0, "unit": "kg", "per_period": "day"},
        }
    }

    print("\nSending POST /analysis for seafood profile...")
    res = client.post("/analysis", json=payload)
    print("Analysis status:", res.status_code)
    assert res.status_code == 200, res.text
    data = res.json()

    print(f"Summary: {data.get('summary')}")
    print(f"Evaluations count: {len(data.get('evaluations', []))}")
    print("Evaluations returned:")
    for ev in data.get("evaluations", []):
        print(f"  - Rule ID: {ev.get('rule_id')} | Status: {ev.get('status')} | Doc: {ev.get('document_title')} | Gap: {ev.get('coverage_gap')}")

    print(f"Clarifying questions: {data.get('clarifying_questions')}")
    print(f"Action checklist items: {len(data.get('action_checklist', []))}")

    print("\nLive E2E analysis verification SUCCEEDED.")

if __name__ == "__main__":
    main()
