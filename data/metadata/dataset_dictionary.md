# Dataset Data Dictionary (SRS section 3)

| Field | Description |
|---|---|
| audio_id | Stable unique ID for the recording (e.g. `SS00042`), kept across all derived artefacts. |
| filename | Stored filename inside the categorized dataset. |
| class_label | One of the 10 mandatory SRS classes. |
| source | Origin of the clip (`esc50`, `mp3:<folder>`, `user_uploads`, `synthetic`). |
| original_filename | Filename as delivered by the source. |
| sha256 | SHA-256 content hash (exact-duplicate detection). |
| split | `train`, `val`, or `test` (stratified 70/15/15). |
| augmented | `original` for real recordings; augmentation name for derived train clips. |
| relative_path | Path of the stored clip relative to `output_root`. |

## Notes
- Validation and test rows are **originals only** (no augmentation leakage).
- Environment / device / source-distance are not known for public-source clips
  and are recorded as `unknown`; they are populated for any self-recorded audio.
- Synthetic placeholder clips (currently `gunshot`, `panic_scream`) are tagged in
  `source`/`augmented` and are **not** counted as unique real recordings.
