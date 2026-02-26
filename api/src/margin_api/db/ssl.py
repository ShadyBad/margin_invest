"""PostgreSQL SSL context factory with optional CA certificate verification."""

from __future__ import annotations

import logging
import os
import ssl
import tempfile

logger = logging.getLogger(__name__)


def create_pg_ssl_context() -> ssl.SSLContext:
    """Create an SSL context for asyncpg PostgreSQL connections.

    If MARGIN_DB_CA_CERT is set (PEM string), uses CERT_REQUIRED.
    Otherwise falls back to CERT_NONE with a logged warning.
    """
    ssl_ctx = ssl.create_default_context()

    ca_cert = os.environ.get("MARGIN_DB_CA_CERT", "")
    if ca_cert.strip():
        ca_path = os.path.join(tempfile.gettempdir(), "margin-pg-ca.pem")
        with open(ca_path, "w") as f:
            f.write(ca_cert)
        ssl_ctx.load_verify_locations(cafile=ca_path)
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        ssl_ctx.check_hostname = False  # Railway self-signed certs won't match hostname
        logger.info("DB SSL: CERT_REQUIRED with CA certificate")
    else:
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        logger.info(
            "DB SSL: CERT_NONE — set MARGIN_DB_CA_CERT env var for certificate verification"
        )

    return ssl_ctx
