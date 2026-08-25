# Phase 9B: Historical Constituent Data Acquisition Audit

Status: Acquisition design only. No backtest implemented. No production model files modified.

## Executive Conclusion

A defensible point-in-time backtest cannot be built from the current `data/universe.json` or from today's NSE Indices CSVs. Those are current snapshots. The accessible official pages expose current constituent downloads, historical index-level reports, methodology, and exchange archives, but do not expose a public, versioned archive of every historical Nifty 100 and Nifty Midcap 150 constituent snapshot with historical sectors.

The best practical route is:

1. Request an authorized historical constituent/EOD dataset from NSE Indices at `indices@nse.co.in`, or obtain the equivalent from an authorized vendor.
2. Request dated membership, identifiers, effective dates, sector/industry fields, and benchmark TRI data together.
3. If licensing cost is not acceptable, build a smaller research-grade archive manually from official reconstitution notices and retain the source documents and provenance. Do not describe that archive as complete until every review interval reconciles.
4. Do not scrape NSE/NSE Indices pages automatically for a public repository. Public terms prohibit systematic automated collection, and the data may not be redistributable.

## 1. Sources Investigated

| Source | What was verified | Classification | Practical result |
|---|---|---|---|
| NSE Indices Nifty 100 page | Current constituent CSV, factsheet, methodology link, current sector distribution | FREE AND PUBLIC for the displayed/current material | Good for present-day validation; not a dated historical archive |
| NSE Indices Nifty Midcap 150 page | Current constituent CSV, factsheet, methodology link, current sector distribution | FREE AND PUBLIC for the displayed/current material | Good for present-day validation; not a dated historical archive |
| NSE Indices historical-data page | Interactive historical index-data report | FREE BUT MANUAL | Useful for index series; page does not expose a historical constituent-snapshot archive |
| NSE Indices methodology page | Links to common equity-index methodology PDF | FREE AND PUBLIC | Establishes methodology and review rules, not past membership files |
| NSE Indices Data Subscription | Explicitly offers ongoing and historical index/individual-security data and directs users to request EOD constituent data | LICENSED/PAID or UNKNOWN until quoted | Most direct authoritative acquisition route |
| NSE Indices Index Licensing | Describes licensed use of NSE indices and approval/licensing requirements | LICENSED/PAID | Do not publish derived index-data products without permission |
| NSE Indices disclaimer | Says use/distribution of index data and use to create financial products requires a license; warns that product information is not investment advice | LICENSED/PAID | Obtain written permission for repository redistribution and public outputs |
| NSE India terms of use | Prohibits systematic/automated data collection and copying/distribution without permission; has a specific restriction on gaming, virtual trading, or simulation activities | NOT SUITABLE for unattended scraping | Manual inspection does not create redistribution rights |
| NSE India research-data exception | Mentions no-cost research-oriented access under conditions, including qualifying institutions, volume limit, possible NDA, and reporting | FREE BUT MANUAL | Potential route only for eligible accredited research organizations; confirm terms with NSE |
| NSE exchange circular archive | Public dated circulars and downloadable PDF/ZIP documents | FREE BUT MANUAL | Possible evidence for additions/removals; not guaranteed to contain complete constituent lists or sectors |
| NSE historical reports | Public security-wise price/volume, listing, symbol/name-change, and index-history links | FREE AND PUBLIC for listed reports | Useful supporting data and identity mapping; does not establish index membership by itself |
| Yahoo Finance/yfinance | Historical market data and current ticker retrieval | UNKNOWN; NOT SUITABLE as authoritative membership source | May support price research subject to its terms, but cannot establish historical index membership or sector snapshots |
| Unverified GitHub/third-party constituent datasets | May contain convenient historical lists | UNKNOWN | Use only as leads; never as authoritative input without reconciliation and provenance |

Verified official URLs:

