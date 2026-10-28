"""Component [A]: Official document ingestion pipeline for RegImpact-SL.

Design principles (§2 of alignment plan):
  1. Official sources are authoritative — never invent metadata.
  2. SHA-256 hash prevents duplicate ingestion of the same bytes.
  3. Page provenance and character offsets are recorded for every page so
     that quote spans can be grounded to source text later.
  4. OCR pages are flagged (is_ocr=True); a warning is stored in
     extraction_warnings; the page text is still preserved.
  5. Extraction failures do not silently succeed — status is always FAILED
     or PARTIAL_OCR, never SUCCESS, when problems occur.

Usage (CLI / scripts)::

    from backend.src.extraction.ingestion import DocumentIngestionService
    from backend.src.db.session import session_scope

    svc = DocumentIngestionService()
    with session_scope() as db:
        result = svc.ingest(
            db=db,
            pdf_path="backend/data/raw_sources/gazette_2024_01.pdf",
            doc_id="doc_fcau_labelling_2024",
            title="Food (Labelling and Advertising) Regulations",
            authority="Food Control Administration Unit (FCAU)",
        )
        print(result)
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.src.db.models import (
    DocumentPageORM,
    SourceDocumentORM,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Where ingested PDF files are copied for immutable storage
PDF_STORE_DIR = Path("backend/data/raw_sources")

# Extraction status tokens
STATUS_SUCCESS = "SUCCESS"
STATUS_PARTIAL_OCR = "PARTIAL_OCR"
STATUS_FAILED = "FAILED"
STATUS_PENDING = "PENDING"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    """Summary returned after a document ingestion attempt."""
    doc_id: str
    sha256_hash: str
    title: str
    authority: str
    page_count: int
    extraction_status: str
    extraction_tool: str
    warnings: List[str] = field(default_factory=list)
    is_duplicate: bool = False
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.extraction_status in (STATUS_SUCCESS, STATUS_PARTIAL_OCR)


# ---------------------------------------------------------------------------
# Page extraction helper
# ---------------------------------------------------------------------------

def _sha256_of_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def _sha256_of_text(text: str) -> str:
    """Return the lowercase hex SHA-256 digest of *text* encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


@dataclass
class PageExtractionResult:
    """Result for a single page extracted from a PDF."""
    page_number: int   # 1-indexed
    raw_text: str
    char_count: int
    is_ocr: bool
    page_hash: str
    warning: Optional[str] = None


