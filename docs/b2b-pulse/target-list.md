# Target List: First 100 Outreach Prospects

Build two lists of 50 each: RIAs under $1B AUM and fintech/newsletter operators who would embed scoring data.

---

## List 1: 50 RIAs Under $1B AUM

### Primary Source: SEC IAPD / Form ADV

**Database**: https://adviserinfo.sec.gov/IAPD

The Investment Adviser Public Disclosure (IAPD) database is the authoritative source. Every SEC-registered RIA files Form ADV, which is fully searchable.

#### Search & Filter Criteria

1. **AUM Range**: $50M -- $1B. Below $50M is likely too small to pay $500/mo for data infrastructure. Above $1B typically has in-house quant teams.

2. **ADV Part 2A (Brochure) Text Signals** -- Download brochures and search for:
   - "quantitative" or "systematic" (indicates rules-based process, natural API consumer)
   - "factor" or "factor-based" (direct alignment with our scoring model)
   - "third-party data" or "external data" (already buying vendor feeds)
   - "compliance" + "reproducibility" or "audit trail" (pain point awareness)
   - "technology" or "proprietary software" (tech-forward firm)

3. **ADV Part 1A Item 5 -- Compensation**: Filter for firms charging asset-based fees (not commission-based). Fee-only RIAs are more likely to invest in analytical infrastructure.

4. **ADV Part 1A Item 6 -- Other Business Activities**: Exclude firms primarily in insurance or real estate. Target firms listing "financial planning" + "portfolio management."

5. **Number of Employees**: 5--50. Large enough to have a technology budget, small enough that a $500/mo API is material to their workflow.

#### How to Execute the Search

```
1. Go to https://adviserinfo.sec.gov/IAPD
2. Click "Investment Adviser Search" > "Firm"
3. Use Advanced Search:
   - State: Start with CA, NY, TX, MA, IL (highest density of tech-forward RIAs)
   - Leave firm name blank for broad results
4. Export results to CSV
5. For each firm, download the ADV Part 2A brochure (PDF)
6. Run keyword search across brochures for the signals above
7. Cross-reference AUM from ADV Part 1A Item 5.F
```

**Supplemental EDGAR full-text search** (for ADV brochure text mining at scale):
```
https://efts.sec.gov/LATEST/search-index?q=%22quantitative%22+%22factor-based%22&dateRange=custom&startdt=2025-01-01&forms=ADV
```

#### Geographic Targeting Strategy

**Tier 1 (start here)**: San Francisco Bay Area, New York Metro, Boston, Austin, Chicago. Highest concentration of tech-forward RIAs with existing API infrastructure.

**Tier 2**: Denver, Seattle, Miami, Nashville. Growing fintech/RIA hubs with less vendor saturation.

**Tier 3**: All other states. Lower density but less competition for attention.

Rationale: Tech-forward firms are more likely to have engineering staff who can integrate an API. Starting in Tier 1 maximizes the probability of finding firms that already consume data feeds programmatically.

#### Qualification Signals (Post-Search)

After building the initial list from IAPD, qualify each prospect:

- **Website check**: Does the firm's website mention technology, systematic investing, or data-driven approaches? If the website looks like a 2008 WordPress template, deprioritize.
- **LinkedIn company page**: Does the firm employ software engineers or data analysts? If yes, high priority.
- **13F filing**: Does the firm file 13F-HR? (Indicates $100M+ in equities under management.) If yes, they are already in the institutional reporting regime and care about data provenance.
- **CRD number lookup**: Cross-reference with FINRA BrokerCheck for any compliance history that might indicate heightened regulatory sensitivity (a feature, not a bug -- these firms are the most motivated buyers).

---

### Secondary Source: LinkedIn Sales Navigator

#### Search Queries

**Query 1 -- Decision Makers at Quantitative RIAs**:
```
Title: ("Chief Investment Officer" OR "CIO" OR "Head of Research" OR "Portfolio Manager" OR "Director of Technology")
Company headcount: 11-50
Industry: "Investment Management" OR "Financial Services"
Keywords: "quantitative" OR "systematic" OR "factor investing" OR "data-driven"
Geography: United States
```

**Query 2 -- Operations/Compliance Leads (secondary contact)**:
```
Title: ("Chief Compliance Officer" OR "CCO" OR "Head of Operations" OR "COO")
Company headcount: 11-50
Industry: "Investment Management"
Keywords: "RIA" OR "registered investment adviser"
Geography: United States
```

**Query 3 -- Tech Leads at RIAs**:
```
Title: ("CTO" OR "VP Engineering" OR "Lead Developer" OR "Head of Technology")
Company headcount: 11-50
Industry: "Investment Management" OR "Financial Services"
Keywords: "API" OR "Python" OR "data pipeline" OR "quant"
Geography: United States
```

