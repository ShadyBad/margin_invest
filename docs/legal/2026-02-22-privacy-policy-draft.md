# Margin Invest — Privacy Policy Draft

**Prepared:** 2026-02-22
**Status:** DRAFT — Not legal advice. Have an attorney review before publishing.

---

## Codebase-Verified Facts Used in This Draft

| Category | What We Found |
|----------|---------------|
| User profile data | Email (required), name (optional), avatar (optional) |
| Authentication | Email/password (Argon2id) + OAuth (Google, GitHub) |
| MFA | TOTP secrets + WebAuthn credentials (Fernet-encrypted) + recovery codes (hashed) |
| Sessions | JWT in HttpOnly cookies, refreshed every 60s |
| Billing | Stripe — only Stripe IDs and subscription state stored locally; Stripe handles all payment method data |
| User API keys | Fernet-encrypted per-provider keys (Polygon, Finnhub, FMP, etc.) with audit log (event type, IP, timestamp) |
| Avatar storage | Cloudflare R2 (processed locally with Pillow, stored as 256x256 WebP) |
| Email | Resend — password reset emails only |
| Data providers | SEC EDGAR, Finnhub, Polygon, FMP, yfinance, FRED — receive ticker symbols and date ranges only, no PII |
| Analytics | None detected in codebase |
| IP logging | API key event audit log only |
| Data retention | No explicit purge policies; MFA data deleted on disable; API keys soft-revoked |

---

# VERSION 1: FULL / DETAILED

---

## Privacy Policy

**Last Updated: [DATE]**

This Privacy Policy describes how [LEGAL ENTITY NAME] ("Margin Invest," "we," "us," or "our") collects, uses, stores, and shares information when you use the Margin Invest platform, website, and related services (collectively, the "Service").

By using the Service, you agree to the collection and use of information as described in this policy. If you do not agree, do not use the Service.

---

### 1. Information We Collect

#### 1.1 Information You Provide

**Account information.** When you create an account, we collect your email address. You may optionally provide your name and a profile avatar image.

**Password.** If you register with email and password (rather than OAuth), we store a cryptographic hash of your password using the Argon2id algorithm. We never store your plaintext password.

**Multi-factor authentication (MFA) data.** If you enable MFA, we store encrypted TOTP secrets, WebAuthn/passkey credentials (credential ID, public key, sign count), and hashed recovery codes. TOTP secrets are encrypted at rest using Fernet symmetric encryption.

**Data provider API keys.** You may optionally provide your own API keys for third-party financial data providers (such as Polygon, Finnhub, or FMP). These keys are encrypted at rest using Fernet symmetric encryption and are used solely to fetch financial data on your behalf.

**Avatar image.** If you upload a profile photo, we process it locally (center-crop, resize to 256x256, convert to WebP format) and store the result on Cloudflare R2 object storage.

**Communications.** If you contact us, we may retain the content of your message and your contact information.

#### 1.2 Information Collected Automatically

**Session tokens.** We use JSON Web Tokens (JWTs) stored in HttpOnly cookies to maintain your authenticated session. These tokens contain your user ID, authentication method, MFA status, and session metadata. They do not contain your password, financial data, or API keys.

**Security event data.** We log failed login attempts (count and timestamp) and account lockout events. When you create, rotate, revoke, or access a stored API key, we log the event type, timestamp, and your IP address for security auditing purposes.

**We do not currently use third-party analytics, tracking scripts, or advertising pixels.** [IF THIS CHANGES, UPDATE THIS SECTION AND NOTIFY USERS.]

#### 1.3 Information from Third Parties

**OAuth providers.** If you sign in with Google or GitHub, we receive your email address, display name, and profile image URL from the OAuth provider. We do not receive or store your OAuth provider password.

**Stripe.** Our payment processor, Stripe, provides us with your Stripe customer ID, subscription ID, subscription plan, subscription status, and current billing period end date. Stripe handles all payment method data (credit cards, bank accounts) directly. We do not receive, process, or store your payment card numbers or bank account details.

---

### 2. How We Use Your Information

We use the information we collect to:

- **Provide the Service** — Authenticate you, maintain your session, display your profile, and deliver scoring and analysis features
- **Process payments** — Manage your subscription through Stripe
- **Fetch financial data** — Use your stored API keys (if provided) to retrieve market data from third-party providers on your behalf
- **Send transactional emails** — Deliver password reset emails and, if applicable, account security notifications
- **Maintain security** — Detect and prevent unauthorized access, enforce account lockout policies, and audit API key usage
- **Improve the Service** — Diagnose technical issues and maintain platform reliability

