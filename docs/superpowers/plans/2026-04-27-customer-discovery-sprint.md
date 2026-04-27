# Customer Discovery Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the Margin Invest customer discovery sprint to produce a binding go/no-go decision on whether a Spectrum Mark customer will pay $49+/month, based on charge-gate (Day 21) and retention-gate (Day 51) evidence.

**Architecture:** Two-gate operational sprint: Pre-flight feasibility check → 14-day recruitment → 10-day interview window (overlapping recruitment) → 5-day paid preorder test → charge-gate decision (Day 21) → 30-day retention monitoring → retention-gate decision (Day 51) → exploratory Phase 5 (Days 21-28) → committed Phase 5 (Day 51+ if retention gate passes). Each phase is human-executed via copy-paste prompts to fresh Claude Code sessions; this plan provides task-level granularity within each phase.

**Tech Stack:** Claude Code + Superpowers skills, Stripe Checkout, Reddit/Twitter/Substack/Discord (recruitment channels), Zoom (interviews), git-versioned markdown artifacts under `docs/customer-discovery/`.

**Source documents:**
- Spec: [docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-design.md](../specs/2026-04-27-customer-discovery-pressure-test-design.md)
- Operational guide with verbatim prompts: [docs/customer-discovery/action-plan.md](../../customer-discovery/action-plan.md)

**Convention:** Where this plan says "use the action-plan prompt for X," paste the corresponding `===PROMPT===` block from action-plan.md into a fresh Claude Code session. Plan tasks track *what action to take* and *what gate to verify*; action-plan.md holds the verbatim prompt text.

---

## Phase 0 — Pre-execution gates

Phase 0 of the action plan is already locked. These tasks confirm you're ready to start Pre-flight.

### Task 0.1: Read source documents end-to-end

**Files:**
- Read: `docs/superpowers/specs/2026-04-27-customer-discovery-pressure-test-design.md`
- Read: `docs/customer-discovery/action-plan.md`
- Read: `docs/customer-discovery/icp.md`, `interview-guide.md`, `rubric.md`, `preorder-test.md`

- [ ] **Step 1: Read the spec end-to-end**

Read the entire 281-line pressure-test spec. Focus on the Top-5 must-do amendments and the Open Questions list at the end.

- [ ] **Step 2: Read the action plan v2 end-to-end**

Read the entire 600-line operational guide. Pay attention to the two-gate structure, the time budget, and the new Pre-flight phase.

- [ ] **Step 3: Re-read the four locked Phase 0 artifacts**

icp.md (8.9 KB), interview-guide.md (13 KB), rubric.md (9.6 KB), preorder-test.md (9.9 KB). These are scope-locked and must NOT be rewritten — only added to per Pre-flight tasks.

- [ ] **Step 4: Verify decision criteria are internalized**

Without re-reading: state aloud or write down:
- The charge-gate threshold (≥4/10 paid)
- The retention-gate threshold (≥80% of charge-gate cohort)
- The kill threshold (≤1/10 paid OR ≥60% disinterest)
- The doorstop on founder hours (≥30 hours over 21 days, or rescope to 8/5)

If you can't recall any of these, re-read the spec executive summary.

### Task 0.2: Decide sprint scope tier

**Decision:** full-scope (15 interviews / 10 paid asks) OR half-scope (8 interviews / 5 paid asks).

- [ ] **Step 1: Audit your calendar for the next 21 days**

Open your calendar. Count free 45-minute slots over the next 21 weekday-evenings + weekends. The target is ≥18 slots if doing full scope, ≥10 if doing half scope.

- [ ] **Step 2: Estimate available founder-hours**

Be honest. Add up: sourcing time, DM time, call time, transcript time, response chasing, decision writing.
- Full scope minimum: ≥30 hours over 21 days
- Half scope minimum: ≥18 hours over 21 days

- [ ] **Step 3: Commit to a tier in writing**

Update `docs/customer-discovery/action-plan.md` with a leading note: "Scope tier: FULL" or "Scope tier: HALF" and the date. If HALF, mentally substitute (8 interviews, 5 paid asks, 60+ pipeline) wherever this plan says (15, 10, 100+).

- [ ] **Step 4: Commit the scope decision**

```bash
git add docs/customer-discovery/action-plan.md
git commit -m "docs(discovery): commit scope tier for sprint execution"
```

---

## Phase Pre-flight — Feasibility & Compliance Gates

**Goal:** all six artifacts and two confirmations before Phase 1 launches.

### Task PF.1: Write beta-deliverable.md

**Files:**
- Create: `docs/customer-discovery/beta-deliverable.md`

- [ ] **Step 1: Audit current build state**

Run a quick survey of `web/` and `api/` to inventory what's deployable today vs. what would need work to ship to a paying customer. Check:
- Auth flow (sign-up, sign-in, password reset)
- Asset detail pages (which tickers covered)
- Score pages (composite, factor breakdown)
- Smart Money page
- Backtesting tool
- Risk diffing UI

- [ ] **Step 2: Draft the Day-35 deliverable spec**

Create `docs/customer-discovery/beta-deliverable.md` with these sections:

```markdown
# Margin Invest Founder Beta — Day-35 Deliverable

**Customer charge date:** Day 21 (sprint date + 21)
**Beta access date:** Day 35 (charge + 14)
**Subscription:** $49/month, cancel anytime via self-serve portal

## Included on Day 35

- Authentication: email + password sign-up/sign-in, password reset
- Asset detail pages for {N} tickers: {list specific tickers or universe}
- Composite scores with factor breakdown
- {Other features that exist today}

## Not included on Day 35 (roadmap)

- {Features deliberately excluded}
- {Features that exist but aren't customer-ready}

## Known limitations on Day 35

- {Any rough edges, performance constraints, partial features}

## Cancellation policy

Self-serve via Stripe customer portal. No questions asked.
```

- [ ] **Step 3: Commit beta-deliverable.md**

```bash
git add docs/customer-discovery/beta-deliverable.md
git commit -m "docs(discovery): add Day-35 beta deliverable scope"
```

### Task PF.2: Write recruitment-channel-rules.md

**Files:**
- Create: `docs/customer-discovery/recruitment-channel-rules.md`

- [ ] **Step 1: Read ToS for each recruitment channel**

For each of: r/SecurityAnalysis, r/investing, r/SecurityAnalysis equivalents, Twitter/X, Substack comments (Bearcave / Hindenburg / Kerrisdale), Discord servers (RoaringKitty, SuperInvestor, etc.):
- Read the sub wiki / ToS / community guidelines
- Note specific prohibitions on solicitation, paid promotion, spam DMs

