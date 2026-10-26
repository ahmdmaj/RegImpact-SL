import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import fitz

doc = fitz.open("backend/data/raw_sources/food_amendment_colouring_substances_regulations_2011_en.pdf")
print("Total pages:", len(doc))
for i, page in enumerate(doc):
    imgs = page.get_images()
    print(f"Page {i+1} images count: {len(imgs)}")
    for img in imgs:
        xref = img[0]
        base_img = doc.extract_image(xref)
        print(f"  Image xref={xref}: format={base_img['ext']}, width={base_img['width']}, height={base_img['height']}, size={len(base_img['image'])} bytes")
