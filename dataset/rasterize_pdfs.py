#!/usr/bin/env python3
"""
Rasterize PDF receipts to JPG so the fraud CNN (Notebook 03) can read them.
A CNN needs pixels; the 23 Indian receipts saved as PDF must be converted first.

For each dataset/indian/*.pdf -> writes dataset/indian/<same name>.jpg (page 1, 200 DPI).
Originals (.pdf) are kept. Re-runnable: skips if the .jpg already exists.

Run: python dataset/rasterize_pdfs.py
"""

from pathlib import Path
import fitz  # PyMuPDF (install: pip install PyMuPDF)

ROOT = Path(__file__).resolve().parent
DPI = 200


def main():
    indian = ROOT / "indian"
    pdfs = sorted(indian.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in dataset/indian/ — nothing to do.")
        return

    converted = skipped = failed = 0
    for pdf in pdfs:
        jpg = pdf.with_suffix(".jpg")
        if jpg.exists():
            skipped += 1
            continue
        try:
            doc = fitz.open(pdf)
            page = doc.load_page(0)  # first page only — receipts are single-page
            pix = page.get_pixmap(dpi=DPI)
            pix.save(jpg)
            doc.close()
            converted += 1
            print(f"  ✓ {pdf.name} -> {jpg.name}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {pdf.name}: {e}")

    print(f"\nDone. converted={converted}  skipped(existing)={skipped}  failed={failed}")
    print(f"Total JPGs now in dataset/indian/: "
          f"{len(list(indian.glob('*.jpg')))}")


if __name__ == "__main__":
    main()