- [ ] **Step 2: Document findings per channel**

Create `docs/customer-discovery/recruitment-channel-rules.md`:

```markdown
# Recruitment Channel Compliance Rules

## Reddit (r/SecurityAnalysis, r/investing, r/stocks)

- ToS: {link}
- Solicitation rules: {what's allowed / forbidden}
- Recommended approach: comment on prospect's posts first, build rapport, then DM after they reply
- Gift offer: {OK / forbidden — drop $50 if forbidden}
- Account history requirement: {>X karma, >Y days old}

## Twitter/X

- Solicitation rules: {summary}
- Recommended approach: reply to relevant posts, follow, then DM after mutual follow
- Anti-spam triggers: stagger DMs to ≤10/day per account, vary message structure
- Account history requirement: established posting history, not fresh account

## Substack comments (Bearcave / Hindenburg / Kerrisdale)

- Recommended approach: identify thoughtful commenters with finance-research signal
- Outreach: profile click → email if listed, otherwise nothing

## Discord (paid investing servers)

- Per-server rules: {each server's specific guidelines}
- Recommended approach: only servers where solicitation is explicitly allowed by mods

## Channel-by-channel gift policy

| Channel | $50 gift offer | Rationale |
|---|---|---|
| Reddit | {Yes/No} | {sub rules} |
| Twitter | Yes (lower-volume DMs only) | no explicit prohibition |
| Substack | Yes (email only) | private email = no community rules |
| Discord | Per server | varies |
```

- [ ] **Step 3: Commit recruitment-channel-rules.md**

```bash
git add docs/customer-discovery/recruitment-channel-rules.md
git commit -m "docs(discovery): add per-channel recruitment compliance rules"
```

### Task PF.3: Update interview-guide.md with consent, anonymization, gift rules

**Files:**
- Modify: `docs/customer-discovery/interview-guide.md`

⚠️ Phase 0 artifacts are scope-locked. This task **adds** sections to interview-guide.md without rewriting existing language.

- [ ] **Step 1: Read interview-guide.md to identify the opening section**

Find the section that contains the opening script (the part the interviewer says before asking the 5 questions).

- [ ] **Step 2: Add verbal consent script to opening**

Insert the following immediately AFTER any existing opening niceties and BEFORE the disqualifier check:

```markdown
### Consent script (added 2026-04-27)

Before asking any questions or running the disqualifier check, say verbatim:

> "Quick housekeeping before we start: I take notes that I store in a private code repository so I can review patterns later. I'll use a first name only and won't store your handle or specific holdings — is that OK?"

Wait for verbal yes. If the prospect declines: thank them, end the call politely, do NOT run the disqualifier check or 5 questions. Mark in pipeline.csv as "consent declined." NO gift paid.
```

- [ ] **Step 3: Add anonymization rules section**

Insert a new section near the top of interview-guide.md:

```markdown
## Anonymization rules (apply at capture time, not later)

When writing the transcript:
- Use first name only in filename and content
- Tickers: replace with $TICKER_A, $TICKER_B, $TICKER_C... (assigned in order of mention)
- Dollar amounts: bucket as ($1-5K), ($5-20K), ($20-100K), ($100K+)
- AUM: bucket the same way
- Brokerage names: keep generic ("major retail brokerage", "specialty broker")

Real handle stays in pipeline.csv only. Real ticker/dollar values stay in your head only.
```

- [ ] **Step 4: Add gift payout rule section**

Insert a new section near the closing-ask section:

```markdown
## $50 gift payout rule (added 2026-04-27)

Gift is paid AFTER the call ends, only if one of:

1. **Qualified-and-completed call**: disqualifier check passed, ≥25 min, preorder ask delivered if eligible.
2. **Disqualified-but-probed call**: disqualifier check failed, but the 5-min probe (tools used / wishes for existing tools) was completed and captured in disqualified-log.md.

NO gift paid for: consent declined, ghosted, ended <25 min, disqualified-and-no-probe.

State this rule in the recruitment DM AND in the interview opening so the prospect knows the conditions.
```

- [ ] **Step 5: Add disqualified-prospect probe section**

Insert a new section after the disqualifier check section:

```markdown
## Disqualified-prospect 5-min probe (added 2026-04-27)

If the disqualifier check fails (options trader / indexer / robo user / no cost basis on top 3):

1. Don't end the call yet. Pivot:
   > "Got it — sounds like our usual conversation isn't quite aimed at how you invest. If you have a few more minutes, I'd love a quick read on the tools you DO use and what you wish existed."

2. Run a 5-min probe:
   - "What tools do you currently use to manage / research investments?"
   - "What's a workflow that frustrates you?"
   - "What would you pay for if it existed?"

3. Capture answers in `docs/customer-discovery/disqualified-log.md`.

4. Pay the $50 gift (kept-promise rule).

This data feeds Phase 4 NO-GO pivot logic. Without it, we have no signal on alternative ICPs.
```

- [ ] **Step 6: Commit interview-guide.md amendments**

```bash
git add docs/customer-discovery/interview-guide.md
git commit -m "docs(discovery): add consent, anonymization, gift, and probe rules to interview guide"
```

### Task PF.4: Scaffold disqualified-log.md

**Files:**
- Create: `docs/customer-discovery/disqualified-log.md`

- [ ] **Step 1: Create the file with column headers**

```markdown
# Disqualified Prospect Probe Log

Captures 5-min probe data from prospects who failed the disqualifier check. Source data for Phase 4 NO-GO pivot logic.

| date | source | first_name | why_disqualified | tools_used | wishes_for_existing_tools | gift_paid |
|------|--------|------------|------------------|------------|---------------------------|-----------|
| | | | | | | |
```

- [ ] **Step 2: Commit the scaffold**

```bash
git add docs/customer-discovery/disqualified-log.md
git commit -m "docs(discovery): scaffold disqualified-prospect probe log"
```

### Task PF.5: Pre-block 18 calendar slots

**Files:**
- (none — calendar work)

- [ ] **Step 1: Open your calendar**

Use whatever calendar you'll actually run interviews in. Block slots before you start recruiting.

- [ ] **Step 2: Create 18 holds (45 min each)**

For full scope. Half scope: 10 holds.

Distribute across the 21-day sprint window. Rough allocation:
- Days 4-7: 4 slots (early adopters who reply fast)
- Days 8-14: 8 slots (steady recruiting)
- Days 15-21: 6 slots (stragglers + buffer)

