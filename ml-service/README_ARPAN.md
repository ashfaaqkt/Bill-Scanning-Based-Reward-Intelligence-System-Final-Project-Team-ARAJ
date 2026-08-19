# Fake Receipt Detection System

> **Status: standalone tool, not part of the live pipeline.** Nothing in
> `app.py` or `fraud.py` imports `fake_receipt_detector_arpan.py` — the serving
> fraud path is the 448px tamper CNN plus the perceptual-hash and OCR signals in
> `fraud.py`. This detector is run manually from the CLI, and by
> `dataset/process_labels_arpan.py`.
>
> It needs `pytesseract` (a system install) plus `ml-service/requirements_arpan.txt`,
> which are deliberately kept out of the service's own `requirements.txt` so a
> deployment never depends on them.
>
> Five of its eight analyzers are genuinely new work — paper characteristics,
> printing artifacts, geometry, FFT/AI-artifact detection and EXIF metadata. The
> other three overlap with checks `ocr.py` and Gemini already perform. Its output
> on our 200 labelled samples is quarantined in
> `dataset/processed/processed_labels_arpan.csv`: the run was done against mock
> images, so every row reads "LIKELY AUTHENTIC" and the file is excluded from all
> prepared data.

A comprehensive OCR-based system to detect AI-generated and fake receipts using computer vision, image forensics, and logical consistency analysis.

## 🎯 Features

- **Text Quality Analysis**: Detects AI artifacts in text rendering, OCR quality issues, and gibberish
- **Paper Characteristics**: Analyzes paper texture, edges, creases, and wear patterns
- **Printing Artifacts**: Detects thermal printer characteristics and inconsistencies
- **Visual Consistency**: Checks lighting, shadows, noise patterns, and reflections
- **Geometric Analysis**: Validates perspective, parallel lines, and scale relationships
- **AI Artifact Detection**: Uses ELA, frequency analysis, and GAN artifact detection
- **Metadata Analysis**: Examines EXIF data and file properties
- **Logical Consistency**: Verifies dates, mathematical calculations, and business information
- **CORD/SROIE Dataset Support**: Compatible with standard receipt datasets

## 📋 Requirements

- Python 3.8+
- OpenCV
- NumPy
- SciPy
- pytesseract (requires Tesseract OCR installation)
- Pillow

Install dependencies:
```bash
pip install -r requirements.txt
```

### Installing Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

## 🚀 Quick Start

### 1. Analyze a Single Receipt

```python
from receipt_authenticity_detector import ReceiptAuthenticityDetector

# Initialize detector
detector = ReceiptAuthenticityDetector("path/to/receipt.jpg")

# Run analysis
results = detector.analyze()

# Print results
print(f"Authenticity Score: {results['overall_score']}/100")
print(f"Verdict: {results['verdict']['verdict']}")

# Export detailed report
detector.export_report("report.json")
```

### 2. Compare Two Receipts

```python
from receipt_authenticity_detector import ReceiptAuthenticityDetector

# Analyze both receipts
detector1 = ReceiptAuthenticityDetector("receipt1.jpg")
detector2 = ReceiptAuthenticityDetector("receipt2.jpg")

results1 = detector1.analyze()
results2 = detector2.analyze()

# Compare scores
print(f"Receipt 1: {results1['overall_score']}/100")
print(f"Receipt 2: {results2['overall_score']}/100")

if results1['overall_score'] < results2['overall_score'] - 10:
    print("Receipt 1 is likely FAKE")
else:
    print("Receipt 2 is likely FAKE")
```

### 3. Work with CORD Dataset

```python
from cord_sroie_loader import CORDDatasetLoader, ReceiptPreprocessor

# Load dataset
loader = CORDDatasetLoader("/path/to/cord")

# Iterate through receipts
for image, annotations in loader.iterate_dataset('train'):
    # Preprocess
    preprocessed = ReceiptPreprocessor.full_pipeline(image)
    
    # Analyze
    detector = ReceiptAuthenticityDetector(preprocessed)
    results = detector.analyze()
    
    print(f"Score: {results['overall_score']}/100")
```

### 4. Batch Processing