We do not use your information to build advertising profiles, sell data, or target you with third-party ads.

---

### 3. How We Share Your Information

We share your information only in the following circumstances:

#### 3.1 Service Providers

We use the following third-party service providers that may process data on our behalf:

| Provider | Purpose | Data Shared |
|----------|---------|-------------|
| **Stripe** | Payment processing | Email, subscription state; Stripe handles payment methods directly |
| **Google / GitHub** | OAuth authentication | Authentication tokens (they already have your data; we receive profile info from them) |
| **Cloudflare R2** | Avatar image storage | Your processed avatar image (256x256 WebP) |
| **Resend** | Transactional email delivery | Your email address and email content (password reset links) |

#### 3.2 Financial Data Providers

When you use the scoring and analysis features, we make API calls to third-party financial data providers (SEC EDGAR, Finnhub, Polygon, FMP, yfinance, FRED). **These calls include only ticker symbols and date ranges. We do not transmit your name, email, or any other personal information to these providers.**

If you provide your own API keys for these providers, your key is transmitted to the respective provider when making data requests on your behalf. Your relationship with that provider is governed by their terms.

#### 3.3 Legal Requirements

We may disclose your information if required by law, regulation, legal process, or governmental request, or if we believe disclosure is necessary to protect the rights, property, or safety of Margin Invest, our users, or the public.

#### 3.4 Business Transfers

If Margin Invest is involved in a merger, acquisition, or sale of assets, your information may be transferred as part of that transaction. We will notify you of any such change.

#### 3.5 No Sale of Personal Information

We do not sell, rent, or trade your personal information to third parties for their marketing purposes.

---

### 4. Data Storage and Security

**Storage locations.** Your account data is stored in a PostgreSQL database. Avatar images are stored on Cloudflare R2. Session tokens are stored client-side in HttpOnly cookies.

**Encryption at rest.** Sensitive data is encrypted using industry-standard methods:
- Passwords: Argon2id hashing (OWASP-recommended parameters)
- TOTP secrets: Fernet symmetric encryption
- User API keys: Fernet symmetric encryption
- Recovery codes: Cryptographic hashing

**Encryption in transit.** All data transmitted between your browser and our servers is encrypted using TLS (HTTPS).

**Access controls.** Database access is restricted to application services. Encryption keys are stored as environment variables, separate from application data.

**Security measures.** We implement account lockout after failed login attempts, enforce strong password requirements (minimum 12 characters with complexity rules), and require MFA for credential-based accounts.

**No security system is perfect.** While we use commercially reasonable measures to protect your information, we cannot guarantee absolute security. If you become aware of a security incident, please contact us immediately.

---

### 5. Data Retention

We retain your information for as long as your account is active or as needed to provide the Service.

**When you delete or disable features:**
- Disabling MFA deletes your TOTP secrets, WebAuthn credentials, and recovery codes
- Revoking an API key marks it as inactive (soft delete with timestamp)
- Deleting your avatar removes it from Cloudflare R2

**Account deletion.** [DESCRIBE ACCOUNT DELETION PROCESS AND TIMELINE. CONFIRM WHETHER FULL DELETION IS SUPPORTED AND WHAT DATA IS RETAINED AFTER DELETION (E.G., STRIPE RECORDS, ANONYMIZED ANALYTICS).]

**Legal obligations.** We may retain certain information as required by law or for legitimate business purposes (e.g., billing records, fraud prevention).

---

### 6. Your Rights and Choices

#### 6.1 Account Controls

You can:
- Update your email, name, and avatar through your account settings
- Enable or disable MFA
- Add, revoke, or delete stored API keys
- Link or unlink OAuth providers (Google, GitHub)
- [DELETE YOUR ACCOUNT — CONFIRM PROCESS]

#### 6.2 California Residents (CCPA/CPRA)

[INCLUDE IF CALIFORNIA USERS ARE SERVED.]

If you are a California resident, you may have additional rights under the California Consumer Privacy Act (CCPA) and the California Privacy Rights Act (CPRA), including the right to:
- **Know** what personal information we collect, use, and disclose
- **Delete** your personal information (subject to certain exceptions)
- **Correct** inaccurate personal information
- **Opt out** of the "sale" or "sharing" of personal information — we do not sell or share your personal information as defined under CCPA/CPRA
- **Non-discrimination** for exercising your privacy rights

