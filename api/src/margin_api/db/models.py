"""SQLAlchemy ORM models for Margin Invest."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from margin_api.db.base import Base

# Use JSONB on PostgreSQL, fall back to JSON on other backends (e.g. SQLite for tests).
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(100))
    sub_industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market_cap: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    scores: Mapped[list[Score]] = relationship(back_populates="asset")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="asset")
    financial_data: Mapped[list[FinancialData]] = relationship(back_populates="asset")


class FinancialData(Base):
    """Raw financial data fetched from data providers."""

    __tablename__ = "financial_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    period_end: Mapped[str] = mapped_column(String(10))  # ISO date
    filing_date: Mapped[str] = mapped_column(String(10))
    income_statement: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    balance_sheet: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    cash_flow: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    price_history: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    earnings_data: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="yfinance")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship(back_populates="financial_data")

    __table_args__ = (
        UniqueConstraint("asset_id", "period_end", name="uq_financial_data_asset_period"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(50))  # google, github, etc.
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="user")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    composite_percentile: Mapped[float]
    conviction_level: Mapped[str] = mapped_column(String(20))
    signal: Mapped[str] = mapped_column(String(20))
    quality_percentile: Mapped[float] = mapped_column(default=0.0)
    value_percentile: Mapped[float] = mapped_column(default=0.0)
    momentum_percentile: Mapped[float] = mapped_column(default=0.0)
    data_coverage: Mapped[float] = mapped_column(default=1.0)
    growth_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    score_detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    intrinsic_value: Mapped[float | None] = mapped_column(nullable=True)
    buy_price: Mapped[float | None] = mapped_column(nullable=True)
    sell_price: Mapped[float | None] = mapped_column(nullable=True)
    actual_price: Mapped[float | None] = mapped_column(nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship(back_populates="scores")

    __table_args__ = (
        Index("ix_scores_asset_scored", "asset_id", "scored_at"),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    conviction_level: Mapped[str] = mapped_column(String(20))
    signal: Mapped[str] = mapped_column(String(20))
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    asset: Mapped[Asset] = relationship(back_populates="recommendations")


class SignalTransition(Base):
    """Audit trail for signal changes on scored assets."""

    __tablename__ = "signal_transitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    previous_signal: Mapped[str] = mapped_column(String(20))
    new_signal: Mapped[str] = mapped_column(String(20))
    previous_conviction: Mapped[str] = mapped_column(String(20))
    new_conviction: Mapped[str] = mapped_column(String(20))
    actual_price_at_transition: Mapped[float | None] = mapped_column(nullable=True)
    intrinsic_value_at_transition: Mapped[float | None] = mapped_column(nullable=True)
    composite_percentile: Mapped[float]
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship()

    __table_args__ = (
        UniqueConstraint("asset_id", "transitioned_at", name="uq_signal_transition_asset_time"),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_name: Mapped[str] = mapped_column(String(50))
    encrypted_key: Mapped[str] = mapped_column(Text)
    is_platform_managed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="api_keys")
    events: Mapped[list[ApiKeyEvent]] = relationship(back_populates="api_key")


class ApiKeyEvent(Base):
    """Audit trail for API key lifecycle events."""

    __tablename__ = "api_key_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(20))  # created, rotated, revoked, accessed
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    api_key: Mapped[ApiKey] = relationship(back_populates="events")


# ---------------------------------------------------------------------------
# Authentication models
# ---------------------------------------------------------------------------


class CredentialUser(Base):
    """User with username/password credentials and optional MFA."""

    __tablename__ = "credential_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_totp_counter: Mapped[int | None] = mapped_column(nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="free")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    totp_secrets: Mapped[list[TotpSecret]] = relationship(back_populates="user")
    webauthn_credentials: Mapped[list[WebAuthnCredential]] = relationship(
        back_populates="user"
    )
    challenge_tokens: Mapped[list[MfaChallengeToken]] = relationship(back_populates="user")


class TotpSecret(Base):
    """Encrypted TOTP secret for a credential user."""

    __tablename__ = "totp_secrets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("credential_users.id"), index=True)
    encrypted_secret: Mapped[str] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[CredentialUser] = relationship(back_populates="totp_secrets")


class WebAuthnCredential(Base):
    """WebAuthn/passkey credential for a credential user."""

    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("credential_users.id"), index=True)
    credential_id: Mapped[str] = mapped_column(Text, unique=True)
    public_key: Mapped[str] = mapped_column(Text)
    sign_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[CredentialUser] = relationship(back_populates="webauthn_credentials")


class MfaChallengeToken(Base):
    """Short-lived challenge token issued after password verification, consumed by MFA step."""

    __tablename__ = "mfa_challenge_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("credential_users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[CredentialUser] = relationship(back_populates="challenge_tokens")
