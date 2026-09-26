# data/ — Dataset deliverables (SRS section 3)

The **raw audio** and heavy generated copies are intentionally not committed
(licensing + size; see `.gitignore`). They live locally under `paths.output_root`
in `config/config.yaml` (default `D:/sonicsentinel_data/`).

This folder holds the **lightweight, committable dataset evidence**, produced by:

```
python src/organize.py            # build categorized dataset + metadata
python src/build_dataset_docs.py  # write the files below from that metadata
python src/validate_dataset.py    # quality + integrity report
```

## Layout

```
data/
├── raw/                     # (local) place source audio here; git-ignored
├── processed/               # (local) preprocessed copies; git-ignored
├── audio_dataset/           # (local) categorized clips per class; git-ignored
├── augmented/               # (local) augmented train clips; git-ignored
├── metadata/
│   ├── metadata.csv             # audio_id, class, source, hash, split, augmented…
│   ├── dataset_dictionary.md    # field definitions
│   ├── class_distribution.csv   # per-class / per-split counts
│   └── dataset_statistics.json  # totals, durations, sample rates, quality
└── splits/
    ├── train.csv
    ├── validation.csv
    └── test.csv
```

## Honesty note
All counts in these files are the **real** measured values. The current build
has **2,244 unique original clips (< the SRS 3,000 target)**; several classes are
below 300. `gunshot` and `panic_scream` currently use disclosed synthetic
placeholders (tagged `synthetic_*`). Drop real, ethically-sourced recordings into
`Dataset/<class>/` and re-run the commands above to update every file here.
