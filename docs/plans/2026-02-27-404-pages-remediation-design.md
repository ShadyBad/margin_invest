# 404 Pages Remediation: Security, API Docs, Contact

**Date:** 2026-02-27
**Status:** Approved

## Root Cause

The landing page footer (`web/src/components/landing/footer-section.tsx`) links to `/security`, `/api`, and `/contact`, but no corresponding `page.tsx` files exist under `web/src/app/`. These pages were never created — the links were added before the pages were built. This is purely a missing-pages issue, not a routing, deployment, or CMS problem.

The authenticated-area footer (`web/src/components/layout/footer.tsx`) does not link to these pages, so the 404s only surface from the landing/marketing pages.

## Technical Approach

**Static Next.js pages** — three new `page.tsx` files following the existing pattern used by `/legal`, `/methodology`, and `/support`. No new dependencies, no CMS, no MDX.

All three pages are publicly accessible (no auth gate). This is standard for trust/compliance pages and optimal for SEO.

### Route Mapping

| Footer Link | Route | Notes |
|---|---|---|
| Security | `/security` | New page |
| API | `/api-docs` | New page. Cannot use `/api` — Next.js reserves `app/api/` for API route handlers. Footer link updated. |
| Contact | `/contact` | New page |

### File Changes

**New files:**
- `web/src/app/security/page.tsx`
- `web/src/app/api-docs/page.tsx`
- `web/src/app/contact/page.tsx`
- `web/src/app/sitemap.ts`
- `web/src/app/robots.ts`
- Tests for each page

**Modified files:**
- `web/src/components/landing/footer-section.tsx` — change `/api` to `/api-docs`
- `web/src/components/layout/footer.tsx` — add Security, API Docs, Contact links

## Page Content

### Security (`/security`)

Full security posture disclosure. Seven sections:

1. **Hero** — "How We Protect Your Data." One-liner: Margin Invest is built with security as a first-class constraint, not an afterthought.

2. **Infrastructure & Encryption**
   - Railway container-based hosting with isolated deployments
   - TLS everywhere (HTTPS enforced, HSTS headers)
   - Data encrypted at rest (PostgreSQL encrypted volumes)
   - All inter-service communication over encrypted channels
   - Security headers: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, CSP report-only

3. **Authentication & Access Control**
   - JWT-based session authentication with HMAC signing
   - TOTP multi-factor authentication (MFA)
   - httpOnly secure cookies for MFA tokens
   - Password hashing with industry-standard algorithms
   - Rate limiting on auth endpoints (slowapi)
   - API key authentication for programmatic access

4. **Data Protection**
   - No sale of personal data to third parties
   - Minimal data collection (auth + platform functionality only)
   - Data deletion available on request
   - Aggregated anonymized analytics only
   - Pickle model checksums for ML artifact integrity

5. **Pipeline Integrity**
   - Deterministic scoring: same inputs always produce same outputs
   - Human oversight pipeline: staged → approved → published
   - Circuit breakers: score drift >30%, ingestion failure >20%, ML regression >50%
   - Governance audit log with full event history

6. **Compliance Posture**
   - Industry best practices aligned with SOC 2 principles (formal certification on roadmap)
   - GDPR-aligned data handling (deletion requests, minimal collection)
   - No misleading claims about certifications not yet obtained

7. **Vulnerability Disclosure**
   - Dedicated email: `security@margin-invest.com`
   - 48-hour acknowledgment SLA
   - Responsible disclosure expectations
   - Link to `/support` for general security questions

### API Documentation (`/api-docs`)

Developer-facing REST API reference. Six sections:

1. **Hero** — "API Reference." Programmatic access to scoring, backtesting, and institutional data. CTA: "Request API Key" linking to `/account` or `/register`.

2. **Authentication**
   - API key via `X-API-Key` header
   - Key generation in Account Settings
   - Key rotation and revocation
   - Example curl request

3. **Rate Limits & Usage**
   - Rate limit policy (slowapi-enforced)
   - Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
   - Plan-based tiers if applicable
   - 429 handling guidance