Title each hold "INTERVIEW SLOT (placeholder)". Color-code if useful.

- [ ] **Step 3: Verify slots vs. existing commitments**

For each blocked slot, confirm:
- No conflict with engineering work (`/flow:dev` calendar holds)
- Quiet location available (no interruptions during call)
- Computer/headset working

- [ ] **Step 4: Document the slots**

If you can't block 18 (or 10 for half scope): output INFEASIBLE in the action-plan.md notes and rescope downward. Document the rescope decision.

### Task PF.6: Confirm founder-hour budget

**Files:**
- (none — internal commitment)

- [ ] **Step 1: List the hours you'll block**

Be specific. For each weekday in the sprint, identify:
- Hours for sourcing (recommend mornings or evenings)
- Hours for DMs (recommend during sourcing window)
- Hours for transcript work (recommend post-call)

- [ ] **Step 2: Sum the total**

Full scope minimum: 30+ hours over 21 days. Realistic estimate: 42 hours.
Half scope minimum: 18 hours over 21 days.

- [ ] **Step 3: If <minimum, rescope**

If you can't realistically commit the minimum hours: rescope sprint to half (or quarter) before starting Phase 1. Don't power through — quality drops, signal corrupts.

### Task PF.7: Decide PII retention policy

**Files:**
- Modify: `docs/customer-discovery/beta-deliverable.md` OR Create: `docs/customer-discovery/retention.md`

- [ ] **Step 1: Pick a policy**

Two options:
- **Option A**: delete all transcripts 30 days after `decision.md` is committed.
- **Option B**: move transcripts to encrypted local storage post-decision (out of git entirely, into ~/Documents or similar).

- [ ] **Step 2: Document the choice**

Add a "PII retention" section to `beta-deliverable.md` OR create a new `retention.md`. State the chosen policy, the trigger (decision.md commit date), and the cleanup procedure.

- [ ] **Step 3: Commit**

```bash
git add docs/customer-discovery/beta-deliverable.md  # or retention.md
git commit -m "docs(discovery): commit PII retention policy"
```

### Task PF.8: Pre-flight gate review

**Files:**
- (none — checklist verification)

- [ ] **Step 1: Verify all artifacts exist**

```bash
ls -la docs/customer-discovery/
```

Expected files:
- `icp.md`, `interview-guide.md`, `rubric.md`, `preorder-test.md` (Phase 0, locked)
- `action-plan.md` (v2)
- `beta-deliverable.md` (Task PF.1)
- `recruitment-channel-rules.md` (Task PF.2)
- `disqualified-log.md` (Task PF.4)
- `retention.md` (or section in beta-deliverable.md, Task PF.7)

- [ ] **Step 2: Verify interview-guide.md has the four new sections**

Check for: consent script, anonymization rules, gift payout rule, disqualified-prospect probe.

- [ ] **Step 3: Verify calendar holds exist**

Open calendar. Count placeholder interview slots. Should be 18 (full scope) or 10 (half scope).

- [ ] **Step 4: Confirm hours commitment in writing**

Add a leading note to action-plan.md: "Founder-hours committed: {X} hours across {dates}."

- [ ] **Step 5: Pre-flight gate signoff**

Commit a marker:

```bash
git add docs/customer-discovery/action-plan.md
git commit -m "docs(discovery): pre-flight gate passed — ready for Phase 1"
```

If anything is missing, do NOT proceed to Phase 1. Fix it first.

---

## Phase 1 — Recruit Marks

**Goal:** 18 scheduled calls (full) or 10 scheduled (half), 100+ pipeline (full) or 60+ (half), zero network hires.

**Source prompt:** action-plan.md "Phase 1 — Recruit Marks" section. Paste into a fresh Claude Code session per session below.

### Task 1.1: Generate first batch of search queries

**Files:**
- Modify: `docs/customer-discovery/pipeline.csv` (create if missing)

- [ ] **Step 1: Open a fresh Claude Code session**

Start a new conversation. Paste the action-plan.md Phase 1 prompt block.

- [ ] **Step 2: Request first batch of search queries**

Tell Claude: "Generate the first batch of 5-10 search queries for the highest-yield source from icp.md. Use the channel rules in recruitment-channel-rules.md."

- [ ] **Step 3: Save queries to pipeline.csv setup notes**

Create `pipeline.csv` if missing:

```bash
echo "handle,source,url_to_post_that_qualified_them,why_qualified,dm_sent_date,response,scheduled_date,completed_date,gift_paid_date,status,notes" > docs/customer-discovery/pipeline.csv
git add docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): scaffold prospect pipeline tracker"
```

### Task 1.2: Source first batch of 10 prospects

**Files:**
- Modify: `docs/customer-discovery/pipeline.csv`

- [ ] **Step 1: Run the search queries manually**

In your browser (Reddit, Twitter, Substack, Discord per channel rules), run each query. For each candidate prospect:
- Click their profile
- Read their last 5-10 posts
- Confirm they match the ICP signals (active investor, self-directed, has rituals)
- Confirm they don't fail disqualifiers

- [ ] **Step 2: Paste prospect profiles back to Claude**

For each candidate, paste a brief summary into the Claude session:
- Handle
- Source URL
- 2-3 quotes from their posts that signal qualification
- Any concerns

- [ ] **Step 3: Let Claude flag any disqualified prospects**

Claude will flag prospects whose posts suggest disqualifier failure (options trader, influencer, sell-side analyst, indexer). Skip them.

- [ ] **Step 4: Add 10 qualified prospects to pipeline.csv**

Append rows. status = "queued" until DM sent.

- [ ] **Step 5: Commit batch 1**

```bash
git add docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): pipeline batch 1 — {source}, {N} prospects"
```

### Task 1.3: Send first batch of DMs

**Files:**
- Modify: `docs/customer-discovery/pipeline.csv`

- [ ] **Step 1: Request DM drafts from Claude**

For each prospect in batch 1, ask Claude: "Draft a personalized DM (≤4 sentences) for {handle} based on their post {URL}. Reference something specific. Don't mention Margin Invest. Offer $50 thank-you for qualified-and-completed call (paid AFTER, state explicitly)."

- [ ] **Step 2: Review each DM draft**

Check:
- Does it reference something specific (not generic)?
- Is it ≤4 sentences?
- Does it state the gift rule clearly?
- Does it NOT mention Margin Invest or any product?

Edit if needed.

- [ ] **Step 3: Send via channel-appropriate method**

