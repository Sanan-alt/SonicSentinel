# Alert Rules (SRS deliverable 7)

Configurable, data-driven alert policy. Editing these files changes behaviour
with no code changes. Admins can also edit thresholds at runtime via
**Admin → Settings** (`/admin/settings`), which hot-reloads the engine.

## Files
- `alert_rules.json` — the rules the runtime engine loads
  (`webapp/services/alerts.py → AlertEngine.from_file`).
- `severity_rules.yaml` — YAML mirror + human reference for severity/escalation.

## Fields (per category)
| Field | Meaning |
|---|---|
| `severity` | Informational / Low / Medium / High / Critical |
| `min_confidence` | Minimum top-class confidence (%) for the alert to fire |
| `top_two_margin` | Minimum gap (%) between the top two classes |
| `required_consecutive` | Consecutive detections needed (repeated-event confirmation) |
| `require_model_agreement` | If true, Python + GTM must agree |
| `min_audio_quality` | Minimum acceptable audio quality (Good > Acceptable > Poor > Unusable) |
| `recommended_action` | Operator guidance (general, safety-oriented) |
| `manual_review_condition` | When the event is routed for manual review |
| `escalate` | Whether a fired alert escalates |

## How a decision is made
`AlertEngine.decide()` checks confidence, top-two margin, consecutive count,
audio quality, and (optionally) model agreement. An alert fires only when all
configured conditions pass **and** severity is Medium/High/Critical. Failing
checks (low confidence, poor quality, similar top-two, model disagreement) route
the event to **manual review** instead of silently alerting.

Rules are stored in JSON (SRS allows JSON/YAML/CSV/DB).
