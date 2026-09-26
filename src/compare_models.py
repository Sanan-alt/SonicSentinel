"""Model comparison report over unseen TEST recordings (SRS section 6).

Produces a per-recording comparison for the held-out test split:
  reports/comparison/model_comparison.csv
  reports/comparison/model_comparison.json
  reports/comparison/model_comparison.md

Fields per row (SRS section 6):
  audio_id, filename, actual_class,
  python_pred, python_conf, python_all_conf,
  gtm_pred, gtm_conf, gtm_all_conf,
  class_match, top_class_conf_diff, python_top_two_margin, gtm_top_two_margin,
  audio_quality, severity, alert_status, manual_review, final_decision,
  python_correct, gtm_correct, disagreement_reason

GTM columns are filled ONLY if a real Google Teachable Machine export is present
(models/gtm/export/). Otherwise they are honestly recorded as "NOT AVAILABLE"
and the summary states the GTM comparison is BLOCKED — the Python prediction is
never copied into the GTM column.

The SRS asks for >=100 unseen recordings with >=10 per class. The script reports
the REAL coverage; where a class has fewer than 10 test recordings it is listed
under "REQUIRED DATA NOT AVAILABLE" rather than being padded.

Run (after training):
    python src/compare_models.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "webapp"))

from sonic.config import load_config          # noqa: E402
from sonic.features import extract_features    # noqa: E402
from sonic.preprocessing import AudioSettings, load_audio  # noqa: E402


def _score(bundle, feats):
    vec = bundle["scaler"].transform(feats.reshape(1, -1))
    model = bundle["model"]
    classes = list(bundle["classes"])
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(vec)[0]
    else:
        idx = int(model.predict(vec)[0])
        proba = np.zeros(len(classes)); proba[idx] = 1.0
    scores = {classes[i]: round(float(proba[i]) * 100, 2) for i in range(len(classes))}
    top = int(np.argmax(proba))
    ordered = sorted(scores.values(), reverse=True)
    margin = round(ordered[0] - ordered[1], 2) if len(ordered) > 1 else ordered[0]
    return classes[top], round(float(proba[top]) * 100, 2), scores, margin


def main() -> None:
    import joblib

    cfg = load_config()
    settings = AudioSettings.from_config(cfg)

    py_path = cfg.path("models_dir") / "sonicsentinel_model.joblib"
    second_path = cfg.path("models_dir") / "python2" / "second_model.joblib"
    if not py_path.exists():
        print("Python model missing. Run: python src/train.py", file=sys.stderr)
        sys.exit(1)
    py_bundle = joblib.load(py_path)
    second_bundle = joblib.load(second_path) if second_path.exists() else None

    # Real GTM (honest): only used if a valid export exists.
    gtm = None
    try:
        from services.gtm_service import GTMService
        gtm = GTMService(cfg.path("gtm_model_dir") / "export", list(py_bundle["classes"]))
        if not gtm.configured:
            gtm = None
    except Exception:
        gtm = None

    # Alert engine + quality for per-row severity/decision.
    from services.alerts import AlertEngine
    from services import audio_io
    engine = AlertEngine.from_file(cfg.path("alert_rules"))

    # Test-split originals from metadata.
    meta_path = cfg.path("metadata_csv")
    rows = [r for r in csv.DictReader(meta_path.open(encoding="utf-8"))
            if r.get("split") == "test" and r.get("augmented", "original") == "original"]
    if not rows:
        print("No test recordings found. Run: python src/organize.py && extract && train", file=sys.stderr)
        sys.exit(1)

    out_rows = []
    py_correct = second_correct = gtm_correct = 0
    per_class_seen = Counter()

    for r in rows:
        p = cfg.output_root / r["relative_path"]
        if not p.exists():
            continue
        try:
            y = load_audio(p, settings)
            feats = extract_features(y, settings.sample_rate, cfg)
        except Exception:
            continue

        actual = r["class_label"]
        per_class_seen[actual] += 1

        py_c, py_conf, py_scores, py_margin = _score(py_bundle, feats)

        # Second independent Python model (comparison baseline, NOT GTM).
        if second_bundle is not None:
            s_c, s_conf, s_scores, s_margin = _score(second_bundle, feats)
        else:
            s_c, s_conf, s_scores, s_margin = None, None, {}, None

        # Real GTM if configured; else NOT AVAILABLE (never Python-copied).
        if gtm is not None:
            g = gtm.predict(y, settings.sample_rate)
        else:
            g = None
        if g is not None:
            gtm_c, gtm_conf, gtm_scores = g["predicted_class"], g["confidence"], g["scores"]
            gtm_margin = None
            gtm_available = True
        else:
            gtm_c, gtm_conf, gtm_scores, gtm_margin = "NOT AVAILABLE", "", {}, ""
            gtm_available = False

        quality = audio_io.assess_quality(y, settings.sample_rate)["quality"]
        # Comparison is between Python and GTM (SRS). If GTM unavailable, we still
        # report the Python-vs-second-model comparison for internal evidence.
        compare_to_c = gtm_c if gtm_available else s_c
        compare_to_conf = gtm_conf if gtm_available else s_conf
        class_match = "yes" if (compare_to_c is not None and py_c == compare_to_c) else "no"
        conf_diff = (round(abs(py_conf - (compare_to_conf or 0)), 2)
                     if compare_to_conf not in (None, "") else "")

        decision = engine.decide(py_c, py_conf, py_margin, quality,
                                 "Acceptable Match" if class_match == "yes" else "Model Disagreement")

        py_ok = py_c == actual
        s_ok = (second_bundle is not None) and (s_c == actual)
        g_ok = gtm_available and gtm_c == actual
        py_correct += int(py_ok)
        second_correct += int(s_ok)
        gtm_correct += int(g_ok)

        disagreement = ""
        if class_match == "no":
            disagreement = (f"Python={py_c} vs {'GTM' if gtm_available else 'model2'}="
                            f"{compare_to_c}; conf diff {conf_diff}")

        out_rows.append({
            "audio_id": r["audio_id"],
            "filename": r["filename"],
            "actual_class": actual,
            "python_pred": py_c,
            "python_conf": py_conf,
            "python_all_conf": json.dumps(py_scores),
            "second_model_pred": s_c,
            "second_model_conf": s_conf,
            "gtm_pred": gtm_c,
            "gtm_conf": gtm_conf,
            "gtm_all_conf": json.dumps(gtm_scores) if gtm_available else "NOT AVAILABLE",
            "class_match": class_match,
            "top_class_conf_diff": conf_diff,
            "python_top_two_margin": py_margin,
            "gtm_top_two_margin": gtm_margin,
            "audio_quality": quality,
            "severity": decision["severity"],
            "alert_status": decision["alert_status"],
            "manual_review": "yes" if decision["manual_review"] else "no",
            "final_decision": py_c,
            "python_correct": "yes" if py_ok else "no",
            "gtm_correct": ("yes" if g_ok else "no") if gtm_available else "N/A",
            "disagreement_reason": disagreement,
        })

    n = len(out_rows)
    reports_dir = cfg.path("reports_dir") / "comparison"
    reports_dir.mkdir(parents=True, exist_ok=True)
    # Also mirror into the repo reports/comparison for submission.
    repo_dir = _ROOT / "reports" / "comparison"
    repo_dir.mkdir(parents=True, exist_ok=True)

    for target in (reports_dir, repo_dir):
        with (target / "model_comparison.csv").open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        (target / "model_comparison.json").write_text(json.dumps(out_rows, indent=2), encoding="utf-8")

    # SRS coverage: >=100 rows, >=10 per class.
    short_classes = {c: per_class_seen.get(c, 0) for c in cfg.classes if per_class_seen.get(c, 0) < 10}
    summary = {
        "total_unseen_test_recordings": n,
        "meets_min_100": n >= 100,
        "per_class_test_counts": dict(per_class_seen),
        "classes_below_10_test_recordings": short_classes,
        "python_accuracy_on_report": round(py_correct / n, 4) if n else 0,
        "second_model_accuracy_on_report": (round(second_correct / n, 4)
                                            if (n and second_bundle is not None) else "N/A (second model not trained)"),
        "gtm_configured": gtm is not None,
        "gtm_comparison_status": "OK" if gtm is not None else "BLOCKED — GTM model unavailable",
    }

    md = ["# Model Comparison Report (unseen test set)", "",
          f"- **Unseen test recordings:** {n} ({'MEETS' if n >= 100 else 'BELOW'} the 100 minimum)",
          f"- **Python accuracy on this report:** {summary['python_accuracy_on_report']}",
          f"- **Second Python model accuracy:** {summary['second_model_accuracy_on_report']}",
          f"- **GTM comparison:** {summary['gtm_comparison_status']}",
          "", "## Per-class test coverage (SRS wants >=10 each)", "",
          "| Class | Test recordings | >=10? |", "|---|---:|:--:|"]
    for c in cfg.classes:
        cnt = per_class_seen.get(c, 0)
        md.append(f"| {c} | {cnt} | {'yes' if cnt >= 10 else 'NO'} |")
    if short_classes:
        md += ["", "### REQUIRED DATA NOT AVAILABLE",
               f"These classes have <10 unseen test recordings: {short_classes}. "
               "Import more real recordings and re-run the pipeline to satisfy the "
               ">=10-per-class requirement."]
    if gtm is None:
        md += ["", "### GTM columns",
               "GTM is not configured, so `gtm_pred`/`gtm_conf` are `NOT AVAILABLE` and the "
               "Python vs GTM comparison is BLOCKED. A second independent Python model is "
               "included (`second_model_*`) as an interim cross-model comparison. Configure a "
               "real GTM export (see documentation/GOOGLE_TEACHABLE_MACHINE.md) to complete this."]
    for target in (reports_dir, repo_dir):
        (target / "model_comparison.md").write_text("\n".join(md), encoding="utf-8")
        (target / "model_comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Comparison report: {n} unseen test recordings "
          f"({'>=100 OK' if n >= 100 else 'BELOW 100'})")
    print(f"  Python acc {summary['python_accuracy_on_report']}, "
          f"2nd model acc {summary['second_model_accuracy_on_report']}, "
          f"GTM: {summary['gtm_comparison_status']}")
    if short_classes:
        print(f"  Classes with <10 test recordings: {short_classes}")
    print(f"  Written to {repo_dir} (and {reports_dir})")


if __name__ == "__main__":
    main()