- Nifty 100: `https://www.niftyindices.com/indices/equity/broad-based-indices/NIFTY-100`
- Nifty 100 current CSV: `https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv`
- Nifty Midcap 150: `https://www.niftyindices.com/indices/equity/broad-based-indices/NIFTY-MIDCAP-150`
- Nifty Midcap 150 current CSV: `https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv`
- Historical index data: `https://www.niftyindices.com/reports/historical-data`
- Index methodology: `https://www.niftyindices.com/resources/index-methodology`
- Data subscription: `https://www.niftyindices.com/offerings/data-subscription`
- Index licensing: `https://www.niftyindices.com/offerings/index-licensing`
- NSE circulars: `https://www.nseindia.com/resources/exchange-communication-circulars`
- NSE historical reports: `https://www.nseindia.com/resources/historical-reports-capital-market-daily-monthly-archives`
- NSE terms: `https://www.nseindia.com/nse-terms-of-use`
- NSE disclaimer: `https://www.nseindia.com/nse-disclaimer`

## 2. Availability Findings

### Historical CSV/XLS availability

Current CSV downloads are publicly linked for both target indices. No public URL pattern for dated historical Nifty 100 or Midcap 150 constituent CSV/XLS snapshots was verified. Do not guess or generate historical URLs from the current filename pattern.

The historical-data page provides a user-selected historical index report. It is not evidence that historical constituent membership or historical sector data is downloadable through the same interface.

### Reconstructing membership from official documents

Reconstruction is theoretically possible from dated NSE/NSE Indices reconstitution notices, circulars, and archived constituent files if the complete chain can be obtained. It is not automatically complete merely because circulars are public. Each interval needs:

- prior snapshot;
- every addition and deletion;
- effective date;
- corporate-action treatment;
- segment assignment;
- sector/industry at that date;
- reconciliation to the expected 100 and 150 counts.

NSE exchange circulars are a useful manual evidence source, but the page does not demonstrate that all historical index reconstitution notices contain a full constituent list or sector field. Therefore this route is `FREE BUT MANUAL`, with completeness `UNKNOWN` until audited.

### Historical dates and cadence

The official Nifty LargeMidcap 250 page states that it is made from Nifty 100 and Nifty Midcap 150 and that the index is reconstituted semi-annually along with those indices. It also states that the aggregate large-cap and mid-cap weights reset quarterly. The membership snapshot cadence for this project should therefore be semi-annual review-effective dates, not quarterly weight-reset dates.

The accessible pages do not provide a verified complete list of all historical effective dates. Obtain those dates from the licensed delivery or the official notice archive and store the source for every date.

### Historical sector fields

Current Nifty Indices constituent CSVs include an Industry field used by the repository's current universe. The accessible historical interfaces do not establish that historical snapshots include Industry. Historical sector must therefore be delivered with the snapshot or reconstructed from a dated official classification source. Current sector labels must not be copied backward.

## 3. Cost and Licensing

For a public GitHub repository, "downloadable from a public web page" does not mean "redistributable under an open license." The NSE terms and NSE Indices disclaimer impose material constraints:

- NSE terms state that content is owned or licensed, restrict copying/distribution without permission, and prohibit systematic or automated collection.
- NSE terms also state that website content must not be used for virtual trading or simulation activities.
- NSE Indices states that use/distribution of index data and use of index data to create financial products requires a license.
- NSE Indices advertises ongoing and historical data products and provides a contact for EOD constituent data.
- NSE's research-oriented no-cost route is conditional and restricted to accredited academic institutions, recognized research organizations, and think tanks, with possible NDA and reporting obligations.

Recommended repository policy:

- Do not commit licensed historical files or scraped NSE pages unless written redistribution permission explicitly allows it.
- Commit only schema documentation, checksums, source references, and loader code that expects user-supplied licensed/private files.
- If permission covers derived outputs but not raw data, publish only permitted aggregates and retain raw snapshots outside GitHub.
- Obtain legal/licensing confirmation before calling a public backtest "official".

## 4. Recommended Acquisition Approach

### Preferred: authorized historical delivery

Request from NSE Indices:

- Nifty 100 historical constituent snapshots;
- Nifty Midcap 150 historical constituent snapshots;
- effective dates and publication/effective timestamps;
- stable identifiers such as ISIN, plus historical and current symbols;
- historical Industry/sector field and classification version;
- index review and corporate-action files;
- Nifty 100, Nifty Midcap 150, and Nifty LargeMidcap 250 TRI histories;
- written terms covering internal research, GitHub publication, derived results, and redistribution.