- Reddit: comment on their post first (rapport), then DM after engagement (per channel rules)
- Twitter/X: reply or follow first, then DM after mutual follow
- Substack: email if available, otherwise comment

Stagger sending (≤10 DMs/day per account on Twitter to avoid spam triggers).

- [ ] **Step 4: Update pipeline.csv with dm_sent_date**

For each DM sent, set `dm_sent_date` and `status = "dm sent"`.

- [ ] **Step 5: Commit DM batch sent**

```bash
git add docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): pipeline batch 1 — {N} DMs sent"
```

### Task 1.4: Track responses and schedule

**Files:**
- Modify: `docs/customer-discovery/pipeline.csv`

- [ ] **Step 1: Monitor responses for 48-72 hours**

Check each channel daily. Most responses (if they come) arrive within 48 hours.

- [ ] **Step 2: For each response, classify**

- "Sure, when?" → schedule call
- "What's this about?" → reply with brief honest description (still no Margin Invest pitch)
- "Not interested" → mark and move on
- No response in 7 days → mark "no_response"

- [ ] **Step 3: Schedule via Calendly or direct**

For "sure" responses: send Calendly link or propose 2-3 specific slots from your pre-blocked calendar holds. Match interview to a held slot.

- [ ] **Step 4: Update pipeline.csv**

Set `response`, `scheduled_date`, `status` (e.g., "scheduled", "no_response", "declined").

- [ ] **Step 5: Commit response tracking**

```bash
git add docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): pipeline batch 1 — {N} scheduled, {M} declined"
```

### Task 1.5: Iterate batches 2-N

Repeat Tasks 1.1 → 1.4 with the next source/channel from icp.md until the pipeline reaches the target (100+ for full scope, 60+ for half).

- [ ] **Step 1: Source channel rotation**

Don't exhaust one channel before moving on. Distribute across all 3 sources. Each batch of 10 should ideally include 3-4 from each top channel.

- [ ] **Step 2: Quality monitoring**

After each batch, eyeball the response rate. If trending below 5%, the prospects may not be well-qualified — tighten the search queries.

- [ ] **Step 3: Stop after each batch and ask Claude if to continue**

Per the action-plan.md prompt: "Stop after each batch of 10 and ask if I want to continue — quality over speed."

### Task 1.6: Day-7 yield checkpoint (CRITICAL GATE)

**Files:**
- Modify: `docs/customer-discovery/pipeline.csv`

- [ ] **Step 1: Count scheduled calls at Day 7**

```bash
grep -c ",scheduled," docs/customer-discovery/pipeline.csv
```

- [ ] **Step 2: Apply the gate**

- ≥8 scheduled (full) or ≥5 scheduled (half): continue Phase 1 as planned
- <8 scheduled (full) or <5 scheduled (half): pause and pick ONE remediation

- [ ] **Step 3: If <target, choose a remediation**

Pick exactly one and document in pipeline.csv notes:

(a) **Expand channels**: add Twitter Lists for stocktwits-pro, paid Discord servers (RoaringKitty, SuperInvestor), Substack comments on Bearcave/Hindenburg/Kerrisdale.

(b) **Raise gift to $75-100**: re-DM cold prospects with the gift bump. Update pipeline.csv notes for each re-DM.

(c) **Rescope**: accept reality, drop to half scope (8 interviews / 5 paid asks). Update action-plan.md leading note.

Do NOT just "send harder" without picking one.

- [ ] **Step 4: Commit the gate decision**

```bash
git add docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): Day-7 yield gate — {N} scheduled, decision: {a/b/c}"
```

### Task 1.7: Phase 1 gate signoff

**Files:**
- Modify: `docs/customer-discovery/pipeline.csv`

- [ ] **Step 1: Verify acceptance criteria**

- 18 scheduled calls (full scope) or 10 scheduled (half scope)
- 100+ qualified prospects in pipeline (full) or 60+ (half)
- Zero network hires (verify each scheduled call)
- Day-7 gate passed or rescoped explicitly

- [ ] **Step 2: Commit Phase 1 close**

```bash
git add docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): Phase 1 complete — {N} interviews scheduled"
```

---

## Phase 2 — Run Interviews

**Goal:** 15 (or 8) anonymized transcripts + 15 (or 8) scorecards. Disqualified-log captures probes.

**Source prompt:** action-plan.md "Phase 2 — Run Interviews" prompt. Paste into a fresh Claude Code session **per interview**.

Phase 2 tasks are templates. You execute Tasks 2.1-2.4 once per interview.

### Task 2.1 (template, run per interview): Pre-call prep for interview N

**Files:**
- Create: `docs/customer-discovery/transcripts/{NN}-{firstname}.md`

- [ ] **Step 1: Open a fresh Claude Code session ~30 min before the call**

Paste the action-plan.md Phase 2 prompt. Substitute:
- N = interview number
- firstname = prospect first name
- X = minutes until call
- source = recruitment source from pipeline.csv
- why_qualified = qualification reason from pipeline.csv

- [ ] **Step 2: Let Claude generate the transcript template**

Claude will create `docs/customer-discovery/transcripts/{NN}-{firstname}.md` with:
- Header (date, source, qualification reason)
- Consent acknowledgment block
- Disqualifier checklist
- Five question blocks
- Closing-ask section
- Red-flag section

- [ ] **Step 3: Read the Mom Test pre-call reminder Claude provides**

Three bullets on what NOT to do during the call. Internalize them.

- [ ] **Step 4: Open interview-guide.md in another window**

Have the verbatim 5 questions visible during the call.

- [ ] **Step 5: Confirm Zoom link, audio test, quiet location**

Standard pre-call hygiene.

### Task 2.2 (template, run per interview): Run interview N

**Files:**
- (none — synchronous call)

- [ ] **Step 1: Open with the consent script**

Verbatim from interview-guide.md:
> "Quick housekeeping before we start: I take notes that I store in a private code repository so I can review patterns later. I'll use a first name only and won't store your handle or specific holdings — is that OK?"

If they decline: thank them, end politely. Mark in pipeline.csv as "consent declined." NO gift. End at this step.

- [ ] **Step 2: Run the disqualifier check**

5 disqualifier questions verbatim from interview-guide.md.

If they fail: pivot to the 5-min probe (Task 2.4 below) instead of running the 5 questions. Pay gift after probe completes.

- [ ] **Step 3: Run the 5 questions**

Verbatim. Use "tell me more" follow-ups. Capture verbatim quotes in the transcript template.

- [ ] **Step 4: Discipline checks during the call**

