from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from margin_api.audit.cli import run_audit_engine
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_run_audit_engine_end_to_end_synthetic(
    synthetic_audit_db: AsyncSession,
) -> None:
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock(return_value={"ETag": '"abc"'})
    with patch("margin_api.audit.cli.build_s3_client", return_value=mock_s3):
        result = await run_audit_engine(
            session=synthetic_audit_db,
            report_date=date(2026, 4, 27),
            r2_prefix="audits/test/",
            r2_bucket="audit-bucket",
            with_marginal_attribution=False,
        )
    assert result.manifest.report_date == date(2026, 4, 27)
    assert mock_s3.put_object.call_count == 7


@pytest.mark.asyncio
async def test_audit_engine_deterministic_re_run(
    synthetic_audit_db: AsyncSession,
) -> None:
    """Spec §8.7: re-running on identical input data produces byte-identical
    manifest content hash. This test is a merge-blocker."""
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock(return_value={"ETag": '"abc"'})
    fixed_run_id = UUID("00000000-0000-0000-0000-000000000042")
    with patch("margin_api.audit.cli.build_s3_client", return_value=mock_s3), \
         patch("margin_api.audit.cli._git_sha", return_value="a" * 40):
        first = await run_audit_engine(
            session=synthetic_audit_db,
            report_date=date(2026, 4, 27),
            r2_prefix="audits/test/",
            r2_bucket="audit-bucket",
            run_id=fixed_run_id,
        )
        second = await run_audit_engine(
            session=synthetic_audit_db,
            report_date=date(2026, 4, 27),
            r2_prefix="audits/test/",
            r2_bucket="audit-bucket",
            run_id=fixed_run_id,
        )
    assert first.manifest_sha256 == second.manifest_sha256
    assert {k: v.sha256 for k, v in first.manifest.files.items()} == \
           {k: v.sha256 for k, v in second.manifest.files.items()}
