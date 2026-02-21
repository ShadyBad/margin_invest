"""Tests for the unified User model, LinkedProvider, and RecoveryCode.

These tests verify the model restructuring that merges the old OAuth-only User
and password-only CredentialUser into a single User table with nullable auth
fields, plus new LinkedProvider and RecoveryCode tables.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from margin_api.db.base import Base
from margin_api.db.models import (
    ApiKey,
    LinkedProvider,
    MfaChallengeToken,
    RecoveryCode,
    TotpSecret,
    User,
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


# ---------------------------------------------------------------------------
# User model structure
# ---------------------------------------------------------------------------


class TestUnifiedUserModel:
    """The unified User model has columns from both old User and CredentialUser."""

    def test_table_name(self):
        assert User.__tablename__ == "users"

    def test_has_all_columns(self):
        columns = {c.name for c in User.__table__.columns}
        expected = {
            "id",
            "email",
            "name",
            # OAuth fields
            "oauth_id",
            # Credential fields
            "password_hash",
            "mfa_enabled",
            "mfa_grace_deadline",
            "failed_login_attempts",
            "locked_until",
            "last_totp_counter",
            "password_changed_at",
            # Billing
            "stripe_customer_id",
            "stripe_subscription_id",
            "subscription_plan",
            "subscription_status",
            "current_period_end",
            # Avatars
            "avatar_url",
            "oauth_avatar_url",
            # Timestamps
            "created_at",
            "updated_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_provider_column_removed(self):
        """The old 'provider' column should no longer exist on User."""
        columns = {c.name for c in User.__table__.columns}
        assert "provider" not in columns

    def test_username_column_removed(self):
        """The old CredentialUser 'username' column is not on unified User."""
        columns = {c.name for c in User.__table__.columns}
        assert "username" not in columns

    def test_email_unique(self):
        col = User.__table__.columns["email"]
        assert col.unique is True

    def test_oauth_id_unique(self):
        col = User.__table__.columns["oauth_id"]
        assert col.unique is True

    def test_oauth_id_nullable(self):
        col = User.__table__.columns["oauth_id"]
        assert col.nullable is True

    def test_name_nullable(self):
        col = User.__table__.columns["name"]
        assert col.nullable is True

    def test_password_hash_nullable(self):
        col = User.__table__.columns["password_hash"]
        assert col.nullable is True

    def test_mfa_grace_deadline_nullable(self):
        col = User.__table__.columns["mfa_grace_deadline"]
        assert col.nullable is True

    def test_locked_until_nullable(self):
        col = User.__table__.columns["locked_until"]
        assert col.nullable is True


class TestUserHasPasswordProperty:
    """User.has_password returns True only when password_hash is set."""

    def test_has_password_true(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(
                email="cred@example.com",
                password_hash="hashed_pw",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            assert user.has_password is True

    def test_has_password_false(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(
                email="oauth@example.com",
                oauth_id="google|123",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            assert user.has_password is False


class TestUserRelationships:
    """User has relationships to all auth/billing sub-tables."""

    def test_has_linked_providers_relationship(self):
        assert hasattr(User, "linked_providers")

    def test_has_api_keys_relationship(self):
        assert hasattr(User, "api_keys")

    def test_has_totp_secrets_relationship(self):
        assert hasattr(User, "totp_secrets")

    def test_has_webauthn_credentials_relationship(self):
        assert hasattr(User, "webauthn_credentials")

    def test_has_challenge_tokens_relationship(self):
        assert hasattr(User, "challenge_tokens")

    def test_has_recovery_codes_relationship(self):
        assert hasattr(User, "recovery_codes")


class TestUserCRUD:
    """CRUD operations on the unified User model."""

    def test_create_oauth_only_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(
                email="oauth@example.com",
                name="OAuth User",
                oauth_id="google|abc123",
            )
            session.add(user)
            session.commit()
            found = session.execute(
                select(User).where(User.email == "oauth@example.com")
            ).scalar_one()
            assert found.name == "OAuth User"
            assert found.oauth_id == "google|abc123"
            assert found.password_hash is None
            assert found.mfa_enabled is False
            assert found.has_password is False

    def test_create_credential_only_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(
                email="cred@example.com",
                password_hash="argon2_hash_here",
            )
            session.add(user)
            session.commit()
            found = session.execute(
                select(User).where(User.email == "cred@example.com")
            ).scalar_one()
            assert found.password_hash == "argon2_hash_here"
            assert found.oauth_id is None
            assert found.has_password is True

    def test_create_hybrid_user(self, sync_engine):
        """A user with both OAuth and password credentials."""
        with Session(sync_engine) as session:
            user = User(
                email="hybrid@example.com",
                name="Hybrid User",
                oauth_id="github|456",
                password_hash="argon2_hash",
            )
            session.add(user)
            session.commit()
            found = session.execute(
                select(User).where(User.email == "hybrid@example.com")
            ).scalar_one()
            assert found.oauth_id == "github|456"
            assert found.has_password is True

    def test_email_uniqueness_enforced(self, sync_engine):
        with Session(sync_engine) as session:
            user1 = User(email="dup@example.com", password_hash="hash1")
            user2 = User(email="dup@example.com", password_hash="hash2")
            session.add(user1)
            session.commit()
            session.add(user2)
            with pytest.raises(IntegrityError):
                session.commit()

    def test_default_subscription_plan(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="plan@example.com", password_hash="hash")
            session.add(user)
            session.commit()
            session.refresh(user)
            assert user.subscription_plan == "analyst"


# ---------------------------------------------------------------------------
# LinkedProvider model
# ---------------------------------------------------------------------------


class TestLinkedProviderModel:
    """LinkedProvider tracks which OAuth providers are linked to a user."""

    def test_table_name(self):
        assert LinkedProvider.__tablename__ == "linked_providers"

    def test_columns(self):
        columns = {c.name for c in LinkedProvider.__table__.columns}
        expected = {
            "id",
            "user_id",
            "provider",
            "oauth_id",
            "provider_email",
            "linked_at",
        }
        assert expected.issubset(columns), f"Missing: {expected - columns}"

    def test_user_fk(self):
        col = LinkedProvider.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "users.id"

    def test_cascade_delete(self):
        col = LinkedProvider.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert fks[0].ondelete == "CASCADE"

    def test_unique_constraint_provider_oauth_id(self):
        constraint_names = [
            c.name
            for c in LinkedProvider.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_linked_providers_provider_oauth_id" in constraint_names

    def test_unique_constraint_user_provider(self):
        constraint_names = [
            c.name
            for c in LinkedProvider.__table__.constraints
            if hasattr(c, "name") and c.name
        ]
        assert "uq_linked_providers_user_id_provider" in constraint_names

    def test_provider_email_nullable(self):
        col = LinkedProvider.__table__.columns["provider_email"]
        assert col.nullable is True

    def test_create_linked_provider(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="lp@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            lp = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="google|789",
                provider_email="lp@gmail.com",
            )
            session.add(lp)
            session.commit()
            session.refresh(user)
            assert len(user.linked_providers) == 1
            assert user.linked_providers[0].provider == "google"
            assert lp.user.email == "lp@example.com"

    def test_user_can_have_multiple_providers(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="multi@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            lp1 = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="google|111",
            )
            lp2 = LinkedProvider(
                user_id=user.id,
                provider="github",
                oauth_id="github|222",
            )
            session.add_all([lp1, lp2])
            session.commit()
            session.refresh(user)
            assert len(user.linked_providers) == 2

    def test_same_provider_per_user_rejected(self, sync_engine):
        """A user cannot link the same provider twice."""
        with Session(sync_engine) as session:
            user = User(email="duppr@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            lp1 = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="google|aaa",
            )
            lp2 = LinkedProvider(
                user_id=user.id,
                provider="google",
                oauth_id="google|bbb",
            )
            session.add(lp1)
            session.commit()
            session.add(lp2)
            with pytest.raises(IntegrityError):
                session.commit()


# ---------------------------------------------------------------------------
# RecoveryCode model
# ---------------------------------------------------------------------------


class TestRecoveryCodeModel:
    """RecoveryCode stores hashed backup codes for MFA recovery."""

    def test_table_name(self):
        assert RecoveryCode.__tablename__ == "recovery_codes"

    def test_columns(self):
        columns = {c.name for c in RecoveryCode.__table__.columns}
        expected = {
            "id",
            "user_id",
            "code_hash",
            "used",
            "used_at",
            "created_at",
        }
        assert expected.issubset(columns), f"Missing: {expected - columns}"

    def test_user_fk(self):
        col = RecoveryCode.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "users.id"

    def test_cascade_delete(self):
        col = RecoveryCode.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert fks[0].ondelete == "CASCADE"

    def test_used_at_nullable(self):
        col = RecoveryCode.__table__.columns["used_at"]
        assert col.nullable is True

    def test_create_recovery_code(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="rc@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            code = RecoveryCode(
                user_id=user.id,
                code_hash="sha256_of_code",
            )
            session.add(code)
            session.commit()
            session.refresh(user)
            assert len(user.recovery_codes) == 1
            assert user.recovery_codes[0].used is False
            assert user.recovery_codes[0].used_at is None
            assert code.user.email == "rc@example.com"

    def test_mark_code_as_used(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="rcused@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            code = RecoveryCode(
                user_id=user.id,
                code_hash="sha256_of_code",
            )
            session.add(code)
            session.commit()
            code.used = True
            code.used_at = datetime.now(UTC)
            session.commit()
            session.refresh(code)
            assert code.used is True
            assert code.used_at is not None


# ---------------------------------------------------------------------------
# FK references: TotpSecret, WebAuthnCredential, MfaChallengeToken -> User
# ---------------------------------------------------------------------------


class TestMfaModelsPointToUser:
    """TotpSecret, WebAuthnCredential, MfaChallengeToken FK to users.id."""

    def test_totp_secret_fk_to_users(self):
        col = TotpSecret.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "users.id"

    def test_webauthn_credential_fk_to_users(self):
        col = WebAuthnCredential.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "users.id"

    def test_mfa_challenge_token_fk_to_users(self):
        col = MfaChallengeToken.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "users.id"

    def test_totp_secret_relationship_to_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="totp@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            secret = TotpSecret(
                user_id=user.id,
                encrypted_secret="encrypted_data",
            )
            session.add(secret)
            session.commit()
            session.refresh(user)
            assert len(user.totp_secrets) == 1
            assert secret.user.email == "totp@example.com"

    def test_webauthn_credential_relationship_to_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="wa@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            cred = WebAuthnCredential(
                user_id=user.id,
                credential_id="cred_abc123",
                public_key="pubkey_data",
            )
            session.add(cred)
            session.commit()
            session.refresh(user)
            assert len(user.webauthn_credentials) == 1
            assert cred.user.email == "wa@example.com"

    def test_mfa_challenge_token_relationship_to_user(self, sync_engine):
        with Session(sync_engine) as session:
            user = User(email="mfa@example.com", password_hash="hash")
            session.add(user)
            session.flush()
            token = MfaChallengeToken(
                user_id=user.id,
                token_hash="a" * 64,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
            session.add(token)
            session.commit()
            session.refresh(user)
            assert len(user.challenge_tokens) == 1
            assert token.user.email == "mfa@example.com"


# ---------------------------------------------------------------------------
# Table creation smoke test
# ---------------------------------------------------------------------------


class TestTableCreationWithNewModels:
    def test_all_new_tables_created(self, sync_engine):
        table_names = set(Base.metadata.tables.keys())
        assert "users" in table_names
        assert "linked_providers" in table_names
        assert "recovery_codes" in table_names
        assert "totp_secrets" in table_names
        assert "webauthn_credentials" in table_names
        assert "mfa_challenge_tokens" in table_names

    def test_credential_users_table_gone(self):
        """The old credential_users table should no longer exist in metadata."""
        table_names = set(Base.metadata.tables.keys())
        assert "credential_users" not in table_names

    def test_api_key_fk_to_users(self):
        col = ApiKey.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "users.id"
