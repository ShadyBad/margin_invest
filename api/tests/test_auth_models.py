"""Tests for authentication database models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from margin_api.db.base import Base
from margin_api.db.models import (
    CredentialUser,
    MfaChallengeToken,
    TotpSecret,
    WebAuthnCredential,
)
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture()
def sync_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


class TestCredentialUserModel:
    def test_table_name(self):
        assert CredentialUser.__tablename__ == "credential_users"

    def test_columns(self):
        columns = {c.name for c in CredentialUser.__table__.columns}
        expected = {
            "id",
            "username",
            "email",
            "password_hash",
            "mfa_enabled",
            "failed_login_attempts",
            "locked_until",
            "last_totp_counter",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(columns)

    def test_username_unique(self):
        col = CredentialUser.__table__.columns["username"]
        assert col.unique is True

    def test_email_unique(self):
        col = CredentialUser.__table__.columns["email"]
        assert col.unique is True

    def test_create_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = CredentialUser(
                username="testuser",
                email="test@example.com",
                password_hash="hashed_pw",
            )
            session.add(user)
            session.commit()
            result = session.execute(
                select(CredentialUser).where(CredentialUser.username == "testuser")
            )
            found = result.scalar_one()
            assert found.email == "test@example.com"
            assert found.mfa_enabled is False
            assert found.failed_login_attempts == 0
            assert found.locked_until is None
            assert found.last_totp_counter is None
            assert found.created_at is not None
            assert found.updated_at is not None

    def test_username_uniqueness_enforced(self, sync_engine):
        with Session(sync_engine) as session:
            user1 = CredentialUser(
                username="testuser",
                email="a@example.com",
                password_hash="hash1",
            )
            user2 = CredentialUser(
                username="testuser",
                email="b@example.com",
                password_hash="hash2",
            )
            session.add(user1)
            session.commit()
            session.add(user2)
            with pytest.raises(IntegrityError):
                session.commit()

    def test_email_uniqueness_enforced(self, sync_engine):
        with Session(sync_engine) as session:
            user1 = CredentialUser(
                username="user1",
                email="same@example.com",
                password_hash="hash1",
            )
            user2 = CredentialUser(
                username="user2",
                email="same@example.com",
                password_hash="hash2",
            )
            session.add(user1)
            session.commit()
            session.add(user2)
            with pytest.raises(IntegrityError):
                session.commit()

    def test_relationships_exist(self):
        assert hasattr(CredentialUser, "totp_secrets")
        assert hasattr(CredentialUser, "webauthn_credentials")
        assert hasattr(CredentialUser, "challenge_tokens")


class TestTotpSecretModel:
    def test_table_name(self):
        assert TotpSecret.__tablename__ == "totp_secrets"

    def test_columns(self):
        columns = {c.name for c in TotpSecret.__table__.columns}
        expected = {"id", "user_id", "encrypted_secret", "confirmed", "created_at"}
        assert expected.issubset(columns)

    def test_user_fk(self):
        col = TotpSecret.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "credential_users.id"

    def test_create_with_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = CredentialUser(
                username="totpuser",
                email="totp@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.flush()
            secret = TotpSecret(
                user_id=user.id,
                encrypted_secret="encrypted_data",
            )
            session.add(secret)
            session.commit()
            assert secret.confirmed is False
            assert secret.user.username == "totpuser"

    def test_user_relationship(self):
        assert hasattr(TotpSecret, "user")


class TestWebAuthnCredentialModel:
    def test_table_name(self):
        assert WebAuthnCredential.__tablename__ == "webauthn_credentials"

    def test_columns(self):
        columns = {c.name for c in WebAuthnCredential.__table__.columns}
        expected = {
            "id",
            "user_id",
            "credential_id",
            "public_key",
            "sign_count",
            "created_at",
        }
        assert expected.issubset(columns)

    def test_credential_id_unique(self):
        col = WebAuthnCredential.__table__.columns["credential_id"]
        assert col.unique is True

    def test_user_fk(self):
        col = WebAuthnCredential.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "credential_users.id"

    def test_create_with_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = CredentialUser(
                username="webauthnuser",
                email="webauthn@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.flush()
            cred = WebAuthnCredential(
                user_id=user.id,
                credential_id="cred_abc123",
                public_key="pubkey_data",
            )
            session.add(cred)
            session.commit()
            assert cred.sign_count == 0
            assert cred.user.username == "webauthnuser"

    def test_user_relationship(self):
        assert hasattr(WebAuthnCredential, "user")


class TestMfaChallengeTokenModel:
    def test_table_name(self):
        assert MfaChallengeToken.__tablename__ == "mfa_challenge_tokens"

    def test_columns(self):
        columns = {c.name for c in MfaChallengeToken.__table__.columns}
        expected = {
            "id",
            "user_id",
            "token_hash",
            "expires_at",
            "used",
            "created_at",
        }
        assert expected.issubset(columns)

    def test_user_fk(self):
        col = MfaChallengeToken.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "credential_users.id"

    def test_create_with_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = CredentialUser(
                username="mfauser",
                email="mfa@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.flush()
            token = MfaChallengeToken(
                user_id=user.id,
                token_hash="a" * 64,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
            session.add(token)
            session.commit()
            assert token.used is False
            assert token.user.username == "mfauser"

    def test_user_relationship(self):
        assert hasattr(MfaChallengeToken, "user")


class TestAuthTableCreation:
    @pytest.fixture()
    def sync_engine(self):
        return create_engine("sqlite:///:memory:")

    def test_create_all_auth_tables(self, sync_engine):
        Base.metadata.create_all(sync_engine)
        table_names = set(Base.metadata.tables.keys())
        assert "credential_users" in table_names
        assert "totp_secrets" in table_names
        assert "webauthn_credentials" in table_names
        assert "mfa_challenge_tokens" in table_names


class TestCredentialUserRelationships:
    def test_totp_secrets_cascade(self, sync_engine):
        with Session(sync_engine) as session:
            user = CredentialUser(
                username="reluser",
                email="rel@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.flush()
            secret = TotpSecret(
                user_id=user.id,
                encrypted_secret="enc_secret",
            )
            session.add(secret)
            session.commit()
            session.refresh(user)
            assert len(user.totp_secrets) == 1
            assert user.totp_secrets[0].encrypted_secret == "enc_secret"

    def test_webauthn_credentials_relationship(self, sync_engine):
        with Session(sync_engine) as session:
            user = CredentialUser(
                username="wauser",
                email="wa@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.flush()
            cred = WebAuthnCredential(
                user_id=user.id,
                credential_id="cred_1",
                public_key="pk1",
            )
            session.add(cred)
            session.commit()
            session.refresh(user)
            assert len(user.webauthn_credentials) == 1

    def test_challenge_tokens_relationship(self, sync_engine):
        with Session(sync_engine) as session:
            user = CredentialUser(
                username="ctuser",
                email="ct@example.com",
                password_hash="hash",
            )
            session.add(user)
            session.flush()
            token = MfaChallengeToken(
                user_id=user.id,
                token_hash="b" * 64,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
            session.add(token)
            session.commit()
            session.refresh(user)
            assert len(user.challenge_tokens) == 1
