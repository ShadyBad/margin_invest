"""Stage 2: download R2 bundle, validate hashes, render markdown report.

Per spec §6 Stage 2.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from margin_api.audit.schema import AuditManifest  # noqa: E402


class BundleHashMismatch(Exception):
    """Raised when a file's sha256 does not match the manifest."""


def download_and_verify_bundle(local_dir: Path) -> AuditManifest:
    """Read manifest.json from local_dir and verify every file's hash.

    Actual R2 download is up to the caller; this function operates on a
    directory that already contains the bundle.
    """
    manifest_path = local_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json missing in {local_dir}")
    raw = json.loads(manifest_path.read_text())
    manifest = AuditManifest.model_validate(raw)
    for name, file_hash in manifest.files.items():
        path = local_dir / name
        if not path.exists():
            raise BundleHashMismatch(f"{name} listed in manifest but not in bundle")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != file_hash.sha256:
            raise BundleHashMismatch(
                f"{name}: expected sha256={file_hash.sha256}, got {actual}"
            )
    return manifest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = REPO_ROOT / "docs" / "templates"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def render_report(
    *,
    local_dir: Path,
    out_path: Path,
    r2_prefix: str,
    r2_url: str,
    with_marginal_attribution: bool,
) -> None:
    """Load CSVs from bundle, render Jinja template to markdown report."""
    manifest = download_and_verify_bundle(local_dir)
    metrics_rows = _read_csv(local_dir / "performance_metrics.csv")
    attribution_rows = _read_csv(local_dir / "component_attribution.csv")
    calibration_rows = _read_csv(local_dir / "conviction_calibration.csv")
    v2_rows = _read_csv(local_dir / "v2_proposal_inputs.csv")
    candidates_rows = _read_csv(local_dir / "candidates_part_a.csv")

    # Convert metrics values to floats for template rendering
    metrics_rows_with_floats = [
        {**r, "value": float(r["value"])} for r in metrics_rows
    ]
    metrics_by_name = {r["metric"]: float(r["value"]) for r in metrics_rows}

    # Convert numeric fields in attribution rows
    attribution_rows_with_floats = []
    for r in attribution_rows:
        row_copy = dict(r)
        # Convert numeric columns to float where they exist
        for col in ["spread", "rank_ic", "ci_lo", "ci_hi", "p_value_holm"]:
            if col in row_copy and row_copy[col] and str(row_copy[col]).strip():
                try:
                    row_copy[col] = float(row_copy[col])
                except (ValueError, TypeError):
                    row_copy[col] = None
            elif col in row_copy and (not row_copy[col] or not str(row_copy[col]).strip()):
                row_copy[col] = None
        # Convert n_top and n_bottom to int where they exist
        for col in ["n_top", "n_bottom"]:
            if col in row_copy and row_copy[col] and str(row_copy[col]).strip():
                try:
                    row_copy[col] = int(row_copy[col])
                except (ValueError, TypeError):
                    row_copy[col] = None
            elif col in row_copy and (not row_copy[col] or not str(row_copy[col]).strip()):
                row_copy[col] = None
        attribution_rows_with_floats.append(row_copy)

    # Convert numeric fields in calibration rows
    calibration_rows_with_floats = []
    for r in calibration_rows:
        row_copy = dict(r)
        # Convert numeric columns to float where they exist
        for col in ["n", "mean_alpha_60d", "sharpe", "sortino", "max_drawdown", "anova_p"]:
            if col in row_copy and row_copy[col] and str(row_copy[col]).strip():
                try:
                    row_copy[col] = float(row_copy[col])
                except (ValueError, TypeError):
                    row_copy[col] = None
            elif col in row_copy and (not row_copy[col] or not str(row_copy[col]).strip()):
                row_copy[col] = None
        # Handle boolean monotonic field
        if "monotonic" in row_copy:
            row_copy["monotonic"] = str(row_copy["monotonic"]).lower() == "true"
        calibration_rows_with_floats.append(row_copy)

    # Convert numeric fields in v2 proposal rows
    v2_rows_with_floats = []
    v2_float_cols = [
        "current_weight",
        "attribution_spread",
        "marginal_alpha_loss_when_zeroed",
        "proposed_new_weight",
    ]
    for r in v2_rows:
        row_copy = dict(r)
        # Convert numeric columns to float where they exist
        for col in v2_float_cols:
            if col in row_copy and row_copy[col] and row_copy[col].strip():
                try:
                    row_copy[col] = float(row_copy[col])
                except (ValueError, TypeError):
                    row_copy[col] = None
            elif col in row_copy and not row_copy[col]:
                row_copy[col] = None
        v2_rows_with_floats.append(row_copy)

    def _mean_alpha(window: str) -> float:
        col = f"alpha_{window}"
        vals = [float(r[col]) for r in candidates_rows if r.get(col) not in (None, "")]
        return sum(vals) / len(vals) if vals else 0.0

    def _n_closed(window: str) -> int:
        col = f"alpha_{window}"
        return sum(1 for r in candidates_rows if r.get(col) not in (None, ""))

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("audit-report.md.j2")

    manifest_sha = hashlib.sha256(
        (local_dir / "manifest.json").read_bytes()
    ).hexdigest()

    text = template.render(
        report_date=manifest.report_date,
        manifest=manifest,
        manifest_sha256=manifest_sha,
        r2_url=r2_url,
        r2_prefix=r2_prefix,
        with_marginal_attribution=with_marginal_attribution,
        verdict_summary="(populated by Stage 1; use excess_cagr to write a one-line verdict)",
        metrics={
            "excess_cagr": metrics_by_name.get("excess_cagr", 0.0),
            "sharpe": metrics_by_name.get("sharpe", 0.0),
            "max_drawdown": metrics_by_name.get("max_drawdown", 0.0),
        },
        metrics_rows=metrics_rows_with_floats,
        attribution_rows=attribution_rows_with_floats,
        calibration_rows=calibration_rows_with_floats,
        v2_proposal_rows=v2_rows_with_floats,
        part_a_mean_alpha_30d=_mean_alpha("30d"),
        part_a_mean_alpha_60d=_mean_alpha("60d"),
        part_a_n_closed_30d=_n_closed("30d"),
        part_a_n_closed_60d=_n_closed("60d"),
        holm_family_size=24,
    )
    out_path.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render audit report from R2 bundle.")
    parser.add_argument("--local-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--r2-prefix", type=str, required=True)
    parser.add_argument("--r2-url", type=str, required=True)
    parser.add_argument("--with-marginal-attribution", action="store_true")
    args = parser.parse_args()
    render_report(
        local_dir=args.local_dir,
        out_path=args.out,
        r2_prefix=args.r2_prefix,
        r2_url=args.r2_url,
        with_marginal_attribution=args.with_marginal_attribution,
    )
    print(f"wrote {args.out}")
