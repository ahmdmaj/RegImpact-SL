import os
import glob
import hashlib
import json
import re
import fitz  # PyMuPDF
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+psycopg://regimpact:regimpact@db:5432/regimpact"
)

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def detect_language(sample_text):
    # Check Sinhala unicode block 0D80–0DFF
    sinhala_chars = len(re.findall(r'[\u0D80-\u0DFF]', sample_text))
    # Check Tamil unicode block 0B80–0BFF
    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', sample_text))
    # Check Latin chars
    latin_chars = len(re.findall(r'[A-Za-z]', sample_text))
    
    total = sinhala_chars + tamil_chars + latin_chars
    if total == 0:
        return "Unknown / Scanned"
    
    s_pct = sinhala_chars / total
    t_pct = tamil_chars / total
    l_pct = latin_chars / total
    
    if l_pct > 0.8:
        return "English"
    elif s_pct > 0.6:
        return "Sinhala"
    elif t_pct > 0.6:
        return "Tamil"
    elif s_pct > 0.15 and t_pct > 0.15 and l_pct > 0.15:
        return "Trilingual / Multilingual"
    elif s_pct > 0.2:
        return "Sinhala / Mixed"
    elif t_pct > 0.2:
        return "Tamil / Mixed"
    else:
        return "English / Mixed"

def analyze_pdf(filepath):
    rel_path = os.path.relpath(filepath, "/app") if filepath.startswith("/app") else filepath
    size_bytes = os.path.getsize(filepath)
    sha256 = compute_sha256(filepath)
    filename = os.path.basename(filepath)
    
    doc_info = {
        "filename": filename,
        "path": rel_path,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "page_count": 0,
        "metadata": {},
        "gazette_number": None,
        "gazette_date": None,
        "reg_title": None,
        "document_type": "Unknown",
        "language": "Unknown",
        "text_sample": "",
        "readable_text_length": 0
    }
    
    try:
        doc = fitz.open(filepath)
        doc_info["page_count"] = len(doc)
        doc_info["metadata"] = {k: v for k, v in doc.metadata.items() if v} if doc.metadata else {}
        
        extracted_text = ""
        for pno in range(min(3, len(doc))):
            extracted_text += doc[pno].get_text() + "\n"
        
        doc_info["readable_text_length"] = len(extracted_text.strip())
        doc_info["text_sample"] = extracted_text[:500].replace("\n", " ").strip()
        doc_info["language"] = detect_language(extracted_text)
        
        # Determine Gazette details
        text_lower = extracted_text.lower()
        
        # Check Gazette Number patterns
        # Patterns like "No. 2494/48", "No. 2494/06", "No. 2443/27", "No. 2,494", "No. 1688/28", "2494-06"
        gaz_match = re.search(r'(?:no\.?|අංක|இலக்கம்)\s*[:.-]?\s*([0-9]+[0-9,/]*[-/][0-9]+|[0-9,]{4,5})', extracted_text, re.IGNORECASE)
        if gaz_match:
            doc_info["gazette_number"] = gaz_match.group(1).replace(",", "").strip()
        elif "2494-06" in filename or "2494/06" in filename:
            doc_info["gazette_number"] = "2494/06"
        elif "2494-47" in filename or "2494/47" in filename:
            doc_info["gazette_number"] = "2494/47"
        elif "2443-27" in filename or "2443/27" in filename:
            doc_info["gazette_number"] = "2443/27"
        elif "2496-03" in filename or "2496/03" in filename:
            doc_info["gazette_number"] = "2496/03"
        elif "1688-28" in filename or "1688/28" in filename:
            doc_info["gazette_number"] = "1688/28"
            
        # Check Date patterns
        date_match = re.search(r'([0-9]{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+[0-9]{4}|(?:[0-9]{4}[./-][0-9]{2}[./-][0-9]{2}))', extracted_text, re.IGNORECASE)
        if date_match:
            doc_info["gazette_date"] = date_match.group(1).strip()
            
        # Check Titles
        if "iodization of salt" in text_lower or "iodized salt" in text_lower or "2494/48" in str(doc_info["gazette_number"]):
            doc_info["reg_title"] = "Food (Iodization of Salt) Regulations 2026"
        elif "labelling and advertising" in text_lower or "food (labelling" in text_lower:
            doc_info["reg_title"] = "Food (Labelling and Advertising) Regulations 2026"
        elif "colouring substances" in text_lower:
            doc_info["reg_title"] = "Food (Colouring Substances) (Amendment) Regulations 2026"
        elif "flavouring substances" in text_lower or "flavour enhancers" in text_lower:
            doc_info["reg_title"] = "Food (Flavouring Substances & Flavour Enhancers) Regulations 2026"
        elif "preservative" in text_lower:
            doc_info["reg_title"] = "Food (Preservatives) Regulations"
        elif "cold storage" in text_lower:
            doc_info["reg_title"] = "Cold Storage Test Regulations"
        elif "regimpact final plan" in filename.lower():
            doc_info["reg_title"] = "RegImpact Project Proposal / Implementation Plan"
        elif "lec 03" in filename.lower():
            doc_info["reg_title"] = "University Lecture Slides (Lec 03)"
            
        # Determine document type
        if "gazette" in text_lower or "extraordinary" in text_lower or "democratic socialist republic" in text_lower:
            doc_info["document_type"] = "Official Sri Lankan Gazette"
        elif "regulations" in text_lower or "ministry of health" in text_lower:
            doc_info["document_type"] = "Regulatory Document / Regulations"
        elif "plan" in filename.lower() or "proposal" in filename.lower():
            doc_info["document_type"] = "Project Specification / Plan"
        elif "lec" in filename.lower() or "slide" in text_lower:
            doc_info["document_type"] = "Lecture Presentation / Slides"
        elif "test" in filename.lower():
            doc_info["document_type"] = "Test Fixture / E2E Artifact"
        else:
            doc_info["document_type"] = "Regulatory or Administrative Document"
            
        doc.close()
    except Exception as e:
        doc_info["document_type"] = f"Error reading PDF: {str(e)}"
        
    return doc_info

