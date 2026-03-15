"""SQLAlchemy ORM models for Margin Invest."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
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
    tickers_partial: Mapped[int] = mapped_column(default=0)
    provider_stats: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    circuit_breaker_trips: Mapped[int] = mapped_column(default=0)
    pipeline_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)

    snapshot: Mapped[UniverseSnapshot] = relationship()
    ticker_statuses: Mapped[list[IngestionTickerStatus]] = relationship(back_populates="run")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(50))
    # queued | running | completed | failed | cancelled
    status: Mapped[str] = mapped_column(String(20))
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    progress_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(20))  # schedule | cli | chained
    parent_job_id: Mapped[int | None] = mapped_column(ForeignKey("job_runs.id"), nullable=True)
    pipeline_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
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
    cusip: Mapped[str | None] = mapped_column(String(9), nullable=True, index=True)
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
    v4_scores: Mapped[list[V4Score]] = relationship(back_populates="asset")


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
    data_categories_present: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="yfinance")
    consistency_flags: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
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
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OAuth fields (nullable — absent for credential-only users)
    oauth_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Credential fields (nullable — absent for OAuth-only users)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    mfa_grace_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_totp_counter: Mapped[int | None] = mapped_column(nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Billing
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="analyst")
    subscription_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Avatars
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    oauth_avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    linked_providers: Mapped[list[LinkedProvider]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="user")
    totp_secrets: Mapped[list[TotpSecret]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    webauthn_credentials: Mapped[list[WebAuthnCredential]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    challenge_tokens: Mapped[list[MfaChallengeToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recovery_codes: Mapped[list[RecoveryCode]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    @property
    def auth_methods(self) -> list[str]:
        methods = []
        if self.has_password:
            methods.append("credentials")
        if self.linked_providers:
            methods.extend(lp.provider for lp in self.linked_providers)
        return methods


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

    __table_args__ = (Index("ix_scores_asset_scored", "asset_id", "scored_at"),)


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

    asset: Mapped[Asset] = relationship(back_populates="v3_scores")

    __table_args__ = (Index("ix_v3_scores_asset_scored", "asset_id", "scored_at"),)


class V4Score(Base):
    __tablename__ = "v4_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    opportunity_type: Mapped[str] = mapped_column(String(30))
    conviction: Mapped[str] = mapped_column(String(20))
    rules_conviction: Mapped[str] = mapped_column(String(20))
    track_a: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    track_b: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    track_c: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    style: Mapped[str] = mapped_column(String(10))
    timing_signal: Mapped[str] = mapped_column(String(30))
    max_position_pct: Mapped[float] = mapped_column(Float, default=0.0)
    regime: Mapped[str] = mapped_column(String(20))
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    ml_alpha: Mapped[float | None] = mapped_column(Float, nullable=True)
    ml_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ml_override: Mapped[str] = mapped_column(String(20), default="none")
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    published: Mapped[bool] = mapped_column(default=False)

    asset: Mapped[Asset] = relationship(back_populates="v4_scores")

    __table_args__ = (
        Index("ix_v4_scores_asset_scored", "asset_id", "scored_at"),
        Index("ix_v4_scores_scored_at", "scored_at"),
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
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    environment_snapshot: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    pit_data_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

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


class MlModelRun(Base):
    """Tracks ML model training runs (clustering + LightGBM)."""

    __tablename__ = "ml_model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "lightgbm_cluster"
    n_clusters: Mapped[int] = mapped_column(default=0)
    n_features: Mapped[int] = mapped_column(default=0)
    n_samples: Mapped[int] = mapped_column(default=0)
    train_metrics: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    model_qualifies: Mapped[bool] = mapped_column(default=False)
    overall_rank_ic: Mapped[float | None] = mapped_column(Float, nullable=True)
    vae_rank_ic: Mapped[float | None] = mapped_column(Float, nullable=True)
    vae_artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Model bytes stored in DB for persistence across container deploys
    cluster_model_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    vae_model_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # SHA-256 checksums for integrity verification before unpickling
    cluster_model_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vae_model_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deployment_status: Mapped[str] = mapped_column(String(20), default="candidate")
    seed: Mapped[int] = mapped_column(Integer, default=42)
    run_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class SeedValidationReport(Base):
    """Distributional validation results for a multi-seed ML training run."""

    __tablename__ = "seed_validation_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_group_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    n_seeds: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_distributions: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    gate_passed: Mapped[bool] = mapped_column(default=False)
    gate_details: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    selected_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_comparison: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    environment_snapshot: Mapped[dict] = mapped_column(JSONVariant, nullable=False)


class ReproducibilityAudit(Base):
    """Audit trail for pipeline reproducibility."""

    __tablename__ = "reproducibility_audits"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    environment_snapshot: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    input_data_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


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
# Event / Notification models
# ---------------------------------------------------------------------------


class Event(Base):
    """Persisted event (score changes, earnings, etc.)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    notifications: Mapped[list[Notification]] = relationship(back_populates="event")

    __table_args__ = (Index("ix_events_ticker_timestamp", "ticker", "timestamp"),)


