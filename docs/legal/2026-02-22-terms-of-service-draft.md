# Margin Invest — Terms of Service Draft

**Prepared:** 2026-02-22
**Status:** DRAFT — Not legal advice. Have an attorney review before publishing.

---

## Codebase-Verified Facts Used in This Draft

| Category | Finding |
|----------|---------|
| Subscription tiers | Analyst (free, 3 analyses/mo, 5-ticker watchlist), Portfolio ($29/mo, unlimited, 25-ticker), Institutional ($79/mo, unlimited, API access, correlation, sector rotation) |
| Payment | Stripe checkout + customer portal; no payment card data stored locally |
| Auth | Email/password (Argon2id) + OAuth (Google, GitHub) + MFA (TOTP, WebAuthn) |
| UGC | Profile avatar only; no user-created watchlists, notes, or portfolios stored |
| Public API | Mentioned as Institutional feature; not yet exposed |
| Rate limits | None implemented on user-facing API |
| Refund logic | None in codebase; Stripe portal handles cancellation |
| Suspension | No suspension/ban mechanism implemented |
| Data export | Not implemented |
| Uptime/SLA | No commitments |
| Account restrictions | Unique email constraint; no multi-account or sharing detection |

---

# VERSION 1: FULL / DETAILED

---

## Terms of Service

**Last Updated: [DATE]**

These Terms of Service ("Terms") govern your access to and use of the Margin Invest platform, website, and related services (collectively, the "Service") operated by [LEGAL ENTITY NAME] ("Margin Invest," "we," "us," or "our").

By creating an account or using the Service, you agree to these Terms. If you do not agree, do not use the Service.

These Terms incorporate by reference our [Legal Disclaimers](/legal) and [Privacy Policy](/privacy). Please read all three documents.

---

### 1. Eligibility

To use Margin Invest, you must:

- Be at least [18] years old [CONFIRM AGE MINIMUM]
- Be a resident of the United States [OR CONFIRM WHETHER NON-US USERS ARE PERMITTED]
- Be capable of forming a binding legal agreement
- Not be prohibited from using the Service under applicable law

[IF STATE EXCLUSIONS EXIST, LIST THEM HERE.]

By creating an account, you represent that you meet these requirements.

---

### 2. Account Registration and Security

#### 2.1 Account Creation

You may create an account using an email address and password, or by authenticating through a supported OAuth provider (currently Google and GitHub). You must provide accurate and complete information during registration.

Each person may maintain only one account. You may not create multiple accounts, share account credentials, or allow others to access your account.

#### 2.2 Password and Security Requirements

If you register with email and password, your password must meet our security requirements (currently: minimum 12 characters, including uppercase, lowercase, digit, and special character).

#### 2.3 Multi-Factor Authentication

Margin Invest requires multi-factor authentication (MFA) for accounts that use email and password login. New accounts receive a [72]-hour grace period to set up MFA. After the grace period, MFA is mandatory to access the Service.

You are responsible for safeguarding your MFA credentials, recovery codes, and any registered passkeys.

#### 2.4 Account Security

You are responsible for all activity that occurs under your account. You agree to:

- Keep your login credentials confidential
- Notify us immediately if you suspect unauthorized access to your account
- Not share your account with any other person

We are not liable for any loss resulting from unauthorized use of your account.

---

### 3. Description of the Service

Margin Invest is a quantitative stock analysis platform. It provides automated scoring, factor analysis, backtested performance data, conviction classifications, and related research tools for US equities.

**The Service is not financial advice.** Please review our [Legal Disclaimers](/legal) for complete disclosure of what Margin Invest is and is not. In particular:

- Margin Invest is not a broker-dealer, investment adviser, or custodian
- We do not execute trades, hold funds, or connect to brokerage accounts
- Scores, ratings, and classifications are model outputs, not recommendations
- Backtested results are hypothetical and do not predict future performance
- We do not provide margin, leverage, or lending of any kind

---

### 4. Subscription Plans and Billing

#### 4.1 Plans

Margin Invest offers the following subscription tiers:

| Feature | Analyst (Free) | Portfolio ($29/mo) | Institutional ($79/mo) |
|---------|---------------|-------------------|----------------------|
| Analyses per month | 3 | Unlimited | Unlimited |
| Scoring detail | Composite score | Full 6-factor breakdown | Full 6-factor breakdown |
| Score history | None | 90 days | Unlimited |
| Watchlist size | 5 tickers | 25 tickers | Unlimited |
| Conviction alerts | No | Yes | Yes |
| Correlation analysis | No | No | Yes |
| Sector rotation | No | No | Yes |
| API access | No | No | [PLANNED — DETAILS TBD] |

