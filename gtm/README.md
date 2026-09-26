# Google Teachable Machine (GTM) Integration

Google Teachable Machine is a **browser-based** tool. Its audio model cannot be
created or trained from Python, so this folder contains everything around GTM
except the trained artefact itself, which a human must export from the browser.

## What is automated here

- `export_dataset.py` — builds `gtm/dataset_export/` with one folder per class
  (exact GTM class names), containing only the **training-split originals** used
  by the Python model. Upload these folders straight into a GTM Audio Project.
- `webapp/services/gtm_service.py` — loads and validates a real GTM export from
  `models/gtm/export/` and runs it independently. It never uses the Python model
  as a stand-in.

## What a human must do (the only manual step)

1. Run `python gtm/export_dataset.py`.
2. Open https://teachablemachine.withgoogle.com → **Audio Project**.
3. Create the 10 classes with the exact names in `documentation/GOOGLE_TEACHABLE_MACHINE.md`.
4. Upload the matching folder from `gtm/dataset_export/` into each class.
5. Train, then **Export → Tensorflow / Tensorflow.js**.
6. Place the export files into `models/gtm/export/`:
   - TensorFlow.js: `model.json` + `metadata.json` + weight shards, **or**
   - Keras: `model.h5` (or `model.savedmodel/`) + `labels.txt`.

## States the app reports (never faked)

| State | Meaning |
|---|---|
| `GTM_NOT_CONFIGURED` | No export present. App shows GTM = "Not available". |
| `GTM_MODEL_INVALID` | Files present but labels/format wrong. |
| `GTM_MODEL_READY` | Valid export loaded; independent GTM predictions available. |

Until a valid export is present, model comparison is marked
`BLOCKED — GTM model unavailable`. The Python prediction is **never** copied into
the GTM result.