class Notification(Base):
    """User-facing notification derived from an event."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    event: Mapped[Event] = relationship(back_populates="notifications")


# ---------------------------------------------------------------------------
# Authentication models
# ---------------------------------------------------------------------------


class LinkedProvider(Base):
    """Tracks which OAuth providers are linked to a user account."""

    __tablename__ = "linked_providers"
    __table_args__ = (
        UniqueConstraint("provider", "oauth_id", name="uq_linked_providers_provider_oauth_id"),
        UniqueConstraint("user_id", "provider", name="uq_linked_providers_user_id_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(50))
    oauth_id: Mapped[str] = mapped_column(String(255))
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="linked_providers")


class RecoveryCode(Base):
    """Hashed backup codes for MFA recovery."""

    __tablename__ = "recovery_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    code_hash: Mapped[str] = mapped_column(Text)
    used: Mapped[bool] = mapped_column(default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="recovery_codes")


class TotpSecret(Base):
    """Encrypted TOTP secret for a user."""

    __tablename__ = "totp_secrets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    encrypted_secret: Mapped[str] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="totp_secrets")


class WebAuthnCredential(Base):
    """WebAuthn/passkey credential for a user."""

    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    credential_id: Mapped[str] = mapped_column(Text, unique=True)
    public_key: Mapped[str] = mapped_column(Text)
    sign_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="webauthn_credentials")


class MfaChallengeToken(Base):
    """Short-lived challenge token issued after password verification, consumed by MFA step."""

    __tablename__ = "mfa_challenge_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped[User] = relationship(back_populates="challenge_tokens")


# ---------------------------------------------------------------------------
# Shadow Portfolio models
# ---------------------------------------------------------------------------


class ShadowPortfolioSnapshot(Base):
    """Daily shadow portfolio state -- append-only, never backdated."""

    __tablename__ = "shadow_portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    as_of_date: Mapped[str] = mapped_column(String(10), nullable=False)
    portfolio_value: Mapped[float] = mapped_column(Float, nullable=False)
    total_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    num_positions: Mapped[int] = mapped_column(default=0)
    positions_json: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("as_of_date", name="uq_shadow_snapshot_date"),
        Index("ix_shadow_snapshot_date", "as_of_date"),
    )


# ---------------------------------------------------------------------------
# 13F / Institutional Holdings models
# ---------------------------------------------------------------------------


class Manager(Base):
    """SEC-registered institutional investment manager (13F filer)."""

    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text)
    short_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    tier: Mapped[str] = mapped_column(String(20), default="top_aum")
    aum_latest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    first_filing_date: Mapped[date | None] = mapped_column(nullable=True)
    last_filing_date: Mapped[date | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    filings: Mapped[list[FilingMetadata]] = relationship(back_populates="manager")


class SecurityMaster(Base):
    """CUSIP-keyed security reference table for 13F cross-referencing."""

    __tablename__ = "security_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    cusip: Mapped[str] = mapped_column(String(9), unique=True, index=True)
    ticker: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    figi: Mapped[str | None] = mapped_column(String(12), nullable=True)
    issuer_name: Mapped[str] = mapped_column(Text)
    security_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    resolution_method: Mapped[str] = mapped_column(String(20), default="unresolved")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    asset: Mapped[Asset | None] = relationship()


class FilingMetadata(Base):
    """Metadata for a single 13F-HR filing."""

    __tablename__ = "filing_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("managers.id"), index=True)
    accession_number: Mapped[str] = mapped_column(String(25), unique=True)
    filing_type: Mapped[str] = mapped_column(String(15))
    period_of_report: Mapped[date] = mapped_column(index=True)
    filed_date: Mapped[date]
    total_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_holdings: Mapped[int | None] = mapped_column(nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_amendment: Mapped[bool] = mapped_column(default=False)
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("filing_metadata.id"), nullable=True
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("job_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    manager: Mapped[Manager] = relationship(back_populates="filings")
    holdings: Mapped[list[InstitutionalHolding]] = relationship(back_populates="filing")

    __table_args__ = (Index("ix_filing_manager_period", "manager_id", "period_of_report"),)


class InstitutionalHolding(Base):
    """Individual holding line from a 13F filing."""

    __tablename__ = "institutional_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filing_metadata.id"), index=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("managers.id"), index=True)
    security_master_id: Mapped[int] = mapped_column(ForeignKey("security_master.id"), index=True)
    cusip: Mapped[str] = mapped_column(String(9))
    period_of_report: Mapped[date]
    shares_held: Mapped[int] = mapped_column(BigInteger)
    value_thousands: Mapped[int] = mapped_column(BigInteger)
    put_call: Mapped[str] = mapped_column(String(10), default="NONE")
    investment_discretion: Mapped[str | None] = mapped_column(String(10), nullable=True)
    voting_authority_sole: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    voting_authority_shared: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    voting_authority_none: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    filing: Mapped[FilingMetadata] = relationship(back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("filing_id", "cusip", "put_call", name="uq_holding_filing_cusip_putcall"),
        Index("ix_holding_cusip_period", "cusip", "period_of_report"),
        Index("ix_holding_manager_period", "manager_id", "period_of_report"),
        Index("ix_holding_secmaster_period", "security_master_id", "period_of_report"),
    )


class AccumulationSignal(Base):
    """Aggregated institutional accumulation signal per asset per quarter."""

    __tablename__ = "accumulation_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    period_of_report: Mapped[date]
    curated_holders: Mapped[int] = mapped_column(default=0)
    total_holders: Mapped[int] = mapped_column(default=0)
    curated_new_positions: Mapped[int] = mapped_column(default=0)
    total_new_positions: Mapped[int] = mapped_column(default=0)
    curated_net_shares: Mapped[int] = mapped_column(BigInteger, default=0)
    total_net_shares: Mapped[int] = mapped_column(BigInteger, default=0)
    signal_score: Mapped[float] = mapped_column(Float, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship()

    __table_args__ = (
        UniqueConstraint("asset_id", "period_of_report", name="uq_accumulation_asset_period"),
    )


class ProcessedWebhookEvent(Base):
    """Idempotency tracking for Stripe webhook events."""

    __tablename__ = "processed_webhook_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AuditLog(Base):
    """Append-only audit log for security-relevant events."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


