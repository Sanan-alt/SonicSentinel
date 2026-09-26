# Demonstration Video Script (SRS section 13)

The mandatory `.mp4` must be recorded from the **running system** — it cannot be
generated here. Follow this shot list so every required item is captured, then
save the file as `documentation/SonicSentinel_Demo.mp4` (or link it in the README).

## Setup before recording
```powershell
python src/run_pipeline.py     # ensure a trained model exists
python webapp/app.py           # start the app
```
Optional: place a GTM export in `models/gtm/export/` to show real GTM predictions;
otherwise the video will honestly show GTM = "Not available / BLOCKED".

## Shot list (in order)
1. **Login** — log in as `admin@sonicsentinel.ai`.
2. **Audio upload** — upload a clip on Audio Analysis.
3. **File validation** — show a rejected invalid/oversized/silent file.
4. **Metadata** — show extracted duration, sample rate, channels, size.
5. **Preprocessing** — mention resample/mono/trim/normalise.
6. **Waveform** + **Spectrogram** — show both visuals.
7. **Python prediction** + **Python confidence** — top class + all-class scores.
8. **GTM prediction** + **GTM confidence** — real if configured, else "Not available".
9. **Model comparison** + **confidence difference** — the comparison panel (or BLOCKED state).
10. **Audio quality** — Good/Acceptable/Poor/Unusable.
11. **Repeated detection** — Live Monitor showing consecutive-window confirmation.
12. **Critical alert** — trigger a gunshot/scream clip; show the alert.
13. **Alert acknowledgement** — acknowledge/escalate on Critical Events.
14. **Manual review** + **reviewer override** — review queue, correct a class.
15. **Dashboard** — live stats.
16. **Event history** — search/filter.
17. **Report generation** — CSV export / per-event report.
18. **Every sound class** — run one clip per class (use `sample_audio/`).
19. **Low-confidence case** — a borderline clip routed to review.
20. **Model-disagreement case** — (once GTM configured) a clip where models differ.
21. **Noisy case** — a noisy clip; show quality = Poor.
22. **Overlapping-sound case** — a clip with two events; show overlap.
23. **Real-time critical detection** — Live Monitor firing a critical alert.

## Honesty note
Do not stage fake predictions. If GTM is not configured, narrate that the GTM
comparison is BLOCKED by design until the browser export is added — this is
compliant and demonstrates the anti-shortcut behaviour.
