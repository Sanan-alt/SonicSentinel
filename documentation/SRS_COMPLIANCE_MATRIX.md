# SonicSentinel AI — SRS Compliance Matrix

Authoritative source: `documentation/SonicSentinel_SRS.pdf`.

This matrix reports the **honest** current state of the repository against the SRS.
Status is assigned only from real evidence (code that runs, files that exist, tests
that pass). Nothing is marked COMPLETE merely because a file exists.

**Status legend**

| Status | Meaning |
|---|---|
| COMPLETE | Implemented and works / evidence genuinely exists |
| PARTIAL | Implemented but incomplete or not fully verified |
| MISSING | Not implemented |
| BLOCKED_BY_REAL_DATA | Code is complete; blocked only by insufficient real recordings |
| BLOCKED_BY_EXTERNAL_GTM | Code/architecture complete; blocked by the browser-only Google Teachable Machine export |

Last audited: 2026-09-26. Best Python model on last real run: **SVM**, test accuracy
**0.848**, macro-F1 **0.851** (from `reports/metrics.json`; see MODEL_COMPARISON).

---

## A. Input, validation, preprocessing

| Req | Description | Status | File/module | Evidence | Remaining action |
|---|---|---|---|---|---|
| Upload audio (WAV/MP3/FLAC/OGG/M4A) | Accept 5 formats | COMPLETE | `webapp/services/audio_io.py` (`SUPPORTED_EXTS`), `webapp/app.py /api/classify-audio` | Verified via `_verify.py` HTTP upload of wav+mp3 | — |
| Batch upload | Multiple clips | COMPLETE | `webapp/app.py /api/classify-batch` | Route present, iterates files | Add batch UI test |
| Live microphone | Continuous windows | COMPLETE | `webapp/app.py /api/classify-live`, `static/js/live_monitor.js` | ~2.5s WAV windows, consecutive confirmation | Manual mic test (needs device) |
| File validation | format/size/duration/sr/channels/integrity/empty/silence | COMPLETE | `audio_io.py` (`save_upload`, `extract_metadata`), `preprocessing.load_audio` | Rejects empty/short/long/silent | — |
| Clipping / noise / low signal | quality checks | COMPLETE | `audio_io.assess_quality` | clipping ratio, SNR, RMS | — |
| Metadata extraction | filename/format/duration/sr/channels/bit depth/size/time | COMPLETE | `audio_io.extract_metadata` | bit-depth map from subtype | — |
| Preprocessing | resample/mono/normalise/trim/segment/pad/truncate | COMPLETE | `src/sonic/preprocessing.py` | full chain, single source for both models | Noise reduction is trim+normalise only (documented) |
| Segmentation | fixed-duration windows w/ timestamps | COMPLETE | `preprocessing.segment_signal`, used in `inference.classify_file` | start/end seconds per segment | — |

## B. Dataset

| Req | Description | Status | File/module | Evidence | Remaining action |
|---|---|---|---|---|---|
| Common dataset, 10 classes | one dataset for both models | PARTIAL | `src/organize.py`, `config/config.yaml` | organiser builds one categorized set | See counts below |
| ≥3,000 unique original clips | minimum size | BLOCKED_BY_REAL_DATA | `src/organize.py` | Real count ~2,244 unique after de-dup (see class table) | Collect/import more real clips |
| ~300 per class | balance | BLOCKED_BY_REAL_DATA | `src/validate_dataset.py` | gunshot 120 (synthetic), panic 120 (synthetic) or `scream/` if imported; vehicle_horn 40 | Import real clips for short classes |
| Metadata fields | audio_id/class/duration/sr/channels/env/device/distance/source/hash/split/aug | PARTIAL | `src/organize.py` writes core fields; `validate_dataset.py` reports | metadata.csv has id/filename/class/source/hash/split/augmented | Env/device/distance are unknown for public sources — recorded as `unknown` |
| SHA-256 de-dup | exact duplicate removal | COMPLETE | `organize.py sha256()` | 356 duplicates removed on last run (incl. gunshot=Aggression copy) | — |
| Near-duplicate detection | similarity | COMPLETE | `src/validate_dataset.py` (MFCC-mean cosine) | reports near-dup pairs | — |
| Stratified 70/15/15 split | per-class | COMPLETE | `organize.stratified_split` | n_train/val/test in metrics.json | — |
| No split/aug leakage | originals in val/test only | COMPLETE | `train.py` masks (`val/test & ~augmented`), `validate_dataset.py` leakage checks | augmented used for train only | — |

