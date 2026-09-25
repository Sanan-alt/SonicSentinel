"""Configurable alert-rule engine (SRS Steps 14-17, requirement liii).

Loads alert_rules.json and decides, for a classified event, the severity,
whether an alert fires, whether manual review is needed, and the recommended
action. Rules are data-driven so administrators can retune without code edits.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUALITY_RANK = {"Unusable": 0, "Poor": 1, "Acceptable": 2, "Good": 3}


class AlertEngine:
    def __init__(self, rules: dict[str, Any]):
        self.defaults = rules.get("defaults", {})
        self.categories = rules.get("categories", {})

    @classmethod
    def from_file(cls, path: Path | str) -> "AlertEngine":
        with open(path, "r", encoding="utf-8") as stream:
            return cls(json.load(stream))

    def rule_for(self, category: str) -> dict[str, Any]:
        merged = dict(self.defaults)
        merged.update(self.categories.get(category, {}))
        return merged

    def decide(
        self,
        final_class: str,
        confidence: float,
        top_two_margin: float,
        audio_quality: str,
        agreement: str,
        consecutive: int = 1,
    ) -> dict[str, Any]:
        """Return the alert decision for one classified event.

        confidence and top_two_margin are percentages (0-100).
        """
        rule = self.rule_for(final_class)
        severity = rule.get("severity", "Informational")
        reasons: list[str] = []

        quality_ok = QUALITY_RANK.get(audio_quality, 0) >= QUALITY_RANK.get(
            rule.get("min_audio_quality", "Acceptable"), 2)
        confidence_ok = confidence >= float(rule.get("min_confidence", 60.0))
        margin_ok = top_two_margin >= float(rule.get("top_two_margin", 0.0))
        consec_ok = consecutive >= int(rule.get("required_consecutive", 1))
        agreement_ok = (not rule.get("require_model_agreement", False)) or (
            agreement in ("Acceptable Match", "Weak Match"))

        # Manual review conditions (SRS Step 17).
        manual_review = False
        if agreement == "Model Disagreement" and self.defaults.get(
                "manual_review_on_disagreement", True):
            manual_review = True
            reasons.append("model disagreement")
        if not confidence_ok:
            manual_review = True
            reasons.append("low confidence")
        if not quality_ok:
            manual_review = True
            reasons.append("poor audio quality")
        if not margin_ok:
            manual_review = True
            reasons.append("similar top-two classes")

        # Alert fires only when all configured conditions pass.
        alert_fires = (
            confidence_ok and quality_ok and margin_ok and consec_ok and agreement_ok
            and severity in ("Medium", "High", "Critical")
        )

        alert_status = "Active" if alert_fires else "None"
        return {
            "severity": severity,
            "alert_fires": alert_fires,
            "alert_status": alert_status,
            "manual_review": manual_review,
            "recommended_action": rule.get("recommended_action", "Log event."),
            "escalate": bool(rule.get("escalate", False)) and alert_fires,
            "reasons": reasons,
            "checks": {
                "confidence_ok": confidence_ok, "quality_ok": quality_ok,
                "margin_ok": margin_ok, "consecutive_ok": consec_ok,
                "agreement_ok": agreement_ok,
            },
        }
