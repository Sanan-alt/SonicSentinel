"""Mapping of raw data sources to the 10 mandatory SRS sound classes.

Two sources are mapped here:

1. ESC-50 (Dataset/Dataset/audio) - filenames like ``1-100032-A-0.wav`` where
   the trailing number is the ESC-50 target (0-49). We map only the ESC-50
   categories that correspond to an SRS class; everything else is dropped so
   we never mislabel a clip.
2. Hand-collected mp3 folders (Aggression, Glass breaking) - mapped by folder.

NOTE (Option A): ESC-50 has no gunshot category, and no real recordings exist
yet for gunshot, panic_scream, or person_asking_for_help. Those classes are
intentionally absent from the current dataset and will be added when data
arrives. The model trains only on classes that have real data.
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
MP3_FOLDER_TO_SRS: dict[str, str] = {
    "aggression": "aggression",
    "glassbreak": "glass_breaking",
}


def esc50_target_map(meta_csv_path) -> dict[int, str]:
    """Return {esc50_target_int: esc50_category_name} from the local esc50.csv."""
    import csv

    mapping: dict[int, str] = {}
    with open(meta_csv_path, "r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            mapping[int(row["target"])] = row["category"]
    return mapping