# ---------------------------------------------------------------------------
# Governance models
# ---------------------------------------------------------------------------


class PipelineApproval(Base):
    """Tracks approval gates for high-stakes pipeline outputs."""

    __tablename__ = "pipeline_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    gate_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="staged")
    pipeline_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    payload_ref: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    impact_summary: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_pipeline_approvals_status", "status"),
        Index("ix_pipeline_approvals_gate_type", "gate_type"),
    )


class GovernanceEvent(Base):
    """Lightweight event log for governance actions."""

    __tablename__ = "governance_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(50))
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class GovernanceConfig(Base):
    """Key-value config for governance thresholds."""

    __tablename__ = "governance_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True)
    config_value: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class UserProposal(Base):
    """System-generated proposals for end-user approval."""

    __tablename__ = "user_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    proposal_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payload: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_user_proposals_user_status", "user_id", "status"),)


# ---------------------------------------------------------------------------
# Data Healing / Correction models
# ---------------------------------------------------------------------------


class CorrectionEventRecord(Base):
    """Persisted correction event from the data healing pipeline."""

    __tablename__ = "correction_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    correction_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    period_end: Mapped[str] = mapped_column(String(10))
    field_path: Mapped[str] = mapped_column(String(100))
    detection_tier: Mapped[str] = mapped_column(String(20))
    detection_detail: Mapped[str] = mapped_column(String(500))
    original_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    corrected_value: Mapped[float] = mapped_column(Float)
    correction_method: Mapped[str] = mapped_column(String(30))
    correction_source: Mapped[str] = mapped_column(String(100))
    correction_confidence: Mapped[float] = mapped_column(Float)
    correction_config_version: Mapped[str] = mapped_column(String(20))
    sector_distribution_snapshot: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    scoring_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    asset: Mapped[Asset] = relationship()


