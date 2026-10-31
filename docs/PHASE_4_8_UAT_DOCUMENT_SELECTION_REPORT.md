# RegImpact-SL — Phase 4.8: UAT Document Selection & Verification Report

**Date:** 2026-10-31  
**Auditor Roles:** Senior QA Engineer, Regulatory Document Verification Auditor, and UAT Coordinator  
**Project:** RegImpact-SL  
**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md`  
**Reference Document:** `docs/FINAL_END_TO_END_UAT_REPORT.md`  
**Evaluation Target:** Newly placed candidate document identified as Gazette No. 2494  
**Final Verdict:** **NOT SUITABLE (DEMONSTRABLY INVALID DOCUMENT)**

---

## 1. Executive Summary & Verdict

In response to the UAT unblocking requirement, the candidate PDF placed on the local system was located, interrogated with binary and text layout parsers, and evaluated against the database corpus and regulatory criteria.

### Final Verdict: **NOT SUITABLE**
The placed PDF file (`sri-lanka-government-gazette-19-06-2026-no-2494-6a3cf85f7348c.pdf`) is **demonstrably invalid** for the RegImpact-SL UAT:
1. **Wrong Document Identity:** The file is **Sri Lanka Weekly Gazette No. 2,494** published on **Friday, June 19, 2026**, covering **Part I : Section (IIA) – Advertising (Public Service Recruitment & Examinations)**. It is **NOT** Extraordinary Gazette No. 2494/48, is **NOT** dated 26 June 2026, and does **NOT** contain the *"Food (Iodization of Salt) Regulations 2026"*.
2. **Zero Regulatory Content:** Across all 102 pages, there are **no statutory provisions, no product standards, no chemical/biological thresholds (e.g. iodine ppm), and no regulatory obligations/prohibitions** under the Food Act No. 26 of 1980 or any other regulatory enactment. The entire document consists of civil service job vacancy notices (Registrar of Births, Deaths & Marriages), application forms, and examination candidate instructions.
3. **Severe Ingestion Hazard:** Ingesting a 102-page non-statutory advertising gazette into the RegImpact-SL pipeline would violate the core architectural premise of the platform, overwhelm the clause segmentation and LLM rule compilation pipeline with non-regulatory civil service notices, and fail to produce verifiable Kleene AST rules.

---

## 2. Phase 1 — Locate and Identify the PDF

An automated filesystem discovery was executed across candidate local directories:
- `backend/data/raw_sources`
- `C:\Users\HP\Downloads`
- `C:\Users\HP\Desktop`

### 2.1 File Identification & Provenance
- **Exact Filename:** `sri-lanka-government-gazette-19-06-2026-no-2494-6a3cf85f7348c.pdf`
- **Absolute Local Path:** `C:\Users\HP\Downloads\sri-lanka-government-gazette-19-06-2026-no-2494-6a3cf85f7348c.pdf`
- **File Placement Timestamp:** 2026-10-31 22:40:44 (local time)
- **File Size:** `1,430,406 bytes` (1.36 MB)
- **Cryptographic Hash (SHA-256):**  
  `4f21b6f970b344042aa2c9176714846e6ab270ed0996f0238b8e09e31bae421a`
- **Total Page Count:** **102 pages**
- **Readability:** Verified readable using PyMuPDF (`pymupdf 1.25.x`). Text layer is fully native and extractable.

### 2.2 Embedded PDF Metadata
- **Format:** PDF 1.4
- **Title:** *(Empty string)*
- **Author:** *(Empty string)*
- **Subject:** *(Empty string)*
- **Creator Tool:** `Adobe InDesign 19.4 (Windows)`
- **PDF Producer:** `Adobe PDF Library 17.0`
- **Creation Date:** `D:20260625135641+05'30'` (2026-06-25 13:56:41)
- **Modification Date:** `D:20260625135646+05'30'`

### 2.3 Statutory Identity Confirmed from Document Contents

Direct inspection of the extracted text from Page 1, Page 2, and subsequent pages confirms:

```text
================================================================================
The Gazette of the Democratic Socialist Republic of Sri Lanka
(Published by Authority)
PART I : SECTION (IIA) – ADVERTISING
(Separate paging is given to each language of every Part in order that it may be filed separately)