- Don't lead the witness ("So you'd want X, right?")
- Don't pitch Margin Invest
- Don't anchor with previous prospects' answers
- Note any moment you slipped in the red-flag section

- [ ] **Step 5: Closing-ask (if qualified and call ≥25 min)**

Note: in the new model, the closing ask is async — DO NOT pitch a Stripe link on the call. The Phase 3 follow-up is the actual ask. End by thanking them and saying "I'll send a thank-you and keep you posted."

- [ ] **Step 6: End the call, then immediately anonymize the transcript**

Within 15 min of the call ending while context is fresh:
- Replace tickers with $TICKER_A, $TICKER_B (in order of mention)
- Bucket dollar amounts ($1-5K), ($5-20K), etc.
- Keep first name only
- Keep brokerages generic

### Task 2.3 (template, run per interview): Score the transcript

**Files:**
- Create: `docs/customer-discovery/scores/{NN}-{firstname}.md`
- Modify: `docs/customer-discovery/pipeline.csv`

- [ ] **Step 1: Paste the anonymized transcript back to Claude**

In the same session as Task 2.1, paste the verbatim notes (already anonymized).

- [ ] **Step 2: Claude scores against rubric.md**

Per the action-plan.md prompt: every signal marked "strong" must quote the prospect's exact words. If you don't have a quote, the signal is not strong.

- [ ] **Step 3: Verify the scorecard**

Open `docs/customer-discovery/scores/{NN}-{firstname}.md`. Confirm:
- Quotes are present for every "strong" signal
- Composite score is calculated per rubric.md
- Strong/weak/kill verdict is named

- [ ] **Step 4: Update pipeline.csv**

Set: `completed_date`, `gift_paid_date` (after gift sent), `status = "completed"` or `"disqualified-probed"`.

- [ ] **Step 5: Pay the gift**

Send $50 via PayPal/Venmo/charity donation per prospect's choice. Confirm sent before marking gift_paid_date.

- [ ] **Step 6: Commit the interview**

```bash
git add docs/customer-discovery/transcripts/{NN}-{firstname}.md docs/customer-discovery/scores/{NN}-{firstname}.md docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): interview {NN} {firstname} complete — {strong/weak/disqualified}"
```

### Task 2.4 (template, conditional): Disqualified-but-probed log capture

**Files:**
- Modify: `docs/customer-discovery/disqualified-log.md`

Run only if disqualifier check failed in Task 2.2 Step 2.

- [ ] **Step 1: Pivot the call to the probe**

> "Got it — sounds like our usual conversation isn't quite aimed at how you invest. If you have a few more minutes, I'd love a quick read on the tools you DO use and what you wish existed."

- [ ] **Step 2: Run the 3-question probe**

- "What tools do you currently use to manage / research investments?"
- "What's a workflow that frustrates you?"
- "What would you pay for if it existed?"

5 minutes max.

- [ ] **Step 3: Append to disqualified-log.md**

Add a row with: date, source, first_name, why_disqualified, tools_used, wishes_for_existing_tools, gift_paid (yes after probe).

- [ ] **Step 4: Pay the $50 gift**

Kept-promise rule.

- [ ] **Step 5: Commit**

```bash
git add docs/customer-discovery/disqualified-log.md docs/customer-discovery/pipeline.csv
git commit -m "docs(discovery): disqualified-but-probed {firstname} — {tools_used}"
```

### Task 2.5: Interview cohort verification (run after final interview)

**Files:**
- (none — verification)

- [ ] **Step 1: Count completed interviews**

```bash
ls docs/customer-discovery/transcripts/ | wc -l
ls docs/customer-discovery/scores/ | wc -l
```

Expected: 15 (full) or 8 (half).

- [ ] **Step 2: Verify quality**

Skim each transcript:
- Did the call run ≥25 min?
- Are there verbatim quotes for at least 3 of the 5 questions?
- Is at least one quote a "walk me through a specific time" past-behavior anecdote?

If any interview is <20 min or quote-thin, discard and replace.

- [ ] **Step 3: Verify disqualified-log captures**

```bash
wc -l docs/customer-discovery/disqualified-log.md
```

Should have one row per disqualified-but-probed call.

- [ ] **Step 4: Phase 2 close commit**

```bash
git add docs/customer-discovery/
git commit -m "docs(discovery): Phase 2 complete — {N} interviews scored"
```

---

## Phase 3 — Paid Preorder Test

**Goal:** Stripe live, 10 (or 15) asks sent, 7+ responses logged, every objection tagged.

**Source prompt:** action-plan.md "Phase 3 — Paid Preorder Test" prompt.

### Task 3.1: Decide ask cohort

**Files:**
- Modify: `docs/customer-discovery/preorder-test-results.md` (create if missing)

- [ ] **Step 1: Tally rubric scores from Phase 2**

For each interviewed prospect, note their composite score and strong/weak/kill verdict.

- [ ] **Step 2: Pick Option A or Option B**

- **Option A (default)**: top 10 strong-signal prospects (≥4/6 rubric).
- **Option B (RECOMMENDED if you have ~2 hr extra)**: send to ALL 15 prospects to validate the rubric.

- [ ] **Step 3: Document the decision and rank the cohort**

Create `docs/customer-discovery/preorder-test-results.md`:

```markdown
# Preorder Test Results

**Cohort decision (2026-XX-XX):** Option {A/B}

## Ranked ask cohort

| rank | prospect | composite_score | rubric_verdict | tie_breaker_notes |
|---|---|---|---|---|
| 1 | {firstname} | {N/6} | strong | {dollar-loss specificity, tool spend} |
...

## Asks tracker

| prospect | ask_sent_date | response_date | outcome | amount | objection_tag | objection_notes |
|---|---|---|---|---|---|---|
| | | | | | | |
```

- [ ] **Step 4: Commit the cohort decision**

```bash
git add docs/customer-discovery/preorder-test-results.md
git commit -m "docs(discovery): Phase 3 cohort decision — Option {A/B}, {N} ranked"
```

### Task 3.2: Decide price arms

**Files:**
- Modify: `docs/customer-discovery/preorder-test-results.md`

- [ ] **Step 1: Pick single-price or 2-arm**

Default: single-price ($49). Optional: 2-arm split ($49 vs $29 or $39) — only if Option B (15 asks).

- [ ] **Step 2: If 2-arm: assign prospects to arms**

Random assignment. 7 prospects to $49, 8 to $29 (or 7-8 split per cohort size). Document assignment in preorder-test-results.md.

- [ ] **Step 3: Optional: rapport-vs-cold split**

