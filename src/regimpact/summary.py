from collections import Counter
from pathlib import Path
from .ingestion.corpus_loader import load_regulatory_corpus
from .ingestion.benchmark_loader import load_benchmark

def generate_summary(corpus_path: str, benchmark_path: str):
    print("==================================================")
    print("DATASET SUMMARY")
    print("==================================================\n")
    
    try:
        corpus = load_regulatory_corpus(corpus_path)
        print("Corpus:")
        print(f"{len(corpus)} records")
        
        domains = Counter([r.domain for r in corpus])
        for d, count in domains.items():
            print(f"{count} {d}")
            
        statuses = Counter([r.status for r in corpus])
        print("\nStatuses:")
        for s, count in statuses.items():
            print(f"{count} {s}")
            
        with_dates = sum(1 for r in corpus if r.effective_date is not None)
        print(f"\nRecords with effective dates: {with_dates}")
        
        with_urls = sum(1 for r in corpus if r.source_url is not None)
        print(f"Records with source URLs: {with_urls}")
        
        placeholders = sum(1 for r in corpus if "placeholder" in r.regulation_id.lower())
        print(f"Placeholder records: {placeholders}\n")
    except Exception as e:
        print(f"Failed to load corpus: {e}\n")

    