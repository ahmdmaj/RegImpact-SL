"""Pytest shared fixtures for RegImpact-SL backend tests.

This conftest.py is the single authoritative place for database-related
fixtures used by ALL test modules.

Key design decisions:
  - ALL database tests use an in-memory SQLite engine (sqlite:///:memory:).
  - The in-memory engine is created once per test *function* (function scope)
    to give each test a fully clean, isolated state.
  - The existing 82 tests in test_api.py, test_applicability.py, etc. do NOT
    use any database fixtures and are unaffected.
  - `db_engine` and `db_session` are available to any test file that declares
    them as parameters without any additional import.
"""

import io
import os
import struct
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from pathlib import Path

try:
    from dotenv import load_dotenv
    for _p in [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]:
        if _p.exists():
            load_dotenv(_p, override=False)
except ImportError:
    pass

# Save live environment configuration for opt-in live integration tests
LIVE_DATABASE_URL = os.environ.get("DATABASE_URL")
LIVE_OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
LIVE_GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
print(f"DEBUG CONFTEST: LIVE_DATABASE_URL={LIVE_DATABASE_URL}")

# Default offline test suites to in-memory SQLite and mock LLM providers
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"

from backend.src.db.models import Base
from backend.src.db.session import create_tables


# ---------------------------------------------------------------------------
# Database fixtures (function-scoped → fresh DB per test)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_engine():
    """Create a fresh in-memory SQLite engine with all ORM tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
        future=True,
    )
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def set_fk(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    """Provide a transactional Session that is rolled back after each test."""
    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = factory()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# PDF fixtures (synthetic minimal PDFs for offline tests)
# ---------------------------------------------------------------------------

def _make_minimal_pdf(text_pages: list[str]) -> bytes:
    """Build a minimal, spec-compliant PDF for tests using PyMuPDF."""
    try:
        import pymupdf
        doc = pymupdf.open()
        for page_text in text_pages:
            page = doc.new_page(width=612, height=792)
            page.insert_text((72, 72), page_text, fontsize=10)
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    except ImportError:
        pass

    # Pure Python fallback for environments without PyMuPDF
    objects = []
    page_obj_ids = []
    current_obj_id = 2

    for page_text in text_pages:
        escaped = page_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_content = f"BT /F1 10 Tf 72 700 Td ({escaped}) Tj ET".encode("latin-1", errors="replace")
        stream_length = len(stream_content)
        content_obj = (
            f"{current_obj_id} 0 obj\n"
            f"<< /Length {stream_length} >>\n"
            f"stream\n"
        ).encode() + stream_content + b"\nendstream\nendobj\n"
        objects.append(content_obj)
        content_id = current_obj_id
        current_obj_id += 1

        page_obj = (
            f"{current_obj_id} 0 obj\n"
            f"<< /Type /Page /Parent 999 0 R "
            f"/MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\n"
            f"endobj\n"
        ).encode()
        objects.append(page_obj)
        page_obj_ids.append(current_obj_id)
        current_obj_id += 1

    kids = " ".join(f"{oid} 0 R" for oid in page_obj_ids)
    pages_obj = (
        f"999 0 obj\n"
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_ids)} >>\n"
        f"endobj\n"
    ).encode()
    catalog_obj = b"1000 0 obj\n<< /Type /Catalog /Pages 999 0 R >>\nendobj\n"
    header = b"%PDF-1.4\n"
    body = b"".join(objects) + pages_obj + catalog_obj
    xref_pos = len(header) + len(body)
    all_obj_ids = sorted(list(range(2, current_obj_id)) + [999, 1000])
    max_id = max(all_obj_ids)
    xref = f"xref\n0 {max_id + 1}\n0000000000 65535 f \n".encode()
    for _ in range(max_id):
        xref += b"0000000000 00000 n \n"
    trailer = (
        f"trailer\n<< /Size {max_id + 1} /Root 1000 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return header + body + xref + trailer


@pytest.fixture()
def minimal_pdf_bytes() -> bytes:
    """Single-page minimal PDF with a sample regulatory clause text."""
    page_text = (
        "Regulation 4. Every food manufacturing enterprise having a production "
        "capacity of 50 kg per day or more, and engaged in the production of "
        "prepackaged food products, shall ensure that each retail package carries "
        "a nutrition information panel in Sinhala, Tamil, and English."
    )
    return _make_minimal_pdf([page_text])


@pytest.fixture()
def two_page_pdf_bytes() -> bytes:
    """Two-page minimal PDF with two different clause texts."""
    pages = [
        "Regulation 4. Every food manufacturing enterprise with production capacity of 50 kg per day shall label products.",
        "Schedule 1 Part B Item 12. Any industrial food manufacturing activity employing 20 or more persons shall obtain an EPL.",
    ]
    return _make_minimal_pdf(pages)


@pytest.fixture()
def pdf_file(tmp_path, minimal_pdf_bytes):
    """Write minimal_pdf_bytes to a temporary file and return the Path."""
    p = tmp_path / "test_regulation.pdf"
    p.write_bytes(minimal_pdf_bytes)
    return p


@pytest.fixture()
def two_page_pdf_file(tmp_path, two_page_pdf_bytes):
    """Write two_page_pdf_bytes to a temporary file and return the Path."""
    p = tmp_path / "test_regulation_two_page.pdf"
    p.write_bytes(two_page_pdf_bytes)
    return p