Rare addition. If you have stamina: 7 prospects get rapport-driven personalized follow-up; 3 get cold-template. Document in preorder-test-results.md.

- [ ] **Step 4: Commit price/cohort splits**

```bash
git add docs/customer-discovery/preorder-test-results.md
git commit -m "docs(discovery): Phase 3 price/rapport assignment"
```

### Task 3.3: Set up Stripe Checkout product

**Files:**
- (Stripe dashboard, no repo files)

- [ ] **Step 1: Open a fresh Claude Code session**

Paste the action-plan.md Phase 3 Step 2 prompt. Invoke `/stripe:stripe-best-practices`.

- [ ] **Step 2: Create the Stripe product**

Per Claude's walkthrough:
- Product name: "Margin Invest Founder Beta"
- Description: "Early access to systematic equity screener with forensic accounting filters, Kelly sizing, 13F diffing, and risk factor diffing. Beta access begins {Day 35 date}. Cancel anytime."
- Price: $49/month subscription (or your chosen price)
- Trial period: 0 days

- [ ] **Step 3: If 2-arm test: create second product**

Second product at the second price. Both link to the same beta-deliverable.md scope.

- [ ] **Step 4: Document Stripe product IDs**

In a private notes file (NOT committed): `~/.margin-invest-stripe-notes.md` with product IDs and Stripe dashboard links.

### Task 3.4: Set up Stripe Checkout session

**Files:**
- (Stripe dashboard)

- [ ] **Step 1: Configure Checkout session**

Per Claude's walkthrough. Required:
- Collects email (for beta access delivery)
- Works for buyers without a Stripe account
- Self-serve cancellation portal enabled
- Success URL: simple thank-you page (must be live)
- Cancel URL: simple back-to-info page

- [ ] **Step 2: Add beta-deliverable.md link**

In the Checkout description or success page, link to a public-readable copy of `beta-deliverable.md`. Customer must see scope before paying.

If beta-deliverable.md is private: paste the "Included" + "Not included" sections into the Checkout description verbatim.

- [ ] **Step 3: Generate Checkout URL(s)**

One per price arm if 2-arm test. Save to private notes.

### Task 3.5: Verify checkout flow with test card

**Files:**
- (Stripe dashboard, test mode)

- [ ] **Step 1: Open Stripe in test mode**

Use Stripe's test card 4242 4242 4242 4242 with any future expiry.

- [ ] **Step 2: Run a full transaction**

- Click the Checkout URL
- Enter test card
- Confirm subscription created in test mode
- Confirm subscription cancellable from customer portal
- Confirm refund-able from dashboard

- [ ] **Step 3: Switch to live mode**

Only after test mode succeeds. Verify the live URL is the one you'll send to prospects.

### Task 3.6 (template, run per ask): Draft personalized ask for prospect N

**Files:**
- Modify: `docs/customer-discovery/preorder-test-results.md`

- [ ] **Step 1: Open a fresh Claude Code session per ask batch (5 asks at a time)**

Paste the action-plan.md Phase 3 Step 3 prompt.

- [ ] **Step 2: For each prospect, request a draft**

Tell Claude: "Draft a personalized follow-up for {firstname} based on their interview. Quote their words back, but anonymize tickers ($TICKER_A) and dollar buckets. End with the preorder ask from preorder-test.md and the Stripe link {URL}."

- [ ] **Step 3: Review each draft**

- Does it quote the prospect's actual words?
- Does it use anonymized tickers/dollars?
- Does it reference beta-deliverable.md or include the scope?
- Is the ask clear (price, charge timing, delivery date, cancellation)?

- [ ] **Step 4: If running rapport-vs-cold split: 3 cold drafts**

3 prospects get a clean cold-template ask referencing only the public Stripe page, no quoted material.

### Task 3.7 (template, run per ask): Send ask, log response

**Files:**
- Modify: `docs/customer-discovery/preorder-test-results.md`

- [ ] **Step 1: Send via the original recruitment channel**

Reddit DM, Twitter DM, email — whatever you used to recruit them.

- [ ] **Step 2: Update preorder-test-results.md**

Set `ask_sent_date`. Status `"sent_awaiting_response"`.

- [ ] **Step 3: Monitor responses for 5-7 days**

Check daily.

- [ ] **Step 4: Classify each response**

- Paid: Stripe charge succeeded. Set `outcome = "paid"`, `amount`, `response_date`.
- Declined: explicit no. Set `outcome = "declined"`, capture objection.
- Objection: not a hard no, asks questions. Handle per Task 3.8.
- No response: 7+ days silent. Set `outcome = "no_response"`.

### Task 3.8: Tag every objection

**Files:**
- Modify: `docs/customer-discovery/preorder-test-results.md`

- [ ] **Step 1: For each non-payment, ask one follow-up question**

Per action-plan.md Phase 3 Step 4:
- Price objection: "What number would feel like a no-brainer to you?"
- Timing/delivery objection: "What specifically would you need to see in the first beta for it to be worth $49?"

- [ ] **Step 2: Tag the objection**

One of:
- `delivery-risk`: would buy a working product
- `price-objection`: $49 is too high
- `feature-gap`: would buy if X existed
- `disinterest`: don't have the problem

- [ ] **Step 3: Capture quotes in objection_notes**

Verbatim. These feed Phase 4 dominant-pattern analysis.

- [ ] **Step 4: Do NOT discount**

Per action-plan.md Phase 3 Step 4: never offer a discount in response to a price objection. Capture the answer to "what number would feel like a no-brainer" and move on.

### Task 3.9: Wait for 7+ responses, commit

**Files:**
- Modify: `docs/customer-discovery/preorder-test-results.md`

- [ ] **Step 1: Verify response count**

```bash
grep -c "outcome,paid\|outcome,declined\|outcome,no_response" docs/customer-discovery/preorder-test-results.md
```

Should be ≥7 of 10 (or ≥10 of 15).

- [ ] **Step 2: If <7 responses after 7 days post-last-ask**

Send one polite nudge to no-response prospects. Wait 3 more days.

After that: count silent prospects as `no_response` and proceed.

- [ ] **Step 3: Commit Phase 3 close**

```bash
git add docs/customer-discovery/preorder-test-results.md
git commit -m "docs(discovery): Phase 3 complete — {N} paid, {M} declined, {K} no-response"
```

---

## Phase 4 — Decision (charge gate, then retention gate)

**Goal:** binding decision committed to `decision.md`. Refunds first if NO-GO.