To exercise these rights, contact us at [CONTACT EMAIL]. We will verify your identity before processing your request.

**Categories of personal information collected** (per CCPA categories):
- Identifiers: email address, name, IP address (limited to API key audit logs)
- Commercial information: subscription plan and payment history (via Stripe)
- Internet activity: session tokens, security event logs
- Geolocation: not collected

We do not collect sensitive personal information as defined under CPRA.

#### 6.3 Other State Privacy Laws

[REVIEW WHETHER ADDITIONAL STATE DISCLOSURES ARE NEEDED BASED ON USER BASE — E.G., VIRGINIA (VCDPA), COLORADO (CPA), CONNECTICUT (CTDPA), UTAH (UCPA), TEXAS (TDPSA), OREGON (OCPA). MANY FOLLOW SIMILAR FRAMEWORKS TO CCPA.]

---

### 7. Cookies and Similar Technologies

**Session cookies.** We use HttpOnly cookies to store your JWT session token. This is essential for authentication and cannot be disabled while using the Service.

**No tracking cookies.** We do not currently use analytics cookies, advertising cookies, or third-party tracking pixels.

**Third-party cookies.** Our payment processor (Stripe) and OAuth providers (Google, GitHub) may set their own cookies during checkout or authentication flows. These are governed by their respective privacy policies.

[IF YOU ADD ANALYTICS OR TRACKING IN THE FUTURE, UPDATE THIS SECTION AND IMPLEMENT A COOKIE CONSENT MECHANISM.]

---

### 8. Children's Privacy

Margin Invest is not directed to children under [18 — CONFIRM AGE MINIMUM]. We do not knowingly collect personal information from children. If you believe a child has provided us with personal information, please contact us and we will delete it.

---

### 9. International Users

[INCLUDE IF NON-US USERS MAY ACCESS THE SERVICE.]

Margin Invest is operated from the United States and analyzes US equities. If you access the Service from outside the United States, your information will be transferred to, stored in, and processed in the United States.

[IF EU/UK USERS ARE SERVED: ADDITIONAL GDPR DISCLOSURES MAY BE REQUIRED, INCLUDING LEGAL BASIS FOR PROCESSING, DATA PROTECTION OFFICER, RIGHT TO LODGE COMPLAINT WITH SUPERVISORY AUTHORITY, AND CROSS-BORDER TRANSFER MECHANISMS.]

---

### 10. Third-Party Links

The Service may contain links to third-party websites or services. We are not responsible for their privacy practices. We encourage you to read their privacy policies before providing them with any information.

---

### 11. Changes to This Policy

We may update this Privacy Policy from time to time. When we do, we will revise the "Last Updated" date at the top. [OPTIONAL: We will notify registered users of material changes via email or in-platform notification at least [14] days before the changes take effect.] Your continued use of the Service after changes constitutes acceptance.

---

### 12. Contact Us

If you have questions about this Privacy Policy or want to exercise your privacy rights, contact us at:

[LEGAL ENTITY NAME]
[CONTACT EMAIL]
[MAILING ADDRESS]

---
---

# VERSION 2: CONCISE

Same substantive disclosures, tighter prose. Suitable as the published page if you prefer brevity.

---

## Privacy Policy

**Last Updated: [DATE]**

This policy describes how [LEGAL ENTITY NAME] ("Margin Invest") handles your information.

### What We Collect

**You provide:** Email address (required), name and avatar (optional), password (stored as Argon2id hash), MFA credentials (encrypted), and optionally your own API keys for data providers (encrypted).

**Automatically:** JWT session tokens (HttpOnly cookies), failed login counts, account lockout timestamps, and API key usage audit logs (event type, IP address, timestamp).

**From third parties:** Profile info from Google/GitHub if you use OAuth. Subscription state from Stripe. We never receive your payment card details — Stripe handles those directly.

**We do not use analytics, tracking scripts, or ad pixels.**

### How We Use It

To authenticate you, deliver scoring features, process payments via Stripe, send password reset emails via Resend, enforce security policies, and maintain the platform.

We don't build ad profiles, sell data, or target you with third-party advertising.

### Who We Share With

| Provider | Why | What |
|----------|-----|------|
| Stripe | Payments | Email, subscription state |
| Google / GitHub | OAuth login | Auth tokens |
| Cloudflare R2 | Avatar storage | Your 256x256 avatar image |
| Resend | Email delivery | Your email + password reset links |