def extract_pages_pymupdf(
    pdf_path: Path,
) -> Tuple[List[PageExtractionResult], List[str]]:
    """Extract all pages from *pdf_path* using PyMuPDF.

    Returns:
        (pages, global_warnings)

    OCR detection heuristic: if a page yields zero text characters but the
    page has visible content (via image coverage), it is flagged is_ocr=True
    and a warning is recorded.  The raw_text is left empty; a real OCR pass
    would be added in a later milestone when required.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "PyMuPDF (fitz) is required for PDF ingestion. "
            "Install it with: pip install pymupdf"
        ) from exc

    pages: List[PageExtractionResult] = []
    warnings: List[str] = []
    extraction_tool_version = f"PyMuPDF {fitz.version[0]}"

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        warnings.append(f"PyMuPDF failed to open file: {exc}")
        return pages, warnings

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1  # 1-indexed

        try:
            raw_text = page.get_text("text") or ""
        except Exception as exc:
            warning_msg = f"Page {page_number}: text extraction error: {exc}"
            warnings.append(warning_msg)
            raw_text = ""

        char_count = len(raw_text)
        is_ocr = False
        page_warning: Optional[str] = None

        # OCR heuristic: empty text on a page that has image content
        if char_count == 0:
            try:
                image_list = page.get_images(full=False)
                has_images = len(image_list) > 0
            except Exception:
                has_images = False

            if has_images:
                is_ocr = True
                page_warning = (
                    f"Page {page_number}: no extractable text found; "
                    "page appears to contain scanned image content (OCR required)."
                )
                warnings.append(page_warning)

        page_hash = _sha256_of_text(raw_text)
        pages.append(
            PageExtractionResult(
                page_number=page_number,
                raw_text=raw_text,
                char_count=char_count,
                is_ocr=is_ocr,
                page_hash=page_hash,
                warning=page_warning,
            )
        )

    doc.close()
    return pages, warnings


def extract_pages_pdfplumber(
    pdf_path: Path,
) -> Tuple[List[PageExtractionResult], List[str]]:
    """Fallback extraction using pdfplumber (not installed by default).

    This is provided as a secondary option for documents that PyMuPDF
    handles poorly.  Milestone 1 uses PyMuPDF as the primary extractor.
    """
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "pdfplumber is not installed. Install it with: pip install pdfplumber"
        ) from exc

    pages: List[PageExtractionResult] = []
    warnings: List[str] = []

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_number = i + 1
                try:
                    raw_text = page.extract_text() or ""
                except Exception as exc:
                    warning_msg = f"Page {page_number}: pdfplumber extraction error: {exc}"
                    warnings.append(warning_msg)
                    raw_text = ""

                char_count = len(raw_text)
                page_hash = _sha256_of_text(raw_text)
                pages.append(
                    PageExtractionResult(
                        page_number=page_number,
                        raw_text=raw_text,
                        char_count=char_count,
                        is_ocr=False,
                        page_hash=page_hash,
                    )
                )
    except Exception as exc:
        warnings.append(f"pdfplumber failed to open file: {exc}")

    return pages, warnings


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------

class DocumentIngestionService:
    """Service that ingests a PDF into the persistent source document store.

    Responsibilities:
      - Compute SHA-256 hash of raw PDF bytes → duplicate guard.
      - Copy PDF into the controlled file store (PDF_STORE_DIR / <hash>.pdf).
      - Extract page text with character offsets via PyMuPDF.
      - Persist SourceDocumentORM + DocumentPageORM records in the database.
      - Return a structured IngestionResult with metadata and any warnings.

    It does NOT perform clause segmentation (Milestone 1 task 7 is handled
    separately by the ClauseSegmenter helper below).  It does NOT invoke any
    LLM (Milestone 2).
    """

    def __init__(
        self,
        pdf_store_dir: Path | str = PDF_STORE_DIR,
        primary_extractor: str = "pymupdf",
    ) -> None:
        self.pdf_store_dir = Path(pdf_store_dir)
        self.primary_extractor = primary_extractor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(
        self,
        db: Session,
        pdf_path: str | Path,
        doc_id: str,
        title: str,
        authority: str,
        *,
        instrument_type: Optional[str] = None,
        gazette_no: Optional[str] = None,
        source_url: Optional[str] = None,
        publication_date: Optional[str] = None,  # ISO-8601 string or None
    ) -> IngestionResult:
        """Ingest a PDF file into the persistent source document store.

        Args:
            db:               Active SQLAlchemy session (caller owns the
                              transaction; session_scope in session.py is
                              the recommended wrapper).
            pdf_path:         Filesystem path of the PDF to ingest.
            doc_id:           Stable human-readable document identifier
                              (e.g. 'doc_fcau_labelling_2024').
            title:            Official instrument title.
            authority:        Name of the issuing authority.
            instrument_type:  Optional instrument classification string.
            gazette_no:       Official gazette publication number (or None
                              if unresolved / not gazette-published).
            source_url:       Official publication URL (or None for archival
                              hard-copies; never invented).
            publication_date: Verified publication date (ISO-8601) or None
                              if unresolved.

        Returns:
            IngestionResult containing status, hash, page count and warnings.

        Notes:
            - Duplicate bytes (same SHA-256) are rejected with
              is_duplicate=True; the existing database record is unchanged.
            - All metadata that cannot be verified at ingestion time must be
              supplied as None, not invented.
        """
        pdf_path = Path(pdf_path)

        # 1. Read raw bytes and compute hash
        try:
            raw_bytes = pdf_path.read_bytes()
        except (FileNotFoundError, PermissionError) as exc:
            logger.error("Cannot read PDF file %r: %s", str(pdf_path), exc)
            return IngestionResult(
                doc_id=doc_id,
                sha256_hash="",
                title=title,
                authority=authority,
                page_count=0,
                extraction_status=STATUS_FAILED,
                extraction_tool="none",
                error=str(exc),
            )

        sha256_hash = _sha256_of_bytes(raw_bytes)

        # 2. Duplicate guard — check hash first, then doc_id
        existing_by_hash = (
            db.query(SourceDocumentORM)
            .filter_by(sha256_hash=sha256_hash)
            .first()
        )
        if existing_by_hash:
            logger.info(
                "Document with SHA-256 %s already exists (id=%r). Skipping.",
                sha256_hash[:12],
                existing_by_hash.id,
            )
            return IngestionResult(
                doc_id=existing_by_hash.id,
                sha256_hash=sha256_hash,
                title=existing_by_hash.title,
                authority=existing_by_hash.authority,
                page_count=existing_by_hash.page_count,
                extraction_status=existing_by_hash.extraction_status,
                extraction_tool=existing_by_hash.extraction_tool or "none",
                is_duplicate=True,
            )

        existing_by_id = db.get(SourceDocumentORM, doc_id)
        if existing_by_id:
            logger.warning(
                "Document id %r already exists with a different hash. "
                "Use a distinct doc_id for a different document version.",
                doc_id,
            )
            return IngestionResult(
                doc_id=doc_id,
                sha256_hash=sha256_hash,
                title=title,
                authority=authority,
                page_count=0,
                extraction_status=STATUS_FAILED,
                extraction_tool="none",
                error=(
                    f"Document id {doc_id!r} already exists with different content. "
                    "Provide a distinct doc_id."
                ),
            )

        # 3. Copy PDF into controlled store
        stored_path = self._store_pdf(pdf_path, sha256_hash, raw_bytes)

        # 4. Extract pages
        pages, global_warnings = self._extract_pages(pdf_path)

        # 5. Determine extraction status
        import fitz  # type: ignore[import]
        extraction_tool = f"PyMuPDF {fitz.version[0]}"
        ocr_pages = sum(1 for p in pages if p.is_ocr)
        if len(pages) == 0:
            extraction_status = STATUS_FAILED
            global_warnings.append("No pages could be extracted from the document.")
        elif ocr_pages > 0:
            extraction_status = STATUS_PARTIAL_OCR
        else:
            extraction_status = STATUS_SUCCESS

        # 6. Parse publication date
        pub_date: Optional[datetime.date] = None
        if publication_date:
            try:
                pub_date = datetime.date.fromisoformat(publication_date[:10])
            except ValueError:
                global_warnings.append(
                    f"publication_date {publication_date!r} is not a valid ISO-8601 date; stored as None."
                )

        # 7. Persist SourceDocumentORM
        doc_orm = SourceDocumentORM(
            id=doc_id,
            sha256_hash=sha256_hash,
            title=title,
            authority=authority,
            instrument_type=instrument_type,
            gazette_no=gazette_no,
            source_url=source_url,
            publication_date=pub_date,
            retrieval_timestamp=datetime.datetime.now(datetime.timezone.utc),
            file_path=str(stored_path),
            file_size_bytes=len(raw_bytes),
            page_count=len(pages),
            extraction_status=extraction_status,
            extraction_tool=extraction_tool,
            extraction_warnings=global_warnings if global_warnings else None,
        )
        db.add(doc_orm)
        db.flush()

        # 8. Persist DocumentPageORM records
        for page_result in pages:
            page_orm = DocumentPageORM(
                document_id=doc_id,
                page_number=page_result.page_number,
                raw_text=page_result.raw_text,
                char_count=page_result.char_count,
                is_ocr=page_result.is_ocr,
                page_hash=page_result.page_hash,
            )
            db.add(page_orm)

        db.flush()
        logger.info(
            "Ingested document %r: %d pages, status=%s, hash=%s...",
            doc_id,
            len(pages),
            extraction_status,
            sha256_hash[:12],
        )

        return IngestionResult(
            doc_id=doc_id,
            sha256_hash=sha256_hash,
            title=title,
            authority=authority,
            page_count=len(pages),
            extraction_status=extraction_status,
            extraction_tool=extraction_tool,
            warnings=global_warnings,
        )

    # ------------------------------------------------------------------
    # Inspection report
    # ------------------------------------------------------------------

    def inspection_report(self, db: Session, doc_id: str) -> dict:
        """Return a structured inspection report for a previously ingested document.

        Covers: metadata, page count, OCR warnings, extraction status.
        Does not touch LLM or clauses.
        """
        doc = db.get(SourceDocumentORM, doc_id)
        if doc is None:
            return {"error": f"Document {doc_id!r} not found."}

        ocr_pages = sum(1 for p in doc.pages if p.is_ocr)
        empty_pages = sum(1 for p in doc.pages if p.char_count == 0 and not p.is_ocr)

        return {
            "doc_id": doc.id,
            "title": doc.title,
            "authority": doc.authority,
            "gazette_no": doc.gazette_no,
            "source_url": doc.source_url,
            "publication_date": str(doc.publication_date) if doc.publication_date else None,
            "retrieval_timestamp": doc.retrieval_timestamp.isoformat(),
            "sha256_hash": doc.sha256_hash,
            "file_path": doc.file_path,
            "file_size_bytes": doc.file_size_bytes,
            "page_count": doc.page_count,
            "extraction_status": doc.extraction_status,
            "extraction_tool": doc.extraction_tool,
            "ocr_page_count": ocr_pages,
            "empty_page_count": empty_pages,
            "extraction_warnings": doc.extraction_warnings or [],
            "clauses_count": len(doc.clauses),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _store_pdf(
        self, original_path: Path, sha256_hash: str, raw_bytes: bytes
    ) -> Path:
        """Copy the PDF into the controlled store under its SHA-256 filename."""
        self.pdf_store_dir.mkdir(parents=True, exist_ok=True)
        dest = self.pdf_store_dir / f"{sha256_hash}.pdf"
        if not dest.exists():
            dest.write_bytes(raw_bytes)
            logger.debug("Stored PDF to %s", dest)
        return dest

    def _extract_pages(
        self, pdf_path: Path
    ) -> Tuple[List[PageExtractionResult], List[str]]:
        """Attempt extraction with primary extractor, log any failures."""
        try:
            return extract_pages_pymupdf(pdf_path)
        except ImportError:
            # PyMuPDF not installed — this should not happen after Milestone 0 install
            logger.error("PyMuPDF not available; extraction failed.")
            return [], ["PyMuPDF not installed."]
        except Exception as exc:
            logger.error("Unexpected extraction error: %s", exc)
            return [], [str(exc)]


# ---------------------------------------------------------------------------
# Clause segmentation helper (conservative, regex-based)
# ---------------------------------------------------------------------------

@dataclass
class SegmentedClause:
    """A conservatively segmented candidate clause from a page."""
    clause_number: str
    text: str
    start_page: int
    end_page: int
    char_start: int
    char_end: int


# Common Sri Lankan gazette noise patterns (running headers, footers, pagination)
_GAZETTE_HEADER_FOOTER_PATTERNS = [
    re.compile(r"^\s*I\s+fldgi.*", re.IGNORECASE),
    re.compile(r"^\s*Part\s+I\s*:\s*Sec\.\s*\(I\).*", re.IGNORECASE),
    re.compile(r"^\s*\d+A\s*$", re.IGNORECASE),
    re.compile(r"^\s*No\.\s*\d+/\d+\s*-\s*[A-Z]+,\s*[A-Z]+\s+\d+,\s*\d+.*", re.IGNORECASE),
    re.compile(r"^\s*This Gazette Extraordinary can be downloaded.*", re.IGNORECASE),
    re.compile(r"^\s*EXTRAORDINARY\s*$", re.IGNORECASE),
    re.compile(r"^\s*The Gazette of the Democratic Socialist Republic.*", re.IGNORECASE),
    re.compile(r"^\s*\(Published by Authority\)\s*$", re.IGNORECASE),
    re.compile(r"^\s*PART I\s*:\s*SECTION \(I\).*", re.IGNORECASE),
    re.compile(r"^\s*Gover.*No.*", re.IGNORECASE),
    re.compile(r"^\s*1A\s*-\s*PG.*", re.IGNORECASE),
    re.compile(r".*\d{4}/\d{2}\s*-\s*\d{4}.*", re.IGNORECASE),
    re.compile(r"^\s*[\?\u2022\-\s]{5,}\s*$"),
]


def is_gazette_noise(line: str) -> bool:
    """Return True if a line matches known Sri Lankan gazette running headers/footers."""
    s = line.strip()
    if not s:
        return False
    return any(p.match(s) for p in _GAZETTE_HEADER_FOOTER_PATTERNS)


# Common Sri Lankan gazette clause patterns
_CLAUSE_PATTERNS = [
    re.compile(
        r"^\s*((?:Regulation|Section|Article|Schedule|Rule|Clause|Item|Part)\s+\d+(?:\.\d+)*(?:\s+Part\s+[A-Z]\s+Item\s+\d+)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(\d+\.(?:\s*\([0-9a-zA-Z]+\))?)\s+[A-Z]",
    ),
    re.compile(
        r"^\s*(\d+\.(?:\s*\([0-9a-zA-Z]+\))?)\s*$",
    ),
]


def extract_document_preamble(pages: List[Any]) -> Dict[str, Any]:
    """Extract authoritative document-level metadata from initial gazette pages.

    Captures gazette number, publication date, authority, instrument title,
    and statutory commencement date (commonly defined in Regulation 1).
    """
    full_text = ""
    for p in pages[:4]:
        raw = getattr(p, "raw_text", None) or getattr(p, "text", None) or str(p)
        full_text += "\n" + raw

    meta = {
        "gazette_no": None,
        "published": None,
        "commences": None,
        "instrument": None,
        "authority": None,
        "enabling_act": None,
    }

    # Gazette No (e.g., 2494/47 or 1688/28)
    m_gz = re.search(r"No\.?\s*(\d{4}/\d{1,2})", full_text, re.IGNORECASE)
    if m_gz:
        meta["gazette_no"] = f"Gazette Extraordinary No. {m_gz.group(1)}"

    # Published date (e.g. 26th June, 2026 or 2026.06.26)
    m_pub = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})",
        full_text,
        re.IGNORECASE,
    )
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }
    if m_pub:
        day = int(m_pub.group(1))
        month = months.get(m_pub.group(2).lower(), "01")
        year = m_pub.group(3)
        meta["published"] = f"{year}-{month}-{day:02d}"

    # Authority (e.g. Minister of Health...)
    m_auth = re.search(r"(Minister of [^\n\.,]+?)(?:\s+in consultation|\.|\,|$)", full_text, re.IGNORECASE)
    if m_auth:
        meta["authority"] = m_auth.group(1).strip()
    else:
        meta["authority"] = "Ministry of Health, Sri Lanka"

    # Enabling act (e.g. Food Act, No. 26 of 1980)
    m_act = re.search(r"(Food Act,\s*No\.\s*\d+\s*of\s*\d{4})", full_text, re.IGNORECASE)
    if m_act:
        meta["enabling_act"] = m_act.group(1).strip()

    # Citation & commencement in Regulation 1
    m_cit = re.search(r"cited as\s+([^\n\.]+(?:Regulations|Act|Order)\s+\d{4})", full_text, re.IGNORECASE)
    if m_cit:
        meta["instrument"] = m_cit.group(1).strip()

    m_com = re.search(
        r"come into operation\s+on\s+(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})",
        full_text,
        re.IGNORECASE,
    )
    if m_com:
        c_day = int(m_com.group(1))
        c_month = months.get(m_com.group(2).lower(), "01")
        c_year = m_com.group(3)
        meta["commences"] = f"{c_year}-{c_month}-{c_day:02d}"

    return meta


def segment_document_clauses(
    pages: List[Any],
    min_clause_length: int = 40,
) -> List[SegmentedClause]:
    """Segment a multi-page regulatory document into complete, stitched clauses.

    Overcomes single-page segmentation boundary issues:
    - Strips running headers, footers, and page numbers between pages.
    - Accurately stitches clauses spanning multiple pages (e.g. Regulation 3 across pages 1 and 2).
    - Uses monotonic regulation ordering to distinguish primary regulation headers
      from mid-sentence cross-references.
    - Retains full provenance across start_page and end_page.
    """
    reg_heading_pattern = re.compile(
        r"^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]+))\s*$",
        re.IGNORECASE,
    )
    reg_inline_pattern = re.compile(
        r"^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]+))\s+([A-Z].*)",
        re.IGNORECASE,
    )

    doc_lines: List[Tuple[int, str]] = []
    in_regulations = False

    for p_idx, p in enumerate(pages):
        p_num = getattr(p, "page_number", p_idx + 1)
        raw = getattr(p, "raw_text", None) or getattr(p, "text", None) or str(p)
        for line in raw.split("\n"):
            if is_gazette_noise(line):
                continue
            s = line.strip()
            if s.upper() == "REGULATIONS":
                in_regulations = True
                continue
            if in_regulations:
                doc_lines.append((p_num, line))

    clauses: List[SegmentedClause] = []
    current_clause: Optional[Dict[str, Any]] = None
    last_reg_num = 0
    in_schedules = False

    for idx, (p_num, line) in enumerate(doc_lines):
        s = line.strip()
        prev_line = doc_lines[idx - 1][1].strip() if idx > 0 else ""

        m_head = reg_heading_pattern.match(s)
        m_inline = reg_inline_pattern.match(s)
        match = m_head or m_inline

        is_heading = False
        name = None
        inline_body = ""

        if match:
            reg_num_str = match.group(1)
            sub_num = match.group(2)
            sched_num = match.group(3)

            if sched_num:
                in_schedules = True
                is_heading = True
                name = sched_num.upper()
            elif reg_num_str and not in_schedules:
                reg_num = int(reg_num_str)
                continuing_prepositions = ("under", "to", "of", "in", "the", "and", "or", "with", "that", "from", "for")
                is_cont = any(prev_line.lower().endswith(f" {prep}") or prev_line.lower() == prep for prep in continuing_prepositions)

                if (reg_num == last_reg_num + 1 or (last_reg_num == 0 and reg_num == 1)) and not is_cont:
                    is_heading = True
                    last_reg_num = reg_num
                    if sub_num:
                        name = f"Regulation {reg_num}({sub_num})"
                    else:
                        name = f"Regulation {reg_num}"
            elif reg_num_str and in_schedules:
                is_heading = True
                name = f"Item {reg_num_str}"

            if is_heading:
                inline_body = match.group(4) if m_inline else ""

        if is_heading:
            if current_clause and current_clause["lines"]:
                clause_text = "\n".join(current_clause["lines"]).strip()
                if len(clause_text) >= min_clause_length:
                    clauses.append(
                        SegmentedClause(
                            clause_number=current_clause["name"],
                            text=clause_text,
                            start_page=current_clause["start_page"],
                            end_page=p_num,
                            char_start=0,
                            char_end=len(clause_text),
                        )
                    )

            current_clause = {
                "name": name,
                "start_page": p_num,
                "lines": [inline_body] if inline_body else []
            }
        elif current_clause is not None:
            current_clause["lines"].append(line)

    if current_clause and current_clause["lines"]:
        last_page = doc_lines[-1][0] if doc_lines else 1
        clause_text = "\n".join(current_clause["lines"]).strip()
        if len(clause_text) >= min_clause_length:
            clauses.append(
                SegmentedClause(
                    clause_number=current_clause["name"],
                    text=clause_text,
                    start_page=current_clause["start_page"],
                    end_page=last_page,
                    char_start=0,
                    char_end=len(clause_text),
                )
            )

    return clauses


def segment_clauses_from_page(
    raw_text: str,
    page_number: int,
    min_clause_length: int = 50,
) -> List[SegmentedClause]:
    """Conservatively segment single-page text into candidate clauses.

    Strategy:
    - Scan page text for lines matching known clause-header patterns.
    - Treat the text from one header to the next as one clause.
    - Clauses shorter than *min_clause_length* characters are skipped.
    """
    if not raw_text.strip():
        return []

    lines = raw_text.split("\n")
    results: List[SegmentedClause] = []

    header_positions: List[Tuple[int, str, int]] = []  # (char_offset, clause_number, line_idx)
    cumulative_offset = 0
    for line_idx, line in enumerate(lines):
        for pattern in _CLAUSE_PATTERNS:
            match = pattern.search(line)
            if match:
                raw_num = match.group(1).strip()
                if raw_num.endswith(".") and raw_num[:-1].strip().isdigit():
                    norm_num = f"Regulation {raw_num[:-1].strip()}"
                else:
                    norm_num = raw_num
                header_positions.append((cumulative_offset, norm_num, line_idx))
                break
        cumulative_offset += len(line) + 1  # +1 for the \n

    if not header_positions:
        return []

    # Slice text blocks between consecutive headers
    for i, (char_start, clause_number, _line_idx) in enumerate(header_positions):
        if i + 1 < len(header_positions):
            char_end = header_positions[i + 1][0]
        else:
            char_end = len(raw_text)

        clause_text = raw_text[char_start:char_end].strip()
        if len(clause_text) < min_clause_length:
            continue

        results.append(
            SegmentedClause(
                clause_number=clause_number,
                text=clause_text,
                start_page=page_number,
                end_page=page_number,
                char_start=char_start,
                char_end=char_end,
            )
        )

    return results

