# notebooks/ — Analysis notebooks (SRS section 2)

The pipeline is implemented as reproducible **scripts** (under `src/`), which is
the source of truth for grading. These notebooks are thin, optional wrappers that
call the same scripts so reviewers can explore interactively.

| Notebook | Wraps | Purpose |
|---|---|---|
| `01_dataset_analysis.ipynb` | `src/validate_dataset.py` | class balance, duplicates, quality |
| `02_feature_analysis.ipynb` | `src/sonic/features.py` | feature distributions |
| `03_model_training.ipynb` | `src/train.py` | train + compare models |
| `04_model_evaluation.ipynb` | `reports/metrics.json` | confusion matrix, per-class metrics |
| `05_model_comparison.ipynb` | `src/compare_models.py` | Python vs GTM comparison report |

To run any pipeline step without a notebook, use the equivalent script command
documented in the top-level `README.md`. Notebooks are provided for convenience;
they do not contain logic that is not already in `src/`.
