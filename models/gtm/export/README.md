# Place your Google Teachable Machine export here

This folder is where the **human-exported** GTM audio model goes. It is empty on
purpose — the model must be created in the browser (see
`documentation/GOOGLE_TEACHABLE_MACHINE.md`).

Drop ONE of these layouts here:

- **TensorFlow.js:** `model.json`, `metadata.json`, and weight `*.bin` files.
- **Keras:** `model.h5` (or `model.savedmodel/`) and `labels.txt`.

`metadata.json` (tfjs) or `labels.txt` (Keras) must list all 10 class names.

Until a valid export is present, the application reports `GTM_NOT_CONFIGURED`
and marks model comparison as `BLOCKED — GTM model unavailable`. The Python
model is never used as a GTM stand-in.