**Source prompt:** action-plan.md "Phase 4 — Go / No-Go Decision (amended, two-gate)" prompts (charge gate AND retention gate).

### Task 4a.1: Compute charge-gate metrics

**Files:**
- Create: `docs/customer-discovery/decision.md`

- [ ] **Step 1: Open a fresh Claude Code session**

Paste the action-plan.md Phase 4 charge-gate prompt.

- [ ] **Step 2: Let Claude compute raw numbers**

- Asks sent
- Responses (paid + declined + no_response)
- Paid count
- Total $ collected
- Conversion rate = paid / asks_sent

- [ ] **Step 3: Let Claude compute objection-pattern analysis**

Counts by tag: delivery-risk, price-objection, feature-gap, disinterest. Identify dominant pattern.

- [ ] **Step 4: Save raw computation to decision.md**

Claude writes `docs/customer-discovery/decision.md` with section: "Charge gate raw numbers."

### Task 4a.2: Determine charge-gate verdict

**Files:**
- Modify: `docs/customer-discovery/decision.md`

- [ ] **Step 1: Apply the decision rule**

- ≥4/10 paid AND dominant objection ≠ disinterest → **GO (charge)**
- 2-3/10 paid → **SOFT GO**
- ≤1/10 paid OR ≥60% disinterest → **NO-GO**

- [ ] **Step 2: Document verdict in decision.md**

Add section: "Charge-gate verdict: {GO / SOFT GO / NO-GO}".

For each verdict, follow the appropriate branch below.

### Task 4a.3 (NO-GO branch): Issue refunds

**Files:**
- (Stripe dashboard)

⚠️ Refunds happen BEFORE FROZEN.md commit. Do not skip this order.

- [ ] **Step 1: Open Stripe dashboard, switch to live mode**

- [ ] **Step 2: Find every paid customer subscription**

Filter by product = "Margin Invest Founder Beta".

- [ ] **Step 3: Issue refund for each**

Click subscription → Refund → "Full refund" → reason: "product not yet available." Confirm refund processed (status: refunded).

- [ ] **Step 4: Cancel each subscription**

After refund, cancel the subscription so no future charges occur.

- [ ] **Step 5: Document in decision.md**

Add section: "NO-GO refunds issued: {N} customers, ${total} refunded, {date}."

### Task 4a.4 (NO-GO branch): Send personalized notification

**Files:**
- (email)

- [ ] **Step 1: Open a fresh Claude Code session**

Ask Claude: "For each refunded customer, draft a personalized email naming the decision honestly, thanking them, and confirming the refund was issued."

- [ ] **Step 2: Send each email**

Within 48 hours of decision. Use the email captured at Stripe Checkout.

- [ ] **Step 3: Optional: offer to follow up on a different ICP pivot**

If you genuinely intend to pivot, offer to keep them informed. Don't promise something you won't deliver.

### Task 4a.5 (NO-GO branch): Commit FROZEN.md

**Files:**
- Create: `FROZEN.md` (repo root)

- [ ] **Step 1: After ALL refunds confirmed, draft FROZEN.md**

```markdown
# FROZEN

Feature work paused 2026-XX-XX pending new customer discovery.

See [docs/customer-discovery/decision.md](docs/customer-discovery/decision.md) for the evidence trail.

Pivot candidates from disqualified-log.md are listed in decision.md §"NO-GO pivot candidates."
```

- [ ] **Step 2: Read back top 3 alternative ICPs from disqualified-log.md**

In a fresh Claude Code session, ask: "Read disqualified-log.md and surface the top 3 alternative ICPs based on tools_used and wishes_for_existing_tools patterns. Output a brief sketch per ICP."

Append the output to decision.md.

- [ ] **Step 3: Commit FROZEN.md and decision.md**

```bash
git add FROZEN.md docs/customer-discovery/decision.md
git commit -m "decision: NO-GO — feature work frozen, see decision.md"
```

- [ ] **Step 4: Open a fresh /superpowers:brainstorming on a candidate pivot ICP**

Phase 5 does not run. Sprint ends here.

### Task 4a.6 (charge-gate GO branch): Commit decision.md (charge-gate section)

**Files:**
- Modify: `docs/customer-discovery/decision.md`

- [ ] **Step 1: Per action-plan.md Phase 4 Step 4, write the full charge-gate section**

Sections required:
- Raw numbers
- Verdict (GO charge, SOFT GO, or NO-GO already handled)
- What I learned about the product (cite quotes)
- What I learned about my bias as a builder
- Rubric validity (if Option B was run): conversion rate by rubric bucket
- Price elasticity (if 2-arm test was run): conversion at $49 vs $29
- Rapport-vs-cold conversion (if split was run): footnote calibration
- Next step: exploratory Phase 5 (charge-gate GO), retention monitoring (SOFT GO), or NO-GO (handled above)

- [ ] **Step 2: Commit charge-gate decision**

```bash
git add docs/customer-discovery/decision.md
git commit -m "decision: charge-gate {GO/SOFT GO} — {N}/{M} paid, exploratory Phase 5 unlocked"
```

### Task 4a.7 (charge-gate GO branch): Schedule retention gate

**Files:**
- (calendar)

- [ ] **Step 1: Add Day 51 calendar event**

Title: "RETENTION GATE — Margin Invest customer discovery." Reminder: 1 day prior.

- [ ] **Step 2: Set monitoring cadence**

Weekly check-in on Stripe dashboard between Day 21 and Day 51. Watch for cancellations. Note any with reasons.

- [ ] **Step 3: Plan beta delivery for Day 35**

Between Day 21 and Day 35, finalize the deliverable per beta-deliverable.md. This may overlap with exploratory Phase 5 work.

- [ ] **Step 4: On Day 35, deliver the beta**

Send beta access email per Stripe Checkout email captured. Customer expectation = beta-deliverable.md scope.

### Task 4b.1: Pull Stripe retention data at Day 51

**Files:**
- Modify: `docs/customer-discovery/decision.md`

- [ ] **Step 1: Open a fresh Claude Code session**

Paste the action-plan.md Phase 4 retention-gate prompt.

- [ ] **Step 2: Pull Stripe data**

For each customer who paid at charge gate:
- Status: active / cancelled / past-due
- Second billing cycle: charged / not yet / failed
- Cancellation date and reason (if applicable)

- [ ] **Step 3: Compute retention rate**

retained / charge-gate cohort.

### Task 4b.2: Determine retention-gate verdict

**Files:**
- Modify: `docs/customer-discovery/decision.md`

- [ ] **Step 1: Apply retention thresholds**

