# Fake Receipt Detector - Usage Examples

## Installation
```bash
pip install opencv-python numpy scipy pytesseract pillow
# Install tesseract: sudo apt-get install tesseract-ocr
```

## Basic Usage
```python
from fake_receipt_detector import ReceiptAuthenticityDetector

# Analyze single receipt
detector = ReceiptAuthenticityDetector("receipt.jpg")
results = detector.analyze()

print(f"Score: {results['overall_score']}/100")
print(f"Verdict: {results['verdict']['verdict']}")
detector.export_report("report.json")
```

## Command Line
```bash
python fake_receipt_detector.py receipt.jpg
```

## Compare Two Receipts
```python
det1 = ReceiptAuthenticityDetector("receipt1.jpg")
det2 = ReceiptAuthenticityDetector("receipt2.jpg")
r1, r2 = det1.analyze(), det2.analyze()

if r1['overall_score'] < r2['overall_score'] - 10:
    print("Receipt 1 is FAKE")
elif r2['overall_score'] < r1['overall_score'] - 10:
    print("Receipt 2 is FAKE")
```

## Batch Processing
```python
import glob
for path in glob.glob("receipts/*.jpg"):
    det = ReceiptAuthenticityDetector(path)
    res = det.analyze()
    if res['overall_score'] < 50:
        print(f"SUSPICIOUS: {path} - Score: {res['overall_score']}")
```

## Score Interpretation
- 80-100: Likely Authentic
- 60-79: Possibly Authentic
- 40-59: Suspicious  
- 0-39: Likely Fake/AI-Generated

## Module Scores
Each module returns:
- `score`: 0-100 authenticity score
- `flags`: List of detected issues
- `details`: Detailed measurements

Available modules:
- text: Text quality/OCR analysis
- paper: Paper texture/edges
- print: Thermal printing artifacts
- visual: Lighting/shadows/noise
- geom: Perspective/geometry
- ai: AI generation artifacts
- meta: EXIF metadata
- logic: Content consistency

## CORD/SROIE Dataset Support
See full documentation in README.md for dataset loading and evaluation metrics.
