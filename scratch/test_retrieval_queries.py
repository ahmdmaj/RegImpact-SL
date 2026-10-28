"""Test runtime retrieval with diverse natural language queries (Phase 4.7 Part 4)."""
import json
import urllib.request
import os
import sys

sys.path.insert(0, ".")

from backend.src.db.session import create_engine_from_url, get_session_factory
from backend.src.engine.retrieval import HybridRetrievalEngine, BM25RetrievalEngine, DenseRetrievalEngine

def run_retrieval_tests():
    db_url = "postgresql+psycopg://regimpact:regimpact@localhost:5432/regimpact"
    session = get_session_factory(create_engine_from_url(db_url))()
    
    bm25 = BM25RetrievalEngine(session)
    dense = DenseRetrievalEngine(session)
    hybrid = HybridRetrievalEngine(session, bm25_engine=bm25, dense_engine=dense)
    
    test_queries = [
        ("Query 1 (Direct Lexical)", "Regulation 5 fish molluscs crustaceans colouring substances"),
        ("Query 2 (Paraphrased Semantic)", "Are synthetic food dyes allowed in raw prawns and seafood packaging in Sri Lanka?"),
        ("Query 3 (Different Domain: Sugar Beverages)", "Sugar content colour coding traffic light label limits for sweetened beverages"),
        ("Query 4 (Unrelated Negative Control)", "Automobile import customs duty and vehicle registration requirements"),
    ]
    
    print("=== PART 4: RUNTIME RETRIEVAL AUDIT ===")
    
    for label, q in test_queries:
        print(f"\n------------------------------------------------------------")
        print(f"Executing: {label}")
        print(f"Query text: \"{q}\"")
        
        bm25_res = bm25.search(q, top_k=3)
        dense_res = dense.search(q, top_k=3)
        hybrid_res = hybrid.search(q, top_k=3)
        
        print(f"BM25 Top Candidate:   {bm25_res[0].clause_id if bm25_res else 'NONE'} (score: {bm25_res[0].score if bm25_res else 0})")
        print(f"Dense Top Candidate:  {dense_res[0].clause_id if dense_res else 'NONE'} (score: {dense_res[0].score if dense_res else 0})")
        print(f"Hybrid Top Candidates ({len(hybrid_res)}):")
        for rank, res in enumerate(hybrid_res, 1):
            snippet = res.text[:120].replace('\n', ' ')
            print(f"  [{rank}] {res.clause_id} (RRF: {res.score}) | Doc: {res.document_id}")
            print(f"      Text: {snippet}...")
            print(f"      Coverage Gap: {res.coverage_gap} | Approved: {res.has_approved_rule}")
            
    session.close()

def run_deployed_api_tests():
    print(f"\n============================================================")
    print("=== DEPLOYED API ANALYSIS PROFILE AUDIT (HTTP localhost:8000) ===")
    
    profiles = [
        {
            "label": "Profile A: Seafood SME (Raw Prawns)",
            "payload": {
                "business_name": "Lanka Sea Harvests",
                "business_scale": "SMALL",
                "employee_count": 12,
                "products": [
                    {
                        "product_name": "Frozen Raw Headless Prawns",
                        "category": "SEAFOOD",
                        "ingredients": ["Prawns", "Water"],
                        "additives": ["Tartrazine"],
                    }
                ]
            }
        },
        {
            "label": "Profile B: Sweetened Beverage SME (Fruit Cordial)",
            "payload": {
                "business_name": "Ceylon Citrus Works",
                "business_scale": "SMALL",
                "employee_count": 8,
                "products": [
                    {
                        "product_name": "Lime Fruit Cordial",
                        "category": "BEVERAGE",
                        "ingredients": ["Water", "Sugar", "Lime Juice"],
                        "additives": ["Sodium Benzoate"],
                    }
                ]
            }
        }
    ]
    
    for item in profiles:
        print(f"\n--- Submitting {item['label']} ---")
        data = json.dumps(item["payload"]).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8000/analysis",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                print(f"HTTP Status: {resp.status}")
                print(f"Evaluations Count: {len(body.get('evaluations', []))}")
                print(f"Unsupported Coverage Gaps: {body.get('unsupported_rules_count')}")
                for ev in body.get("evaluations", [])[:4]:
                    print(f"  - Rule/Clause: {ev.get('rule_id')} | Status: {ev.get('status')} | Doc: {ev.get('document_id')}")
                    print(f"    Reason: {ev.get('reason')[:120]}...")
        except Exception as e:
            print(f"API Request Failed: {e}")

if __name__ == "__main__":
    run_retrieval_tests()
    run_deployed_api_tests()
