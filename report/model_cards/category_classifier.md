# Model Card — Spend Category Classifier

| | |
|:---|:---|
| **Notebook** | `notebooks/02_category_classifier.ipynb` |
| **Owner** | Ashfaaq KT |
| **Task** | Multi-class text classification — which spend category is this receipt? |
| **Learning type** | **Supervised** |
| **Algorithm** | TF-IDF + Random Forest |
| **Artifacts** | `ml-service/models/classifier.pkl` (8.8 MB), `ml-service/models/tfidf.pkl` (44 KB) |
| **Served by** | `ml-service/classifier.py` → `/ml/classify` |
| **Status** | ✅ **In production, target beaten** |

---

## What it does

Predicts one of three spend categories from the text extracted off a receipt:
**Food & Beverage**, **General Retail**, **Supermarket / Grocery**. The result
drives the category multiplier in the points engine.

`server.js` uses the prediction when confidence ≥ 0.65 and falls back to Gemini's
own category otherwise, so a low-confidence prediction never silently degrades
the reward calculation.

## Data

| Split | Rows | % |
|:---|---:|---:|
| Train | 998 | 69.9% |
| Validation | 213 | 14.9% |
| Test | 216 | 15.1% |
| **Total** | **1,427** | 100% |

Source: `dataset/processed/category_{train,val,test}.csv`, derived from
`receipts_master.csv` (CORD + SROIE). Features are **`items_text` only** — the
line items. `date` and `merchant` are deliberately excluded because they are
missing for 50.7% of the corpus (see Notebook 01), so a model using them would
work on only half the data.

Features: `TfidfVectorizer(ngram_range=(1,2), max_features=10000, min_df=2)`.

## Comparison — three algorithms

| Model | Val accuracy | Val macro-F1 |
|:---|---:|---:|
| **Random Forest** | 0.9484 | **0.9092** ← selected |
| Linear SVM | 0.9390 | 0.8912 |
| Logistic Regression | 0.9249 | 0.8898 |

**Why Random Forest:** highest macro-F1, which is the metric that matters here
because the classes are imbalanced — macro-F1 weights the rare
Supermarket/Grocery class equally rather than letting the majority class carry
the score.

## Held-out test performance

**Test macro-F1 0.942 · accuracy 0.9444** (n = 216) — target was 0.80.

| Class | Precision | Recall | F1 | Support |
|:---|---:|---:|---:|---:|
| Food & Beverage | 0.95 | 0.87 | 0.91 | 69 |
| General Retail | 0.94 | 0.98 | 0.96 | 136 |
| Supermarket / Grocery | 0.92 | 1.00 | 0.96 | 11 |
| **macro avg** | 0.94 | 0.95 | **0.94** | 216 |

## Limitations

1. **Supermarket / Grocery has only 11 test samples.** Its 0.96 F1 looks strong
   but rests on eleven receipts — a single misclassification moves it by ~9
   points. Treat that number as indicative, not precise.
2. **Food & Beverage recall is the weak spot at 0.87** — roughly one in seven
   restaurant receipts is misfiled, usually as General Retail.
3. **Trained on Malaysian and Indonesian receipts** (SROIE, CORD) but served
   Indian ones. The vocabulary differs, and this domain shift is untested.
4. **The class labels are heuristic**, derived from source dataset conventions
   rather than human judgement. `dataset/processed/indian_category_folders.csv`
   holds 11 genuinely human-assigned Indian categories that would make a better
   evaluation set — currently unused.
5. **sklearn version skew.** The notebook (Python 3.9) and the serving env
   (3.13) differ. Regenerate the served model with
   `ml-service/.venv/bin/python ml-service/train_classifier.py` after any
   retrain, or loading raises an `InconsistentVersionWarning`.

## Reproduce

```bash
jupyter nbconvert --execute notebooks/02_category_classifier.ipynb
ml-service/.venv/bin/python ml-service/train_classifier.py   # regenerate served model
```
