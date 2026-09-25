"""Train and compare Python classification models (SRS Steps 7-8).

Loads the extracted features, trains at least three models on the training
split, tunes them on validation, evaluates the best on the held-out test
split, and saves:
  * the best model + fitted scaler + label list (python_models/)
  * a metrics report + per-class report + confusion matrix (reports/)

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


def build_models(seed: int, names: list[str]) -> dict:
    """Instantiate the requested models. Each is a pipeline-ready estimator."""
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.svm import SVC

    registry = {
        "svm": SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=seed),
        "random_forest": RandomForestClassifier(
            n_estimators=400, max_depth=None, n_jobs=-1, random_state=seed
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=seed),
    }
    if "xgboost" in names:
        try:
            from xgboost import XGBClassifier

            registry["xgboost"] = XGBClassifier(
                n_estimators=400, max_depth=6, learning_rate=0.1,
                subsample=0.9, colsample_bytree=0.9,
                objective="multi:softprob", tree_method="hist",
                random_state=seed, n_jobs=-1, eval_metric="mlogloss",
            )
        except ImportError:
            print("xgboost not available; skipping.", file=sys.stderr)
    return {name: registry[name] for name in names if name in registry}


def main() -> None:
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )
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

    train_mask = split == "train"
    val_mask = split == "val"
    test_mask = split == "test"

    # Only classes that actually have data are used (Option A).
    present_classes = sorted(set(y.tolist()))
    print(f"Classes with data ({len(present_classes)}): {', '.join(present_classes)}\n")

    encoder = LabelEncoder().fit(present_classes)
    scaler = StandardScaler().fit(X[train_mask])

    def prep(mask):
        return scaler.transform(X[mask]), encoder.transform(y[mask])

    X_tr, y_tr = prep(train_mask)
    X_val, y_val = prep(val_mask)
    X_te, y_te = prep(test_mask)

    print(f"Train={len(y_tr)}  Val={len(y_val)}  Test={len(y_te)}\n")

    models = build_models(seed, list(cfg["training"]["models"]))
    comparison = []
    best_name, best_estimator, best_val_f1 = None, None, -1.0

    print(f"{'model':<20}{'val_acc':>9}{'val_macroF1':>13}")
    print("-" * 42)
    for name, estimator in models.items():
        estimator.fit(X_tr, y_tr)
        val_pred = estimator.predict(X_val)
        val_acc = accuracy_score(y_val, val_pred)
        val_f1 = f1_score(y_val, val_pred, average="macro")
        comparison.append({"model": name, "val_accuracy": val_acc, "val_macro_f1": val_f1})
        print(f"{name:<20}{val_acc:>9.3f}{val_f1:>13.3f}")
        if val_f1 > best_val_f1:
            best_name, best_estimator, best_val_f1 = name, estimator, val_f1

    print(f"\nBest model on validation: {best_name} (macro-F1={best_val_f1:.3f})\n")

    # --- Evaluate best model on held-out test set ---
    test_pred = best_estimator.predict(X_te)
    labels_idx = list(range(len(encoder.classes_)))
    class_names = list(encoder.classes_)

    test_acc = accuracy_score(y_te, test_pred)
    macro_f1 = f1_score(y_te, test_pred, average="macro")
    macro_precision = precision_score(y_te, test_pred, average="macro", zero_division=0)
    macro_recall = recall_score(y_te, test_pred, average="macro", zero_division=0)
    cm = confusion_matrix(y_te, test_pred, labels=labels_idx)
    report_dict = classification_report(
        y_te, test_pred, labels=labels_idx, target_names=class_names,
        zero_division=0, output_dict=True,
    )

    # Critical-class recall (SRS NFR-4).
    critical = [c for c in cfg.critical_classes if c in class_names]
    critical_recall = {c: report_dict[c]["recall"] for c in critical}

    print("=" * 52)
    print("TEST-SET PERFORMANCE (best model)")
    print("=" * 52)
    print(f"  Accuracy       : {test_acc:.3f}")
    print(f"  Macro F1       : {macro_f1:.3f}")
    print(f"  Macro Precision: {macro_precision:.3f}")
    print(f"  Macro Recall   : {macro_recall:.3f}\n")
    print(classification_report(
        y_te, test_pred, labels=labels_idx, target_names=class_names, zero_division=0
    ))
    if critical_recall:
        print("Critical-class recall:")
        for c, r in critical_recall.items():
            print(f"  {c:<26}{r:.3f}")

    # --- Save artefacts ---
    import joblib

    models_dir = cfg.path("models_dir")
    reports_dir = cfg.path("reports_dir")
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        {
            "model": best_estimator,
            "scaler": scaler,
            "label_encoder": encoder,
            "classes": class_names,
            "model_name": best_name,
            "feature_names": data["feature_names"].tolist(),
            "version": "1.0.0",
        },
        models_dir / "sonicsentinel_model.joblib",
    )

    metrics = {
        "best_model": best_name,
        "test_accuracy": test_acc,
        "test_macro_f1": macro_f1,
        "test_macro_precision": macro_precision,
        "test_macro_recall": macro_recall,
        "critical_class_recall": critical_recall,
        "model_comparison": comparison,
        "per_class": report_dict,
        "classes": class_names,
        "n_train": int(len(y_tr)),
        "n_val": int(len(y_val)),
        "n_test": int(len(y_te)),
    }
    with (reports_dir / "metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(metrics, stream, indent=2)

    # Confusion matrix as CSV + PNG.
    np.savetxt(
        reports_dir / "confusion_matrix.csv",
        cm, fmt="%d", delimiter=",",
        header=",".join(class_names), comments="",
    )
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(cm, cmap="viridis")
        ax.set_xticks(range(len(class_names)))
        ax.set_yticks(range(len(class_names)))
        ax.set_xticklabels(class_names, rotation=45, ha="right")
        ax.set_yticklabels(class_names)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(f"Confusion Matrix - {best_name}")
        for i in range(len(class_names)):
            for j in range(len(class_names)):
                ax.text(j, i, int(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] < cm.max() / 2 else "black", fontsize=8)
        fig.colorbar(im, ax=ax)
        fig.tight_layout()
        fig.savefig(reports_dir / "confusion_matrix.png", dpi=120)
        plt.close(fig)
    except Exception as error:  # noqa: BLE001
        print(f"(confusion-matrix plot skipped: {error})", file=sys.stderr)

    print(f"\nSaved model -> {models_dir / 'sonicsentinel_model.joblib'}")
    print(f"Saved reports -> {reports_dir}")


if __name__ == "__main__":
    main()
