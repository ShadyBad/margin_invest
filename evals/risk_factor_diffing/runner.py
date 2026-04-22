"""Assessment runner for the filing analysis diffing pipeline.

Loads golden test cases, evaluates system output against expected changes,
and persists run results for regression comparison.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GOLDEN_SET_DEFAULT = Path(__file__).parent / "golden_set.jsonl"
RUNS_DIR = Path(__file__).parent / "runs"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CaseResult:
    """Evaluation result for a single golden test case."""

    case_id: str
    detected: list[dict[str, Any]] = field(default_factory=list)
    missed: list[dict[str, Any]] = field(default_factory=list)
    false_positives: list[dict[str, Any]] = field(default_factory=list)
    severity_errors: list[float] = field(default_factory=list)

    @property
    def precision(self) -> float:
        """Fraction of system detections that were correct."""
        total = len(self.detected) + len(self.false_positives)
        return len(self.detected) / total if total > 0 else 0.0

    @property
    def recall(self) -> float:
        """Fraction of expected must-detect changes that were found."""
        total = len(self.detected) + len(self.missed)
        return len(self.detected) / total if total > 0 else 0.0

    @property
    def mean_severity_error(self) -> float:
        """Mean absolute deviation between expected and reported severity."""
        if not self.severity_errors:
            return 0.0
        return sum(abs(e) for e in self.severity_errors) / len(self.severity_errors)


@dataclass
class AssessmentReport:
    """Aggregate report across all evaluated cases."""

    prompt_version: str
    run_at: str
    num_cases: int
    precision: float
    recall: float
    mean_severity_error: float
    case_results: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_golden_set(path: Path | str = GOLDEN_SET_DEFAULT) -> list[dict[str, Any]]:
    """Load JSONL golden set, skipping cases whose filings are still PLACEHOLDER."""
    path = Path(path)
    cases: list[dict[str, Any]] = []
    with path.open() as fh:
        for line_num, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                case = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_num}: {exc}") from exc

            current_text = case.get("current_filing", {}).get("risk_factors_text", "")
            prior_text = case.get("prior_filing", {}).get("risk_factors_text", "")
            if current_text == "PLACEHOLDER" or prior_text == "PLACEHOLDER":
                continue  # skip stubs without real filing text
            cases.append(case)
    return cases


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------


def _keyword_matches(topic_keyword: str, system_change: dict[str, Any]) -> bool:
    """Return True if the system change references the expected topic keyword.

    Checks both a topic field and a description field (if present)
    using case-insensitive substring matching.
    """
    keyword = topic_keyword.lower()
    topic = str(system_change.get("topic", "")).lower()
    description = str(system_change.get("description", "")).lower()
    return keyword in topic or keyword in description


def _change_type_matches(expected_type: str, system_change: dict[str, Any]) -> bool:
    """Return True if the system change type equals the expected type."""
    return str(system_change.get("change_type", "")).lower() == expected_type.lower()


def evaluate_case(
    case: dict[str, Any],
    system_output: list[dict[str, Any]],
) -> CaseResult:
    """Compare system output against expected changes for one golden case.

    Parameters
    ----------
    case:
        A single golden set record (parsed from JSONL).
    system_output:
        List of change dicts produced by the filing diffing system.
        Each dict should have at minimum: change_type, topic,
        and severity (float 0-1).

    Returns
    -------
    CaseResult with detected/missed/false_positives/severity_errors populated.
    """
    result = CaseResult(case_id=case["case_id"])
    expected: list[dict[str, Any]] = case.get("expected_changes", [])

    matched_system_indices: set[int] = set()

    for exp in expected:
        topic_keyword: str = exp["topic_keyword"]
        change_type: str = exp["change_type"]
        min_severity: float = float(exp["min_severity"])
        must_detect: bool = bool(exp["must_detect"])

        best_match_idx: int | None = None
        best_severity_diff: float = math.inf

        for idx, sys_chg in enumerate(system_output):
            if idx in matched_system_indices:
                continue
            if not _change_type_matches(change_type, sys_chg):
                continue
            if not _keyword_matches(topic_keyword, sys_chg):
                continue
            sys_severity = float(sys_chg.get("severity", 0.0))
            severity_diff = abs(sys_severity - min_severity)
            if severity_diff < best_severity_diff:
                best_severity_diff = severity_diff
                best_match_idx = idx

        if best_match_idx is not None:
            matched_system_indices.add(best_match_idx)
            result.detected.append(exp)
            sys_severity = float(system_output[best_match_idx].get("severity", 0.0))
            result.severity_errors.append(sys_severity - min_severity)
        elif must_detect:
            result.missed.append(exp)

    for idx, sys_chg in enumerate(system_output):
        if idx not in matched_system_indices:
            result.false_positives.append(sys_chg)

    return result


# ---------------------------------------------------------------------------
# Metrics aggregation
# ---------------------------------------------------------------------------


def compute_metrics(
    case_results: list[CaseResult],
) -> dict[str, float]:
    """Aggregate precision, recall, and mean severity error across all cases.

    Returns a dict with keys: precision, recall, mean_severity_error.
    """
    if not case_results:
        return {"precision": 0.0, "recall": 0.0, "mean_severity_error": 0.0}

    precisions = [r.precision for r in case_results]
    recalls = [r.recall for r in case_results]
    sev_errors = [r.mean_severity_error for r in case_results]

    return {
        "precision": sum(precisions) / len(precisions),
        "recall": sum(recalls) / len(recalls),
        "mean_severity_error": sum(sev_errors) / len(sev_errors),
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_run(report: AssessmentReport, prompt_version: str) -> Path:
    """Serialise an AssessmentReport to runs/<prompt_version>_<timestamp>.json.

    Parameters
    ----------
    report:
        Fully populated AssessmentReport.
    prompt_version:
        Short identifier for the prompt variant (e.g. "v1", "v2-cot").

    Returns
    -------
    Path of the written file.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{prompt_version}_{timestamp}.json"
    dest = RUNS_DIR / filename
    with dest.open("w") as fh:
        json.dump(asdict(report), fh, indent=2)
    return dest