def main():
    print("Searching for PDF files in workspace...")
    search_dirs = [
        "/app/backend/data/raw_sources",
        "/app/backend/data/quarantine",
        "/app/backend/data/derived",
        "/app",
    ]
    
    found_files = []
    for sdir in search_dirs:
        if os.path.exists(sdir):
            pdfs = glob.glob(os.path.join(sdir, "*.pdf"))
            for p in pdfs:
                if p not in found_files:
                    found_files.append(p)
                    
    print(f"Total PDF files found across all inspected directories: {len(found_files)}")
    
    inventory = []
    for fp in sorted(found_files):
        info = analyze_pdf(fp)
        inventory.append(info)
        
    # Query database records
    db_records = []
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT s.id, s.title, s.authority, s.sha256_hash, s.file_path, s.file_size_bytes, 
                       s.page_count, s.extraction_status, s.extraction_tool,
                       COUNT(c.id) as clause_count
                FROM source_documents s
                LEFT JOIN clauses c ON s.id = c.document_id
                GROUP BY s.id, s.title, s.authority, s.sha256_hash, s.file_path, s.file_size_bytes, 
                         s.page_count, s.extraction_status, s.extraction_tool
                ORDER BY s.id;
            """)).fetchall()
            for r in rows:
                db_records.append({
                    "id": r[0],
                    "title": r[1],
                    "authority": r[2],
                    "sha256": r[3],
                    "file_path": r[4],
                    "size_bytes": r[5],
                    "page_count": r[6],
                    "extraction_status": r[7],
                    "extraction_tool": r[8],
                    "clause_count": r[9]
                })
        print(f"Found {len(db_records)} source_documents in database.")
    except Exception as e:
        print(f"Error querying database: {e}")

    output_data = {
        "inspected_directories": search_dirs,
        "total_pdf_count": len(inventory),
        "inventory": inventory,
        "database_records": db_records
    }
    
    with open("/app/scratch/inventory_output.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print("Inventory saved to /app/scratch/inventory_output.json.")

if __name__ == "__main__":
    main()

