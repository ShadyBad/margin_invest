"""SQLAlchemy ORM models for Margin Invest."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Float, JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from margin_api.db.base import Base

# Use JSONB on PostgreSQL, fall back to JSON on other backends (e.g. SQLite for tests).
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class UniverseSnapshot(Base):
    __tablename__ = "universe_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(50))
    config_hash: Mapped[str] = mapped_column(String(64))
    ticker_count: Mapped[int]
    tickers: Mapped[dict | None] = mapped_column(JSONVariant)  # actually a list, stored as JSON
    exclusion_rules: Mapped[dict | None] = mapped_column(JSONVariant, default=dict)
    is_active: Mapped[bool] = mapped_column(default=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IngestionTickerStatus(Base):
    __tablename__ = "ingestion_ticker_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    ticker: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))  # pending | ingesting | succeeded | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_fetched: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[IngestionRun] = relationship(back_populates="ticker_statuses")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("universe_snapshots.id"))
    run_type: Mapped[str] = mapped_column(String(20))  # "full" | "subset"
    tickers_requested: Mapped[int]
    tickers_succeeded: Mapped[int] = mapped_column(default=0)
    tickers_failed: Mapped[int] = mapped_column(default=0)
    tickers_skipped: Mapped[int] = mapped_column(default=0)
    failed_tickers: Mapped[dict | None] = mapped_column(JSONVariant, default=list)
    status: Mapped[str] = mapped_column(String(20))  # running | completed | failed | cancelled
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_types: Mapped[list | None] = mapped_column(JSONVariant, default=list)

    snapshot: Mapped[UniverseSnapshot] = relationship()
    ticker_statuses: Mapped[list[IngestionTickerStatus]] = relationship(back_populates="run")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))  # queued | running | completed | failed | cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    progress_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(20))  # schedule | cli | chained
    parent_job_id: Mapped[int | None] = mapped_column(ForeignKey("job_runs.id"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(100))
    sub_industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
    ingestion_status: Mapped[str] = mapped_column(String(30), default="active")
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    last_failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    quarantined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scores: Mapped[list[Score]] = relationship(back_populates="asset")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="asset")
    financial_data: Mapped[list[FinancialData]] = relationship(back_populates="asset")
    v3_scores: Mapped[list[V3Score]] = relationship(back_populates="asset")


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
    oauth_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(50))  # google, github, etc.
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="analyst")
    subscription_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oauth_avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="user")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    composite_percentile: Mapped[float]
    composite_raw_score: Mapped[float] = mapped_column(Float, default=0.0)
    conviction_level: Mapped[str] = mapped_column(String(20))
    signal: Mapped[str] = mapped_column(String(20))
    quality_percentile: Mapped[float] = mapped_column(default=0.0)
    value_percentile: Mapped[float] = mapped_column(default=0.0)
    momentum_percentile: Mapped[float] = mapped_column(default=0.0)
    data_coverage: Mapped[float] = mapped_column(default=1.0)
    growth_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    score_detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    universe_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("universe_snapshots.id"), nullable=True
    )
    margin_invest_value: Mapped[float | None] = mapped_column(nullable=True)
    buy_price: Mapped[float | None] = mapped_column(nullable=True)
    sell_price: Mapped[float | None] = mapped_column(nullable=True)
    actual_price: Mapped[float | None] = mapped_column(nullable=True)
    price_target_invalid_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    opportunity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    winning_track: Mapped[str | None] = mapped_column(String(30), nullable=True)
    asymmetry_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_position_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    timing_signal: Mapped[str | None] = mapped_column(String(30), nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship(back_populates="scores")

    __table_args__ = (
        Index("ix_scores_asset_scored", "asset_id", "scored_at"),
    )


class V3Score(Base):
    __tablename__ = "v3_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    opportunity_type: Mapped[str] = mapped_column(String(20))
    conviction: Mapped[str] = mapped_column(String(20))
    track_a: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    track_b: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    timing_signal: Mapped[str] = mapped_column(String(30))
    max_position_pct: Mapped[float] = mapped_column(Float, default=0.0)
    regime: Mapped[str] = mapped_column(String(20))
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)

    asset: Mapped["Asset"] = relationship(back_populates="v3_scores")

    __table_args__ = (
        Index("ix_v3_scores_asset_scored", "asset_id", "scored_at"),
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


class PriceIntraday(Base):
    """5-minute price bars. Backed by TimescaleDB hypertable in production."""

    __tablename__ = "prices_intraday"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="unknown")


class MetricsDerived(Base):
    """Precomputed factor inputs, one row per asset per date."""

    __tablename__ = "metrics_derived"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    as_of_date: Mapped[str] = mapped_column(String(10), nullable=False)

    # Quality factors
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    roic: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Value factors
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    fcf_yield: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Momentum factors
    return_1m: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_3m: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_6m: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_12m: Mapped[float | None] = mapped_column(Float, nullable=True)

    extra: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("asset_id", "as_of_date", name="uq_metrics_asset_date"),
        Index("ix_metrics_derived_date", "as_of_date"),
    )


class BacktestRun(Base):
    """A single backtest execution with config and aggregate results."""

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    universe_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("universe_snapshots.id"), nullable=False
    )
    start_date: Mapped[str] = mapped_column(String(10))
    end_date: Mapped[str] = mapped_column(String(10))
    rebalance_frequency: Mapped[str] = mapped_column(String(20))
    config: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    annualized_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary_stats: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    results: Mapped[list[BacktestResult]] = relationship(back_populates="run")


class BacktestResult(Base):
    """Per-ticker, per-date score within a backtest run."""

    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    as_of_date: Mapped[str] = mapped_column(String(10), nullable=False)
    signal: Mapped[str] = mapped_column(String(20), nullable=False)
    conviction_level: Mapped[str] = mapped_column(String(20), nullable=False)
    composite_percentile: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    run: Mapped[BacktestRun] = relationship(back_populates="results")

    __table_args__ = (
        UniqueConstraint("run_id", "asset_id", "as_of_date", name="uq_backtest_result"),
        Index("ix_backtest_results_run_date", "run_id", "as_of_date"),
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
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="analyst")
    subscription_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

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