def load_prior_run(prompt_version: str) -> AssessmentReport | None:
    """Load the most recent run for a given prompt_version, or None if absent.

    Scans runs/ for files matching <prompt_version>_*.json and returns the
    latest by filename (which encodes a UTC timestamp).
    """
    if not RUNS_DIR.exists():
        return None
    pattern = f"{prompt_version}_*.json"
    matches = sorted(RUNS_DIR.glob(pattern))
    if not matches:
        return None
    latest = matches[-1]
    with latest.open() as fh:
        data = json.load(fh)
    return AssessmentReport(**data)


# ---------------------------------------------------------------------------
# Convenience: run full evaluation pipeline
# ---------------------------------------------------------------------------


def run_evaluation(
    system_outputs: dict[str, list[dict[str, Any]]],
    prompt_version: str,
    golden_path: Path | str = GOLDEN_SET_DEFAULT,
    notes: str = "",
    *,
    save: bool = True,
) -> AssessmentReport:
    """End-to-end helper: load golden set, evaluate, aggregate, optionally save.

    Parameters
    ----------
    system_outputs:
        Mapping of case_id -> list of change dicts from the filing system.
    prompt_version:
        Short identifier for the prompt variant being tested.
    golden_path:
        Path to the JSONL golden set file.
    notes:
        Optional free-text notes to embed in the report.
    save:
        If True, persist the report via save_run().

    Returns
    -------
    AssessmentReport with all metrics populated.
    """
    cases = load_golden_set(golden_path)
    case_results: list[CaseResult] = []
    for case in cases:
        case_id = case["case_id"]
        outputs = system_outputs.get(case_id, [])
        case_results.append(evaluate_case(case, outputs))

    metrics = compute_metrics(case_results)
    report = AssessmentReport(
        prompt_version=prompt_version,
        run_at=datetime.now(UTC).isoformat(),
        num_cases=len(case_results),
        precision=metrics["precision"],
        recall=metrics["recall"],
        mean_severity_error=metrics["mean_severity_error"],
        case_results=[asdict(r) for r in case_results],
        notes=notes,
    )
    if save:
        save_run(report, prompt_version)
    return report
