<div align="center">

# 🔊 SonicSentinel AI

### *AcousticX Intelligence — Real-time Sound-Event Detection*

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=3000&pause=1000&color=00E5FF&center=true&vCenter=true&width=700&lines=Listening+for+what+matters.;Gunshots.+Glass.+Screams.+Alarms.;Powered+by+Python+%2B+Machine+Learning." alt="Typing SVG" />

<br/>

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Librosa](https://img.shields.io/badge/Librosa-Audio-FF6F00?style=for-the-badge)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-Boosting-EC0000?style=for-the-badge)
![License](https://img.shields.io/badge/License-See%20LICENSE-4CAF50?style=for-the-badge)

<br/>

`Category: NextWave AI and ML` &nbsp;•&nbsp; `Theme: AcousticX Intelligence`

</div>

---

## 🎯 What is SonicSentinel?

SonicSentinel AI listens to uploaded audio and live microphone input, then automatically
detects critical sound events — **machinery faults, glass breaking, alarms, gunshots,
panic screams, aggression, calls for help** and more — so responders never miss what matters.

This repository contains the **Python machine-learning pipeline**: data organisation,
audio preprocessing, acoustic feature extraction, and multi-model training with full
evaluation reports.

---

## 🧩 The 10 Mandatory Sound Classes

<div align="center">

| 🛠️ Machinery Fault | 🪟 Glass Breaking | 🚨 Alarm / Siren | 📯 Vehicle Horn | 🐾 Animal Sound |
|:---:|:---:|:---:|:---:|:---:|
| **🔫 Gunshot** | **😱 Panic Scream** | **🗣️ Person Asking for Help** | **💢 Aggression** | **🌫️ Background Noise** |

</div>

---

## 🗂️ Project Structure

```
SonicSentinel/
├── config/
│   └── config.yaml            # central config (paths, audio, features, models, augmentation)
├── src/                       # ML pipeline
│   ├── sonic/                 # core package
│   │   ├── config.py          # config loader + path resolver
│   │   ├── labels.py          # ESC-50 -> SRS class mapping
│   │   ├── preprocessing.py   # load / mono / resample / trim / normalise / pad
│   │   ├── features.py        # MFCC, mel, chroma, ZCR, RMS, spectral features
│   │   └── augmentation.py    # noise / shift / pitch / stretch / reverb / distance / device
│   ├── organize.py            # build dataset + metadata (dedup + stratified split)
│   ├── extract_features.py    # extract features (+ train-only augmentation) to .npz
│   ├── train.py               # train Python model + independent GTM-substitute; reports
│   └── predict.py             # CLI single-clip prediction
├── webapp/                    # Flask web application
│   ├── app.py                 # routes, auth, real inference, alerts, DB
│   ├── services/              # database, audio_io, visuals, inference, alerts, categories
│   ├── templates/             # Jinja pages (dashboard, live, analysis, reviews, reports…)
│   └── static/                # CSS + JS (wired to the real API)
├── alert_rules/
│   └── alert_rules.json       # configurable alert rules (severity, thresholds, actions)
├── tests/                     # pytest suite (preprocessing, features, augmentation, alerts)
├── sample_audio/              # one demo clip per available class
├── esc50.csv                  # ESC-50 target -> category reference
├── requirements.txt · AI_USAGE.md · LICENSE · README.md
```

> 🔒 The raw audio dataset and generated model artefacts are intentionally **not** committed
> (see `.gitignore`). They are kept locally or in Git LFS / object storage because of size.

---

## 🔬 The Pipeline

```mermaid
flowchart LR
    A[Raw Audio<br/>ESC-50 + mp3] --> B[organize.py<br/>dedup + label + split]
    B --> C[extract_features.py<br/>librosa features]
    C --> D[train.py<br/>SVM · RF · GBoost · XGB]
    D --> E[Best Model + Reports<br/>accuracy · F1 · confusion matrix]
    E --> F[predict<br/>10-class confidence]
```

**Acoustic features extracted** (SRS Step 6): MFCC + delta, Mel spectrogram (dB),
Chroma, Zero-crossing rate, RMS energy, Spectral centroid / bandwidth / roll-off.

**Models compared** (SRS Step 7 — at least three): Support Vector Machine,
Random Forest, Gradient Boosting, XGBoost. The best model is selected on macro-F1.

---

## 🚀 Quick Start

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Place raw audio under Dataset/  (ESC-50 wavs + your mp3 category folders)

# 4. Train the models
python src/organize.py            # build dataset + metadata (dedup + stratified split)
python src/extract_features.py    # extract features (+ train-only augmentation)
python src/train.py               # train Python model + independent GTM-substitute

# 5. Launch the web app
python webapp/app.py              # http://localhost:5000
```

Demo accounts (created on first run): `admin@sonicsentinel.ai` / `admin`,
`operator@sonicsentinel.ai` / `operator`, `reviewer@sonicsentinel.ai` / `reviewer`.

All paths, audio settings, feature parameters, augmentation, the model list, and
**alert rules** (`alert_rules/alert_rules.json`) are configurable without code changes.

> **Note on storage:** heavy generated artefacts (dataset copies, features, models,
> uploads, database) are written under `paths.output_root` in `config/config.yaml`.
> Point it at any drive with free space.

## 🖥️ Web Application

| Page | What it does |
|:---|:---|
| **Dashboard** | Live telemetry from the real event database |
| **Audio Analysis** | Upload a clip → real dual-model prediction, confidence comparison, quality, waveform + spectrogram |
| **Live Monitor** | Web-Audio mic capture; ~2s windows are sent to the models on peak |
| **Critical Events** | Auto-generated high/critical alerts |
| **Manual Review** | Low-confidence / disagreement / poor-quality events queued for reviewers |
| **Event History / Reports** | Full audit trail + CSV export |

Every prediction is produced by the trained Python and GTM-substitute models —
**no random numbers, no hard-coded results** (per SRS anti-shortcut rules).

---

## 📊 Dataset & Metadata

`organize.py` produces a `dataset_metadata.csv` with the SRS-required fields:

| audio_id | filename | class_label | source | original_filename | sha256 | split | augmented |
|:--------:|:--------:|:-----------:|:------:|:-----------------:|:------:|:-----:|:---------:|

- **De-duplication** via SHA-256 (identical re-uploads are dropped automatically).
- **Stratified split** — 70% train / 15% validation / 15% test, per class.
- Every clip keeps a stable **Audio ID** across all derived artefacts.

---

## 🎯 Targets (SRS Non-Functional Requirement)

<div align="center">

| Metric | Target |
|:---|:---:|
| Overall test accuracy | **≥ 85%** |
| Macro F1-score | **≥ 0.80** |
| Critical-class recall<br/>(gunshot, glass, scream, aggression, help) | **≥ 85%** |

</div>

---

## ⚠️ Current Data Status

This is an active build. Real recordings still need to be collected for a few classes
(`gunshot`, `panic_scream`, `person_asking_for_help`). The training pipeline runs on
whatever classes currently have real, correctly-labelled data — and re-runs cleanly the
moment new audio is dropped into `Dataset/` and `python src/organize.py` is run again.

We do **not** mislabel or synthesise fake class data (per SRS anti-shortcut rules).

---

<div align="center">

Made with 🎧 for the **NextWave AI and ML** challenge.

</div>
