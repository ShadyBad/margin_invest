"""Tests for db/ssl.py — both CA cert and fallback paths."""

from __future__ import annotations

import os
import ssl
from unittest.mock import patch


class TestCreatePgSslContext:
    def test_no_ca_cert_returns_cert_none(self):
        """When MARGIN_DB_CA_CERT is unset, falls back to CERT_NONE."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MARGIN_DB_CA_CERT", None)
            from margin_api.db.ssl import create_pg_ssl_context

            ctx = create_pg_ssl_context()

        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.check_hostname is False

    def test_empty_ca_cert_returns_cert_none(self):
        """When MARGIN_DB_CA_CERT is empty string, falls back to CERT_NONE."""
        with patch.dict(os.environ, {"MARGIN_DB_CA_CERT": ""}):
            from margin_api.db.ssl import create_pg_ssl_context

            ctx = create_pg_ssl_context()

        assert ctx.verify_mode == ssl.CERT_NONE

    def test_whitespace_ca_cert_returns_cert_none(self):
        """When MARGIN_DB_CA_CERT is whitespace only, falls back to CERT_NONE."""
        with patch.dict(os.environ, {"MARGIN_DB_CA_CERT": "   "}):
            from margin_api.db.ssl import create_pg_ssl_context

            ctx = create_pg_ssl_context()

        assert ctx.verify_mode == ssl.CERT_NONE

    def test_ca_cert_set_returns_cert_required(self):
        """When MARGIN_DB_CA_CERT has real PEM content, uses CERT_REQUIRED."""
        # Generate a self-signed cert PEM for testing
        import subprocess
        import tempfile

        # Use a real PEM — create a quick self-signed cert
        pem = _generate_self_signed_pem()

        with patch.dict(os.environ, {"MARGIN_DB_CA_CERT": pem}):
            from margin_api.db.ssl import create_pg_ssl_context

            ctx = create_pg_ssl_context()

        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is False


def _generate_self_signed_pem() -> str:
    """Generate a minimal self-signed CA PEM certificate for testing."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from datetime import datetime, timedelta, timezone

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "test-ca")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()
