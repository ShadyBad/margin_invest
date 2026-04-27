# Disqualified Prospect Probe Log

Captures 5-min probe data from prospects who failed the Phase 2 disqualifier check but consented to a brief follow-up.

**Purpose:** source data for Phase 4 NO-GO pivot logic. If the sprint reaches NO-GO, this log surfaces alternative ICPs (who showed up that wasn't Mark, what tools they use, what they wish existed).

**Per the PII retention policy in `action-plan.md`**: rows in this log are deleted 30 days after `decision.md` is committed. The header stays; data rows go.

---

## Log

| date       | source  | first_name | why_disqualified                       | tools_used                        | wishes_for_existing_tools                  | gift_paid |
|------------|---------|------------|----------------------------------------|-----------------------------------|--------------------------------------------|-----------|
|            |         |            |                                        |                                   |                                            |           |

---

## Field guide

- **date**: ISO-8601 date the call took place (`YYYY-MM-DD`)
- **source**: recruitment channel (`reddit / twitter / substack / discord`)
- **first_name**: first name only, never handle
- **why_disqualified**: which disqualifier fired (`passive_only`, `options_primary`, `crypto_primary`, `professional_analyst`, `no_cost_basis`)
- **tools_used**: anonymized list of investment tools they currently use; bucket dollar amounts (`$10-25/mo Tool X, $25-50/mo Tool Y`)
- **wishes_for_existing_tools**: anonymized summary of gaps they named (paraphrase OK; no verbatim ticker symbols, no dollar amounts above buckets)
- **gift_paid**: `yes` (after probe) or `no` (probe declined)

---

## Anonymization rules apply here too

Even though this log is short-form, the same anonymization rules from `interview-guide.md` apply: first name only, tickers as `$TICKER_A` / etc., dollar amounts bucketed, brokerages generic.

---

## How this log feeds Phase 4 NO-GO pivot

If Phase 4 charge-gate verdict is NO-GO:

1. Read the populated rows of this log.
2. Cluster `tools_used` and `wishes_for_existing_tools` patterns. Look for repeated mentions of:
   - Specific tool gaps mentioned by 3+ disqualified prospects
   - Workflows nobody currently has a good answer for
   - Demographic clusters (e.g., "all the index investors who showed up wished they had X")
3. Surface the top 3 alternative ICPs in `decision.md`'s NO-GO section.
4. Use as input to a fresh `/superpowers:brainstorming` on a candidate pivot.

If charge-gate verdict is GO or SOFT GO, this log is informational only — not used for the GO branch decision.
