"""Stage 2: download R2 bundle, validate hashes, render markdown report.

Per spec §6 Stage 2.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from margin_api.audit.schema import AuditManifest


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