- ≥80% retained → **GO (committed)** — ratify charge-gate GO, start committed 90-day Phase 5
- 60-79% retained → **SOFT GO** — hold, investigate churn, decide within 1 week
- ≤40% retained → **NO-GO (demoted)** — refund holdouts, freeze

Operational gloss: cohorts of 4-9 paid, lose ≤1; cohorts of 10+, lose ≤2.

- [ ] **Step 2: Document verdict**

Append "Retention-gate verdict" section to decision.md with retention rate, retained count, churn count, churn reasons.

### Task 4b.3 (retention NO-GO branch): Refund + freeze

**Files:**
- Create: `FROZEN.md`

- [ ] **Step 1: Issue refunds for any remaining paid customers**

Same Stripe dashboard process as Task 4a.3.

- [ ] **Step 2: Send personalized notification**

Same as Task 4a.4. Be specific that you tried, retention didn't hold.

- [ ] **Step 3: Commit FROZEN.md (if not already)**

```bash
git add FROZEN.md docs/customer-discovery/decision.md
git commit -m "decision: retention-gate NO-GO (demoted) — {N}/{M} retained, frozen"
```

### Task 4b.4 (retention GO branch): Append to decision.md

**Files:**
- Modify: `docs/customer-discovery/decision.md`

- [ ] **Step 1: Add final verdict section**

Per action-plan.md Phase 4 retention-gate prompt Step 3:
- Retention numbers
- Churn reasons (if available)
- Final verdict: COMMITTED GO
- 90-day commitment with top-3 priorities from charge-gate GO section

- [ ] **Step 2: Commit final decision**

```bash
git add docs/customer-discovery/decision.md
git commit -m "decision: retention-gate GO ratified — committed Phase 5 unlocked"
```

---

## Phase 5 — Roadmap (GO branch only)

**Goal (charge-gate GO, Days 21-28):** scoped exploratory roadmap from transcript evidence. **Goal (retention-gate GO, Day 51+):** committed 90-day implementation via `/flow:dev`.

**Source prompts:** action-plan.md "Phase 5 — Translate Evidence into Roadmap" (both exploratory and committed prompts).

### Task 5a.1 (exploratory, Days 21-28): Read transcripts for priority signals

**Files:**
- Read: `docs/customer-discovery/transcripts/`, `scores/`, `decision.md`, `preorder-test-results.md`

- [ ] **Step 1: Open a fresh Claude Code session**

Paste the action-plan.md Phase 5 exploratory prompt.

- [ ] **Step 2: Run /flow:triage on top-3 priorities**

Per the prompt: each priority must cite transcript quotes (anonymized) and have acceptance criteria a real interviewed prospect could verify.

### Task 5a.2: Draft top-3 priorities

**Files:**
- Create: `docs/customer-discovery/priorities.md`

- [ ] **Step 1: Document each priority**

```markdown
# Top-3 Phase 5 Priorities

## Priority 1: {feature name}

**Source quote(s):**
- {firstname} ({NN}-{firstname}.md): "{verbatim, anonymized}"
- {firstname2}: "{verbatim, anonymized}"

**Acceptance criteria:** {what would make {firstname} use this in their workflow}

**Routing:** /flow:plan if complexity ≥ STANDARD, /flow:execute if MICRO

## Priority 2: ...

## Priority 3: ...
```

- [ ] **Step 2: Commit priorities.md**

```bash
git add docs/customer-discovery/priorities.md
git commit -m "docs(discovery): Phase 5 exploratory priorities from transcripts"
```

### Task 5a.3: Update pricing if needed

**Files:**
- Modify: `web/src/app/pricing/...` (or wherever pricing is)

- [ ] **Step 1: Check decision.md for revised pricing**

If decision.md Output `revised pricing recommendation` (e.g., "raise to $79 based on objection patterns"): apply.

- [ ] **Step 2: TDD: write failing test**

Per CLAUDE.md, web tests first. Write a test asserting the new pricing.

- [ ] **Step 3: Implement and verify**

Update pricing component, run tests, confirm pass.

- [ ] **Step 4: Commit**

```bash
cd web && git add ... && git commit -m "feat(pricing): update to ${new_price}/mo per discovery decision"
```

### Task 5a.4: HOLD — wait for retention gate (Day 51)

**Files:**
- (none — wait period)

- [ ] **Step 1: Do not start committed Phase 5 work**

Per action-plan.md Phase 5 exploratory prompt: "Do NOT start the committed 90-day work until retention gate passes at Day 51."

- [ ] **Step 2: Use the wait time productively**

- Monitor Stripe retention weekly
- Beta delivery on Day 35 per Task 4a.7
- Polish/maintenance on existing features
- DO NOT build the top-3 priorities yet

### Task 5b.1 (committed, Day 51+ after retention GO): Build Priority 1

**Files:**
- (depends on the priority)

- [ ] **Step 1: Open a fresh Claude Code session**

Paste the action-plan.md Phase 5 committed prompt.

- [ ] **Step 2: Drive Priority 1 to DONE via /flow:dev**

Per the prompt: "each feature must have a named prospect from transcripts who asked for it." Cite the quote in /flow:triage.

- [ ] **Step 3: Verify with the named prospect**

Optional but recommended: when Priority 1 ships, send the named prospect a "remember when you mentioned X? we shipped it" email. Their reaction is feedback.

### Task 5b.2: Build Priority 2

Same pattern as Task 5b.1.

### Task 5b.3: Build Priority 3

Same pattern as Task 5b.1.

---

## Verification — operational, not code

- [ ] **Pre-flight done**: 7 items committed, calendar pre-blocked, ≥30 hours blocked.
- [ ] **Phase 1 done**: 18 (or 10) calls scheduled, pipeline.csv has 100+ (or 60+), zero network hires, Day-7 gate passed.
- [ ] **Phase 2 done**: 15 (or 8) anonymized transcripts + scorecards. Disqualified-log captures probes.
- [ ] **Phase 3 done**: 7+ of 10 (or 10+ of 15) asks resolved. Objection tags applied.
- [ ] **Phase 4 charge gate done**: decision.md committed. Refunds first if NO-GO.
- [ ] **Phase 4 retention gate done (Day 51)**: ratified GO or demoted to NO-GO.
- [ ] **Success** = ≥80% of charge-gate paid cohort (minimum ≥4) retained through second billing cycle, attached to real emails of real anonymized-in-git people whose transcripts you can re-read.

If at the end of 51 days you don't have that retained-revenue evidence, no number of additional features will fix it. Change the customer, or change the product.
