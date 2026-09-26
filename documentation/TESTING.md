# Testing (SRS section 8)

## Run everything

```powershell
python scripts/run_all_tests.py     # env + dataset validation + pytest + SRS audit
# or just the unit/functional suite:
python -m pytest -q
```

## Test files & coverage

| File | SRS categories covered |
|---|---|
| `tests/test_pipeline.py` | preprocessing, feature extraction, augmentation, alert engine (unit) |
| `tests/test_all_requirements.py` | 10-class config, upload formats, quality labels, severity mapping, GTM-not-configured honesty, Python inference + GTM-blocked, dataset size reported honestly |
| `tests/test_srs_cases.py` | audio-format, silence, clipping, noise, preprocessing, feature, low-confidence, model-disagreement, database CRUD + hashing (security), duplicate detection, overlap/top-k, boundary/negative |

## Category mapping

| SRS test category | Where |
|---|---|
| Functional | test_all_requirements, test_srs_cases |
| Integration | test_overlap_and_topk_present (model → inference → comparison) |
| Boundary | test_duration_bounds_exist, test_preprocessing_fixed_length |
| Negative | test_unsupported_format_rejected, test_silence_rejected |
| Security | test_database_crud_and_hashing (password hashing, no plaintext) |
| Database | test_database_crud_and_hashing, test_duplicate_detection_by_hash |
| Audio-format | test_unsupported_format_rejected, SUPPORTED_EXTS |
| Silence | test_silence_rejected |
| Clipping | test_clipping_detected |
| Noise | test_noise_quality_label |
| Preprocessing | test_preprocessing_fixed_length |
| Feature-extraction | test_feature_vector_deterministic_length |
| Python model | test_python_inference_and_gtm_blocked, test_overlap_and_topk_present |
| GTM model | test_gtm_not_configured_is_honest (+ test_gtm_real_prediction once configured) |
| Comparison | test_python_inference_and_gtm_blocked, compare_models.py |
| Alert-rule | test_alert_engine_severity_mapping, test_low_confidence_routes_to_review, test_model_disagreement_flagged |
| Duplicate-audio | test_duplicate_detection_by_hash |
| Low-confidence | test_low_confidence_routes_to_review |
| Overlapping-sound | test_overlap_and_topk_present |
| Microphone | manual (skipped in CI — needs a device) |

## Hidden-test readiness checklist

The app can demonstrate, on demand:

- [x] Every mandatory sound class — `python _verify.py` runs all 10 sample clips through the live API
- [x] Silent audio — rejected by `load_audio` / `audio_io` (test_silence_rejected)
- [x] Invalid audio — unsupported format / empty / oversized rejected (audio_io)
- [x] Low-quality audio — quality labelled Poor/Unusable (assess_quality)
- [x] Low-confidence result — routed to manual review (test_low_confidence_routes_to_review)
- [x] Model disagreement — flagged; when GTM configured, comparison marks disagreement
- [x] Overlapping sound — overlap detection via top-two margin / significant classes
- [x] Duplicate audio — SHA-256 duplicate detection (find_by_hash)
- [x] High-severity alert — gunshot/glass/etc. severity mapping + alert firing
- [x] Manual-review case — review queue + reviewer override (audited)
- [x] Real-time detection — Live Monitor with consecutive-window confirmation (manual mic test)

## Items needing external artefacts
- **Microphone tests** need a physical device — verified manually via Live Monitor.
- **Real GTM model tests** need a browser-exported GTM model in `models/gtm/export/`;
  until then GTM tests assert the honest NOT_CONFIGURED behaviour.