```python
import glob
from receipt_authenticity_detector import ReceiptAuthenticityDetector

receipt_files = glob.glob("receipts/*.jpg")

for receipt_path in receipt_files:
    detector = ReceiptAuthenticityDetector(receipt_path)
    result = detector.analyze()
    
    if result['overall_score'] < 50:
        print(f"🚩 SUSPICIOUS: {receipt_path} (Score: {result['overall_score']})")
```

## 📊 Understanding the Output

### Overall Score (0-100)
- **80-100**: Likely authentic
- **60-79**: Possibly authentic (manual review recommended)
- **40-59**: Suspicious (requires investigation)
- **0-39**: Likely fake/AI-generated

### Module Scores
Each detection module provides:
- `score`: 0-100 authenticity score
- `flags`: List of specific issues detected
- `details`: Detailed metrics and measurements

Example output:
```json
{
  "text_analysis": {
    "score": 85,
    "flags": [],
    "details": {
      "text_sharpness": {
        "avg_sharpness": 234.5,
        "suspicious": false
      },
      "ocr_confidence": {
        "avg_confidence": 87.3,
        "suspicious": false
      }
    }
  },
  "ai_detection": {
    "score": 45,
    "flags": [
      "ela_analysis: ELA pattern suggests AI generation",
      "gan_artifacts: GAN-specific artifacts detected"
    ],
    "details": {
      "ela_analysis": {
        "ela_mean": 42.1,
        "ela_std": 3.2,
        "suspicious": true
      }
    }
  },
  "overall_score": 72.5,
  "verdict": {
    "verdict": "POSSIBLY AUTHENTIC",
    "confidence": "MEDIUM",
    "score": 72.5
  }
}
```

## 🔬 Detection Techniques

### 1. Text Quality Analysis
- **Sharpness Detection**: Uses Laplacian variance to measure text crispness
- **Character Consistency**: Detects morphing or impossible characters
- **Gibberish Detection**: Identifies AI-hallucinated nonsensical text
- **Font Consistency**: Checks for uniform thermal printing fonts
- **OCR Confidence**: Low confidence suggests unreadable AI text

### 2. Paper Characteristics
- **Texture Analysis**: Uses Local Binary Patterns and frequency domain analysis
- **Edge Characteristics**: Analyzes irregularity of paper boundaries
- **Crease Analysis**: Validates physics of fold shadows
- **Depth/Dimensionality**: Checks for realistic lighting gradients

### 3. Printing Artifacts
- **Thermal Dot Detection**: Identifies characteristic dot patterns from thermal printers
- **Horizontal Lines**: Detects line-by-line printing artifacts
- **Print Density**: Analyzes consistency of ink/thermal density
- **Registration**: Checks alignment and spacing consistency

### 4. AI-Specific Detection
- **Error Level Analysis (ELA)**: Detects compression inconsistencies
- **Frequency Analysis**: Identifies GAN frequency signatures
- **Repetitive Patterns**: Detects tiling artifacts from image generators
- **GAN Artifacts**: Finds checkerboard patterns and boundary artifacts

### 5. Geometric Analysis
- **Perspective Validation**: Checks vanishing point convergence
- **Parallel Lines**: Verifies geometric consistency
- **Scale Relationships**: Validates size relationships between elements

### 6. Metadata & Logic
- **EXIF Analysis**: Checks for camera metadata and suspicious software tags
- **Date/Time Validation**: Verifies plausibility of timestamps
- **Math Verification**: Checks totals, subtotals, and tax calculations
- **Business Validation**: Looks for expected receipt keywords and format

## 🎓 CORD/SROIE Dataset Support

### CORD Dataset Format
```python
from cord_sroie_loader import CORDDatasetLoader

loader = CORDDatasetLoader("/path/to/cord")
image, annotations = loader.load_sample("receipt_00001")

# Annotations include:
# - company, date, address, total
# - items: [{name, count, price}, ...]
# - bounding_boxes for each word
```

### SROIE Dataset Format
```python
from cord_sroie_loader import SROIEDatasetLoader

loader = SROIEDatasetLoader("/path/to/sroie")
image, annotations = loader.load_sample("X00001")

# Annotations include:
# - company, date, address, total
```