Page                                                         Page
Examinations, Results of Examinations &c.  … -   Post - Vacant  … … … -

No. 2,494 – FRIDAY, JUNE, 19, 2026
IMPORTANT NOTICE REGARDING ACCEPTANCE OF NOTICES FOR PUBLICATION IN THE WEEKLY "GAZETTE"
================================================================================
```

- **Confirmed Gazette Type:** Regular Weekly Gazette (Part I : Section IIA).
- **Confirmed Gazette Number:** **2,494** (Regular edition, NOT Extraordinary sub-number 2494/48).
- **Confirmed Publication Date:** **Friday, 19 June 2026** (NOT 26 June 2026).
- **Confirmed Title / Subject:** Public Service Recruitment Examinations, Posts Vacant in the Registrar General's Department, and General Application Conditions.

---

## 3. Phase 2 — Duplicate and Novelty Verification

The live PostgreSQL database (`regimpact`) was queried to check for prior ingestion or representation of this document:

### 3.1 Database Check (`source_documents`)
- **Query 1: By SHA-256 Hash (`4f21b6f9...`):**
  ```sql
  SELECT id, title, gazette_no FROM source_documents 
  WHERE sha256_hash = '4f21b6f970b344042aa2c9176714846e6ab270ed0996f0238b8e09e31bae421a';
  ```
  *Result:* **0 rows returned** (Hash does not exist in the database).

- **Query 2: By Gazette Number (`2494/48`):**
  ```sql
  SELECT id, title, gazette_no FROM source_documents WHERE gazette_no LIKE '%2494/48%';
  ```
  *Result:* **0 rows returned** (No document with gazette number 2494/48 exists in the database).

- **Query 3: All 2494 Series Gazettes Currently Represented:**
  ```sql
  SELECT id, gazette_no, substring(sha256_hash from 1 for 16) as hash, title 
  FROM source_documents WHERE gazette_no LIKE '%2494%' OR title LIKE '%2494%';
  ```
  *Result:* Exactly 2 documents exist from the 2494 series:
  1. `doc_gazette_2494_47` — Gazette Extraordinary No. 2494/47 (*Food Labelling and Advertising Regulations 2026*, 25 pages, SHA: `83ed19c2...`)
  2. `doc_15803fe0b14...` — Gazette Extraordinary No. 2494/06 (*Food Colour Coding for Sugar Levels Amendment*, 3 pages, SHA: `15803fe0...`)

### 3.2 Novelty Assessment
The placed file is mathematically novel (its SHA-256 hash is unrepresented in PostgreSQL). However, this novelty is solely attributable to the fact that it is a **weekly recruitment notice gazette**, completely distinct from the required statutory instrument.

---

## 4. Phase 3 — Authenticity and Regulatory Suitability Analysis

The document contents were scrutinized across all 102 pages against the requirements of the RegImpact-SL regulatory compiler:

| RegImpact-SL Criterion | Required Characteristic | Placed Document Content | Finding |
|:---|:---|:---|:---:|
| **Instrument Type** | Statutory Regulation, Order, or Rule enacted under primary legislation (e.g. Food Act No. 26 of 1980) | Weekly Government Advertising Gazette (Part I: Sec IIA) | **FAIL** |
| **Numbered Regulations** | Sequenced legal clauses (e.g. `Regulation 1`, `Regulation 2`, `(1)`, `(2)(a)`) | Examination notices and job application numbering (`1. General Qualifications`, `02. Address`) | **FAIL** |
| **Obligations & Prohibitions** | Mandatory statutory commands (`shall not manufacture`, `shall label`, `shall contain`) | Procedural candidate notices (`Applications should be forwarded on or before 20th July, 2026`) | **FAIL** |
| **Defined Legal Terms** | Statutory definitions (e.g. `"food grade salt"`, `"iodine"`, `"package"`) | Civil service terms (`"Sri Lankan citizen"`, `"Registrar General"`, `"Public Service"`) | **FAIL** |
| **Thresholds & Standards** | Chemical, compositional, or physical limits (e.g. `min 15 ppm`, `max 30 ppm`) | Zero product or chemical thresholds. Contains only salary scales and exam center numbers. | **FAIL** |
| **Effective Dates** | Statutory commencement date (`"These regulations shall come into operation on..."`) | Job application deadline (`"on or before 20th July, 2026"`) | **FAIL** |
| **Schedules & Tables** | Regulatory limit tables, labelling formats, or specification schedules | Recruitment vacancy schedules (District, Division, Language Medium) | **FAIL** |

### Exhaustive Keyword Scan of All 102 Pages
An automated script scanned every page of the document for regulatory indicators:
- `"iodiz"` / `"iodine"` / `"iodization"`: **0 occurrences**
- `"salt"`: **1 occurrence** (Page 95, incidental in candidate instructions)
- `"food act"`: **0 occurrences**
- `"2494/48"`: **0 occurrences**
- `"food (iodization of salt)"`: **0 occurrences**

---

## 5. Phase 4 — UAT Suitability Decision

### Verdict: **NOT SUITABLE**

### Supporting Technical & Audit Evidence:
1. **Discrepancy with Candidate Specification:**
   - Specified: *Gazette Extraordinary No. 2494/48, Food (Iodization of Salt) Regulations 2026, 26 June 2026*.
   - Located: *Gazette No. 2,494 (Regular Weekly), Part I : Sec (IIA) Advertising, 19 June 2026*.
2. **Absence of Statutory Provisions:**
   The document contains zero provisions amenable to rule compilation. Feeding 102 pages of job vacancies to `POST /admin/documents/upload` would result in:
   - Segmentation creating hundreds of meaningless candidate clauses from job descriptions.
   - LLM compiler hallucinations or ungrounded rule rejections.
   - Invalidation of the acceptance criteria requiring genuine regulatory evidence grounding.
3. **Demonstrably Invalid under User Exception Clause:**
   The user's prompt explicitly stated:
   > *"Do not download another copy unless the existing file is missing or demonstrably invalid."*  
   The existing file is **demonstrably invalid**.

---

## 6. Official Source Verification & Recommended Resolution

### 6.1 Department of Government Printing Investigation
The official archive of Extraordinary Gazettes for 2026 (`https://www.documents.gov.lk/view/egz/egz_2026.html`) lists Extraordinary Gazettes separately from the Weekly Gazettes:
- **Weekly Gazettes:** Numbered sequentially without slashes (`No. 2494` published 19.06.2026, `No. 2495` published 26.06.2026).
- **Extraordinary Gazettes:** Bear slash suffixes designating extraordinary sub-issues (e.g. `2494/06` published 22.06.2026, `2494/47` published 26.06.2026).

The file downloaded was the **Weekly Gazette 2494**, rather than an Extraordinary Gazette sub-issue.

### 6.2 Recommended Next Action for Product Owner
To proceed with the final end-to-end UAT:
1. Obtain the genuine **Gazette Extraordinary No. 2494/48** (or any genuine unrepresented Extraordinary Gazette containing statutory food, health, or environmental regulations) directly from the Extraordinary Gazettes section of `documents.gov.lk` or the Food Control Administration Unit (FCAU).
2. Save the authentic PDF into:  
   [`backend/data/raw_sources/`](file:///C:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/raw_sources/)
3. Once placed, the Senior QA Engineer will verify the new file and immediately proceed to execute the end-to-end UAT upload, Gemini compilation, and AST execution test.

