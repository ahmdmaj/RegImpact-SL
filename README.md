# RegImpact-SL

## 1. What RegImpact-SL is
RegImpact-SL is a Context-Aware Regulatory Change Impact Analysis system for Small Food Manufacturers in Sri Lanka. This is a research-oriented AI Engineering and Information Systems project.

**Disclaimer: This project is a research prototype and not a legal-advice system.** 
Some records in the dataset are intentionally marked as placeholders, conditionals, or example records requiring further source verification.

## 2. Research Problem
A small food manufacturer in Sri Lanka may be affected by regulatory changes depending on its specific business context. The system should eventually determine:
`CHANGE → APPLICABILITY → REASON → IMPACT → ACTION → EVIDENCE → EFFECTIVE DATE`

## 3. Research Questions
**Main research question:**
"How can a context-aware AI system identify and explain the business-specific impact of regulatory changes for small food manufacturers in Sri Lanka?"

**Supporting questions:**
1. How accurately can a context-aware system determine whether a regulatory change applies to a specific small food manufacturer?
2. How accurately can the system identify the obligations and operational impacts resulting from an applicable regulatory change?
3. Does structured regulatory knowledge combined with hybrid retrieval improve evidence-grounded regulatory impact analysis compared with conventional RAG?

## 4. Current Project Phase
**Phase 3: PROJECT FOUNDATION + DATA LAYER**
This phase focuses on creating domain models, ingestion loaders, data validation, and test suites. RAG, embeddings, vector databases, LLMs, agents, or knowledge graphs have not been implemented yet.

## 5. Dataset Structure
The dataset consists of two manual files (placed in the `data/` directory):
1. `regulatory_corpus_v0.1.json`: Contains regulatory records, authorities, effective dates, obligations, applicability conditions, and business context variables.
2. `regimpact_sl_benchmark_v0.1.csv`: Contains benchmark scenarios, business profiles, expected applicability, reasons, impacts, actions, and evidence references.

## 6. Project Structure
```
regimpact-sl/
├── data/
│   ├── regulatory_corpus_v0.1.json
│   └── regimpact_sl_benchmark_v0.1.csv
├── src/
│   └── regimpact/
│       ├── __init__.py
│       ├── config.py
│       ├── models/
│       ├── ingestion/
│       └── validation/
├── tests/
├── notebooks/
├── docs/
├── requirements.txt
├── README.md
├── .gitignore
└── pyproject.toml
```

## 7. How to install
1. Clone the repository
2. Ensure you have Python 3.11+
3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 8. How to run validation
To generate a summary and validate the datasets, run:
```bash
python -m src.regimpact.summary
```

## 9. How to run tests
To execute the pytest suite:
```bash
pytest
```

## 10. Current Limitations
- The system is purely data-ingestion and validation at this phase.
- No legal interpretation, web scraping, or AI/RAG models have been implemented yet.
- The project is highly coupled to the specific Sri Lankan Food Manufacturer dataset constraints and evaluates exact ground-truth applicability.
