# screenshots/ — Capture guide (SRS sections 5, 11, 13)

Screenshots must be captured from the **running system** and the **real Google
Teachable Machine project**. They are NOT generated or fabricated here — doing so
would violate the SRS anti-shortcut rules. This checklist tells you exactly what
to capture and the filename to save it as.

## Application screenshots (run `python webapp/app.py`, log in as admin)

| Save as | Page / action to capture |
|---|---|
| `01_login.png` | Login page |
| `02_dashboard.png` | Dashboard with live stats |
| `03_upload_result.png` | Audio Analysis after uploading a clip (Python prediction + confidences) |
| `04_comparison.png` | Model comparison panel (shows GTM state / BLOCKED if GTM not configured) |
| `05_waveform_spectrogram.png` | Waveform + spectrogram of an analysed clip |
| `06_live_monitor.png` | Live Monitor running with microphone |
| `07_critical_alert.png` | A critical alert generated |
| `08_alert_ack.png` | Acknowledging / escalating an alert |
| `09_manual_review.png` | Manual review queue + reviewer override |
| `10_event_history.png` | Event history with filters |
| `11_reports.png` | Reports page / CSV export |
| `12_admin_settings.png` | Admin alert-rule editor |
| `13_class_<name>.png` | One result screenshot per mandatory class (×10) |

## Google Teachable Machine screenshots (from teachablemachine.withgoogle.com)

Follow `documentation/GOOGLE_TEACHABLE_MACHINE.md`, then capture:

| Save as | What to capture |
|---|---|
| `gtm_01_classes.png` | All 10 classes created (+ Background Noise) |
| `gtm_02_sample_counts.png` | Training sample counts per class |
| `gtm_03_training.png` | Training configuration / progress |
| `gtm_04_export.png` | Export dialog (TensorFlow / TF.js) |
| `gtm_05_test.png` | A live test prediction in GTM |
| `gtm_06_integration.png` | The app showing GTM = configured after the export is placed |

> Once captured, place the PNGs directly in this folder and reference them from
> the final report / README.
