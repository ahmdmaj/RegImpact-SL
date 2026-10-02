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

    try:
        benchmark = load_benchmark(benchmark_path)
        print("Benchmark:")
        print(f"{len(benchmark)} scenarios")
        
        types = Counter([s.scenario_type for s in benchmark if s.scenario_type])
        for t, count in types.items():
            print(f"{count} {t}")
            
        app = Counter([s.expected_applicability for s in benchmark])
        print("\nApplicability:")
        for a, count in app.items():
            print(f"{count} {a}")
            
        unique_biz = len(set([s.business_id for s in benchmark]))
        unique_reg = len(set([s.regulation_id for s in benchmark]))
        
        print(f"\nNumber of unique businesses: {unique_biz}")
        print(f"Number of unique regulations referenced: {unique_reg}")
    except Exception as e:
        print(f"Failed to load benchmark: {e}\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        generate_summary(sys.argv[1], sys.argv[2])
    else:
        generate_summary("data/regulatory_corpus_v0.1.json", "data/regimpact_sl_benchmark_v0.1.csv")
