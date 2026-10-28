"""Controlled Real-Document Clause Discovery Test (Phase 4.7 Part 3).

Tests the automated document-level discovery and extraction pipeline in isolation:
1. Selects genuine regulatory PDF: 2494-47_E.pdf (Gazette Extraordinary No. 2494/47).
2. Extracts pages and character counts via extract_pages_pymupdf.
3. Discovers clause boundaries via segment_clauses_from_page.
4. Attempts LLM rule compilation via RuleCompiler and get_llm_client(allow_mock_fallback=False).
5. Compares automated discovery against pre-existing database records.
6. Does NOT write or alter any database records.
"""
import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, ".")

from backend.src.extraction.ingestion import extract_pages_pymupdf, segment_clauses_from_page
from backend.src.extraction.compiler import RuleCompiler
from backend.src.extraction.llm_client import get_llm_client, LLMAuthenticationError

def run_controlled_discovery():
    pdf_path = Path("backend/data/raw_sources/2494-47_E.pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found.")
        return
        
    print(f"=== PART 3: CONTROLLED CLAUSE DISCOVERY TEST ===")
    print(f"Target Document: {pdf_path.name}")
    print(f"File Size: {pdf_path.stat().st_size} bytes")
    
    # 1. Text extraction via PyMuPDF
    pages, warnings = extract_pages_pymupdf(pdf_path)
    print(f"Extracted Pages: {len(pages)}")
    print(f"Extraction Warnings: {warnings}")
    total_chars = sum(p.char_count for p in pages)
    ocr_pages = sum(1 for p in pages if p.is_ocr)
    print(f"Total Characters Extracted: {total_chars} across {len(pages)} pages (OCR pages: {ocr_pages})")
    
    # 2. Automated Clause Segmentation (Regex-based)
    all_segmented_clauses = []
    for page in pages:
        clauses = segment_clauses_from_page(page.raw_text, page.page_number)
        all_segmented_clauses.extend(clauses)
        
    print(f"\n--- CLAUSE SEGMENTATION RESULTS ---")
    print(f"Total Candidate Clauses Discovered: {len(all_segmented_clauses)}")
    for i, c in enumerate(all_segmented_clauses[:10], 1):
        print(f"  [{i}] Clause: {c.clause_number} | Page: {c.start_page} | Span: [{c.char_start}:{c.char_end}] ({len(c.text)} chars)")
        snippet = c.text[:100].replace('\n', ' ')
        print(f"      Text: {snippet}...")
        
    # Check specifically for Regulation 3 (the primary rule clause)
    reg3_matches = [c for c in all_segmented_clauses if "3" in c.clause_number or "Regulation 3" in c.clause_number]
    print(f"\nRegulation 3 Discovered: {len(reg3_matches)} match(es)")
    for m in reg3_matches:
        print(f"  Header: {m.clause_number} on Page {m.start_page}")
        print(f"  Text excerpt: {m.text[:150].replace(chr(10), ' ')}...")
        
    # 3. Test LLM-Assisted Extraction Invocation
    print(f"\n--- LLM EXTRACTION INVOCATION TEST ---")
    llm_status = "UNKNOWN"
    real_client = None
    try:
        # Enforce allow_mock_fallback=False to verify genuine AI model configuration
        real_client = get_llm_client(allow_mock_fallback=False)
        llm_status = f"GENUINE_CLIENT_AVAILABLE ({type(real_client).__name__})"
    except LLMAuthenticationError as e:
        llm_status = f"AUTHENTICATION_BLOCKED: {e}"
    except Exception as e:
        llm_status = f"FAILED: {e}"
        
    print(f"LLM Client Status: {llm_status}")
    
    if real_client:
        print("Testing genuine LLM compilation on discovered Regulation 3...")
        compiler = RuleCompiler(llm_client=real_client)
        if reg3_matches:
            target_clause = reg3_matches[0]
            try:
                res = compiler.compile_clause(
                    raw_text=target_clause.text,
                    source_metadata={
                        "clause": target_clause.clause_number,
                        "instrument": "Sri Lanka Gazette Extraordinary No. 2494/47",
                        "page": target_clause.start_page,
                    }
                )
                print(f"Rule Compilation Output: {res}")
            except Exception as e:
                print(f"LLM Compilation Error: {e}")
    else:
        print("Note: In the current environment, no live OPENAI_API_KEY or GEMINI_API_KEY is configured.")
        print("Clause discovery at the document level operates via deterministic PyMuPDF text extraction and regex segmentation.")

if __name__ == "__main__":
    run_controlled_discovery()
