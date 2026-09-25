# Installation & Execution Guide — SonicSentinel AI

## Prerequisites
- **OS:** Windows / macOS / Linux
- **Python:** 3.11–3.13
- **RAM:** 8 GB+ recommended
- **Disk:** ~2 GB free for dependencies + generated artefacts

## 1. Get the code
```powershell
git clone https://github.com/Sanan-alt/SonicSentinel.git
cd SonicSentinel
```

## 2. Virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux
```

## 3. Install dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
> MP3/M4A decoding is handled by `soundfile` + `audioread`. If a format fails to
> decode on your system, install **FFmpeg** and add it to `PATH`.

## 4. Configure storage (important)
Generated data (dataset copies, features, models, uploads, database) is written
under `paths.output_root` in `config/config.yaml`. Set it to any location with
free space:
```yaml
paths:
  output_root: "D:/sonicsentinel_data"   # change as needed
```

## 5. Add audio data
Place raw audio under `Dataset/`:
- ESC-50 `.wav` clips in `Dataset/Dataset/audio/`
- Your hand-collected category folders (e.g. mp3) referenced in `config.yaml`.

## 6. Build the models
```powershell
python src/organize.py            # dedup + label + 70/15/15 stratified split + metadata
python src/extract_features.py    # acoustic features (+ train-only augmentation)
python src/train.py               # Python model + independent GTM-substitute + reports
```
Artefacts land under `output_root`:
- `python_models/sonicsentinel_model.joblib`
- `gtm_model/gtm_model.joblib`
- `reports/metrics.json`, `confusion_matrix.png`

## 7. Run the web app
```powershell
python webapp/app.py
```
Open http://localhost:5000. The SQLite database is created and seeded on first run.

**Demo accounts:** `admin@sonicsentinel.ai / admin`,
`operator@sonicsentinel.ai / operator`, `reviewer@sonicsentinel.ai / reviewer`.

## 8. Run tests
```powershell
python -m pytest tests -q
```

## Troubleshooting
| Problem | Fix |
|---|---|
| `Model unavailable` in the UI | Run `python src/train.py` first. |
| MP3/M4A won't decode | Install FFmpeg and add to PATH. |
| `No space left on device` | Point `output_root` at a drive with free space. |
| Mic not working in Live Monitor | Allow microphone permission in the browser. |

## Administrator / configuration
- **Alert rules:** edit `alert_rules/alert_rules.json` (severity, thresholds, actions).
- **Audio/feature settings:** edit `config/config.yaml`.
- **Add a sound class:** add real data + the class in `config.yaml`, then re-run steps 6.
