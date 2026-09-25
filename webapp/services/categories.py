"""The 10 mandatory SRS sound categories + mapping to pipeline class labels.

The web UI uses these display keys; the ML pipeline uses its own label strings.
Two keys differ, so we map them explicitly:
    pipeline 'aggression'              -> UI 'aggression_conflict'
    pipeline 'person_asking_for_help'  -> UI 'person_help'
"""

from __future__ import annotations

MANDATORY_SOUND_CATEGORIES = [
    {"id": "cat_1", "name": "Machinery Fault", "category_key": "machinery_fault",
     "severity": "High", "badge_color": "warning", "icon": "fa-gears",
     "description": "Bearing wear, motor friction, turbine imbalance, or mechanical vibrations",
     "default_threshold": 0.70},
    {"id": "cat_2", "name": "Glass Breaking", "category_key": "glass_breaking",
     "severity": "High", "badge_color": "danger", "icon": "fa-burst",
     "description": "Sharp high-frequency shattering of window, door, or structural glass",
     "default_threshold": 0.85},
    {"id": "cat_3", "name": "Alarm or Siren", "category_key": "alarm_siren",
     "severity": "High", "badge_color": "warning", "icon": "fa-bell",
     "description": "Continuous or oscillating sirens, fire alarms, evacuation alerts",
     "default_threshold": 0.80},
    {"id": "cat_4", "name": "Vehicle Horn", "category_key": "vehicle_horn",
     "severity": "Medium", "badge_color": "info", "icon": "fa-bullhorn",
     "description": "Automotive blare, sustained klaxon or proximity honks",
     "default_threshold": 0.75},
    {"id": "cat_5", "name": "Animal Sound", "category_key": "animal_sound",
     "severity": "Low", "badge_color": "neutral", "icon": "fa-paw",
     "description": "Canine barking, perimeter distress, or wildlife intrusion",
     "default_threshold": 0.65},
    {"id": "cat_6", "name": "Gunshot", "category_key": "gunshot",
     "severity": "Critical", "badge_color": "danger", "icon": "fa-crosshairs",
     "description": "High-decibel muzzle blast and supersonic ballistic crack",
     "default_threshold": 0.90},
    {"id": "cat_7", "name": "Panic Scream", "category_key": "panic_scream",
     "severity": "Critical", "badge_color": "danger", "icon": "fa-person-falling-burst",
     "description": "High-pitch human distress shrieks, screams of fear or severe pain",
     "default_threshold": 0.82},
    {"id": "cat_8", "name": "Aggression or Violent Conflict", "category_key": "aggression_conflict",
     "severity": "High", "badge_color": "danger", "icon": "fa-hand-fist",
     "description": "Verbal hostility, elevated screaming fights, physical altercation impacts",
     "default_threshold": 0.78},
    {"id": "cat_9", "name": "Person Asking for Help", "category_key": "person_help",
     "severity": "Critical", "badge_color": "danger", "icon": "fa-handshake-angle",
     "description": "Vocal distress cues ('Help', 'Call Police', emergency pleas)",
     "default_threshold": 0.75},
    {"id": "cat_10", "name": "Background Noise", "category_key": "background_noise",
     "severity": "Informational", "badge_color": "secondary", "icon": "fa-wave-square",
     "description": "Normal ambient traffic, wind, ventilation, footsteps or stationary hum",
     "default_threshold": 0.50},
]

# pipeline label -> UI category_key
PIPELINE_TO_UI = {
    "machinery_fault": "machinery_fault",
    "glass_breaking": "glass_breaking",
    "alarm_siren": "alarm_siren",
    "vehicle_horn": "vehicle_horn",
    "animal_sound": "animal_sound",
    "gunshot": "gunshot",
    "panic_scream": "panic_scream",
    "person_asking_for_help": "person_help",
    "aggression": "aggression_conflict",
    "background_noise": "background_noise",
}
UI_TO_PIPELINE = {v: k for k, v in PIPELINE_TO_UI.items()}

_BY_KEY = {c["category_key"]: c for c in MANDATORY_SOUND_CATEGORIES}


def ui_key(pipeline_label: str) -> str:
    return PIPELINE_TO_UI.get(pipeline_label, pipeline_label)


def category_meta(key: str) -> dict:
    """Look up display metadata by UI key or pipeline label."""
    if key in _BY_KEY:
        return _BY_KEY[key]
    return _BY_KEY.get(PIPELINE_TO_UI.get(key, ""), {
        "name": key.replace("_", " ").title(), "category_key": key,
        "severity": "Informational", "badge_color": "secondary", "icon": "fa-wave-square",
    })


def display_name(pipeline_label: str) -> str:
    return category_meta(pipeline_label).get("name", pipeline_label)