class SectorDistributionSnapshot(Base):
    """Snapshot of sector-level distribution stats for a scoring run."""

    __tablename__ = "sector_distribution_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    scoring_run_id: Mapped[str] = mapped_column(String(36), index=True)
    sector: Mapped[str] = mapped_column(String(50))
    field_path: Mapped[str] = mapped_column(String(100))
    median: Mapped[float] = mapped_column(Float)
    mad: Mapped[float] = mapped_column(Float)
    n_observations: Mapped[int] = mapped_column()
    period: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


# ---------------------------------------------------------------------------
# Point-in-Time (PIT) backtesting data models
# ---------------------------------------------------------------------------


class PITFinancialSnapshot(Base):
    """One row per SEC filing, storing as-originally-reported financials."""

    __tablename__ = "pit_financial_snapshots"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    cik: Mapped[str] = mapped_column(String(10), index=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    filing_date: Mapped[date] = mapped_column(index=True)
    period_end: Mapped[date]
    form_type: Mapped[str] = mapped_column(String(10))
    accession_number: Mapped[str] = mapped_column(String(30), unique=True)
    income_statement: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    balance_sheet: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    cash_flow: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    fiscal_quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sic_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (Index("ix_pit_financial_ticker_filing_date", "ticker", "filing_date"),)


class EdgarNoXBRLCache(Base):
    """Cache of accession numbers checked and found to have no XBRL data.

    Prevents repeated HTTP requests to SEC.gov for pre-XBRL era filings
    that will never have parseable data.
    """

    __tablename__ = "edgar_no_xbrl_cache"

    accession_number: Mapped[str] = mapped_column(String(30), primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PITDailyPrice(Base):
    """Daily OHLCV price data for point-in-time backtesting."""

    __tablename__ = "pit_daily_prices"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[date] = mapped_column(primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adj_close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(20), default="yfinance")


class PITUniverseMembership(Base):
    """Quarterly universe membership snapshot for survivorship-bias-free backtesting."""

    __tablename__ = "pit_universe_memberships"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    cik: Mapped[str] = mapped_column(String(10))
    quarter_date: Mapped[date]
    is_active: Mapped[bool] = mapped_column(default=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    sic_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_daily_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_filing_date: Mapped[date | None] = mapped_column(nullable=True)
    delist_detected_at: Mapped[date | None] = mapped_column(nullable=True)
    last_known_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("ticker", "quarter_date", name="uq_pit_universe_ticker_quarter"),
        Index("ix_pit_universe_quarter_date", "quarter_date"),
    )


class SICSectorMap(Base):
    """Static mapping from SIC codes to GICS sectors."""

    __tablename__ = "sic_sector_map"

    sic_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    gics_sector: Mapped[str] = mapped_column(String(50))
    sic_description: Mapped[str | None] = mapped_column(String(200), nullable=True)


class EdgarIndexCache(Base):
    """Cache of parsed EDGAR quarter index entries for resumable backfills."""

    __tablename__ = "edgar_index_cache"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    cache_key: Mapped[str] = mapped_column(String(20), unique=True)
    entries_json: Mapped[dict | list] = mapped_column(JSONVariant)
    entry_count: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (Index("ix_edgar_index_cache_year_quarter", "year", "quarter", unique=True),)


class HistoricalScore(Base):
    """Historical composite scores generated from PIT data for ML training."""

    __tablename__ = "historical_scores"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    score_date: Mapped[date] = mapped_column(index=True)
    composite_score: Mapped[float] = mapped_column(Float)
    composite_tier: Mapped[str] = mapped_column(String(20))
    sub_scores: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("ticker", "score_date", name="uq_historical_score_ticker_date"),
    )
