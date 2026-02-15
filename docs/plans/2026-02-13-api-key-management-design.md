# API Key Management & Stripe Subscription Design

## Goal

Add subscription-gated API key management to Margin Invest. Free users access yfinance-only data. Paid "Margin Invest" subscribers unlock premium provider connections (FMP, Polygon, Finnhub, FRED) via platform-managed or user-provided API keys, with full Stripe billing integration.

## Architecture

Subscription-gated provider keys (Approach A). Stripe manages billing and subscription lifecycle. Our DB stores plan state synced via webhooks. A `require_plan` FastAPI dependency gates premium features. API keys encrypted at rest with Fernet (same pattern as TOTP secrets). Platform-managed keys rotate every 90 days via ARQ background job.

## Tech Stack

- **Billing**: Stripe (Checkout Sessions, Customer Portal, Webhooks)
- **Encryption**: cryptography.fernet (Fernet symmetric encryption)
- **Background jobs**: ARQ (existing worker infrastructure)
- **ORM**: SQLAlchemy 2.0 async (existing)
- **Frontend**: Next.js settings page with Stripe Checkout redirect

---

## 1. Access Control Rules

| Capability | Free | Margin Invest |
|---|---|---|
| View scores (yfinance data only) | Yes | Yes |
| Run backtests | Yes | Yes |
| Dashboard | Yes | Yes |
| Premium providers (FMP, Polygon, Finnhub, FRED) | No | Yes |
| API key management | No | Yes |
| Platform-managed keys (default) | No | Yes |
| BYOK (user's own keys) | No | Yes |
| Priority scoring queue | No | Yes |

### Enforcement Points

- **`require_plan("margin_invest")`** — FastAPI dependency applied to API key CRUD routes and premium ingestion endpoints. Returns 403 with upgrade prompt for free users.
- **Provider Registry** — At ingestion time, if user is on free plan, only providers where `requires_api_key=False` are included in the fallback chain (yfinance + SEC EDGAR only).
- **Frontend** — Settings page shows API key section grayed out with upgrade CTA for free users.

---

## 2. Subscription Logic Flow

### Upgrade Flow

```
User clicks "Upgrade" in settings
  → POST /api/v1/billing/checkout
  → Server creates Stripe Checkout Session (mode=subscription, price=MARGIN_INVEST_PRICE_ID)
  → Returns checkout URL → Frontend redirects to Stripe

Stripe Checkout completes
  → Webhook: checkout.session.completed
  → Server: creates/updates stripe_customer_id on User
  → Webhook: customer.subscription.created
  → Server: sets subscription_plan = "margin_invest", stores subscription_id
  → Server: provisions platform-managed API keys for all 4 providers
  → Redirect to /settings?subscription=active
```

### Cancellation Flow

```
Subscription cancelled (Stripe portal or cancel endpoint)
  → Webhook: customer.subscription.deleted
  → Server: sets subscription_plan = "free"
  → Server: marks platform-managed keys as revoked (keeps BYOK keys but disables access)
  → User sees downgrade notice, API key section locked
```

### Payment Failure Flow

```
Renewal fails
  → Webhook: customer.subscription.updated (status=past_due)
  → Server: sets subscription_plan = "free"
  → Same downgrade behavior
```

### Webhook Security

- Verify `stripe-signature` header against `MARGIN_STRIPE_WEBHOOK_SECRET`
- All handlers idempotent — check current state before applying changes
- Store `stripe_event_id` to deduplicate replayed events

---

## 3. Security & Key Management Architecture

### Encryption at Rest

- New `ApiKeyService` with dedicated Fernet key (`MARGIN_API_KEY_ENCRYPTION_KEY` env var, separate from MFA encryption key)
- `ApiKey.encrypted_key` stores Fernet-encrypted provider API key
- Decryption only at ingestion time — plaintext key passed to provider, used, discarded from memory

### Key Rotation (Platform-Managed)

- ARQ background job `rotate_platform_keys` runs daily
- Checks `ApiKey` rows where `is_platform_managed=True` and `created_at` > 90 days
- Creates new key row, sets `expires_at = now + 24h` on old key
- Both old and new keys valid during 24-hour overlap window
- After overlap expires, old key soft-deleted via `revoked_at` timestamp

### ApiKey Model (Updated)

```python
class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_name: Mapped[str] = mapped_column(String(50))
    encrypted_key: Mapped[str] = mapped_column(Text)
    is_platform_managed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="api_keys")
    events: Mapped[list["ApiKeyEvent"]] = relationship(back_populates="api_key")
```

No unique constraint on `(user_id, provider_name)` — multiple rows allowed during rotation overlap.

**Active key query**: `WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())`

### ApiKeyEvent Model (New)

```python
class ApiKeyEvent(Base):
    __tablename__ = "api_key_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(20))  # created, rotated, revoked, accessed
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    api_key: Mapped["ApiKey"] = relationship(back_populates="events")
```

### User Model Changes

Add to both `User` and `CredentialUser`:

```python
stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
subscription_plan: Mapped[str] = mapped_column(String(20), default="free")  # "free" | "margin_invest"
```

### Config Changes

```python
# Stripe
stripe_secret_key: str = ""
stripe_publishable_key: str = ""
stripe_webhook_secret: str = ""
stripe_price_id: str = ""  # Margin Invest plan price ID

# API Key encryption
api_key_encryption_key: str = ""  # Base64-encoded Fernet key (separate from MFA key)
```

---

## 4. API Routes

### Billing Routes (`/api/v1/billing`)

| Method | Path | Description |
|---|---|---|
| POST | `/checkout` | Create Stripe Checkout Session, return URL |
| POST | `/portal` | Create Stripe Customer Portal session, return URL |
| POST | `/webhook` | Stripe webhook receiver (signature-verified) |
| GET | `/status` | Return current subscription plan + status |

### API Key Routes (`/api/v1/keys`)

All gated by `require_plan("margin_invest")`.

| Method | Path | Description |
|---|---|---|
| GET | `/` | List active keys (masked, never return plaintext) |
| POST | `/` | Create/update key for a provider |
| DELETE | `/{provider_name}` | Revoke key for a provider |
| POST | `/{provider_name}/rotate` | Force immediate rotation (platform-managed) |

---

## 5. Risk Considerations

1. **Stripe webhook replay/failure** — Idempotent handlers + Stripe's built-in retry (up to 3 days). Deduplicate via `stripe_event_id`.
2. **Encryption key loss** — If `MARGIN_API_KEY_ENCRYPTION_KEY` is lost, all stored keys are unrecoverable. Document key backup procedure.
3. **Platform key compromise** — 90-day rotation limits blast radius. Emergency rotation endpoint available.
4. **Race condition on cancellation** — Check plan at ingestion job start, not per-request. Jobs in flight complete; new jobs gated.
5. **BYOK key validity** — Cannot verify user's key until first use. Surface provider errors in UI.

---

## 6. Best Practices

1. **Separate encryption keys** — MFA and API key encryption use different Fernet keys. Compromise of one doesn't expose the other.
2. **Never log plaintext keys** — Decrypted keys exist only in memory during provider calls. Audit log records access events, not key values.
3. **Webhook signature verification** — Always verify `stripe-signature`. Reject unverified payloads with 400.
4. **Stripe Customer Portal** — Use Stripe's hosted portal for subscription management (cancel, update payment method). Minimizes custom code and PCI scope.
5. **Graceful degradation** — If platform-managed key hits rate limit, fall back to free providers (yfinance) rather than failing entirely.
6. **Frontend optimistic UI** — Show subscription state from session immediately, reconcile with server state on settings page load.
