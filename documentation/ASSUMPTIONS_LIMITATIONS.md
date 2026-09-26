# Assumptions & Limitations (SRS section 11)

## Assumptions
- Audio is provided in a supported format (WAV/MP3/FLAC/OGG/M4A); mp3/m4a
  decoding assumes FFmpeg is available on the host.
- A fixed 5-second window at 22.05 kHz mono is representative for these
  sound-event classes; longer clips are segmented.
- The deployment environment can run scikit-learn/XGBoost inference in-process.
- The evaluator can create/train the Google Teachable Machine model in a browser
  (GTM cannot be produced from Python).

## Known limitations
1. **Dataset below SRS target.** 2,244 real unique originals vs the 3,000 target;
   several classes are below 300 (see `data/metadata/class_distribution.csv`).
   `gunshot` and `panic_scream` currently use disclosed synthetic placeholders.
2. **GTM not yet configured.** The GTM comparison is BLOCKED until a human exports
   a GTM model into `models/gtm/export/`. The app never fakes GTM.
3. **Human-voice confusion.** Aggression, Panic Scream, and Person-Asking-for-Help
   overlap acoustically; some confusion between these is expected (the SRS lists
   these as inherently hard pairs).
4. **Noise reduction is lightweight** (silence trim + normalisation), not a full
   spectral denoiser.
5. **Accuracy target.** Last real run: test accuracy 0.848 (just under the 0.85
   target) — reported honestly, not inflated. More balanced real data per class
   is the main lever to exceed it.
6. **Live microphone** requires a device and browser permission; not exercised in
   headless CI.
7. **Not an emergency/law-enforcement system.** This is a competition prototype
   for controlled, ethical testing (per the SRS).

## Privacy & ethics
- Live audio windows that are not confirmed critical events are discarded.
- No audio/user data leaves the host; classification is fully local (Python) +
  local/browser (GTM). No generative-AI API produces predictions.
