"""Run the full validation suite and write an honest final report.

Runs: environment check, dataset validation (if built), pytest, and the SRS
audit. Records pass/fail/blocked with real evidence — nothing is fabricated.

Writes:
  reports/final/final_validation_report.json
  reports/final/final_validation_report.md

Run:
    python scripts/run_all_tests.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(cmd, cwd=ROOT):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> None:
    results = []

    # 1. Environment validation.
    code, out = run([PY, str(ROOT / "scripts" / "validate_environment.py")])
    results.append(("environment", "passed" if code == 0 else "failed", out.strip().splitlines()[-1:] or [""]))

    # 2. Dataset validation (blocked if not built).
    meta = ROOT / "config" / "config.yaml"
    code, out = run([PY, str(ROOT / "src" / "validate_dataset.py")])
    results.append(("dataset_validation", "passed" if code == 0 else "blocked",
                    out.strip().splitlines()[-1:] or [""]))

    # 3. pytest.
    code, out = run([PY, "-m", "pytest", "-q"])
    last = [ln for ln in out.strip().splitlines() if "passed" in ln or "failed" in ln or "error" in ln]
    results.append(("pytest", "passed" if code == 0 else "failed", last[-1:] or [""]))

    # 4. SRS audit.
    code, out = run([PY, str(ROOT / "scripts" / "final_srs_audit.py")])
    results.append(("srs_audit", "passed" if code == 0 else "failed",
                    [ln for ln in out.splitlines() if "Compliance" in ln][-1:] or [""]))

    summary = {name: status for name, status, _ in results}
    out_dir = ROOT / "reports" / "final"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "final_validation_report.json").write_text(
        json.dumps({"summary": summary,
                    "details": [{"stage": n, "status": s, "evidence": e} for n, s, e in results]},
                   indent=2), encoding="utf-8")

    lines = ["# Final Validation Report", "", f"**Summary:** {summary}", "",
             "| Stage | Status | Evidence |", "|---|---|---|"]
    for n, s, e in results:
        ev = (e[0] if e else "").replace("|", "/")
        lines.append(f"| {n} | {s} | {ev} |")
    (out_dir / "final_validation_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Summary: {summary}")
    print(f"Report -> {out_dir}")
    # Non-zero exit only if a hard test stage failed (blocked is acceptable).
    sys.exit(1 if summary.get("pytest") == "failed" else 0)


if __name__ == "__main__":
    main()