### Evaluation Metrics
```python
from cord_sroie_loader import ReceiptEvaluator

evaluator = ReceiptEvaluator()

# Character-level F1 score
f1_metrics = evaluator.f1_score_ocr(predicted_text, ground_truth)

# Normalized Edit Distance
ned = evaluator.normalized_edit_distance(predicted_text, ground_truth)

# Key field evaluation (SROIE Task 3)
field_results = evaluator.evaluate_key_fields(pred_annotations, gt_annotations)
```

## 🛠️ Advanced Usage

### Custom Detection Pipeline

```python
from text_analysis import TextQualityAnalyzer
from ai_detection import AIArtifactDetector
import cv2

# Load image
image = cv2.imread("receipt.jpg")

# Run specific modules
text_analyzer = TextQualityAnalyzer(image)
text_results = text_analyzer.analyze()

ai_detector = AIArtifactDetector(image)
ai_results = ai_detector.analyze()

print(f"Text Quality Score: {text_results['score']}")
print(f"AI Detection Score: {ai_results['score']}")
```

### Preprocessing Pipeline

```python
from cord_sroie_loader import ReceiptPreprocessor
import cv2

image = cv2.imread("receipt.jpg")

# Individual preprocessing steps
deskewed = ReceiptPreprocessor.deskew(image)
denoised = ReceiptPreprocessor.denoise(deskewed)
enhanced = ReceiptPreprocessor.enhance_contrast(denoised)
binary = ReceiptPreprocessor.binarize(enhanced)

# Or use full pipeline
processed = ReceiptPreprocessor.full_pipeline(image)
```

### Creating Synthetic Fakes for Training

```python
from cord_sroie_loader import DatasetAugmenter
import cv2

real_receipt = cv2.imread("real_receipt.jpg")

# Generate synthetic fake
fake_receipt = DatasetAugmenter.create_synthetic_fake(real_receipt, num_artifacts=3)

# Save for training
cv2.imwrite("synthetic_fake.jpg", fake_receipt)
```

## 📈 Performance Optimization

For large-scale processing:

```python
import multiprocessing
from functools import partial

def analyze_receipt(receipt_path):
    detector = ReceiptAuthenticityDetector(receipt_path)
    return detector.analyze()

# Parallel processing
with multiprocessing.Pool(processes=8) as pool:
    results = pool.map(analyze_receipt, receipt_paths)
```

## 🔍 Troubleshooting

### Low OCR Confidence
- Ensure Tesseract is properly installed
- Try preprocessing: `ReceiptPreprocessor.full_pipeline(image)`
- Check image resolution (minimum 300 DPI recommended)

### False Positives
- Adjust detection thresholds in individual modules
- Some real receipts may score low due to poor image quality
- Consider using preprocessing pipeline before analysis

### Memory Issues
- Process images in batches
- Resize large images before analysis
- Use multiprocessing with controlled pool size

## 📚 Module Details

### Available Analysis Modules

| Module | Purpose | Key Metrics |
|--------|---------|-------------|
| `text_analysis` | Text quality and OCR | Sharpness, consistency, gibberish |
| `paper_analysis` | Physical paper properties | Texture, edges, creases, wear |
| `print_analysis` | Thermal printing artifacts | Dots, lines, density, bleeding |
| `visual_analysis` | Lighting and shadows | Consistency, noise, reflections |
| `geometric_analysis` | Perspective and geometry | Lines, scale, orientation |
| `ai_detection` | AI generation artifacts | ELA, frequency, GAN patterns |
| `metadata_analysis` | EXIF and file properties | Camera data, timestamps |
| `logical_analysis` | Content consistency | Dates, math, business info |

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional dataset format support
- Deep learning-based detection models
- Real-time video stream analysis
- Mobile app integration
- Web API endpoint

## 📄 License

MIT License - Feel free to use in commercial and open-source projects.

## 🙏 Acknowledgments

- CORD Dataset: https://github.com/clovaai/cord
- SROIE Dataset: https://rrc.cvc.uab.es/?ch=13
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract

## 📧 Support

For issues and questions:
- Check existing issues
- Review troubleshooting section
- Open a new issue with example images (if possible)

---

**Note**: This system provides automated analysis but should not be the sole basis for fraud detection. Always combine with manual review for critical decisions.
