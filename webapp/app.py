"""SonicSentinel AI - Flask application (real backend).

Reuses the existing UI (templates/static) but replaces the demo internals with:
  * a real SQLite database (users, events, alerts, reviews, audit),
  * hashed-password auth with role gating,
  * real audio upload/validation/storage + metadata + quality,
  * dual-model inference (Python + independent GTM-substitute) with comparison,
  * a configurable alert-rule engine,
  * waveform + spectrogram generation.

Run:
    python webapp/app.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask, flash, jsonify, redirect, render_template,
    request, send_from_directory, session, url_for,
)

# Make src/ and services importable.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "webapp"))

from sonic.config import load_config                       # noqa: E402
from sonic.preprocessing import AudioSettings, load_audio  # noqa: E402
from services import audio_io                              # noqa: E402
from services.categories import (                          # noqa: E402
    MANDATORY_SOUND_CATEGORIES, UI_TO_PIPELINE, category_meta, display_name, ui_key,
)
from services.database import Database                     # noqa: E402
from services import visuals                               # noqa: E402

USER_ROLES = [
    "Normal user", "Audio reviewer", "Security operator",
    "Maintenance operator", "Administrator",
]

cfg = load_config()
app = Flask(__name__)
app.secret_key = "sonicsentinel-secret-key-2026-acoustic-ai"

db = Database(cfg.path("database"))
db.init_db(seed=True)

# Inference service is loaded lazily so the app still starts if models aren't
# trained yet (it will just report that classification is unavailable).
_inference = None
_inference_error = None


def get_inference():
    global _inference, _inference_error
    if _inference is None and _inference_error is None:
        try:
            from services.inference import InferenceService
            _inference = InferenceService(cfg)
        except Exception as error:  # noqa: BLE001
            _inference_error = str(error)
    return _inference


def _reload_inference():
    """Hot-reload the models after the background trainer retrains them."""
    global _inference, _inference_error
    _inference, _inference_error = None, None
    get_inference()


# Continuous background trainer: keeps models current with all Dataset folders
# and user-contributed clips while the app runs (SRS: dataset-driven retraining).
# Runs off the request path. Disable by setting env SONIC_BG_TRAIN=0.
import os  # noqa: E402

_trainer = None
if os.environ.get("SONIC_BG_TRAIN", "1") != "0":
    try:
        from services.trainer import BackgroundTrainer
        _interval = int(os.environ.get("SONIC_TRAIN_INTERVAL", "900"))
        _trainer = BackgroundTrainer(cfg, reload_callback=_reload_inference,
                                     interval_sec=_interval)
        _trainer.start()
    except Exception as _err:  # noqa: BLE001
        print(f"[trainer] background training disabled: {_err}")


# ---------------------------------------------------------------- helpers
def _rel_visual(path: Path | None) -> str | None:
    """Convert an absolute visual path to a /media URL, or None."""
    if not path:
        return None
    return url_for("media", subpath=Path(path).name)


def event_to_view(ev: dict) -> dict:
    """Shape a DB event row into the dict the templates expect."""
    if not ev:
        return {}
    created = ev.get("created_at", "")
    return {
        "id": ev["id"],
        "category": display_name(ev.get("final_class") or ""),
        "category_key": ui_key(ev.get("final_class") or ""),
        "severity": ev.get("severity") or "Informational",
        "confidence_py": round(ev.get("py_confidence") or 0, 1),
        "confidence_tm": round(ev.get("gtm_confidence") or 0, 1),
        "location": ev.get("source_mode", "upload").title(),
        "timestamp": created.replace("T", " ")[:19] if created else "",
        "duration": f"{ev.get('duration') or 0:.1f}s",
        "snr_db": ev.get("audio_quality") or "-",
        "status": ev.get("status") or "Classified",
        "sample_type": ev.get("final_class") or "",
        "agreement": ev.get("agreement"),
        "alert_status": ev.get("alert_status"),
        "manual_review": ev.get("manual_review"),
    }


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def _norm_role(role: str) -> str:
    """Normalise a role to a slug so seed slugs and display strings both match.

    e.g. 'Audio reviewer' -> 'audio_reviewer', 'administrator' -> 'administrator'.
    """
    return (role or "").strip().lower().replace(" ", "_")


def role_required(*roles):
    allowed = {_norm_role(r) for r in roles} | {"administrator"}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            wants_json = request.path.startswith("/api/")
            if not user:
                if wants_json:
                    return jsonify({"error": "Login required."}), 401
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if _norm_role(user.get("role")) not in allowed:
                if wants_json:
                    return jsonify({"error": "You do not have permission for this action."}), 403
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.context_processor
def inject_global_data():
    return {
        "current_user": session.get("user"),
        "sound_categories": MANDATORY_SOUND_CATEGORIES,
        "user_roles": USER_ROLES,
        "active_units_online": db.stats().get("total_events", 0),
    }


# ------------------------------------------------------------------ pages
@app.route("/")
def index():
    recent = [event_to_view(e) for e in db.list_events(limit=4)]
    return render_template("index.html", recent_events=recent)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.verify_login(email, password)
        if user:
            session["user"] = {
                "id": user["id"], "name": user["name"], "email": user["email"],
                "role": user["role"], "department": user.get("department", "General"),
            }
            db.audit(email, "login", "successful login")
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        db.audit(email, "login_failed", "invalid credentials")
        flash("Invalid email or password. Try a demo account below.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Normal user")
        department = request.form.get("department", "Acoustic Monitoring")
        if not name or not email or not password:
            flash("Please fill in all required fields.", "warning")
            return render_template("register.html")
        user = db.create_user(name, email, password, role, department)
        if user is None:
            flash("An account with this email already exists. Please log in.", "info")
            return redirect(url_for("login"))
        session["user"] = {
            "id": user["id"], "name": user["name"], "email": user["email"],
            "role": user["role"], "department": user["department"],
        }
        db.audit(email, "register", f"new user {user['id']}")
        flash(f"Registration successful! Your ID is {user['id']}.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    if session.get("user"):
        db.audit(session["user"]["email"], "logout", "")
    session.pop("user", None)
    flash("You have been securely signed out.", "info")
    return redirect(url_for("index"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = session["user"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        db.update_user(user["email"], name=name or None, department=department or None)
        user["name"] = name or user["name"]
        user["department"] = department or user["department"]
        session["user"] = user
        db.audit(user["email"], "profile_update", "")
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


@app.route("/dashboard")
@login_required
def dashboard():
    events = [event_to_view(e) for e in db.list_events(limit=50)]
    return render_template("dashboard.html", events=events, stats=db.stats())


@app.route("/live-monitor")
@login_required
def live_monitor():
    return render_template("live_monitor.html")


@app.route("/audio-analysis")
@login_required
def audio_analysis():
    return render_template("audio_analysis.html")


@app.route("/critical-events")
@login_required
def critical_events():
    rows = db.list_events(limit=200, where="severity IN ('Critical','High')")
    events = []
    for e in rows:
        view = event_to_view(e)
        alert = db.alert_for_event(e["id"])
        view["alert_id"] = alert["id"] if alert else None
        view["alert_state"] = alert["status"] if alert else None
        events.append(view)
    return render_template("critical_events.html", events=events)


@app.route("/manual-review")
@login_required
def manual_review():
    rows = db.list_events(limit=200, where="manual_review = 1")
    return render_template("manual_review.html", events=[event_to_view(e) for e in rows])


@app.route("/event-history")
@login_required
def event_history():
    events = [event_to_view(e) for e in db.list_events(limit=500)]
    return render_template("event_history.html", events=events)


@app.route("/reports")
@login_required
def reports():
    events = [event_to_view(e) for e in db.list_events(limit=500)]
    return render_template("reports.html", events=events, stats=db.stats(),
                           category_counts=db.category_counts(),
                           severity_counts=db.severity_counts())


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/admin/settings", methods=["GET", "POST"])
@role_required("Administrator")
def admin_settings():
    """Admin page to edit alert thresholds / rules at runtime (SRS xxxv, xxxvi, liii)."""
    import json as _json

    rules_path = cfg.path("alert_rules")
    with open(rules_path, "r", encoding="utf-8") as fh:
        rules = _json.load(fh)

    if request.method == "POST":
        # Update global defaults.
        defaults = rules.setdefault("defaults", {})
        try:
            defaults["min_confidence"] = float(request.form.get("default_min_confidence", defaults.get("min_confidence", 60)))
            defaults["top_two_margin"] = float(request.form.get("default_top_two_margin", defaults.get("top_two_margin", 8)))
        except ValueError:
            flash("Thresholds must be numbers.", "danger")
            return redirect(url_for("admin_settings"))

        # Update per-category min_confidence + required_consecutive + severity.
        for cat, rule in rules.get("categories", {}).items():
            mc = request.form.get(f"mc_{cat}")
            rc = request.form.get(f"rc_{cat}")
            sev = request.form.get(f"sev_{cat}")
            if mc not in (None, ""):
                try:
                    rule["min_confidence"] = float(mc)
                except ValueError:
                    pass
            if rc not in (None, ""):
                try:
                    rule["required_consecutive"] = int(rc)
                except ValueError:
                    pass
            if sev:
                rule["severity"] = sev

        with open(rules_path, "w", encoding="utf-8") as fh:
            _json.dump(rules, fh, indent=2)

        # Hot-reload the alert engine used by the inference service.
        svc = get_inference()
        if svc is not None:
            from services.alerts import AlertEngine
            svc.alert_engine = AlertEngine.from_file(rules_path)

        db.audit(session["user"]["email"], "admin_settings", "updated alert rules")
        flash("Alert rules updated and reloaded.", "success")
        return redirect(url_for("admin_settings"))

    severities = ["Critical", "High", "Medium", "Low", "Informational"]
    return render_template("admin_settings.html", rules=rules, severities=severities)


# Serve generated media (waveforms/spectrograms) + uploads.
@app.route("/media/<path:subpath>")
def media(subpath):
    return send_from_directory(str(cfg.path("visuals_dir")), subpath)


@app.route("/audio/<event_id>")
@login_required
def event_audio(event_id):
    """Serve the stored audio clip for an event (reviewer playback, SRS lviii)."""
    ev = db.get_event(event_id)
    if not ev or not ev.get("stored_path"):
        return ("Not found", 404)
    p = Path(ev["stored_path"])
    if not p.exists():
        return ("File missing", 404)
    return send_from_directory(str(p.parent), p.name)


@app.route("/report/<event_id>")
@login_required
def event_report(event_id):
    """Per-event downloadable analysis report (SRS deliverable lxix)."""
    import json as _json

    ev = db.get_event(event_id)
    if not ev:
        flash("Event not found.", "warning")
        return redirect(url_for("event_history"))

    def _scores(js):
        try:
            return sorted(_json.loads(js or "{}").items(), key=lambda kv: kv[1], reverse=True)
        except Exception:
            return []

    rows = [
        ("Audio ID", ev["id"]),
        ("Filename", ev.get("filename")),
        ("Source", ev.get("source_mode")),
        ("Duration", f"{ev.get('duration')}s"),
        ("Sample rate", f"{ev.get('sample_rate')} Hz"),
        ("Channels", ev.get("channels")),
        ("Final class", display_name(ev.get("final_class") or "")),
        ("Python prediction", f"{ev.get('py_class')} ({ev.get('py_confidence')}%)"),
        ("GTM prediction", f"{ev.get('gtm_class')} ({ev.get('gtm_confidence')}%)"),
        ("Model agreement", ev.get("agreement")),
        ("Confidence difference", f"{ev.get('conf_difference')}%"),
        ("Top-two margin", f"{ev.get('top_two_margin')}%"),
        ("Audio quality", ev.get("audio_quality")),
        ("Severity", ev.get("severity")),
        ("Alert status", ev.get("alert_status")),
        ("Manual review", "Yes" if ev.get("manual_review") else "No"),
        ("Status", ev.get("status")),
        ("Model versions", ev.get("model_versions")),
        ("Timestamp", ev.get("created_at")),
    ]
    return render_template(
        "event_report.html", event=ev, rows=rows,
        py_scores=_scores(ev.get("py_scores_json")),
        gtm_scores=_scores(ev.get("gtm_scores_json")),
        waveform_url=_rel_visual(ev.get("waveform_path")) if ev.get("waveform_path") else None,
        spectrogram_url=_rel_visual(ev.get("spectrogram_path")) if ev.get("spectrogram_path") else None,
    )


# -------------------------------------------------------------------- API
@app.route("/api/validate-audio", methods=["POST"])
def validate_audio():
    data = request.json or {}
    filename = data.get("filename", "")
    size_bytes = data.get("size_bytes", 0)
    duration_sec = data.get("duration_sec", 0)
    sample_rate = data.get("sample_rate", 44100)
    ext = Path(filename.lower()).suffix
    errors = []
    if ext not in audio_io.SUPPORTED_EXTS:
        errors.append(f"Invalid format '{ext}'. Allowed: WAV, MP3, FLAC, OGG, M4A.")
    if size_bytes > audio_io.MAX_SIZE_BYTES:
        errors.append(f"File exceeds 25MB ({size_bytes / 1e6:.2f}MB).")
    if duration_sec > audio_io.MAX_DURATION_S:
        errors.append(f"Duration exceeds 180s ({duration_sec:.1f}s).")
    return jsonify({
        "valid": not errors, "format": ext.upper().replace(".", ""),
        "size_mb": round(size_bytes / 1e6, 2), "duration_sec": round(duration_sec, 2),
        "sample_rate_hz": sample_rate, "errors": errors,
    })


def _run_and_store(dest: Path, info: dict, source_mode: str) -> dict:
    """Shared path: extract metadata, classify, generate visuals, persist."""
    svc = get_inference()
    if svc is None:
        return {"error": f"Model unavailable: {_inference_error}. Run src/train.py."}

    meta = audio_io.extract_metadata(dest)

    # Duplicate detection (SRS lxxiii): flag an identical earlier upload by hash.
    duplicate_of = db.find_by_hash(info["sha256"])

    result = svc.classify_file(dest)

    # Visuals.
    settings = AudioSettings.from_config(cfg)
    y = load_audio(dest, settings)
    stem = dest.stem
    wave_path = visuals.generate_waveform(y, settings.sample_rate,
                                          cfg.path("visuals_dir") / f"{stem}_wave.png")
    spec_path = visuals.generate_spectrogram(y, settings.sample_rate,
                                             cfg.path("visuals_dir") / f"{stem}_spec.png")

    status = "Manual Review" if result["manual_review"] else (
        "Alert Generated" if result["alert_fires"] else "Classified")

    event = {
        "filename": info["filename"], "stored_path": info["stored_path"],
        "uploaded_by": session.get("user", {}).get("email"),
        "source_mode": source_mode,
        "duration": meta["duration"], "sample_rate": meta["sample_rate"],
        "channels": meta["channels"], "file_size": info["file_size"], "sha256": info["sha256"],
        "py_class": result["python"]["predicted_class"],
        "py_confidence": result["python"]["confidence"],
        "py_scores_json": result["python"]["scores"],
        "gtm_class": result["gtm"]["predicted_class"],
        "gtm_confidence": result["gtm"]["confidence"],
        "gtm_scores_json": result["gtm"]["scores"],
        "agreement": result["comparison"]["agreement"],
        "conf_difference": result["comparison"]["confidence_difference"],
        "top_two_margin": result["comparison"]["top_two_margin"],
        "audio_quality": result["audio_quality"]["quality"],
        "final_class": result["final_class"], "severity": result["severity"],
        "alert_status": result["alert_status"],
        "manual_review": 1 if result["manual_review"] else 0,
        "status": status,
        "waveform_path": str(wave_path), "spectrogram_path": str(spec_path),
        "model_versions": result["model_versions"],
    }
    event_id = db.insert_event(event)
    if result["alert_fires"]:
        db.insert_alert(event_id, result["severity"], result["final_class"],
                        result["recommended_action"])
    db.audit(session.get("user", {}).get("email"), "classify",
             f"{event_id} -> {result['final_class']} ({result['severity']})")

    result["event_id"] = event_id
    result["final_class_name"] = display_name(result["final_class"])
    result["metadata"] = meta
    result["waveform_url"] = _rel_visual(wave_path)
    result["spectrogram_url"] = _rel_visual(spec_path)
    result["duplicate_of"] = duplicate_of["id"] if duplicate_of else None
    return result


@app.route("/api/classify-audio", methods=["POST"])
@login_required
def classify_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded (field 'audio')."}), 400
    file = request.files["audio"]
    try:
        dest, info = audio_io.save_upload(file, cfg.path("uploads_dir"))
    except audio_io.AudioValidationError as error:
        return jsonify({"error": str(error), "valid": False}), 400
    try:
        result = _run_and_store(dest, info, "upload")
    except audio_io.AudioValidationError as error:
        return jsonify({"error": str(error), "valid": False}), 400
    if "error" in result:
        return jsonify(result), 503
    return jsonify(result)


@app.route("/api/classify-batch", methods=["POST"])
@login_required
def classify_batch():
    files = request.files.getlist("audio")
    if not files:
        return jsonify({"error": "No files uploaded."}), 400
    results = []
    for file in files:
        try:
            dest, info = audio_io.save_upload(file, cfg.path("uploads_dir"))
            res = _run_and_store(dest, info, "batch")
            results.append({
                "filename": info["filename"],
                "final_class": res.get("final_class_name"),
                "confidence": res.get("python", {}).get("confidence"),
                "severity": res.get("severity"), "event_id": res.get("event_id"),
                "error": res.get("error"),
            })
        except audio_io.AudioValidationError as error:
            results.append({"filename": file.filename, "error": str(error)})
    return jsonify({"count": len(results), "results": results})


# Per-session live-monitoring state for consecutive-window confirmation (Step 15).
# Keyed by user email: {"last_class": str, "count": int}.
_live_state: dict[str, dict] = {}


@app.route("/api/classify-live", methods=["POST"])
@login_required
def classify_live():
    """Classify one live microphone window (SRS Step 12 + Step 15 confirmation).

    Live windows are classified continuously but NOT all stored. Only a
    confirmed critical/high event (after the required number of consecutive
    windows of the same class) is persisted as an event + alert.
    """
    svc = get_inference()
    if svc is None:
        return jsonify({"error": f"Model unavailable: {_inference_error}."}), 503
    if "audio" not in request.files:
        return jsonify({"error": "No audio window uploaded."}), 400
    file = request.files["audio"]

    # Save the window (WAV from the browser) and load the signal.
    try:
        dest, info = audio_io.save_upload(file, cfg.path("uploads_dir"))
    except audio_io.AudioValidationError as error:
        return jsonify({"error": str(error)}), 400

    email = session["user"]["email"]
    state = _live_state.setdefault(email, {"last_class": None, "count": 0})

    try:
        settings = AudioSettings.from_config(cfg)
        y = load_audio(dest, settings)
    except Exception as error:  # noqa: BLE001
        # Clean up the tiny window file and report.
        try:
            Path(dest).unlink(missing_ok=True)
        except Exception:
            pass
        return jsonify({"error": f"Could not decode window: {error}"}), 400

    # Track consecutive detections of the same class.
    peek = svc.classify_signal(y, consecutive=1)
    cls = peek["final_class"]
    if cls == state["last_class"]:
        state["count"] += 1
    else:
        state["last_class"] = cls
        state["count"] = 1

    # Re-run the decision with the true consecutive count so Step-15 rules
    # (e.g. gunshot/aggression require 2 consecutive) are honoured.
    result = svc.classify_signal(y, consecutive=state["count"])
    result["consecutive"] = state["count"]

    confirmed = result["alert_fires"]
    result["confirmed_alert"] = confirmed

    if confirmed:
        # Persist a confirmed live event + alert, and generate visuals.
        try:
            stem = Path(dest).stem
            wave = visuals.generate_waveform(y, settings.sample_rate,
                                             cfg.path("visuals_dir") / f"{stem}_wave.png")
            spec = visuals.generate_spectrogram(y, settings.sample_rate,
                                                cfg.path("visuals_dir") / f"{stem}_spec.png")
            event = {
                "filename": info["filename"], "stored_path": info["stored_path"],
                "uploaded_by": email, "source_mode": "live",
                "duration": settings.duration, "sample_rate": settings.sample_rate,
                "channels": 1, "file_size": info["file_size"], "sha256": info["sha256"],
                "py_class": result["python"]["predicted_class"],
                "py_confidence": result["python"]["confidence"],
                "py_scores_json": result["python"]["scores"],
                "gtm_class": result["gtm"]["predicted_class"],
                "gtm_confidence": result["gtm"]["confidence"],
                "gtm_scores_json": result["gtm"]["scores"],
                "agreement": result["comparison"]["agreement"],
                "conf_difference": result["comparison"]["confidence_difference"],
                "top_two_margin": result["comparison"]["top_two_margin"],
                "audio_quality": result["audio_quality"]["quality"],
                "final_class": result["final_class"], "severity": result["severity"],
                "alert_status": "Active", "manual_review": 1 if result["manual_review"] else 0,
                "status": "Alert Generated",
                "waveform_path": str(wave), "spectrogram_path": str(spec),
                "model_versions": result["model_versions"],
            }
            event_id = db.insert_event(event)
            db.insert_alert(event_id, result["severity"], result["final_class"],
                            result["recommended_action"])
            db.audit(email, "live_alert", f"{event_id} -> {result['final_class']}")
            result["event_id"] = event_id
            state["count"] = 0  # reset after confirming
        except Exception as error:  # noqa: BLE001
            result["store_error"] = str(error)
    else:
        # Discard the un-confirmed window file to avoid clutter.
        try:
            Path(dest).unlink(missing_ok=True)
        except Exception:
            pass

    result["final_class_name"] = display_name(result["final_class"])
    return jsonify(result)


@app.route("/api/alerts/<alert_id>/<action>", methods=["POST"])
@login_required
def alert_action(alert_id, action):
    mapping = {"acknowledge": "Acknowledged", "dismiss": "Dismissed", "escalate": "Escalated"}
    if action not in mapping:
        return jsonify({"error": "Invalid action."}), 400
    db.update_alert(alert_id, mapping[action], session["user"]["email"])
    db.audit(session["user"]["email"], f"alert_{action}", alert_id)
    return jsonify({"ok": True, "status": mapping[action]})


@app.route("/api/reviews", methods=["POST"])
@role_required("Audio reviewer", "Administrator")
def submit_review():
    data = request.json or {}
    event_id = data.get("event_id")
    decision = data.get("decision", "Confirmed")
    corrected = data.get("corrected_class")
    comment = data.get("comment", "")
    if not event_id:
        return jsonify({"error": "event_id required."}), 400
    db.insert_review(event_id, session["user"]["email"], decision, corrected, comment)
    updates = {"status": "Reviewed", "manual_review": 0}
    if decision == "Corrected" and corrected:
        updates["final_class"] = UI_TO_PIPELINE.get(corrected, corrected)
    db.update_event(event_id, **updates)
    db.audit(session["user"]["email"], "review", f"{event_id}:{decision}")

    # Feed the reviewer-verified clip back into the training set so the model
    # learns from real user data on the next background cycle (SRS: retraining).
    if _trainer is not None and decision in ("Confirmed", "Corrected"):
        ev = db.get_event(event_id)
        stored = ev.get("stored_path") if ev else None
        if stored and Path(stored).exists():
            label = updates.get("final_class") or ev.get("final_class")
            if label:
                added = _trainer.add_labelled_clip(stored, label)
                if added:
                    _trainer.trigger_now()
    return jsonify({"ok": True})


@app.route("/api/trainer-status", methods=["GET"])
@login_required
def trainer_status():
    """Report the background trainer's state (SRS: continuous retraining)."""
    if _trainer is None:
        return jsonify({"enabled": False, "status": {"state": "disabled"}})
    return jsonify({"enabled": True, "status": _trainer.status})


@app.route("/api/trainer-run", methods=["POST"])
@role_required("Administrator")
def trainer_run():
    """Admin: kick off a retraining cycle now (rebuilds only if data changed)."""
    if _trainer is None:
        return jsonify({"error": "Background trainer is disabled."}), 400
    _trainer.trigger_now()
    db.audit(session["user"]["email"], "trainer_run", "manual retrain triggered")
    return jsonify({"ok": True, "message": "Retraining cycle started."})


@app.route("/api/export", methods=["GET"])
@login_required
def export_csv():
    import csv
    import io

    rows = db.list_events(limit=5000)
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return app.response_class(
        buf.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sonicsentinel_events.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
