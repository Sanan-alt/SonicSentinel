"""Mapping of raw data sources to the 10 mandatory SRS sound classes.

Two sources are mapped here:

1. ESC-50 (Dataset/Dataset/audio) - filenames like ``1-100032-A-0.wav`` where
   the trailing number is the ESC-50 target (0-49). We map only the ESC-50
   categories that correspond to an SRS class; everything else is dropped so
   we never mislabel a clip.
2. Hand-collected mp3 folders (gunshot, Glass breaking, Help) - mapped by folder.

DATA NOTE: the shipped "Aggression" and "gunshot" folders currently hold
byte-identical files whose audio is aggression (shouting / violent conflict).
The mapping below therefore labels that audio as ``aggression`` (its true
content) and the organiser de-duplicates by content hash, so the duplicate is
counted once. To add a REAL gunshot class, drop genuine gunshot recordings into
``Dataset/gunshot`` (replacing the placeholder copies): because the mapping
already points that folder at ``gunshot``, the new clips are picked up on the
next pipeline run with no code change.

Any folder added under ``paths.mp3_folders`` in config.yaml is trained on
automatically as long as it has an entry in ``MP3_FOLDER_TO_SRS`` below.
"""

from __future__ import annotations

# ESC-50 category name -> SRS class. Categories not listed are ignored.
ESC50_TO_SRS: dict[str, str] = {
    # --- Animal sounds ---
    "dog": "animal_sound",
    "rooster": "animal_sound",
    "pig": "animal_sound",
    "cow": "animal_sound",
    "frog": "animal_sound",
    "cat": "animal_sound",
    "hen": "animal_sound",
    "insects": "animal_sound",
    "sheep": "animal_sound",
    "crow": "animal_sound",
    "crickets": "animal_sound",
    "chirping_birds": "animal_sound",
    # --- Glass breaking ---
    "glass_breaking": "glass_breaking",
    # --- Alarm or siren ---
    "siren": "alarm_siren",
    "clock_alarm": "alarm_siren",
    "church_bells": "alarm_siren",
    # --- Vehicle horn ---
    "car_horn": "vehicle_horn",
    # --- Machinery fault (mechanical / motorised tools) ---
    "engine": "machinery_fault",
    "chainsaw": "machinery_fault",
    "vacuum_cleaner": "machinery_fault",
    "washing_machine": "machinery_fault",
    "hand_saw": "machinery_fault",
    # --- Background noise (ambient / nature / neutral) ---
    "rain": "background_noise",
    "sea_waves": "background_noise",
    "wind": "background_noise",
    "thunderstorm": "background_noise",
    "crackling_fire": "background_noise",
    "water_drops": "background_noise",
    "pouring_water": "background_noise",
}

# Folder key (from config paths.mp3_folders) -> SRS class.
# The audio actually present in each shipped folder is mapped to its TRUE class.
MP3_FOLDER_TO_SRS: dict[str, str] = {
    "aggression": "aggression",              # Dataset/Aggression -> aggression (real content)
    "glassbreak": "glass_breaking",          # Dataset/Glass breaking -> glass_breaking
    "help": "person_asking_for_help",        # Dataset/Help -> person_asking_for_help
    "gunshot": "gunshot",                    # Dataset/gunshot -> gunshot (drop real gunshots here)
    "panic_scream": "panic_scream",          # Dataset/Panic scream -> panic_scream
}


def esc50_target_map(meta_csv_path) -> dict[int, str]:
    """Return {esc50_target_int: esc50_category_name} from the local esc50.csv."""
    import csv

    mapping: dict[int, str] = {}
    with open(meta_csv_path, "r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            mapping[int(row["target"])] = row["category"]
    return mapping
