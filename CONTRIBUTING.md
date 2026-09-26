# Contributing

## Development setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
```

## Workflow
- Keep the pipeline in `src/` as the single source of truth; the web app and the
  re-export folders (`audio_preprocessing/`, `feature_extraction/`, `augmentation/`,
  `database/`) import from it — do not fork logic.
- Run `python -m pytest -q` before committing.
- Regenerate evidence after any pipeline change:
  `python src/organize.py && python src/extract_features.py && python src/train.py`
  then `python src/build_dataset_docs.py`, `python src/compare_models.py`,
  `python src/generate_reports.py`, `python scripts/final_srs_audit.py`.

## Commit conventions
- Meaningful, scoped commits. Stage specific files (avoid `git add .`).
- Never commit `.env`, secrets, the raw `Dataset/`, or heavy generated artefacts
  (they are git-ignored).

## Team commits
Each team member should author commits under their own Git identity so the
public repository shows contributions from all members (SRS section 11).

## Honesty rules (SRS anti-shortcut)
- No hardcoded predictions/confidences/metrics.
- No fabricated dataset counts, screenshots, GTM evidence, or deployment URLs.
- Mark blocked items honestly (`BLOCKED_BY_REAL_DATA`, `BLOCKED_BY_EXTERNAL_GTM`).
