# GTM Integration Evidence (SRS section 5)

This documents how the real Google Teachable Machine model integrates with the
app. The integration code is complete and tested; the trained GTM artefact is
the one human-supplied piece (browser-only export).

## Integration code (present and tested)
- `webapp/services/gtm_service.py` — loads & validates a GTM export, exposes
  states `GTM_NOT_CONFIGURED / GTM_MODEL_INVALID / GTM_MODEL_READY`, and runs the
  model independently.
- `webapp/services/inference.py` — calls GTM on the same preprocessed audio,
  compares with Python, and marks the comparison `BLOCKED` when GTM is absent.
  The Python prediction is never copied into the GTM result.
- `gtm/export_dataset.py` — builds the import-ready GTM training dataset from the
  Python training split.

## Automated test
`tests/test_all_requirements.py::test_gtm_not_configured_is_honest` verifies the
service reports NOT_CONFIGURED and returns `None` (no fake prediction) when no
export is present. Once you place a real export, remove the skip on
`tests/test_srs_cases.py::test_gtm_real_prediction` to exercise real inference.

## What to attach as evidence (human, from the browser)
See `screenshots/README.md` (the `gtm_*` items) and fill
`models/gtm/metadata/model_metadata_template.json`:
- GTM project link
- screenshots of the 10 classes + Background Noise
- per-class training sample counts
- training configuration + observations
- incorrect-classification notes + retraining details
- the exported model files (placed in `models/gtm/export/`)
- a test-prediction screenshot
- a screenshot of the app showing GTM = configured after the export is added

## Current state
`GTM_NOT_CONFIGURED` — no export in `models/gtm/export/` yet. This is expected
until the browser export is added. The app remains fully functional on the Python
model and honestly reports the GTM comparison as BLOCKED.
