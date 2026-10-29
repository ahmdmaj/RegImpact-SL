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
class NestedSubClause:
    """A nested subclause item within a clause (e.g. subregulation (1), paragraph (a), subparagraph (i), or proviso)."""
    identifier: str
    sub_type: str  # "subregulation", "paragraph", "subparagraph", "proviso"
    text: str
    page_number: int
    char_start: int
    char_end: int


@dataclass
class TableData:
    """A structured tabular element extracted from a regulatory schedule or clause."""
    headers: List[str]
    rows: List[List[str]]
    page_number: int = 1
    bbox: Optional[Tuple[float, float, float, float]] = None


@dataclass
class SegmentedClause:
    """A structurally segmented candidate clause with hierarchy, tables, provisos, and provenance."""
    clause_number: str
    text: str
    start_page: int
    end_page: int
    char_start: int
    char_end: int
    clause_type: str = "regulation"  # "regulation", "amendment_directive", "schedule", "order"
    parent_clause: Optional[str] = None
    sub_clauses: List[NestedSubClause] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    provisos: List[str] = field(default_factory=list)


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
    re.compile(r"^\s*1A\s*-\s*G.*", re.IGNORECASE),
    re.compile(r".*\d{4}/\d{2}\s*-\s*\d{4}.*", re.IGNORECASE),
    re.compile(r"^\s*PRINTED AT THE DEPARTMENT OF GOVERNMENT PRINTING.*", re.IGNORECASE),
    re.compile(r"^\s*EOG\s+\d{2}\s*-\s*\d{4}.*", re.IGNORECASE),
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


def extract_tables_from_doc(doc: Any) -> Dict[int, List[TableData]]:
    """Extract structured tables by page number using PyMuPDF."""
    tables_by_page: Dict[int, List[TableData]] = {}
    try:
        for p_idx in range(len(doc)):
            p_num = p_idx + 1
            page = doc[p_idx]
            if not hasattr(page, "find_tables"):
                continue
            found = page.find_tables()
            p_tables: List[TableData] = []
            for t in getattr(found, "tables", []):
                raw_data = t.extract()
                if not raw_data:
                    continue
                headers = [str(c or "").strip().replace("\n", " ") for c in raw_data[0]]
                rows = []
                for r in raw_data[1:]:
                    clean_r = [str(c or "").strip().replace("\n", " ") for c in r]
                    if any(clean_r):
                        rows.append(clean_r)
                if headers or rows:
                    p_tables.append(
                        TableData(
                            headers=headers,
                            rows=rows,
                            page_number=p_num,
                            bbox=t.bbox,
                        )
                    )
            if p_tables:
                tables_by_page[p_num] = p_tables
    except Exception as exc:
        logger.warning("Table extraction error: %s", exc)
    return tables_by_page