This is the most complete and least ambiguous route. It is likely licensed/paid unless the project qualifies for the research-data exception.

### Fallback: manually curated research archive

Use official dated circulars/notices and manually capture one snapshot for each semi-annual effective date. Preserve the original PDF/URL, retrieval date, hash, extraction notes, reviewer, and reconciliation result. This is practical for a short pilot, but not for claiming a long complete history until coverage is proven.

### Not recommended

Do not infer historical membership by taking today's 250 stocks and looking backward. Do not use Wikipedia, GitHub, screeners, or current CSVs as a substitute for point-in-time membership. Do not automatically scrape NSE pages for a scheduled data pipeline under the current public terms.

## 5. Recommended Historical Period

For meaningful validation, target at least 5 years of completed observations after the data is acquired, preferably 7 to 10 years. Because the model requires a 12-month return, 200-day moving average, and 6-month forward evaluation, the raw market-data window must begin at least 14 months before the first evaluation date and extend 6 months beyond the final evaluation date.

A defensible minimum pilot is:

- 3 years of semi-annual snapshots and forward outcomes for pipeline validation;
- 5 years minimum for a first research conclusion;
- 7 to 10 years preferred for regime and turnover diversity.

The start date must be bounded by the earliest complete historical membership, sector, identifier, benchmark, and price data, not by the age of the current universe.

## 6. Recommended Evaluation Dates and Snapshot Count

Use the first tradable session on or after each semi-annual membership effective date. This matches the index review cadence and reduces artificial monthly turnover. A monthly sensitivity can be added later by carrying forward the latest effective snapshot, but it should not be the first implementation.

Snapshot count is data-dependent. For a five-year study with two reviews per year, plan for approximately 10 snapshots per segment, plus the initial snapshot required to start the chain. For seven years, plan for approximately 14 per segment; for ten years, approximately 20 per segment. The exact count must be the number of verified effective dates in the acquired archive, not a guessed fixed number.

Every snapshot must reconcile to 100 Nifty 100 rows and 150 Midcap 150 rows, allowing only documented exceptional effective-date handling.

## 7. Required Data Schema

Minimum requested schema:

```json
{
  "date": "YYYY-MM-DD",
  "symbol": "RELIANCE",
  "segment": "NIFTY100",
  "sector": "Energy"
}
```

For a usable bias-controlled archive, extend each row with provenance and identity fields:

```json
{
  "effective_date": "YYYY-MM-DD",
  "published_at": "YYYY-MM-DDTHH:MM:SS+05:30",
  "symbol": "RELIANCE",
  "yahoo_symbol": "RELIANCE.NS",
  "security_id": "ISIN-or-authoritative-ID",
  "company_name": "Reliance Industries Limited",
  "segment": "NIFTY100",
  "sector": "Energy",
  "classification_scheme": "NSE Industry Classification",
  "source_url": "https://...",
  "source_sha256": "...",
  "snapshot_id": "nifty100-YYYY-MM-DD"
}
```

Use one immutable snapshot file per effective date, plus a manifest containing source, hash, row counts, validation status, and licensing status. Do not overwrite old snapshots when a current constituent list changes.

## 8. Point-in-Time Identity Rules

### Membership

At evaluation date `T`, load only the snapshot whose effective date is known by `T`. A member enters the eligible universe on its documented effective date, not when it first appears in today's file.

### Renamed companies

Represent the company/security with a stable identifier where available. Keep a dated alias table mapping old symbol, new symbol, company name, effective date, and source. Use the symbol that was observable at `T` for the historical data request, while using the stable identifier for joins. Never treat a rename as a new economic security without evidence.

### Mergers

Keep the predecessor in snapshots until the documented end date. Record the successor and corporate-action event separately. Do not splice predecessor and successor prices into a synthetic history unless the data vendor provides an explicitly adjusted series and the methodology permits it. A holding whose identity ends before the forward horizon has an unavailable remainder, not a fabricated return.

### Delisted stocks