Pricing, features, and plan names may change. We will notify existing subscribers before changes take effect on their next billing cycle.

#### 4.2 Billing

Paid subscriptions are billed monthly through Stripe. By subscribing to a paid plan, you authorize Stripe to charge your selected payment method on a recurring monthly basis.

All payment processing is handled by Stripe. We do not receive, process, or store your credit card numbers or bank account details. Your use of Stripe is subject to [Stripe's Terms of Service](https://stripe.com/legal).

#### 4.3 Free Trial

[IF APPLICABLE: New users may receive a [14]-day free trial of [PLAN NAME]. At the end of the trial, your subscription will convert to a paid plan unless you cancel. CONFIRM WHETHER FREE TRIALS ARE OFFERED.]

#### 4.4 Cancellation

You may cancel your subscription at any time through the Stripe Customer Portal accessible from your account settings. Upon cancellation:

- Your paid features remain active until the end of the current billing period
- Your account reverts to the Analyst (free) tier after the billing period ends
- Your account data is retained [CONFIRM RETENTION POLICY]

#### 4.5 Refunds

[OPTION A — NO REFUNDS:]
All subscription fees are non-refundable. If you cancel, you retain access to paid features through the end of your current billing period but will not receive a prorated refund for the remaining days.

[OPTION B — 30-DAY MONEY-BACK:]
If you are unsatisfied with a paid subscription, you may request a full refund within 30 days of your initial subscription purchase by contacting [CONTACT EMAIL]. Refunds are not available for subsequent renewal periods. After 30 days, all fees are non-refundable.

[CHOOSE ONE OPTION AND DELETE THE OTHER.]

#### 4.6 Price Changes

We may change subscription pricing with at least [30] days' notice to existing subscribers. Price changes take effect at the start of the next billing cycle following the notice period. If you do not agree to the new pricing, you may cancel before the change takes effect.

#### 4.7 Payment Failures

If a payment fails, we may suspend access to paid features. We will attempt to notify you and may retry the payment. If payment is not resolved within [14] days, your account may be downgraded to the Analyst (free) tier.

---

### 5. Acceptable Use

#### 5.1 Permitted Use

You may use the Service for your personal, non-commercial investment research, subject to these Terms and any plan-specific limitations (e.g., monthly analysis limits on the Analyst tier).

#### 5.2 Prohibited Conduct

You agree not to:

- **Scrape, crawl, or automated extraction** — Use bots, scrapers, spiders, or other automated tools to extract data from the Service, except through a documented API with valid API credentials on an Institutional plan
- **Redistribute or resell** — Republish, resell, sublicense, or commercially distribute scores, analysis outputs, data, or any other Service content to third parties
- **Circumvent restrictions** — Bypass plan limits, rate limits, authentication, or other access controls
- **Reverse engineer** — Decompile, reverse engineer, or attempt to extract the source code, algorithms, or scoring methodology of the Service
- **Impersonate or misrepresent** — Impersonate another person, create fake accounts, or misrepresent your affiliation
- **Interfere with the Service** — Introduce viruses, overload infrastructure, or interfere with the Service's availability or integrity
- **Violate law** — Use the Service for any purpose that violates applicable law, including securities laws, regulations, or rules
- **Fraudulent trading activity** — Use the Service to engage in market manipulation, insider trading, or any other prohibited trading practice
- **Share account access** — Share your login credentials or allow others to use your account
- **Misrepresent affiliation** — Claim or imply that your use of Margin Invest means you are endorsed by, affiliated with, or acting on behalf of Margin Invest

#### 5.3 Attribution

If you publicly reference or discuss scores or analysis from Margin Invest (for example, in a blog post or social media), you must clearly state that the information is from Margin Invest and is not investment advice.

---

### 6. Intellectual Property

#### 6.1 Our Intellectual Property

The Service — including its design, scoring methodology, algorithms, software, data compilations, visual design, logos, and trademarks — is owned by or licensed to Margin Invest and is protected by applicable intellectual property laws.

We grant you a limited, non-exclusive, non-transferable, revocable license to access and use the Service for your personal, non-commercial investment research during your active subscription, subject to these Terms.

#### 6.2 Scores and Analysis Output

Scores, conviction ratings, factor breakdowns, and other analysis outputs generated by the Service are licensed to you for personal use only. You may not republish, resell, or distribute them commercially without our prior written consent.

For clarity: the underlying financial data (SEC filings, market prices, etc.) is publicly available and is not claimed as our intellectual property. Our intellectual property lies in the methodology, algorithms, and presentation used to produce scores and analysis.

#### 6.3 Your Content

You retain ownership of content you provide to the Service (such as your profile avatar). By uploading content, you grant us a non-exclusive, worldwide, royalty-free license to use, store, process, and display that content solely as necessary to provide the Service.

#### 6.4 Feedback

If you provide suggestions, ideas, or feedback about the Service, we may use them without obligation or compensation to you.

---

### 7. Third-Party Services

#### 7.1 Data Providers

The Service uses third-party data providers (including SEC EDGAR, Finnhub, Polygon, FMP, yfinance, and FRED) for financial data. We do not guarantee the accuracy, completeness, or timeliness of third-party data.

#### 7.2 User-Provided API Keys

You may store your own API keys for third-party data providers. When you do:

- You are responsible for complying with that provider's terms of service
- Your keys are encrypted at rest and used solely to fetch data on your behalf
- We are not responsible for charges incurred with third-party providers through your keys
- You may revoke your keys at any time through account settings

#### 7.3 Payment Processing

Billing is handled by Stripe. Your use of Stripe is governed by Stripe's terms and privacy policy. We are not responsible for Stripe's availability, errors, or policies.

#### 7.4 OAuth Providers

If you authenticate through Google or GitHub, your use of those services is governed by their respective terms and privacy policies.

#### 7.5 Links

The Service may contain links to third-party websites. We do not control or endorse third-party content and are not responsible for it.

---

### 8. Data Provider API Keys (Institutional)

[INCLUDE WHEN INSTITUTIONAL API IS LAUNCHED.]

If you have an Institutional subscription that includes API access:

- API access is for your personal or internal business use only
- You may not redistribute, resell, or sublicense API responses
- We may impose rate limits and usage quotas, which will be documented in the API documentation
- API access may be suspended or revoked if you violate these Terms or exceed usage limits
- We may modify, deprecate, or discontinue API endpoints with reasonable notice
- API access is provided "as is" without uptime guarantees or SLAs

[DEFINE RATE LIMITS, QUOTAS, AND DOCUMENTATION URL WHEN API IS LAUNCHED.]

---

### 9. Availability and Modifications

#### 9.1 No Uptime Guarantee

The Service is provided on an "as available" basis. We do not guarantee any specific level of uptime, availability, or performance. We may experience outages, maintenance windows, or degraded performance.

#### 9.2 Modifications

We may modify, update, or discontinue any feature of the Service at any time. We will make reasonable efforts to notify users of material changes. If we discontinue a paid feature that is central to your subscription tier, you may cancel your subscription for a prorated refund of the remaining billing period.

---

### 10. Suspension and Termination

#### 10.1 By You

You may stop using the Service at any time. To cancel a paid subscription, use the Stripe Customer Portal in your account settings. [TO DELETE YOUR ACCOUNT ENTIRELY, CONTACT [EMAIL] — CONFIRM DELETION PROCESS.]

#### 10.2 By Us

We may suspend or terminate your account if we reasonably believe you have:

- Violated these Terms or any applicable law
- Engaged in fraudulent, abusive, or harmful conduct
- Failed to resolve a payment failure after notice
- Created risk or legal exposure for Margin Invest or other users

Where practicable, we will provide notice and an opportunity to cure before termination, except in cases of fraud, security threats, or legal obligation.

#### 10.3 Effect of Termination

Upon termination:

- Your right to use the Service ends immediately
- You remain liable for any fees incurred before termination
- We may retain your data as described in our Privacy Policy and as required by law
- Sections that by their nature should survive (Intellectual Property, Limitation of Liability, Indemnification, Governing Law, and Arbitration) survive termination

---

### 11. Limitation of Liability and No Warranties

**These provisions are described in full in our [Legal Disclaimers](/legal) page and are incorporated here by reference.** In summary:

- The Service is provided "as is" and "as available" without warranties
- We disclaim all implied warranties including merchantability, fitness, and accuracy
- We are not liable for indirect, incidental, special, consequential, or punitive damages
- We are not liable for investment losses, regardless of whether you relied on the Service
- Our total liability is capped at the greater of your fees in the preceding 12 months or $100
- Some jurisdictions limit these exclusions; in those cases, they apply to the fullest extent permitted

---

### 12. Indemnification

You agree to indemnify and hold harmless Margin Invest and its operators, officers, directors, employees, and affiliates from claims, damages, losses, and expenses (including reasonable attorneys' fees) arising from:

- Your use of the Service
- Your investment decisions
- Your violation of these Terms
- Your violation of any law or third-party right
- Your use of third-party API keys stored on the platform

---

### 13. Dispute Resolution

#### 13.1 Informal Resolution

Before filing a formal dispute, you agree to contact us at [CONTACT EMAIL] and attempt to resolve the matter informally for at least [30] days.

#### 13.2 Arbitration and Class Action Waiver [OPTIONAL — CONSULT ATTORNEY]

[CHECK STATE LAW BEFORE INCLUDING THIS SECTION.]

If informal resolution fails, any dispute shall be resolved through binding individual arbitration administered by [ARBITRATION BODY] under its applicable rules. You waive the right to a jury trial and the right to participate in any class, collective, or representative proceeding.

**Exceptions:** Small claims court and injunctive relief for intellectual property protection. You may opt out of arbitration by notifying [CONTACT EMAIL] within 30 days of creating your account.

#### 13.3 Governing Law and Venue

These Terms are governed by the laws of the State of [STATE], without regard to conflict-of-law principles. Litigation not subject to arbitration shall be brought exclusively in the state or federal courts of [COUNTY], [STATE].

---

### 14. General Provisions

#### 14.1 Entire Agreement

These Terms, together with the Legal Disclaimers and Privacy Policy, constitute the entire agreement between you and Margin Invest regarding your use of the Service.

#### 14.2 Severability

If any provision of these Terms is found unenforceable, the remaining provisions remain in effect. The unenforceable provision will be modified to the minimum extent necessary to make it enforceable.

#### 14.3 Waiver

Our failure to enforce any provision does not waive our right to enforce it later.

#### 14.4 Assignment

You may not assign or transfer your rights under these Terms without our consent. We may assign our rights without restriction.

#### 14.5 Force Majeure

We are not liable for failure to perform due to causes beyond our reasonable control, including natural disasters, pandemics, war, government actions, power failures, internet outages, or third-party service failures.

#### 14.6 Notices

We may send notices to the email address associated with your account. You are responsible for keeping your email current. Notices are deemed received when sent.

---

### 15. Changes to These Terms

We may update these Terms from time to time. When we do, we will revise the "Last Updated" date. [OPTIONAL: We will notify registered users of material changes via email or in-platform notification at least [30] days before they take effect.] Your continued use of the Service after changes constitutes acceptance.

If you do not agree with updated Terms, you must stop using the Service and cancel any paid subscription before the changes take effect.

---

### 16. Contact

Questions about these Terms? Contact us:

[LEGAL ENTITY NAME]
[CONTACT EMAIL]
[MAILING ADDRESS]

---
---

# VERSION 2: CONCISE

Same substantive coverage, tighter prose. Suitable as the published page if you prefer brevity.

---

## Terms of Service

**Last Updated: [DATE]**

These Terms govern your use of Margin Invest, operated by [LEGAL ENTITY NAME]. By using the Service, you agree to these Terms, our [Legal Disclaimers](/legal), and our [Privacy Policy](/privacy).

### Eligibility

You must be at least [18], a US resident [CONFIRM], and legally capable of agreeing to these Terms.

### Your Account

One account per person. Keep your credentials secure. You're responsible for all activity on your account. MFA is required for password-based accounts (72-hour grace period for setup).

### What the Service Is

Margin Invest is a quantitative stock analysis tool providing automated scoring, factor analysis, and backtested data for US equities. It is not financial advice, not a broker, not a custodian, and does not execute trades. See our [Legal Disclaimers](/legal) for full details.

### Plans and Billing

| | Analyst (Free) | Portfolio ($29/mo) | Institutional ($79/mo) |
|-|---|---|---|
| Analyses | 3/month | Unlimited | Unlimited |
| Detail | Composite only | Full 6-factor | Full 6-factor |
| History | None | 90 days | Unlimited |
| Watchlist | 5 | 25 | Unlimited |
| Alerts | No | Yes | Yes |
| Correlation / Sector | No | No | Yes |

Paid plans are billed monthly through Stripe. Cancel anytime via the Stripe portal in your settings — you keep access through the end of the billing period.

[REFUND POLICY: CHOOSE AND INSERT — SEE FULL VERSION FOR OPTIONS.]

We may change pricing with [30] days' notice.

### Acceptable Use

**Do:**
- Use the Service for personal investment research within your plan limits

**Don't:**
- Scrape, crawl, or use bots to extract data
- Redistribute, resell, or sublicense scores or analysis
- Circumvent plan limits or access controls
- Reverse engineer the scoring methodology
- Share your account or create multiple accounts
- Use the Service for market manipulation or any illegal purpose
- Imply endorsement by or affiliation with Margin Invest

### Intellectual Property

The Service, methodology, algorithms, and presentation are our property. You get a limited personal-use license during your subscription. Scores and outputs are licensed to you for personal use — not for commercial redistribution.

You own your content (like your avatar). By uploading it, you license us to store and display it to provide the Service.

### Third-Party Services

We use Stripe (payments), Google/GitHub (OAuth), and financial data providers (EDGAR, Finnhub, Polygon, FMP, yfinance, FRED). We don't guarantee their availability or accuracy. If you store your own API keys, you're responsible for complying with those providers' terms.

### Availability

No uptime guarantee. We may modify or discontinue features. If we remove a core paid feature, you may cancel for a prorated refund.

### Suspension and Termination

You can cancel anytime. We may suspend or terminate accounts for Terms violations, fraud, payment failure, or legal reasons. We'll try to give notice when possible.

### Liability and Warranties

The Service is "as is" without warranties. We're not liable for investment losses. Total liability capped at the greater of your last 12 months of fees or $100. Full details in our [Legal Disclaimers](/legal).

### Indemnification

You hold us harmless from claims arising from your use of the Service, your investment decisions, or your violations of these Terms.

### Disputes

Try to resolve informally first ([CONTACT EMAIL], 30 days). [OPTIONAL: Then binding individual arbitration — CHECK STATE LAW.] Governed by [STATE] law. Venue in [COUNTY], [STATE].

### General

These Terms are the entire agreement. Unenforceable provisions are severed. We can assign; you can't without consent. Force majeure excuses non-performance.

### Changes

We update Terms and revise the date. Continued use means acceptance. If you disagree, stop using the Service and cancel.

### Contact

[LEGAL ENTITY NAME] — [CONTACT EMAIL]

---
---

# Open Questions and Assumptions

| # | Item | Status | Impact on ToS |
|---|------|--------|---------------|
| 1 | **Legal entity name** | Placeholder | Same entity across all legal docs |
| 2 | **Contact email** | Placeholder | Appears in multiple sections |
| 3 | **Age minimum** | Assumed 18+ | Section 1 eligibility |
| 4 | **Non-US users** | Unknown | Section 1 — if permitted, add international provisions |
| 5 | **State exclusions** | None assumed | Section 1 |
| 6 | **Refund policy** | Two options provided | Choose Option A (no refunds) or Option B (30-day money-back) |
| 7 | **Free trial** | Unknown | Section 4.3 — confirm if trials are offered |
| 8 | **Account deletion** | Not implemented | Section 10 — must define process before launch |
| 9 | **Institutional API** | Not yet exposed | Section 8 — placeholder; finalize when API launches |
| 10 | **API rate limits** | Not implemented | Section 8 — define before API launch |
| 11 | **Governing state** | Placeholder | Section 13 |
| 12 | **Arbitration** | Optional, flagged | Section 13 — attorney must review for state enforceability |
| 13 | **Notification period for changes** | 30 days suggested | Section 15 — confirm commitment |
| 14 | **Data retention after cancellation** | Unknown | Section 10 — how long is account data kept after downgrade/deletion? |
| 15 | **Commercial use** | Prohibited by default | Section 5 says "personal, non-commercial" — confirm if business/team use should be permitted on Institutional tier |

### Cross-References

These three documents should be consistent and link to each other:

| Document | Links To |
|----------|----------|
| Terms of Service | Legal Disclaimers, Privacy Policy |
| Legal Disclaimers | Terms of Service, Privacy Policy |
| Privacy Policy | Terms of Service, Legal Disclaimers |

### Recommended Next Steps

| Step | Description |
|------|-------------|
| **Choose refund policy** | Pick Option A or B (or another approach) |
| **Implement account deletion** | Required for CCPA and good practice; referenced in ToS and Privacy Policy |
| **Define data retention schedule** | What happens to scores, API keys, avatars after account deletion? |
| **Attorney review** | Securities attorney for overall compliance; consumer law attorney for arbitration enforceability |
| **Align all three docs** | Ensure Legal Disclaimers, Privacy Policy, and ToS use consistent definitions and cross-reference correctly |
| **Add suspension fields to DB** | If you want to enforce ToS, you need `is_suspended` / `suspension_reason` on the User model |