4. **Core Endpoints** — Grouped by domain, each with method, path, description, example response:
   - **Scores**: `GET /api/v1/score/{ticker}`, `GET /api/v1/score/{ticker}/history`, `GET /api/v1/score/{ticker}/valuation`
   - **Universe**: `GET /api/v1/universe/funnel`
   - **Backtesting**: `GET /api/v1/backtest/default`, `/replay`, `/shadow-portfolio`
   - **Institutional**: `GET /api/v1/13f/holders/{ticker}`, `/accumulation/{ticker}`
   - **Correlations**: `GET /api/v1/correlations/showcase`
   - **Transparency**: `GET /api/v1/transparency/oversight`, `/pipeline-health`

5. **Response Format & Errors**
   - All responses JSON
   - Error shape: `{ "detail": "..." }`
   - Status codes: 401 (missing/invalid key), 403 (insufficient plan), 404 (ticker not found), 429 (rate limited), 500 (internal)

6. **SDKs & Support**
   - REST-only, no official SDKs yet
   - Link to `/contact` for integration support
   - Link to `/security` for data handling

### Contact (`/contact`)

Standalone contact hub, distinct from `/support` (which is FAQ-first). Five sections:

1. **Hero** — "Get in Touch." Whether you're a developer, investor, or researcher — we'll route you to the right person.

2. **Contact Channels** — Grid of 4 cards with response time SLAs:
   - General Support — `support@margin-invest.com` — within 24 hours
   - Security — `security@margin-invest.com` — within 48 hours
   - Legal & Privacy — `legal@margin-invest.com` — within 5 business days
   - Business & Partnerships — `partnerships@margin-invest.com` — within 3 business days

3. **Contact Form** — Client component (`'use client'`):
   - Fields: name, email, subject category (dropdown), message
   - Form submits to `POST /api/v1/contact` or constructs `mailto:` fallback
   - Client-side validation on required fields

4. **Office Hours & Availability**
   - Support: Monday–Friday, 9 AM – 6 PM ET
   - Security reports: Monitored 7 days a week
   - Link to `/status` for platform health

5. **Quick Links** — Cross-navigation:
   - `/support` (FAQ), `/security`, `/api-docs`, `/legal`

## SEO

### Sitemap (`web/src/app/sitemap.ts`)

New file enumerating all public pages:
- `/`, `/methodology`, `/legal`, `/support`, `/status`, `/guides`
- `/security`, `/api-docs`, `/contact`

Excludes: `/dashboard`, `/account`, `/settings`, `/admin/*`, `/login`, `/register`, `/reset-password`, `/mfa/*`

Static `lastModified` dates, `changeFrequency: 'monthly'`.

### Robots (`web/src/app/robots.ts`)

New file:
- `Allow: /` for all user agents
- `Disallow: /dashboard, /account, /settings, /admin, /api/v1`
- Sitemap URL reference

### Metadata

Each page exports:
```ts
export const metadata: Metadata = {
  title: "Page Title | Margin Invest",
  description: "...",
  alternates: { canonical: "https://margin-invest.com/page-path" },
}
```

### No Redirects

These pages never existed, so no 301s are needed. The `/api` → `/api-docs` rename ships atomically (footer link + new page in the same deploy).

## Validation & QA

### Functional Tests (Vitest + @testing-library/react)

Per page:
- Renders without errors
- All expected headings and sections present
- All `mailto:` links have correct `href`
- Contact form validates required fields and submits
- Metadata exports have correct title and description
- Internal links resolve to valid routes

### Link Integrity

- Grep all components for remaining references to `/api` (old broken path), update to `/api-docs`
- Verify no other components reference `/security` or `/contact` before those pages exist

### Regression Prevention

Add a link integrity test: assert every `href` in the landing `FooterSection` and authenticated `Footer` maps to an existing route. This test fails if someone adds a footer link without creating the corresponding page.

### SEO Validation

- Each page returns 200
- `sitemap.ts` output includes all three new pages
- `robots.ts` disallows authenticated routes

## Content Review

Security and API pages contain technical claims about the platform's architecture. Before publishing:
- Security page content must be verified against actual implementation (JWT/HMAC auth, rate limiting, circuit breakers — all confirmed shipped in security remediation and human oversight milestones)
- API endpoint list must be verified against current route registrations
- Response time SLAs on contact page require product owner sign-off

## Out of Scope

- `POST /api/v1/contact` backend endpoint (contact form falls back to `mailto:` construction)
- Live Swagger UI or interactive API explorer
- CMS integration
- Privacy policy as a standalone page (remains section 4 of `/legal`)