Retain delisted members for dates on which they were valid constituents. Use only their observable prices up to delisting. A post-delisting forward horizon is `UNAVAILABLE`; do not drop the stock from the historical universe and do not replace its return with zero.

### Newly listed stocks

Include a newly listed security only from its actual listing and index-effective dates. If it lacks the full frozen model history at `T`, retain it in the snapshot but mark it `INSUFFICIENT_HISTORY` and exclude it from scoring for that date.

## 9. Monthly Versus Rebalance-Date Backtest

Rebalance-date evaluation is recommended first because it follows the documented semi-annual constituent process, reduces data volume, and makes membership provenance auditable. It will yield fewer observations, so confidence intervals and observation counts must be reported.

Monthly evaluation is practical only after a complete snapshot chain exists. It requires a rule for carrying membership and sectors between review dates and measures a more frequent strategy than the index's membership process. It should be a separately labeled sensitivity, not silently mixed into the primary result.

## 10. Alternative Sources

| Alternative | Classification | Use |
|---|---|---|
| Authorized NSE Indices vendor delivery | LICENSED/PAID | Preferred complete solution |
| Bloomberg, FactSet, LSEG/Refinitiv, MSCI, Rimes | LICENSED/PAID | Possible historical index constituents and identifiers; verify exact Nifty coverage and redistribution rights |
| NSE research-data access | FREE BUT MANUAL | Only if the project/institution qualifies and accepts conditions |
| NSE circulars and notices | FREE BUT MANUAL | Manual reconstruction and audit evidence |
| NSE public historical reports | FREE AND PUBLIC | Prices, listings, symbol/name changes, and index series support; not sufficient membership alone |
| Yahoo Finance/yfinance | UNKNOWN | Price research only; not point-in-time membership or authoritative sectors |
| GitHub/community datasets | UNKNOWN / NOT SUITABLE as authority | Discovery and cross-check only |
| Current NSE Indices CSVs | FREE AND PUBLIC | Current snapshot only |

## 11. Acquisition Acceptance Tests

Before implementing any backtest, the acquired archive must pass:

- every snapshot has an effective date and immutable source reference;
- exactly 100 Nifty 100 and 150 Midcap 150 rows per expected snapshot;
- no duplicate stable security IDs within a segment/date;
- segment membership is point-in-time, not today's membership;
- sector field exists or is explicitly marked unavailable for each row;
- all additions/removals reconcile to the preceding snapshot or documented corporate action;
- rename and merger mappings are separately versioned;
- source checksums and licensing terms are recorded;
- benchmark history covers every evaluation date and forward horizon;
- price history covers each member's required pre-date lookback and post-date horizon;
- the earliest and latest dates are not included unless the full required window exists.

## 12. Major Limitations

1. A public web link is not an open redistribution license.
2. Current constituent CSVs cannot establish historical membership.
3. The public historical-data interface exposes index history, not a verified complete constituent archive.
4. Circular-based reconstruction may omit full lists, sectors, timestamps, or corporate actions.
5. Historical sectors can change classification independently of membership.
6. Yahoo symbols are not stable security identities across renames and corporate actions.
7. Delisted and merged securities require a survivorship-aware vendor and careful treatment.
8. NSE's public terms restrict automated collection and simulation use.
9. A five-year study requires roughly 10 verified semi-annual snapshots per segment; more years require proportionally more snapshots.
10. Short-history listings reduce the eligible cross-section at individual dates.
11. Price-return versus total-return benchmark choice can materially change excess-return conclusions.
12. Without written licensing confirmation, raw official files should remain outside a public GitHub repository.

## 13. Phase 9B Recommendation

Acquire a quoted historical constituent and benchmark package from NSE Indices or an authorized vendor. Request a five-year minimum archive first, with a seven-to-ten-year extension if affordable. Use semi-annual review-effective dates, approximately 10 snapshots per segment for the five-year minimum, and the extended schema with stable identifiers and provenance.

If no licensed acquisition is feasible, create a manually curated three-year pilot from official notices, label it research-grade and incomplete until reconciled, and keep all raw source documents outside the public repository. Do not implement the backtest until the archive acceptance tests pass.

No production model files were modified, and no backtest was implemented in Phase 9B.
