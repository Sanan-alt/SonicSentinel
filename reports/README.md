# reports/ — Generated evidence (SRS sections 4, 6)

Reports are generated from **real** runs — nothing here is hand-written or faked.
The heavy live copies are written under `paths.output_root/reports/`
(`D:/sonicsentinel_data/reports/` by default) and mirrored here for submission by
the generator scripts.

## How to (re)generate everything

```
python src/train.py                 # metrics.json, confusion_matrix.{csv,png}, model_comparison_report.csv
python src/compare_models.py        # reports/comparison/model_comparison.{csv,json,md}
python src/generate_reports.py      # copies live reports into this folder + writes summaries
python scripts/final_srs_audit.py   # reports/final/SRS_FINAL_COMPLIANCE.{md,json}
python scripts/run_all_tests.py     # reports/final/final_validation_report.{md,json}
```

## Structure

```
reports/
├── training/       # training logs / hyperparameters chosen
├── evaluation/     # metrics.json, confusion_matrix.png, per-class metrics
├── comparison/     # Python vs GTM comparison report (>=100 unseen rows)
├── dataset/        # dataset_validation.{json,md}
├── quality/        # audio-quality distribution
├── alerts/         # alert statistics
└── final/          # SRS compliance + validation summaries
```

Last real training run (see `evaluation/metrics.json`): Python model **SVM**,
test accuracy **0.848**, macro-F1 **0.851**. These are actual held-out results,
not targets.