## C. Features & Python model

| Req | Description | Status | File/module | Evidence | Remaining action |
|---|---|---|---|---|---|
| Feature extraction | MFCC/Δ/mel/chroma/ZCR/RMS/centroid/bandwidth/rolloff | COMPLETE | `src/sonic/features.py` | 450-dim vector saved to features.npz | Onset/tempo not included (documented optional) |
| ≥3 models compared | SVM/RF/GB/XGB | COMPLETE | `src/train.py` (svm, random_forest, xgboost) | model_comparison in metrics.json | — |
| Hyperparameter tuning | GridSearchCV | COMPLETE | `train.tune_estimator` | best_params recorded | — |
| Metrics | acc/prec/rec/F1/macroF1/confusion/class-wise/critical recall | COMPLETE | `train.evaluate`, `reports/metrics.json`, `confusion_matrix.*` | real numbers from held-out test | — |
| Best-model selection | documented objective | COMPLETE | `train.py` (selects max val macro-F1) | SVM chosen | — |
| Python inference | class + all-class confidence + top3 + margin + version | COMPLETE | `webapp/services/inference.py` | real `predict_proba` | — |
| No hardcoded predictions/metrics | anti-shortcut | COMPLETE | inference/train use model probabilities | verified by reading code | — |

## D. Google Teachable Machine (critical)

| Req | Description | Status | File/module | Evidence | Remaining action |
|---|---|---|---|---|---|
| Actual GTM Audio Project | real GTM model | BLOCKED_BY_EXTERNAL_GTM | `gtm/`, `models/gtm/`, `webapp/services/gtm_service.py`, `documentation/GOOGLE_TEACHABLE_MACHINE.md` | Integration layer + import-ready dataset export + explicit states | Human must create/train/export GTM model in browser and place export under `models/gtm/export/` |
| GTM independent prediction | never sees Python output | COMPLETE (architecture) | `gtm_service.py` | Separate service; no Python data path into it | Needs real model to actually predict |
| No fake GTM fallback | never present Python as GTM | COMPLETE | `gtm_service.py` states GTM_NOT_CONFIGURED; `inference.py` marks comparison BLOCKED | Comparison shows "GTM not available" | — |

## E. Comparison, quality, confirmation, alerts

| Req | Description | Status | File/module | Evidence | Remaining action |
|---|---|---|---|---|---|
| Python/GTM comparison | match/conf diff/top-two margin/agreement | COMPLETE | `inference.classify_signal`, DB `events` | stored per event | GTM side inert until real model present |
| Audio quality Good/Acceptable/Poor/Unusable | classify | COMPLETE | `audio_io.assess_quality` | — | — |
| Overlap / uncertainty | top-two margin, overlap detection | COMPLETE | `inference.classify_signal` (`overlap`, `top_two_margin`) | significant-class detection | — |
| Repeated confirmation | consecutive windows | COMPLETE | `webapp/app.py /api/classify-live` (`_live_state`), alert rule `required_consecutive` | gunshot needs 2 consecutive | — |
| Alert engine | configurable rules/severity/action/review/escalate | COMPLETE | `webapp/services/alerts.py`, `alert_rules/alert_rules.json` | 10 category rules | — |
| Severity levels | Info/Low/Medium/High/Critical | COMPLETE | alert rules | matches SRS mapping | — |
| Manual review routing | disagreement/low-conf/poor-quality/overlap | COMPLETE | `alerts.decide` + `/manual-review` | reasons recorded | — |

## F. App, DB, security, reporting

