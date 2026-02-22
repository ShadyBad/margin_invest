# Support Page Redesign

**Date**: 2026-02-22
**Status**: Approved

## Overview

Replace the current `/support` page with a categorized support hub. The existing page mixes product education with support content and lacks visual wayfinding. The new page is support-focused (product education stays on Methodology), uses topic cards for navigation, accordion FAQs for self-service, and routes users to the correct email contact when they need human help.

## Audience

Primarily retail individual investors. Occasional institutional users.

## Page Structure

```
Navbar
Hero ("How can we help?" + subtitle)
Topic Cards (2x2 grid)
FAQ Accordion (grouped by category)
Contact Section ("Still need help?" + 3 email cards)
Status Page Link
Back to Home
```

### Hero

- **Title**: "How can we help?"
- **Subtitle**: "Find answers to common questions or reach out to our team directly."
- Centered, same `max-w-3xl` container as Legal page.

### Topic Cards

2x2 responsive grid. Each card has an inline SVG icon, title, and one-line description. Clicking a card smooth-scrolls to the corresponding FAQ section.

| Card | Title | Description | Icon |
|------|-------|-------------|------|
| 1 | Account & Access | Login issues, email verification, MFA, and account settings | Shield/Lock |
| 2 | Scores & Data | How scores update, missing data, methodology questions | ChartBar |
| 3 | Billing & Subscription | Plan details, payment questions, cancellations | CreditCard |
| 4 | Security & Privacy | Data protection, vulnerability reporting, privacy practices | Fingerprint |

Styling: `bg-bg-secondary`, `border-border-subtle`, hover state with slight border/bg shift.

### FAQ Accordion

Single-expand per category (opening one item closes the previous within that group). Each category has a heading that matches its topic card.

#### Account & Access

- **I can't log in to my account** — Check email/password, clear cache, try incognito. If using MFA, ensure authenticator app is synced. Contact support@ if unresolved.
- **How do I reset my password?** — Click "Forgot password" on login page. Reset link sent to registered email. Check spam if not received within a few minutes.
- **How do I enable or disable MFA?** — Account Settings > Security. TOTP-based MFA with any authenticator app.
- **How do I update my email address?** — Contact support@margin-invest.com from current registered email.

#### Scores & Data

- **How often are scores updated?** — Periodic refresh based on data source reporting cycles. Price data updates more frequently than fundamentals.
- **Why is a company missing from the platform?** — Scoring engine requires minimum financial data. Companies with insufficient reporting may not pass elimination filters.
- **Why does a metric show as unavailable?** — Some securities lack reporting depth for certain calculations. Expected for newer listings or foreign-domiciled companies.
- **Where can I learn how scoring works?** — Links to Methodology page.

#### Billing & Subscription

- **What plans are available?** — Points to pricing or describes current plan structure.
- **How do I cancel my subscription?** — Account Settings > Subscription. Takes effect at end of current billing period.
- **I was charged incorrectly** — Contact support@margin-invest.com with account email and transaction details.

#### Security & Privacy

- **How is my data protected?** — Encrypted at rest and in transit. No selling of personal data.
- **I want to report a security vulnerability** — Email security@margin-invest.com. Response within 48 hours.
- **How do I request deletion of my data?** — Email legal@margin-invest.com from registered email. Processed per applicable privacy regulations.

### Contact Section

Heading: "Still need help?"
Subtext: Brief line encouraging users to reach out.

Three contact cards (row on desktop, stacked on mobile):

| Channel | Email | Description |
|---------|-------|-------------|
| General Support | support@margin-invest.com | Platform questions, account help, billing issues |
| Security | security@margin-invest.com | Vulnerability reports, suspicious activity |
| Legal & Privacy | legal@margin-invest.com | Data deletion requests, legal inquiries, privacy questions |

Each email is a `mailto:` link. Same card styling as topic cards.

### Status Page Link

Single line below contact cards:
"Check our system status page for real-time platform availability."
Links to `status.margin-invest.com` (placeholder).

### Back to Home

Same pattern as Legal page: `<- Back to home` link with `border-t` separator.

## Technical Details

- **File**: `web/src/app/support/page.tsx` (replace in-place)
- **Client component**: `"use client"` for accordion interactivity
- **State**: `useState` for accordion open/close, single-expand per category
- **Icons**: Inline SVGs, no external icon library
- **Dependencies**: None added
- **Layout**: `max-w-3xl` container, consistent with Legal page
- **Styling**: Existing design tokens only (`bg-bg-primary`, `bg-bg-secondary`, `text-text-primary`, `text-text-secondary`, `text-text-tertiary`, `border-border-subtle`, `text-accent`)

## What Changes

- Product education content (three pillars, portfolio construction, conviction score explanation) removed from Support page. Already covered by Methodology page.
- FAQ items rewritten to be actionable support answers rather than product descriptions.
- Contact routing added (support@, security@, legal@) instead of a single generic email.
- Status page link added (placeholder URL).

## Email Distributions

| Address | Purpose |
|---------|---------|
| support@margin-invest.com | General platform support |
| security@margin-invest.com | Vulnerability reports, security concerns |
| legal@margin-invest.com | Data deletion, legal inquiries, privacy |
| noreply@margin-invest.com | System-generated emails (not shown on support page) |
