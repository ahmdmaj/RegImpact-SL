import sys
import hashlib
import json
from pathlib import Path
from datetime import datetime
import fitz

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import SourceDocumentORM, ClauseORM, RuleORM

raw_dir = Path("backend/data/raw_sources")

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def compile_inventory():
    all_files = sorted([f for f in raw_dir.iterdir() if f.is_file() and f.name != ".gitkeep"])
    
    with session_scope() as db:
        docs = db.query(SourceDocumentORM).all()
        doc_map_by_id = {d.id: d for d in docs}
        doc_map_by_hash = {d.sha256_hash: d for d in docs if d.sha256_hash}
        
        # Substantive file groupings
        substantive_meta = {
            "83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054": {
                "title": "Sri Lanka Gazette Extraordinary No. 2494/47 (Food Labelling & Advertising)",
                "authority": "Minister of Health and Mass Media (Dr. Nalinda Jayatissa)",
                "gazette_no": "2494/47",
                "pub_date": "2026-06-26",
                "commencement": "2026-06-26 (or specified schedule)",
                "url": "http://www.documents.gov.lk (official Sri Lanka Government Gazette)",
                "evidence": "Primary Government Gazette with official masthead, LDB 11/80, Dept of Govt Printing stamp",
                "classification": "AUTHENTIC_PROMULGATED",
                "exclusion_status": "NONE (Active benchmark foundation)",
                "relationships": "Amends/promulgates Food (Labelling and Advertising) Regulations 2026; defines Regulation 3 retail/B2B labelling",
                "uncertainty": "None. Fully verified and grounded with 9 clauses and 2 approved gold rules."
            },
            "d7852dcc0da491ee0f67dbc355ad3ed96c1b860018b6151204d0db9d3fe2f45d": {
                "title": "The Sri Lanka Gazette Extraordinary No. 2443/27",
                "authority": "Minister of Health and Mass Media (Dr. Nalinda Jayatissa)",
                "gazette_no": "2443/27",
                "pub_date": "2025-07-01",
                "commencement": "2025-07-01",
                "url": "http://www.documents.gov.lk",
                "evidence": "Primary Government Gazette, LDB 11/80(30)(A), Dept of Govt Printing stamp PG 7181",
                "classification": "AUTHENTIC_PROMULGATED",
                "exclusion_status": "NONE",
                "relationships": "Amends Food (Labelling and Advertising) Regulations 2022 (Gazette 2319/40), specifically Reg 2 bulk pack proviso",
                "uncertainty": "Clauses extracted (15) but no gold rules compiled yet. Needs rule compilation before benchmark inclusion."
            },
            "672a95c9c8e179b960dbcd00ebdd07f67e2848239a0c67ade17c8eaeed7f37b9": {
                "title": "The Sri Lanka Gazette Extraordinary No. 2496/03",
                "authority": "Minister of Trade, Commerce, Food Security and Co-operative Development (Wasantha Samarasinghe)",
                "gazette_no": "2496/03",
                "pub_date": "2026-07-06",
                "commencement": "2026-07-06",
                "url": "http://www.documents.gov.lk",
                "evidence": "Primary Government Gazette, Companies Act No. 07 of 2007 / Societies Ordinance No. 16 of 1891",
                "classification": "AUTHENTIC_OUT_OF_SCOPE",
                "exclusion_status": "EXCLUDED_OUT_OF_SCOPE",
                "relationships": "Companies (Fees) Orders / Societies (Fees) Orders. Not food regulation.",
                "uncertainty": "Authentic government publication but completely out of project scope (food manufacturing impact). Exclude from benchmark."
            },
            "d5fd93679c6a3c12c64118d6a1e738e11fcbe1d8e577880fb4dae65d868272cd": {
                "title": "The Sri Lanka Gazette Extraordinary No. 2443/06",
                "authority": "Minister of Health and Mass Media (Dr. Nalinda Jayatissa)",
                "gazette_no": "2443/06",
                "pub_date": "2025-06-30",
                "commencement": "Postpones commencement to 1st January 2026",
                "url": "http://www.documents.gov.lk",
                "evidence": "Primary Government Gazette, LDB 11/80, Dept of Govt Printing stamp PG 7175",
                "classification": "AUTHENTIC_PROMULGATED",
                "exclusion_status": "NONE",
                "relationships": "Amends Gazette 2319/40 by repealing Reg 1(ii) and substituting 1st January 2026 commencement date.",
                "uncertainty": "DB record titled as FCAU English Regs; metadata should be formally updated to Gazette 2443/06."
            },
            "15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b": {
                "title": "The Sri Lanka Gazette Extraordinary No. 2494/06 (Sugar Colour Coding Amendment)",
                "authority": "Minister of Health and Mass Media (Dr. Nalinda Jayatissa)",
                "gazette_no": "2494/06",
                "pub_date": "2026-06-23",
                "commencement": "2026-06-23",
                "url": "http://www.documents.gov.lk",
                "evidence": "Primary Government Gazette, LDB 11/80 (29), Dept of Govt Printing stamp PG 7779",
                "classification": "AUTHENTIC_PROMULGATED",
                "exclusion_status": "NONE (Candidate verified)",
                "relationships": "Amends Food (Colour Coding for sugar levels-liquid) Regulations 2022 (Gazette 2319/42), Reg 3 logo & Schedule",
                "uncertainty": "Metadata in DB currently contains placeholder hex title; 5 clauses embedded; needs rule compilation."
            },
            "3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7": {
                "title": "The Sri Lanka Gazette Extraordinary No. 1688/28 (Food Colouring Amendment 2011)",
                "authority": "Minister of Health (Maithripala Sirisena)",
                "gazette_no": "1688/28",
                "pub_date": "2011-01-14",
                "commencement": "2011-01-14",
                "url": "http://www.documents.gov.lk",
                "evidence": "Primary Government Gazette, LD-B 11/80, signed 8th Jan 2011, Dept of Govt Printing stamp 01-695",
                "classification": "AUTHENTIC_IMAGE_RASTER_UNEXTRACTED",
                "exclusion_status": "UNEXTRACTED_SCANNED_SOURCE",
                "relationships": "Amends Food (Colouring Substances) Regulations 2006 (Gazette 1472/19 as amended by 1585/26)",
                "uncertainty": "Scanned raster image PDF without OCR text layer. 0 text/clauses in DB. Requires OCR processing before segmentation."
            },
            "3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f": {
                "title": "The Sri Lanka Gazette Extraordinary No. 2113/16 (Food Preservatives Regulations 2019)",
                "authority": "Minister of Health, Nutrition and Indigenous Medicine (Dr. Rajitha Senarathne)",
                "gazette_no": "2113/16",
                "pub_date": "2019-03-05",
                "commencement": "2020-01-01 (Regulation 1)",
                "url": "http://www.documents.gov.lk",
                "evidence": "Primary Government Gazette, LDB 11/80 [6], Dept of Govt Printing stamp",
                "classification": "AUTHENTIC_PROMULGATED",
                "exclusion_status": "NONE (Candidate verified)",
                "relationships": "Principal Regulations; rescinds Food (Preservatives) Regulations 1989 (Gazette 595/24). Schedules I & II define permitted preservatives.",
                "uncertainty": "Only 2 clauses segmented in DB; operative clauses (Regs 2-8, Schedules I-II) must be segmented prior to benchmark use."
            },
            "b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a": {
                "title": "The Sri Lanka Gazette Extraordinary No. 1795/51 (Food Flavouring Regulations 2013)",
                "authority": "Minister of Health (Maithripala Sirisena)",
                "gazette_no": "1795/51",
                "pub_date": "2013-02-01",
                "commencement": "2014-07-01 (Regulation 1)",
                "url": "http://www.documents.gov.lk",
                "evidence": "Primary Government Gazette, LD-B 11/80, Dept of Govt Printing stamp 02-585",
                "classification": "AUTHENTIC_PROMULGATED",
                "exclusion_status": "NONE (Candidate verified)",
                "relationships": "Principal Regulations; cross-references Food (Labelling and Advertising) Regulations 2005 (Gazette 1376/9). Reg 6-7, Schedules I-III.",
                "uncertainty": "5 clauses in DB were heuristically segmented (Schedules labelled as Regs); core substantive prohibitions need clean segmentation."
            },
            "c70b5668131b76ff206897ef391cb3402bb4bf6be39a76ad1400d24c07330142": {
                "title": "Food (Labelling and Advertising) Regulations Final Draft (11.02.2026)",
                "authority": "Food Advisory Committee (FAC) Working Group",
                "gazette_no": "UNPROMULGATED DRAFT",
                "pub_date": "2026-02-11 (Draft date)",
                "commencement": "UNPROMULGATED",
                "url": "Internal FAC working document",
                "evidence": "Document header indicates internal working draft; not gazetted",
                "classification": "EXCLUDED_NON_PROMULGATED",
                "exclusion_status": "QUARANTINED",
                "relationships": "Unpromulgated draft of labelling regulations. Quarantined in Phase 3.1.",
                "uncertainty": "Non-statutory working document. Strictly excluded from benchmark."
            },
            "b2cfaf0ae21c67ae28864038a0b21293eb4c0f888dbc984c331e975c5528c37f": {
                "title": "IS5103 High Performance Computing - Lecture 03",
                "authority": "Faculty of Computing, Sabaragamuwa University of Sri Lanka",
                "gazette_no": "ACADEMIC SLIDE DECK",
                "pub_date": "None",
                "commencement": "NON-STATUTORY",
                "url": "Course materials (Kayalvizhy)",
                "evidence": "Academic lecture slide deck on high performance computing",
                "classification": "EXCLUDED_NON_STATUTORY",
                "exclusion_status": "QUARANTINED",
                "relationships": "Secondary academic slides; no legal effect.",
                "uncertainty": "Completely non-regulatory. Quarantined in Phase 3.1."
            }
        }
        
        inventory = []
        for f in all_files:
            size = f.stat().st_size
            h = sha256_file(f)
            
            # Check if linked to DB doc
            matched_doc = None
            for d in docs:
                if d.file_path and Path(d.file_path).name == f.name:
                    matched_doc = d
                    break
                if d.sha256_hash == h:
                    matched_doc = d
                    break
                    
            db_id = matched_doc.id if matched_doc else "NOT_IN_DB"
            clauses = db.query(ClauseORM).filter_by(document_id=matched_doc.id).count() if matched_doc else 0
            rules = (
                db.query(RuleORM)
                .join(ClauseORM, RuleORM.clause_id == ClauseORM.clause_id)
                .filter(ClauseORM.document_id == matched_doc.id)
                .count()
                if matched_doc else 0
            )
            
            if h in substantive_meta:
                meta = substantive_meta[h]
                is_substantive = True
            else:
                is_substantive = False
                meta = {
                    "title": "Integration Test Upload Fixture (Regulation 50 Dummy)",
                    "authority": "Test Harness",
                    "gazette_no": "TEST_DUMMY",
                    "pub_date": None,
                    "commencement": None,
                    "url": "None (Generated in-memory during tests)",
                    "evidence": "1,033–1,037 byte dummy PDF fixture from test_gazette_upload.pdf",
                    "classification": "EXCLUDED_TEST_FIXTURE",
                    "exclusion_status": "QUARANTINED_OR_TEST_ONLY",
                    "relationships": "Test fixture for API /regulations/upload endpoint",
                    "uncertainty": "Artifact of integration test suite. Barred from benchmark corpus."
                }
                
            inventory.append({
                "filename": f.name,
                "size_bytes": size,
                "sha256": h,
                "db_doc_id": db_id,
                "is_substantive": is_substantive,
                "meta": meta,
                "clauses_in_db": clauses,
                "rules_in_db": rules
            })
            
        print(f"Compiled {len(inventory)} file inventory entries.")
        Path("backend/data/quarantine/phase3_2_inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
        print("Saved to backend/data/quarantine/phase3_2_inventory.json")

if __name__ == "__main__":
    compile_inventory()
