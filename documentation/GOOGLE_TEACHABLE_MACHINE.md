# Google Teachable Machine (GTM) — Setup & Integration

The SRS requires a second, independently-trained audio model built with Google
Teachable Machine and compared against the Python model. GTM runs only in the
browser, so its trained model must be exported by a human. This document is the
complete, honest procedure. Nothing about GTM is faked in this repository.

## 1. Create the GTM Audio Project

1. Go to https://teachablemachine.withgoogle.com/
2. Choose **Get Started → Audio Project**.

## 2. Exact 10 class names

Create these classes with these exact names (they must match the Python labels):

1. Machinery Fault
2. Glass Breaking
3. Alarm or Siren
4. Vehicle Horn
5. Animal Sound
6. Gunshot
7. Panic Scream
8. Aggression
9. Person Asking for Help
10. Background Noise

GTM also requires a **Background Noise** class for calibration — we already have
it as class 10.

## 3. Prepare GTM training data

Run:

```
python gtm/export_dataset.py
```

This creates `gtm/dataset_export/<Class Name>/` folders containing **only the
training-split original recordings** that the Python model trained on. This
guarantees:

- GTM and Python use the **same underlying recordings** (SRS Step 5/9).
- Validation and test recordings are **never** given to GTM (no leakage).
- Every clip keeps its Audio ID as the filename.

## 4. Train GTM independently

Upload each `gtm/dataset_export/<Class>/` folder into the matching GTM class,
then click **Train Model**. GTM extracts its own audio features and trains its
own model — it never sees the Python model or its predictions.

## 5. Export and store the model

Click **Export Model** and choose one of:

- **TensorFlow.js** → download `model.json`, `metadata.json`, and the weight
  shard files.
- **TensorFlow → Keras** → download `model.h5` (or a `model.savedmodel/` folder)
  and `labels.txt`.

Place the exported files here:

```
models/gtm/export/
    model.json + metadata.json + *.bin        (TensorFlow.js)   OR
    model.h5 + labels.txt                      (Keras)
```

## 6. How the application uses the export

`webapp/services/gtm_service.py` validates the export on startup:

- Confirms the layout and that the labels cover all 10 required classes.
- For Keras exports, loads the model with TensorFlow (if installed) so GTM can
  produce **real, independent** predictions server-side.
- For TensorFlow.js exports, GTM runs in the browser client; the server marks
  the model present but notes that server-side inference needs a conversion.

## 7. Independent prediction & comparison

For each audio window/clip, the app:

1. Preprocesses the audio once (shared front-end recordings).
2. Runs the **Python** model → prediction + confidences.
3. Runs the **GTM** model **separately** → prediction + confidences.
4. Computes agreement, `confidence_difference = |py_top − gtm_top|`, and the
   top-two margin.

The Python prediction is **never** passed into GTM.

## 8. When GTM is not yet configured

If `models/gtm/export/` is empty or invalid, the app reports:

- `python.gtm.state = GTM_NOT_CONFIGURED` (or `GTM_MODEL_INVALID`)
- GTM prediction = **Not available**
- Comparison status = **BLOCKED — GTM model unavailable**

This is intentional and required by the SRS anti-shortcut rules: the app must
never present the Python model (or the secondary Python comparison model) as if
it were Google Teachable Machine.