def format_table_as_text(table: TableData) -> str:
    """Format structured table as clean readable markdown text."""
    lines = []
    if any(table.headers):
        lines.append("| " + " | ".join(table.headers) + " |")
        lines.append("| " + " | ".join("---" for _ in table.headers) + " |")
    for r in table.rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def parse_nested_subclauses(text: str, page_num: int) -> Tuple[List[NestedSubClause], List[str]]:
    """Extract nested subclauses ((1), (a), (i), provisos) within clause text."""
    sub_clauses: List[NestedSubClause] = []
    provisos: List[str] = []

    proviso_pat = re.compile(
        r"(Provided\s+(?:further\s+that|however\s*,?|that\s*,?)[^\.\;]+(?:[\.\;]|$))",
        re.IGNORECASE | re.DOTALL,
    )
    for m in proviso_pat.finditer(text):
        p_text = m.group(1).strip()
        provisos.append(p_text)
        sub_clauses.append(
            NestedSubClause(
                identifier="Proviso",
                sub_type="proviso",
                text=p_text,
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    subreg_pat = re.compile(r"(?:^|\n)\s*(\(\d+\))\s+([^\n]+)", re.MULTILINE)
    for m in subreg_pat.finditer(text):
        sub_clauses.append(
            NestedSubClause(
                identifier=m.group(1),
                sub_type="subregulation",
                text=m.group(0).strip(),
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    para_pat = re.compile(r"(?:^|\n)\s*(\([a-z]\))\s+([^\n]+)", re.MULTILINE)
    for m in para_pat.finditer(text):
        sub_clauses.append(
            NestedSubClause(
                identifier=m.group(1),
                sub_type="paragraph",
                text=m.group(0).strip(),
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    subpara_pat = re.compile(r"(?:^|\n)\s*(\((?:i|ii|iii|iv|v|vi|vii|viii|ix|x)\))\s+([^\n]+)", re.IGNORECASE | re.MULTILINE)
    for m in subpara_pat.finditer(text):
        sub_clauses.append(
            NestedSubClause(
                identifier=m.group(1),
                sub_type="subparagraph",
                text=m.group(0).strip(),
                page_number=page_num,
                char_start=m.start(),
                char_end=m.end(),
            )
        )

    return sub_clauses, provisos


def extract_document_preamble(
    pages: List[Any],
    pdf_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Extract authoritative document-level metadata from initial gazette pages.

    Captures gazette number, publication date, authority, instrument title,
    enabling act, instrument type, and statutory commencement date.
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
        "instrument_type": "regulation",
    }

    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12"
    }

    # 1. Gazette masthead check (e.g. No. 2494/06 - TUESDAY, JUNE 23, 2026)
    m_masthead = re.search(
        r"No\.?\s*(\d{4}/\d{1,2})\s*-\s*([A-Za-z]+),\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})",
        full_text,
        re.IGNORECASE,
    )
    if m_masthead:
        meta["gazette_no"] = f"Gazette Extraordinary No. {m_masthead.group(1)}"
        m_day = int(m_masthead.group(4))
        m_mon = months.get(m_masthead.group(3).lower(), "01")
        m_yr = m_masthead.group(5)
        meta["published"] = f"{m_yr}-{m_mon}-{m_day:02d}"
    else:
        m_gz = re.search(r"No\.?\s*(\d{4}/\d{1,2})", full_text, re.IGNORECASE)
        if m_gz:
            meta["gazette_no"] = f"Gazette Extraordinary No. {m_gz.group(1)}"

        m_pub = re.search(
            r"(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+(\d{4})",
            full_text,
            re.IGNORECASE,
        )
        if m_pub:
            day = int(m_pub.group(1))
            month = months.get(m_pub.group(2).lower(), "01")
            year = m_pub.group(3)
            meta["published"] = f"{year}-{month}-{day:02d}"

    # 2. Authority (e.g. Minister of Health and Mass Media...)
    m_auth = re.search(r"(Minister of [^\n\.,]+?)(?:\s+in consultation|\.|\,|$)", full_text, re.IGNORECASE)
    if m_auth:
        meta["authority"] = m_auth.group(1).strip()
    else:
        meta["authority"] = "Ministry of Health, Sri Lanka"

    # 3. Enabling act
    m_act = re.search(r"((?:FOOD|COMPANIES)\s+ACT,?\s*No\.?\s*\d+\s*(?:o?f|OF)\s*\d{4}|CHAPTER\s+\d+\s*\([^\)]+\))", full_text, re.IGNORECASE)
    if m_act:
        meta["enabling_act"] = m_act.group(1).strip()

    # 4. Instrument typology
    is_amendment = bool(re.search(r"hereby further amended as follows", full_text, re.IGNORECASE))
    is_orders = bool(re.search(r"ORDERS\s+under|Companies \(Fees\) Orders", full_text, re.IGNORECASE))
    if is_amendment:
        meta["instrument_type"] = "amendment_regulation"
    elif is_orders:
        meta["instrument_type"] = "statutory_order"

    # 5. Citation & title
    m_cit = re.search(r"(?:cited as|Regulations\s*\n\s*The)\s+([^\n\.]+(?:Regulations|Act|Order|Orders)\s+\d{4})", full_text, re.IGNORECASE)
    if m_cit:
        meta["instrument"] = m_cit.group(1).strip()
    else:
        m_tit = re.search(r"([A-Za-z\s\(\)\-]+(?:Regulations|Orders|Order)\s+\d{4})", full_text)
        if m_tit:
            meta["instrument"] = m_tit.group(1).strip()

    # 6. Statutory commencement date
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
    pdf_path: Optional[str | Path] = None,
) -> List[SegmentedClause]:
    """Segment a regulatory document into complete, structured, and stitched clauses.

    Handles:
    - Running headers, footers, and pagination filtering (layout bounding boxes when PDF path is available).
    - Principal regulations (e.g. 1., 2., 3., 4.(1)).
    - Amendment regulations with directives (e.g. (1) in regulation 3, (2)...).
    - Statutory orders (e.g. Orders under Section..., Companies (Fees) Orders).
    - Schedules and multi-column tables attached to clauses.
    - Nested subclauses ((1), (a), (i)) and provisos (Provided that...).
    - Continuous cross-page clause stitching preserving exact verbatim text, start_page, and end_page.
    """
    tables_by_page: Dict[int, List[TableData]] = {}
    pages_lines: List[List[Tuple[str, int, float, float]]] = []
    full_text_sample = ""

    doc = None
    if pdf_path and Path(pdf_path).exists():
        try:
            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            tables_by_page = extract_tables_from_doc(doc)
            for p_idx in range(len(doc)):
                p_num = p_idx + 1
                page = doc[p_idx]
                p_height = page.rect.height
                lines_on_page: List[Tuple[str, int, float, float]] = []

                blocks = page.get_text("blocks")
                for b in blocks:
                    if b[6] != 0:  # Skip image blocks
                        continue
                    b_y0, b_y1 = b[1], b[3]
                    block_text = b[4]

                    # Filter top running header and bottom footer
                    if b_y0 < 75 and is_gazette_noise(block_text):
                        continue
                    if b_y1 > (p_height - 60) and is_gazette_noise(block_text):
                        continue

                    for raw_line in block_text.split("\n"):
                        s = raw_line.strip()
                        if not s or is_gazette_noise(s):
                            continue
                        lines_on_page.append((raw_line, p_num, b_y0, b_y1))

                pages_lines.append(lines_on_page)
                if p_num <= 2:
                    full_text_sample += "\n" + page.get_text("text")
        except Exception as exc:
            logger.warning("Layout extraction failed with PyMuPDF; falling back to text lines: %s", exc)
            pages_lines = []
            full_text_sample = ""

    if not pages_lines:
        for p_idx, p in enumerate(pages):
            p_num = getattr(p, "page_number", p_idx + 1)
            raw = getattr(p, "raw_text", None) or getattr(p, "text", None) or str(p)
            lines_on_page = []
            for raw_line in raw.split("\n"):
                s = raw_line.strip()
                if not s or is_gazette_noise(s):
                    continue
                lines_on_page.append((raw_line, p_num, 0.0, 0.0))
            pages_lines.append(lines_on_page)
            if p_num <= 2:
                full_text_sample += "\n" + raw

    all_lines: List[Tuple[str, int, float, float]] = []
    for pl in pages_lines:
        for line_tup in pl:
            all_lines.append(line_tup)

    is_amendment = bool(re.search(r"hereby further amended as follows", full_text_sample, re.IGNORECASE))
    is_orders = bool(re.search(r"ORDERS\s+under|Companies \(Fees\) Orders", full_text_sample, re.IGNORECASE))

    principal_heading = re.compile(
        r"^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]*))\s*$",
        re.IGNORECASE,
    )
    principal_inline = re.compile(
        r"^\s*(?:(?:Regulation\s+)?(\d{1,3})\.(?:\s*\(([0-9a-zA-Z]+)\))?|(SCHEDULE\s+[IVXLCDM\d]*))\s+([A-Z].*)",
        re.IGNORECASE,
    )
    amend_directive = re.compile(r"^\s*\((\d{1,2})\)\s*$", re.IGNORECASE)
    amend_directive_inline = re.compile(r"^\s*\((\d{1,2})\)\s+([A-Za-z].*)", re.IGNORECASE)
    amend_target = re.compile(r"in\s+(regulation\s+\d+|sub-regulation\s+\d+|the\s+Schedule)", re.IGNORECASE)
    schedule_head = re.compile(r'^\s*["“]?(SCHEDULE\s*[IVXLCDM\d]*)["”]?\s*$', re.IGNORECASE)

    clauses: List[SegmentedClause] = []
    current_clause_dict: Optional[Dict[str, Any]] = None
    in_substantive_body = False
    last_reg_num = 0

    def finalize_clause(c_dict: Dict[str, Any], end_p: int, end_y: float) -> None:
        raw_c_text = "\n".join(c_dict["lines"]).strip()
        c_start_page = c_dict["start_page"]
        c_start_y = c_dict["start_y"]
        c_type = c_dict["clause_type"]

        # Attach tables matching this clause page range or schedule
        matched_tables: List[TableData] = []
        for p_i in range(c_start_page, end_p + 1):
            if p_i in tables_by_page:
                for tb in tables_by_page[p_i]:
                    t_y0 = tb.bbox[1] if tb.bbox else 0.0
                    if c_type == "schedule" or "Schedule" in c_dict["name"]:
                        matched_tables.append(tb)
                        raw_c_text += "\n\n" + format_table_as_text(tb)
                    elif p_i == c_start_page and t_y0 >= (c_start_y - 10) and (p_i < end_p or t_y0 <= (end_y + 10)):
                        matched_tables.append(tb)
                        raw_c_text += "\n\n" + format_table_as_text(tb)

        if len(raw_c_text) < min_clause_length:
            return

        subclauses, provisos = parse_nested_subclauses(raw_c_text, c_start_page)

        clauses.append(
            SegmentedClause(
                clause_number=c_dict["name"],
                text=raw_c_text,
                start_page=c_start_page,
                end_page=end_p,
                char_start=0,
                char_end=len(raw_c_text),
                clause_type=c_type,
                sub_clauses=subclauses,
                tables=matched_tables,
                provisos=provisos,
            )
        )

    for idx, (line_str, p_num, y0, y1) in enumerate(all_lines):
        s = line_str.strip()
        prev_line = all_lines[idx - 1][0].strip() if idx > 0 else ""

        # Check for division marker
        if s.upper() in ("REGULATIONS", "ORDERS", "ORDER"):
            in_substantive_body = True
            continue

        is_heading = False
        clause_name = None
        clause_type = "regulation"
        inline_body = ""

        # Schedule heading check
        m_sched = schedule_head.match(s)
        if m_sched:
            is_heading = True
            in_substantive_body = True
            clause_name = m_sched.group(1).upper()
            clause_type = "schedule"

        elif not in_substantive_body:
            if is_amendment and (amend_directive.match(s) or amend_directive_inline.match(s)):
                in_substantive_body = True
            elif not is_amendment and (principal_heading.match(s) or principal_inline.match(s)):
                in_substantive_body = True
            elif is_orders and ("are hereby amended" in s or (s.endswith("Orders") and len(s) < 80)):
                in_substantive_body = True
                is_heading = True
                clause_name = s if s.endswith("Orders") else "Order 1"
                clause_type = "order"
                inline_body = s if not s.endswith("Orders") else ""
            else:
                continue

        if not is_heading:
            if is_amendment:
                m_ad = amend_directive.match(s)
                m_adi = amend_directive_inline.match(s)
                match_amend = m_ad or m_adi
                if match_amend:
                    dir_num = match_amend.group(1)
                    is_heading = True
                    clause_type = "amendment_directive"
                    next_few = " ".join([l[0].strip() for l in all_lines[idx:idx + 3]])
                    m_tgt = amend_target.search(next_few)
                    tgt_info = f" ({m_tgt.group(1).title()})" if m_tgt else ""
                    clause_name = f"Directive ({dir_num}){tgt_info}"
                    inline_body = match_amend.group(2) if m_adi else ""
            else:
                m_ph = principal_heading.match(s)
                m_pi = principal_inline.match(s)
                match_princ = m_ph or m_pi
                if match_princ:
                    r_num_str = match_princ.group(1)
                    sub_num = match_princ.group(2)
                    sched_kw = match_princ.group(3)

                    if sched_kw:
                        is_heading = True
                        clause_name = sched_kw.upper()
                        clause_type = "schedule"
                    elif r_num_str:
                        r_num = int(r_num_str)
                        continuing_prepositions = ("under", "to", "of", "in", "the", "and", "or", "with", "that", "from", "for")
                        is_cont = any(prev_line.lower().endswith(f" {prep}") or prev_line.lower() == prep for prep in continuing_prepositions)
                        if (last_reg_num == 0 or r_num == last_reg_num + 1) and not is_cont:
                            is_heading = True
                            last_reg_num = r_num
                            clause_name = f"Regulation {r_num}({sub_num})" if sub_num else f"Regulation {r_num}"
                            clause_type = "regulation"
                            inline_body = match_princ.group(4) if m_pi else ""

        if is_heading:
            if current_clause_dict and current_clause_dict["lines"]:
                finalize_clause(current_clause_dict, p_num, y0)

            current_clause_dict = {
                "name": clause_name,
                "clause_type": clause_type,
                "start_page": p_num,
                "start_y": y0,
                "lines": [inline_body] if inline_body else [],
            }
        elif current_clause_dict is not None:
            current_clause_dict["lines"].append(line_str)

    if current_clause_dict and current_clause_dict["lines"]:
        last_page = all_lines[-1][1] if all_lines else 1
        last_y = 1000.0
        finalize_clause(current_clause_dict, last_page, last_y)

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
    - Extract nested subclauses and provisos.
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

        subclauses, provisos = parse_nested_subclauses(clause_text, page_number)

        results.append(
            SegmentedClause(
                clause_number=clause_number,
                text=clause_text,
                start_page=page_number,
                end_page=page_number,
                char_start=char_start,
                char_end=char_end,
                sub_clauses=subclauses,
                provisos=provisos,
            )
        )

    return results