Financial data providers (SEC EDGAR, Finnhub, Polygon, FMP, yfinance, FRED) receive only ticker symbols and date ranges — never your personal info.

We don't sell your information. We may disclose it if required by law.

### Security

- Passwords: Argon2id hashing
- MFA secrets and API keys: Fernet encryption at rest
- All traffic: TLS in transit
- Account lockout after failed attempts; MFA enforced for password-based accounts

No system is perfectly secure. Contact us immediately if you suspect unauthorized access.

### Data Retention

Data is kept while your account is active. Disabling MFA deletes MFA credentials. Revoking an API key marks it inactive. Deleting your avatar removes it from storage.

[ACCOUNT DELETION: DESCRIBE PROCESS AND WHAT IS RETAINED.]

### Cookies

We use one essential HttpOnly session cookie (JWT). No analytics or advertising cookies. Stripe and OAuth providers may set their own cookies during their flows.

### Your Rights

You can update your profile, manage MFA, revoke API keys, and manage OAuth links in account settings.

[CALIFORNIA RESIDENTS: YOU HAVE RIGHTS UNDER CCPA/CPRA INCLUDING ACCESS, DELETION, AND CORRECTION. WE DO NOT SELL YOUR INFORMATION. CONTACT [EMAIL] TO EXERCISE RIGHTS.]

[ADDITIONAL STATE PRIVACY LAWS: REVIEW BASED ON USER BASE.]

### Children

Margin Invest is not for users under [18]. We don't knowingly collect children's data.

### International

The Service is US-based. Your data is stored and processed in the United States. [ADD GDPR DISCLOSURES IF EU/UK USERS ARE SERVED.]

### Changes

We'll update the "Last Updated" date when this policy changes. Continued use means acceptance.

### Contact

[LEGAL ENTITY NAME] — [CONTACT EMAIL]

---
---

# Open Questions and Assumptions

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Legal entity name** | Placeholder | Same entity as legal disclaimers page |
| 2 | **Contact email** | Placeholder | Recommend a dedicated privacy@ address |
| 3 | **Age minimum** | Assumed 18+ | Confirm; some investment platforms use 21+ |
| 4 | **Account deletion** | Unknown | Is there a self-serve deletion flow? What data survives deletion (Stripe records, anonymized data, backups)? This must be documented. |
| 5 | **Data retention periods** | No explicit policy | Consider adding defined retention periods (e.g., audit logs kept 2 years, account data deleted 30 days after deletion request) |
| 6 | **California/CCPA** | Assumed yes | If California residents use the Service, CCPA disclosures are required. Include unless you specifically block CA users. |
| 7 | **Other state privacy laws** | Placeholder | Virginia, Colorado, Connecticut, Texas, Oregon, and others have enacted privacy laws. Review based on user base. |
| 8 | **Non-US users** | Unknown | If EU/UK users access the Service, GDPR compliance may be required (legal basis, DPO, transfer mechanisms). |
| 9 | **Stripe data handling** | Assumed standard | Confirm you don't store any payment method info locally. Verified in code — looks clean. |
| 10 | **Resend data retention** | Unknown | Resend may retain email metadata. Review their DPA. |
| 11 | **Cloudflare R2 data location** | Unknown | Confirm R2 bucket region for data residency disclosure. |
| 12 | **Future analytics** | None now | If you add analytics later, update Cookies section and implement consent mechanism. |
| 13 | **Cookie consent banner** | Not needed currently | No tracking cookies detected. If you add them, a consent mechanism is likely required. |
| 14 | **Do Not Track** | Not addressed | Consider adding a statement about browser DNT signals. |
| 15 | **Data breach notification** | Not addressed | Some states require breach notification within specific timeframes. Consider adding a brief disclosure. |

### Recommended Additional Steps

| Step | Description |
|------|-------------|
| **Attorney review** | Have a privacy attorney review, especially CCPA/CPRA compliance and whether other state laws apply. |
| **Data Processing Agreements** | Ensure DPAs are in place with Stripe, Resend, and Cloudflare. |
| **Account deletion flow** | Implement and document a self-serve account deletion process. Required under CCPA and good practice. |
| **Retention schedule** | Define explicit data retention periods for each data category. |
| **Privacy policy link** | Add a link to this policy in the site footer, registration flow, and cookie banner (if applicable). |
| **Cross-reference** | Link to this policy from the Legal Disclaimers page, and vice versa. |