#### LinkedIn Filtering Tips

- Use the "Posted on LinkedIn" filter to find recently active prospects (higher reply rate).
- Use "Changed jobs" filter (last 90 days) to catch new CIOs/CTOs who are evaluating vendor stack.
- Save searches as Lead Lists for drip tracking.

---

## List 2: 50 Fintech Operators & Newsletter Operators

### Source 1: Fintech Directories

**Crunchbase**:
```
Search: Category = "Financial Services" OR "WealthTech" OR "Investment Management"
Filters:
  - Funding Stage: Seed, Series A, Series B (too early = no budget; too late = built in-house)
  - Founded: 2020-2025 (modern stack, more likely to consume APIs)
  - Headcount: 5-100
  - Description keywords: "portfolio", "scoring", "analytics", "investment research"
```

**Product Hunt / BetaList**:
```
Search: "investment" OR "stock analysis" OR "portfolio" OR "fintech"
Filter: Launched in last 24 months
Look for: Tools that display stock ratings, screeners, or portfolio analytics
Signal: If they show scores/ratings without citing methodology, they need a deterministic engine
```

**AngelList (Wellfound)**:
```
Markets: "Finance" > "WealthTech" or "Quantitative Finance"
Stage: Seed to Series B
Filter by: "Hiring engineers" (signal of active product development)
```

**Y Combinator Directory** (ycombinator.com/companies):
```
Industry: "Fintech"
Sub-tags: "Asset Management", "Investing", "Financial Services"
Batch: W23 through current
```

### Source 2: Newsletter Aggregators & Investment Media

**Substack**:
```
Browse: Finance > Investing
Sort by: Paid subscribers (where visible) or engagement
Criteria:
  - Publishes stock picks, sector analysis, or portfolio recommendations
  - References data sources (shows sophistication; crude opinion blogs are not targets)
  - Has >1,000 subscribers (enough scale to justify $500/mo for data)
  - Charges for premium tier (demonstrates willingness to invest in content quality)
```

**Beehiiv Directory** (beehiiv.com/explore):
```
Category: Finance & Business
Filter: Newsletters with >5,000 subscribers
Signal: Mentions "data-driven" or "quantitative" in description
```

**SparkLoop / Letterhead Marketplace**:
```
Search for investment/finance newsletters
Focus on newsletters that cross-promote (indicates business sophistication)
```

**ConvertKit Creator Directory**:
```
Category: Finance
Look for creators selling premium data products or research services
```

### Source 3: Twitter/X Financial Community

Search queries to identify operators who publish investment analysis:

```
"stock screener" + "building" (building their own tooling -- prime API customer)
"factor investing" + "newsletter"
"quant" + "side project" OR "shipping"
"investment API" + "looking for"
```

Use Followerwonk or SparkToro to find accounts with 1K-50K followers in the investing niche. Accounts in this range are large enough to monetize but not so large that they have in-house data teams.

### Qualification Criteria for Fintech/Newsletter Operators

| Signal | Weight | Why |
|---|---|---|
| Charges for premium content/tier | High | Demonstrates revenue; can justify $500/mo |
| References specific data sources | High | Already consumes third-party data |
| Publishes stock picks or ratings | High | Direct use case for scoring API |
| Has engineering team or API docs | High | Can integrate programmatically |
| Mentions compliance or methodology | Medium | Cares about defensibility |
| >5,000 subscribers/users | Medium | Scale justifies cost |
| Mentions building own screener | Very High | Actively looking for what we sell |

---

## Outreach Sequencing

### Batch 1 (Week 1): 20 prospects
- 10 RIAs from Tier 1 geographies with strongest ADV keyword matches
- 10 fintech operators with highest qualification signal density

### Batch 2 (Week 2): 30 prospects
- 15 RIAs (mix of Tier 1 and Tier 2)
- 15 fintech/newsletter operators

### Batch 3 (Week 3): 50 prospects
- Remaining 25 RIAs
- Remaining 25 fintech/newsletter operators

Stagger sends to avoid spam filter clustering. Personalize the first line of each email with a specific reference to the prospect's ADV brochure language, published methodology, or recent content.

---

## Tools for List Building

| Tool | Purpose | Cost |
|---|---|---|
| SEC IAPD | Authoritative RIA search | Free |
| EDGAR Full-Text Search | ADV brochure keyword mining | Free |
| LinkedIn Sales Navigator | Decision-maker identification | ~$100/mo |
| Crunchbase Pro | Fintech startup filtering | ~$49/mo |
| Apollo.io or Hunter.io | Email discovery and verification | ~$49/mo |
| SparkToro | Audience intelligence for newsletter operators | ~$50/mo |

**Do not purchase contact lists.** Build from authoritative sources (SEC filings, LinkedIn, public directories) to ensure accuracy and avoid CAN-SPAM issues with purchased data.
