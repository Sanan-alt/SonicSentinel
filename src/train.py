"""Train and compare classification models (SRS Steps 7-9).

Trains TWO independent models on the SAME training split:
  * The Python model: the best of several compared algorithms (SVM, RF,
    Gradient Boosting, XGBoost), selected on validation macro-F1.
  * The GTM-substitute model: a separate, independently-trained model
    (a different algorithm family) standing in for the Google Teachable
    Machine audio model. It never sees the Python model's outputs.

Augmented feature vectors are used ONLY for training. Validation and test use
original clips only (SRS: val/test must not be used for training and are the
same unseen recordings for both models).

Saves:
  * python_models/sonicsentinel_model.joblib  (Python model bundle)
  * gtm_model/gtm_model.joblib                 (GTM-substitute bundle)
  * reports/metrics.json, confusion_matrix.csv/png

Run:
    python src/train.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sonic.config import load_config


def make_estimator(name: str, seed: int):
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.svm import SVC

    if name == "svm":
        return SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=seed)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=seed)
    if name == "gradient_boosting":
        return GradientBoostingClassifier(random_state=seed)
    if name == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.1,
            subsample=0.9, colsample_bytree=0.9,
            objective="multi:softprob", tree_method="hist",
            random_state=seed, n_jobs=-1, eval_metric="mlogloss",
        )
    raise ValueError(f"unknown model: {name}")


def param_grid(name: str) -> dict:
    """Small hyperparameter grids for tuning (SRS requirement xxiv)."""
    if name == "svm":
        return {"C": [1, 10, 50], "gamma": ["scale", 0.01]}
    if name == "random_forest":
        return {"n_estimators": [200, 400], "max_depth": [None, 30]}
    if name == "gradient_boosting":
        # Gradient boosting is slow to fit on the augmented set; keep a tiny
        # grid so tuning stays practical (it is not the top performer anyway).
        return {"n_estimators": [150]}
    if name == "xgboost":
        return {"max_depth": [4, 6], "learning_rate": [0.05, 0.1]}
    return {}


def tune_estimator(name: str, seed: int, X, y, enabled: bool):
    """Return the best estimator after a light GridSearchCV, or a default fit."""
    est = make_estimator(name, seed)
    if not enabled:
        est.fit(X, y)
        return est, {}
    from sklearn.model_selection import GridSearchCV

    grid = param_grid(name)
    if not grid:
        est.fit(X, y)
        return est, {}
    search = GridSearchCV(est, grid, scoring="f1_macro", cv=3, n_jobs=-1)
    search.fit(X, y)
    return search.best_estimator_, search.best_params_


def evaluate(estimator, X, y_true, class_names):
    from sklearn.metrics import (
        accuracy_score, classification_report, confusion_matrix,
        f1_score, precision_score, recall_score,
    )

    pred = estimator.predict(X)
    labels_idx = list(range(len(class_names)))
    return {
        "accuracy": accuracy_score(y_true, pred),
        "macro_f1": f1_score(y_true, pred, average="macro"),
        "macro_precision": precision_score(y_true, pred, average="macro", zero_division=0),
        "macro_recall": recall_score(y_true, pred, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, pred, labels=labels_idx),
        "report": classification_report(
            y_true, pred, labels=labels_idx, target_names=class_names,
            zero_division=0, output_dict=True,
        ),
        "pred": pred,
    }


def main() -> None:
    from sklearn.preprocessing import LabelEncoder, StandardScaler

    cfg = load_config()
    seed = int(cfg["training"]["seed"])
    np.random.seed(seed)

    features_path = cfg.path("features_file")
    if not features_path.exists():
        print("Features not found. Run: python src/extract_features.py", file=sys.stderr)
        sys.exit(1)

    data = np.load(features_path, allow_pickle=True)
    X, y, split = data["X"], data["y"], data["split"]
    augmented = data["augmented"] if "augmented" in data.files else np.zeros(len(y), dtype=bool)

    # Masks. Train may include augmented; val/test are originals only.
    train_mask = split == "train"
    val_mask = (split == "val") & (~augmented)
    test_mask = (split == "test") & (~augmented)

    present_classes = sorted(set(y[~augmented].tolist()))
    print(f"Classes with data ({len(present_classes)}): {', '.join(present_classes)}")

    encoder = LabelEncoder().fit(present_classes)
    scaler = StandardScaler().fit(X[train_mask])

    def prep(mask):
        return scaler.transform(X[mask]), encoder.transform(y[mask])

    X_tr, y_tr = prep(train_mask)
    X_val, y_val = prep(val_mask)
    X_te, y_te = prep(test_mask)
    class_names = list(encoder.classes_)
    print(f"Train={len(y_tr)} (incl. augmented)  Val={len(y_val)}  Test={len(y_te)}\n")

    # -- 1. Compare candidate Python models on validation --
    from sklearn.metrics import accuracy_score, f1_score

    tune = bool(cfg["training"].get("hyperparameter_tuning", True))
    comparison = []
    best_name, best_est, best_val_f1, best_params = None, None, -1.0, {}
    print(f"{'model':<20}{'val_acc':>9}{'val_macroF1':>13}  best_params")
    print("-" * 60)
    for name in cfg["training"]["models"]:
        try:
            est, params = tune_estimator(name, seed, X_tr, y_tr, tune)
        except Exception as error:  # noqa: BLE001
            print(f"{name:<20} (unavailable: {error})")
            continue
        vp = est.predict(X_val)
        acc = accuracy_score(y_val, vp)
        f1 = f1_score(y_val, vp, average="macro")
        comparison.append({"model": name, "val_accuracy": acc, "val_macro_f1": f1,
                           "best_params": params})
        print(f"{name:<20}{acc:>9.3f}{f1:>13.3f}  {params}")
        if f1 > best_val_f1:
            best_name, best_est, best_val_f1, best_params = name, est, f1, params
    print(f"\nBest Python model: {best_name} (val macro-F1={best_val_f1:.3f}) params={best_params}\n")

    # -- 2. Train the independent GTM-substitute model --
    gtm_name = cfg["training"].get("gtm_model", "random_forest")
    # If the GTM choice equals the Python best, pick a different family so the
    # two models are genuinely independent.
    if gtm_name == best_name:
        gtm_name = "gradient_boosting" if best_name != "gradient_boosting" else "random_forest"
    print(f"Training GTM-substitute model ({gtm_name}, independent)...")
    gtm_est, _ = tune_estimator(gtm_name, seed + 1, X_tr, y_tr, tune)

    # -- 3. Evaluate both on the held-out test set --
    py_eval = evaluate(best_est, X_te, y_te, class_names)
    gtm_eval = evaluate(gtm_est, X_te, y_te, class_names)

    critical = [c for c in cfg.critical_classes if c in class_names]

    def summarise(tag, ev):
        print("=" * 52)
        print(f"TEST-SET PERFORMANCE - {tag}")
        print("=" * 52)
        print(f"  Accuracy={ev['accuracy']:.3f}  MacroF1={ev['macro_f1']:.3f} "
              f"MacroP={ev['macro_precision']:.3f}  MacroR={ev['macro_recall']:.3f}")
        for c in critical:
            print(f"    critical recall [{c}]: {ev['report'][c]['recall']:.3f}")
        print()

    summarise(f"Python model ({best_name})", py_eval)
    summarise(f"GTM-substitute ({gtm_name})", gtm_eval)

    # -- 4. Save artefacts --
    import joblib

    models_dir = cfg.path("models_dir")
    gtm_dir = cfg.path("gtm_model_dir")
    reports_dir = cfg.path("reports_dir")
    for d in (models_dir, gtm_dir, reports_dir):
        d.mkdir(parents=True, exist_ok=True)

    feature_names_list = data["feature_names"].tolist()
    joblib.dump(
        {"model": best_est, "scaler": scaler, "label_encoder": encoder,
         "classes": class_names, "model_name": best_name,
         "feature_names": feature_names_list, "version": "1.0.0"},
        models_dir / "sonicsentinel_model.joblib",
    )
    joblib.dump(
        {"model": gtm_est, "scaler": scaler, "label_encoder": encoder,
         "classes": class_names, "model_name": gtm_name,
         "feature_names": feature_names_list, "version": "1.0.0"},
        gtm_dir / "gtm_model.joblib",
    )

    metrics = {
        "python_model": best_name,
        "gtm_model": gtm_name,
        "model_comparison": comparison,
        "classes": class_names,
        "n_train": int(len(y_tr)), "n_val": int(len(y_val)), "n_test": int(len(y_te)),
        "python": {
            "test_accuracy": py_eval["accuracy"], "test_macro_f1": py_eval["macro_f1"],
            "test_macro_precision": py_eval["macro_precision"],
            "test_macro_recall": py_eval["macro_recall"],
            "critical_class_recall": {c: py_eval["report"][c]["recall"] for c in critical},
            "per_class": py_eval["report"],
        },
        "gtm": {
            "test_accuracy": gtm_eval["accuracy"], "test_macro_f1": gtm_eval["macro_f1"],
            "test_macro_precision": gtm_eval["macro_precision"],
            "test_macro_recall": gtm_eval["macro_recall"],
            "critical_class_recall": {c: gtm_eval["report"][c]["recall"] for c in critical},
            "per_class": gtm_eval["report"],
        },
    }
    with (reports_dir / "metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(metrics, stream, indent=2)

    cm = py_eval["confusion_matrix"]
    np.savetxt(reports_dir / "confusion_matrix.csv", cm, fmt="%d", delimiter=",",
               header=",".join(class_names), comments="")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(cm, cmap="viridis")
        ax.set_xticks(range(len(class_names))); ax.set_yticks(range(len(class_names)))
        ax.set_xticklabels(class_names, rotation=45, ha="right")
        ax.set_yticklabels(class_names)
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        ax.set_title(f"Confusion Matrix - Python model ({best_name})")
        for i in range(len(class_names)):
            for j in range(len(class_names)):
                ax.text(j, i, int(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] < cm.max() / 2 else "black", fontsize=8)
        fig.colorbar(im, ax=ax); fig.tight_layout()
        fig.savefig(reports_dir / "confusion_matrix.png", dpi=120)
        plt.close(fig)
    except Exception as error:  # noqa: BLE001
        print(f"(confusion-matrix plot skipped: {error})", file=sys.stderr)

    # --- Per-recording model comparison report (SRS Deliverable 6) ---
    import csv as _csv

    audio_ids = data["audio_id"] if "audio_id" in data.files else np.array([""] * len(y))
    test_ids = audio_ids[test_mask]
    py_pred = best_est.predict(X_te)
    gtm_pred = gtm_est.predict(X_te)
    py_proba = best_est.predict_proba(X_te) if hasattr(best_est, "predict_proba") else None
    gtm_proba = gtm_est.predict_proba(X_te) if hasattr(gtm_est, "predict_proba") else None

    report_rows = []
    for i in range(len(y_te)):
        actual = class_names[y_te[i]]
        py_c = class_names[py_pred[i]]
        gtm_c = class_names[gtm_pred[i]]
        py_conf = round(float(py_proba[i][py_pred[i]]) * 100, 2) if py_proba is not None else ""
        gtm_conf = round(float(gtm_proba[i][gtm_pred[i]]) * 100, 2) if gtm_proba is not None else ""
        report_rows.append({
            "audio_id": test_ids[i] if i < len(test_ids) else "",
            "actual_class": actual,
            "python_pred": py_c, "python_conf": py_conf,
            "gtm_pred": gtm_c, "gtm_conf": gtm_conf,
            "class_match": "yes" if py_c == gtm_c else "no",
            "conf_difference": round(abs((py_conf or 0) - (gtm_conf or 0)), 2),
            "python_correct": "yes" if py_c == actual else "no",
            "gtm_correct": "yes" if gtm_c == actual else "no",
        })

    report_path = reports_dir / "model_comparison_report.csv"
    with report_path.open("w", encoding="utf-8", newline="") as fh:
        writer = _csv.DictWriter(fh, fieldnames=list(report_rows[0].keys()))
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"Saved Python model -> {models_dir / 'sonicsentinel_model.joblib'}")
    print(f"Saved GTM model    -> {gtm_dir / 'gtm_model.joblib'}")
    print(f"Saved reports      -> {reports_dir}")
    print(f"Model comparison report ({len(report_rows)} test recordings) -> {report_path}")


if __name__ == "__main__":
    main()
