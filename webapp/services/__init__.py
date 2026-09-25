"""Backend services for the SonicSentinel Flask app.

Modules:
    database    SQLite schema + data-access helpers
    audio_io    upload validation, storage, metadata extraction
    visuals     waveform / spectrogram image generation
    inference   dual-model prediction + comparison + alert decision
    alerts      configurable alert-rule engine
"""
