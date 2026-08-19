"""
Train the category classifier IN THE SERVING ENVIRONMENT (ml-service/.venv).

Why this exists: Notebook 02 trains in the root .venv (Python 3.9 / sklearn 1.5.x)
for learning, but the Flask service loads the model in ml-service/.venv
(Python 3.13 / sklearn 1.8.x). Loading a model pickled by a different sklearn
version raises InconsistentVersionWarning and risks invalid results. Running this
script with ml-service/.venv regenerates classifier.pkl + tfidf.pkl with the SAME
sklearn that serves them — so train == serve, no version mismatch.

Run:
    ml-service/.venv/bin/python ml-service/train_classifier.py

Mirrors Notebook 02: 3-model comparison (LogReg / LinearSVM / RandomForest) on the
3-class target, pick best by macro-F1, save. (RandomForest is used for inference
because it supports predict_proba for the confidence score.)
"""

import os
import sklearn
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score, classification_report

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "dataset", "processed")
MODELS = os.path.join(HERE, "models")
os.makedirs(MODELS, exist_ok=True)

TARGET, FEATURE = "category_3class", "text"
SEED = 42


def load(split):
    return pd.read_csv(os.path.join(DATA, f"category_{split}.csv"))


def main():
    print(f"Training with scikit-learn {sklearn.__version__} (serving env)")
    train, val, test = load("train"), load("val"), load("test")

    vec = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, min_df=2)
    Xtr = vec.fit_transform(train[FEATURE].fillna(""))
    Xva = vec.transform(val[FEATURE].fillna(""))
    Xte = vec.transform(test[FEATURE].fillna(""))
    ytr, yva, yte = train[TARGET], val[TARGET], test[TARGET]

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
        "Linear SVM": LinearSVC(class_weight="balanced", random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                                n_jobs=-1, random_state=SEED),
    }

    print("\n3-model comparison (validation macro-F1):")
    scored = {}
    for name, m in models.items():
        m.fit(Xtr, ytr)
        pred = m.predict(Xva)
        f1 = f1_score(yva, pred, average="macro")
        scored[name] = (m, f1)
        print(f"  {name:20s} acc={accuracy_score(yva, pred):.4f}  macro-F1={f1:.4f}")

    # Prefer Random Forest for serving (predict_proba → confidence); it also wins here.
    best_name = max(scored, key=lambda k: scored[k][1])
    if best_name != "Random Forest":
        print(f"  [note] {best_name} had the top macro-F1, but Random Forest is saved for "
              f"predict_proba support used by the /ml/classify confidence score.")
    best = scored["Random Forest"][0]

    test_pred = best.predict(Xte)
    print(f"\nSaved model: Random Forest")
    print(f"  TEST macro-F1: {f1_score(yte, test_pred, average='macro'):.4f}  "
          f"accuracy: {accuracy_score(yte, test_pred):.4f}")
    print(classification_report(yte, test_pred, zero_division=0))

    joblib.dump(best, os.path.join(MODELS, "classifier.pkl"))
    joblib.dump(vec, os.path.join(MODELS, "tfidf.pkl"))
    print(f"Wrote {MODELS}/classifier.pkl + tfidf.pkl (sklearn {sklearn.__version__})")


if __name__ == "__main__":
    main()
