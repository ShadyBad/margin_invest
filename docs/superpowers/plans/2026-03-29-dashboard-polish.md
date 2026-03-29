# Dashboard Polish Implementation Plan

> For agentic workers: Use superpowers:subagent-driven-development

Goal: Fix 8 dashboard issues. Architecture: All independent.

Tech Stack: FastAPI, SQLAlchemy, NextAuth v5, Next.js 16, React 19, Vitest, pytest

---

### Task 1: OAuth Avatar -- Include avatar_url in Security Status Response

Files: schemas/auth.py, routes/auth.py, test_auth_security_endpoints.py

- [ ] Step 1: Write failing test for avatar_url in security-status response
- [ ] Step 2: Run test -- Expected: FAIL
- [ ] Step 3: Add avatar_url field to SecurityStatusResponse schema
- [ ] Step 4: Return user avatar URL from endpoint
- [ ] Step 5: Run test -- Expected: PASS
- [ ] Step 6: Commit

---

### Task 2: OAuth Avatar -- JWT Refresh and Dev Warning

Files: web/src/lib/auth.ts, web/src/components/ui/avatar.tsx, avatar.test.tsx

- [ ] Step 1: In JWT refresh, set oauthAvatarUrl from security.avatar_url when missing
- [ ] Step 2: Add console.warn in avatar onError for dev mode
- [ ] Step 3: Write test for fallback to initials on img error
- [ ] Step 4: Run tests -- Expected: PASS
- [ ] Step 5: Commit

---

### Task 3: Hide Sentiment/Growth Track When Null

Files: factor-signature.tsx, factor-signature.test.tsx (create)

- [ ] Step 1: Write tests -- 3 tracks when 2 null, 5 when all present, inline dots, dynamic height
- [ ] Step 2: Run tests -- Expected: FAIL
- [ ] Step 3: Filter visibleFactors, dynamic height/width, remove null-dot branch
- [ ] Step 4: Run tests -- Expected: PASS
- [ ] Step 5: Regression check dashboard tests
- [ ] Step 6: Commit

---

### Task 4: Score Clipping Fix + Card Enrichment (Hero Card)

Files: pick-hero-card.tsx, format.ts, pick-hero-card.test.tsx

- [ ] Step 1: Add formatRelativeTime to format.ts
- [ ] Step 2: Write tests for MoS, upside, opportunity type, freshness, truncate
- [ ] Step 3: Run tests -- Expected: FAIL
- [ ] Step 4: Add FreshnessIndicator, metadata row, fix spacing mt-4, add truncate
- [ ] Step 5: Run tests -- Expected: PASS
- [ ] Step 6: Commit

---

### Task 5: Card Enrichment (Medium Card) + Score Spacing Fix

Files: pick-medium-card.tsx, pick-medium-card.test.tsx

- [ ] Step 1: Write tests for MoS, opportunity type
- [ ] Step 2: Run tests -- Expected: FAIL
- [ ] Step 3: Add metadata row, fix spacing mb-4
- [ ] Step 4: Run tests -- Expected: PASS
- [ ] Step 5: Commit

---

### Task 6: Minimum Score Floor for Dashboard Picks

Files: dashboard.py, test_dashboard_v4_primary.py

- [ ] Step 1: Write test -- Asset with score 4.5 excluded from picks
- [ ] Step 2: Run test -- Expected: FAIL
- [ ] Step 3: Add MINIMUM_PICK_SCORE = 5.0, filter queries
- [ ] Step 4: Run test -- Expected: PASS
- [ ] Step 5: Full dashboard tests
- [ ] Step 6: Commit

---

### Task 7: OAuth Auth Route Fix

Files: Create set-password/route.ts, remove-password/route.ts. Reference: change-password/route.ts

- [ ] Step 1: Create set-password route -- copy change-password pattern with session auth
- [ ] Step 2: Create remove-password route -- same pattern
- [ ] Step 3: Verify route priority (exact beats catch-all)
- [ ] Step 4: Run existing password-section tests
- [ ] Step 5: Commit

---

### Task 8: Data Seeding (Operational)

- [ ] Step 1: Run backfill-13f CLI
- [ ] Step 2: Verify Smart Money page
- [ ] Step 3: Run run-backtest CLI
- [ ] Step 4: Verify Backtesting page

---

### Task 9: Final Integration Verification

- [ ] Step 1: Full Python test suite
- [ ] Step 2: Full web test suite
- [ ] Step 3: Lint check
- [ ] Step 4: Final commit if needed
