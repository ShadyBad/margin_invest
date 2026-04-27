from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

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
