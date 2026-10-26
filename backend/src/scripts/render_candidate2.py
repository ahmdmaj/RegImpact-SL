from pathlib import Path
import fitz

doc = fitz.open("backend/data/raw_sources/food_amendment_colouring_substances_regulations_2011_en.pdf")
out_dir = Path("backend/data/quarantine")
out_dir.mkdir(parents=True, exist_ok=True)

for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=150)
    out_file = out_dir / f"colouring_2011_p{i+1}.png"
    pix.save(str(out_file))
    print(f"Saved {out_file} ({out_file.stat().st_size} bytes)")