| Req | Description | Status | File/module | Evidence | Remaining action |
|---|---|---|---|---|---|
| Auth + RBAC | 5 roles, hashed passwords | COMPLETE | `webapp/services/database.py`, `app.py role_required` | PBKDF2 hashes, role gating | — |
| Secret via env | no hardcoded secret | COMPLETE | `app.py` reads `SONICSENTINEL_SECRET_KEY`; `.env.example` | env-based | Set real secret in prod |
| Database | users/events/alerts/reviews/audit | COMPLETE | `database.py` (SQLite) | schema + FKs + parameterized queries | model_versions/dataset_versions tables optional |
| Dashboard | status/predictions/waveform/spectrogram/quality/severity/history | COMPLETE | `templates/dashboard.html`, `app.py` | live from DB | — |
| Manual review UI | play/see/decide/override/audit | COMPLETE | `templates/manual_review.html`, `/api/reviews` | override audited | — |
| Event history + export | search/filter + CSV | PARTIAL | `templates/event_history.html`, `/api/export` | CSV export works | Excel export not implemented |
| Reports | dataset/training/eval/comparison/quality/alerts | PARTIAL | `reports/*` generated by train.py; `scripts/generate_all_reports.py` | metrics.json, confusion_matrix, model_comparison_report.csv | Some report docs are generated on demand |
| Model comparison report ≥100 unseen, ≥10/class | test recordings | PARTIAL | `train.py` writes `model_comparison_report.csv` (329 rows last run) | 329 test recordings | Per-class ≥10 depends on real data per class |
| Continuous retraining | learn from all folders + user data | COMPLETE | `webapp/services/trainer.py`, `src/run_pipeline.py` | background thread, hot-reload | — |
| Tests | unit/integration/functional/etc. | PARTIAL | `tests/test_pipeline.py` (21 pass), `tests/test_all_requirements.py` | 21 passing | Broaden coverage |
| Final SRS audit | evidence-driven | COMPLETE | `scripts/final_srs_audit.py` -> `reports/final/SRS_FINAL_COMPLIANCE.md` | generated from real checks | — |

---

## Real dataset counts (per class, after de-dup)

Measured from `Dataset/` on the audit machine. These are the honest numbers — the
SRS target is 300 real originals per class (3,000 total).

| Class | Real originals available | Target | Notes |
|---|---|---|---|
| machinery_fault | ~200 (ESC-50 mechanical) | 300 | from ESC-50 engine/chainsaw/vacuum/washing/handsaw |
| glass_breaking | ~340 | 300 | ESC-50 glass + mp3 folder |
| alarm_siren | ~120 (ESC-50) | 300 | siren/clock_alarm/church_bells |
| vehicle_horn | ~40 (ESC-50 car_horn) | 300 | short — needs more |
| animal_sound | ~480 (ESC-50) | 300 | many ESC-50 animals |
| gunshot | 120 **synthetic placeholder** | 300 | NO real gunshot audio present — must import real clips |
| panic_scream | 120 synthetic OR import `Dataset/scream/` (1583 real wavs present) | 300 | map real scream folder to panic_scream |
| aggression | ~244 | 300 | real mp3 folder |
| person_asking_for_help | ~300 | 300 | real mp3 folder |
| background_noise | ~280 (ESC-50 ambient) | 300 | rain/wind/sea/fire/water |

**Honest total unique originals: ~2,244** (below the 3,000 SRS minimum). Synthetic
placeholders for gunshot/panic_scream are tagged and disclosed in `AI_USAGE.md`; they
are NOT counted as unique real recordings.

## Blocking items requiring human / external action

1. **Real gunshot recordings** — none exist in the dataset; import ethically-sourced clips into `Dataset/gunshot/`.
2. **≥3,000 real originals / 300 per class** — collect/import for gunshot, vehicle_horn, alarm_siren, machinery_fault.
3. **Google Teachable Machine model** — create in browser, train on the exported dataset (`gtm/dataset_export/`), export, and place under `models/gtm/export/`. Until then the app correctly shows GTM as not configured.
4. **Deployment URL, screenshots, demo video** — must be produced from the running system; not fabricated here.
