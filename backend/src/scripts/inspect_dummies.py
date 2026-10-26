import sys
import hashlib
from pathlib import Path
from datetime import datetime

raw_dir = Path("backend/data/raw_sources")
files = sorted([f for f in raw_dir.iterdir() if f.is_file() and f.name != ".gitkeep"])

dummies = [f for f in files if f.stat().st_size in (1033, 1037)]
print(f"Total dummy files: {len(dummies)}")

# Group by mtime date or exact hour
times = {}
for f in dummies:
    t = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    times[t] = times.get(t, 0) + 1

for t, cnt in sorted(times.items()):
    print(f"  {t}: {cnt} files")

# Check hashes of dummies
dummy_hashes = set()
for f in dummies:
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    dummy_hashes.add(h)
print(f"Unique hashes among {len(dummies)} dummy files: {len(dummy_hashes)}")
for dh in list(dummy_hashes)[:5]:
    print(f"  {dh}")
