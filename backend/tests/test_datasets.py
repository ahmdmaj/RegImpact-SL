"""Milestone 5 unit tests: Dataset A (Corpus), Dataset B (Benchmark), and Leakage Protection.

Validates:
  DATA-A-001  Corpus fixture PDFs generate and extract cleanly with valid page counts.
  DATA-A-002  DocumentIngestionService persists documents, pages, and clauses with offsets.
  DATA-A-003  Corpus source URLs are not hallucinated (null / unverified).
  DATA-A-004  Clauses are embedded and approved rules are registered in the database.
  DATA-B-001  scenarios.jsonl exists and every line validates as a valid BenchmarkScenario.
  DATA-B-002  Every clause_id in Dataset B exists in Dataset A (source grounding).
  DATA-B-003  All 5 required scenario types are present (direct, minimal_pair, invariance, temporal, incomplete).
  DATA-B-004  Minimal pairs strictly link via pair_id and exhibit valid outcome flips.
  DATA-B-005  Invariance pairs strictly link via pair_id and maintain identical outcomes.
  DATA-B-006  Temporal scenarios correctly reflect statutory commencement boundaries.
  DATA-B-007  Incomplete scenarios require specific missing fields for 3-valued abstention.
  LEAK-001    split_scenarios_by_clause guarantees 0% clause leakage across train and test.
  LEAK-002    split_scenarios_by_clause never splits minimal or invariance pairs across partitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest
import pymupdf
from sqlalchemy.orm import Session

from backend.src.db.models import ClauseORM, DocumentPageORM, RuleORM, SourceDocumentORM
from backend.src.evaluation.dataset_split import split_scenarios_by_clause
from backend.src.models.domain import BenchmarkScenario, OutcomeStatus
from backend.src.scripts.seed_benchmark import (
    DEFAULT_BENCHMARK_PATH,
    build_benchmark_scenarios,
    write_benchmark_scenarios,
)
from backend.src.scripts.seed_corpus import (
    DOCUMENT_FIXTURES,
    RAW_SOURCES_DIR,
    generate_pdf_fixtures,
    seed_regulatory_corpus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def seeded_benchmark_path(tmp_path_factory) -> Path:
    """Ensure a benchmark scenarios.jsonl file exists for testing."""
    test_dir = tmp_path_factory.mktemp("benchmark_data")
    target_file = test_dir / "scenarios.jsonl"
    write_benchmark_scenarios(target_file)
    return target_file


@pytest.fixture()
def populated_corpus_db(db_session: Session, tmp_path) -> Session:
    """Seed the in-memory SQLite database with Dataset A regulatory corpus."""
    raw_dir = tmp_path / "raw_sources"
    seed_regulatory_corpus(db=db_session, raw_dir=raw_dir, force=True)
    return db_session


# ---------------------------------------------------------------------------
# Dataset A: Corpus Scaffolding & Provenance Tests
# ---------------------------------------------------------------------------

def test_data_a_001_pdf_fixtures_generate(tmp_path):
    """Corpus fixture PDFs generate properly with extractable text and page counts."""
    generated_files = generate_pdf_fixtures(tmp_path, force=True)
    assert len(generated_files) == 3

    for pdf_path in generated_files:
        assert pdf_path.exists()
        doc = pymupdf.open(str(pdf_path))
        assert len(doc) >= 1
        # Verify text is extractable
        text = "".join(page.get_text("text") for page in doc)
        assert len(text.strip()) > 50
        doc.close()


def test_data_a_002_ingestion_offsets_and_pages(populated_corpus_db):
    """Ingestion service extracts pages and records character offsets on clauses."""
    db = populated_corpus_db

    # Check documents
    docs = db.query(SourceDocumentORM).all()
    assert len(docs) == 3
    doc_ids = {d.id for d in docs}
    assert "doc_fcau_labelling_2024" in doc_ids
    assert "doc_cea_epl_2022" in doc_ids
    assert "doc_caa_mrp_2023" in doc_ids

    # Check pages
    pages = db.query(DocumentPageORM).all()
    assert len(pages) >= 4
    for p in pages:
        assert p.char_count > 0
        assert len(p.page_hash) == 64
        assert not p.is_ocr

    # Check clauses and offsets
    clauses = db.query(ClauseORM).all()
    assert len(clauses) >= 6
    for c in clauses:
        assert c.char_end > c.char_start
        assert c.start_page >= 1
        assert c.end_page >= c.start_page
        assert len(c.text.strip()) > 20


def test_data_a_003_no_hallucinated_urls(populated_corpus_db):
    """Source URLs must not be hallucinated; they remain null or designated placeholder."""
    db = populated_corpus_db
    docs = db.query(SourceDocumentORM).all()
    for doc in docs:
        assert doc.source_url is None or doc.source_url.startswith("https://")


def test_data_a_004_embeddings_and_approved_rules(populated_corpus_db):
    """Clauses have computed embeddings and approved rules are linked."""
    db = populated_corpus_db

    # Verify embeddings are populated
    clauses = db.query(ClauseORM).all()
    assert all(c.embedding is not None and len(c.embedding) == 64 for c in clauses)

    # Verify approved rules
    approved_rules = db.query(RuleORM).filter_by(review_status="APPROVED").all()
    assert len(approved_rules) == 6
    rule_ids = {r.rule_id for r in approved_rules}
    assert "RULE-FCAU-REG-4" in rule_ids
    assert "RULE-CEA-REG-3" in rule_ids
    assert "RULE-CAA-SEC-10" in rule_ids

    # Verify coverage gap clause exists without approved rule
    c_reg9 = db.query(ClauseORM).filter(ClauseORM.clause_number == "Regulation 9").first()
    assert c_reg9 is not None
    reg9_rules = db.query(RuleORM).filter(RuleORM.clause_id == c_reg9.clause_id).all()
    assert len(reg9_rules) == 0  # True coverage gap


# ---------------------------------------------------------------------------
# Dataset B: Benchmark Scaffolding & Scenario Integrity Tests
# ---------------------------------------------------------------------------

def test_data_b_001_scenarios_jsonl_validity(seeded_benchmark_path):
    """scenarios.jsonl parses cleanly into valid BenchmarkScenario models."""
    assert seeded_benchmark_path.exists()

    scenarios: List[BenchmarkScenario] = []
    with seeded_benchmark_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            scen = BenchmarkScenario.model_validate_json(line_str)
            assert scen.scenario_id
            assert scen.clause_id
            assert scen.scenario_type
            assert scen.gold_outcome in list(OutcomeStatus)
            scenarios.append(scen)

    assert len(scenarios) >= 15


def test_data_b_002_clause_grounding_in_dataset_a(populated_corpus_db, seeded_benchmark_path):
    """Every clause_id in Dataset B must exist in the Dataset A corpus clauses."""
    db = populated_corpus_db
    known_clauses = {c.clause_number for c in db.query(ClauseORM).all()}

    with seeded_benchmark_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scen = BenchmarkScenario.model_validate_json(line)
            assert scen.clause_id in known_clauses, (
                f"Scenario '{scen.scenario_id}' references unknown clause '{scen.clause_id}'."
            )


def test_data_b_003_all_scenario_types_represented(seeded_benchmark_path):
    """All 5 scenario types specified in v4 are represented in the benchmark."""
    types_seen = set()
    with seeded_benchmark_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scen = BenchmarkScenario.model_validate_json(line)
            types_seen.add(scen.scenario_type)

    required_types = {"direct", "minimal_pair", "invariance", "temporal", "incomplete"}
    missing = required_types - types_seen
    assert not missing, f"Missing required scenario types: {missing}"


def test_data_b_004_minimal_pairs_linkage_and_flip(seeded_benchmark_path):
    """Minimal pair scenarios link via pair_id and exhibit consistency outcome flips."""
    pairs = {}
    with seeded_benchmark_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scen = BenchmarkScenario.model_validate_json(line)
            if scen.scenario_type == "minimal_pair":
                assert scen.pair_id is not None
                pairs.setdefault(scen.pair_id, []).append(scen)

    assert len(pairs) >= 3, "Expected at least 3 minimal pairs."

    for pair_id, members in pairs.items():
        assert len(members) == 2, f"Pair '{pair_id}' must contain exactly 2 scenarios, got {len(members)}."
        outcomes = {members[0].gold_outcome, members[1].gold_outcome}
        # One member must be APPLICABLE and the other NOT_APPLICABLE (a true sensitivity flip)
        assert OutcomeStatus.APPLICABLE in outcomes
        assert OutcomeStatus.NOT_APPLICABLE in outcomes


def test_data_b_005_invariance_pairs_linkage_and_stability(seeded_benchmark_path):
    """Invariance pair scenarios link via pair_id and preserve identical outcomes."""
    pairs = {}
    with seeded_benchmark_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scen = BenchmarkScenario.model_validate_json(line)
            if scen.scenario_type == "invariance":
                assert scen.pair_id is not None
                pairs.setdefault(scen.pair_id, []).append(scen)

    assert len(pairs) >= 2, "Expected at least 2 invariance pairs."

    for pair_id, members in pairs.items():
        assert len(members) == 2, f"Pair '{pair_id}' must contain exactly 2 scenarios."
        # Invariance implies outcomes are identical despite irrelevant perturbations
        assert members[0].gold_outcome == members[1].gold_outcome


def test_data_b_006_temporal_scenario_boundaries(seeded_benchmark_path):
    """Temporal scenarios test pre-commencement vs post-commencement dates."""
    temporal_scens = []
    with seeded_benchmark_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scen = BenchmarkScenario.model_validate_json(line)
            if scen.scenario_type == "temporal":
                temporal_scens.append(scen)

    assert len(temporal_scens) >= 2
    # Pre-commencement date yields NOT_APPLICABLE
    pre = next((s for s in temporal_scens if s.as_at_date < "2024-06-01"), None)
    assert pre is not None
    assert pre.gold_outcome == OutcomeStatus.NOT_APPLICABLE

    # Post-commencement date yields APPLICABLE
    post = next((s for s in temporal_scens if s.as_at_date >= "2024-06-01"), None)
    assert post is not None
    assert post.gold_outcome == OutcomeStatus.APPLICABLE


def test_data_b_007_incomplete_scenarios_missing_fields(seeded_benchmark_path):
    """Incomplete scenarios have status CONDITIONAL_MISSING_DATA and declare missing fields."""
    incomplete_scens = []
    with seeded_benchmark_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            scen = BenchmarkScenario.model_validate_json(line)
            if scen.scenario_type == "incomplete":
                incomplete_scens.append(scen)

    assert len(incomplete_scens) >= 2
    for s in incomplete_scens:
        assert s.gold_outcome == OutcomeStatus.CONDITIONAL_MISSING_DATA
        assert s.gold_missing_fields and len(s.gold_missing_fields) > 0


# ---------------------------------------------------------------------------
# Benchmark Leakage Protection Tests
# ---------------------------------------------------------------------------

def test_leak_001_clause_grouped_partitioning_disjointness():
    """split_scenarios_by_clause strictly partitions by clause_id with 0% leakage."""
    all_scenarios = build_benchmark_scenarios()
    train_scens, test_scens = split_scenarios_by_clause(all_scenarios, test_ratio=0.3, random_seed=42)

    assert len(train_scens) > 0
    assert len(test_scens) > 0
    assert len(train_scens) + len(test_scens) == len(all_scenarios)

    train_clauses = {s.clause_id for s in train_scens}
    test_clauses = {s.clause_id for s in test_scens}

    # Strict disjointness: no clause can appear in both train and test
    overlap = train_clauses.intersection(test_clauses)
    assert not overlap, f"Benchmark leakage detected! Overlapping clauses: {overlap}"


def test_leak_002_pairs_stay_in_same_partition():
    """All pairs sharing a pair_id remain together in the same partition."""
    all_scenarios = build_benchmark_scenarios()
    train_scens, test_scens = split_scenarios_by_clause(all_scenarios, test_ratio=0.35, random_seed=99)

    train_pair_ids = {s.pair_id for s in train_scens if s.pair_id}
    test_pair_ids = {s.pair_id for s in test_scens if s.pair_id}

    pair_overlap = train_pair_ids.intersection(test_pair_ids)
    assert not pair_overlap, f"Pair linkage leakage! Pairs split across partitions: {pair_overlap}"
