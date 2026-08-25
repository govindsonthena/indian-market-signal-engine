# Phase 9A: Backtesting Design and Historical Universe Audit

Status: Design only. No backtest is implemented in this phase.

## 1. Scope and Frozen Model

The Phase 4 indicators, Phase 5 scoring, Phase 6 market regime, and Phase 6 selection rules are treated as immutable. The backtest must call those existing functions rather than duplicate or modify their formulas.

Current production universe is 100 Nifty 100 constituents plus 150 Nifty Midcap 150 constituents. The current 250-stock file is a present-day snapshot and must not be reused as the historical universe for earlier dates.

## 2. Historical Universe Availability

### Verified authoritative sources

NSE Indices pages provide:

- Current Nifty 100 constituent CSV: `https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv`
- Current Nifty Midcap 150 constituent CSV: `https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv`
- Current Nifty LargeMidcap 250 constituent CSV: `https://www.niftyindices.com/IndexConstituent/ind_niftylargemidcap250list.csv`
- Historical index-level report interface: `https://www.niftyindices.com/reports/historical-data`
- Index methodology page: `https://www.niftyindices.com/resources/index-methodology`

The index pages expose current constituents, company/industry fields, factsheets, and methodology links. The historical-data page provides historical index data selection, not a public dated constituent-snapshot archive.

### Rebalance facts

The Nifty LargeMidcap 250 page states that it is composed of Nifty 100 and Nifty Midcap 150, with large-cap and mid-cap aggregate weights reset quarterly. It also states that the index is reconstituted semi-annually along with Nifty 100 and Nifty Midcap 150.

Therefore:

- Membership changes should be modeled at the semi-annual index review dates.
- Weight-reset dates and membership review dates are separate concepts.
- A stock is eligible only after it is known to be in the constituent snapshot effective on that date.

### Availability conclusion

No public, versioned historical constituent files for every required review date were identified from the accessible NSE Indices pages. The current CSVs cannot establish past membership. A valid backtest therefore needs one of:

1. Official archived constituent CSVs captured at each review date.
2. A licensed historical constituent/index dataset from NSE Indices or an authorized vendor.
3. A carefully documented reconstruction from dated official notices, with each inclusion, exclusion, effective date, sector, and corporate action independently recorded.

If those snapshots are unavailable, the implementation must stop with `HISTORICAL_UNIVERSE_UNAVAILABLE`; it must not substitute the current 250 stocks.

Historical sector fields should come from the corresponding historical constituent snapshot or historical official industry classification. Current sectors must not be backfilled into prior periods without an explicit, documented assumption.

## 3. Recommended Evaluation Dates

Use semi-annual review-effective dates as the primary evaluation schedule, with the first tradable session after the published effective date as the selection date. This aligns membership with the official index process and avoids pretending that an intra-period current list was known historically.

A monthly schedule is useful as a secondary robustness analysis, but only if historical membership is carried forward from the most recent effective snapshot and the model is explicitly re-run monthly. Monthly dates increase turnover and make the membership/sector timestamp problem harder to audit.

Recommended initial schedule:

- Every review-effective date available in the historical constituent archive.
- Exclude a date unless both the constituent snapshot and sufficient pre-date market history are present.
- Exclude the final dates whose full six-month forward window is not yet observable.

## 4. Look-Ahead Prevention

For evaluation date `T`:

- Use only OHLCV observations with trading date `<= T`.
- Use the constituent and sector snapshot effective and publicly available by `T`.
- Calculate all indicators from the truncated series ending at `T`.
- Calculate benchmark returns and cross-sectional percentiles using only stocks eligible at `T`.
- Run regime and selection using only those values.
- Record the recommendation after the close of `T`, or execute at the next session open in a later implementation.
- Use prices after `T` only for forward-return measurement.

Never use the final production universe, future sector labels, future prices, future benchmark values, or the full-period cross-sectional ranking when calculating a historical score.

A validation helper should assert that every input row used for scoring has `date <= T` and that no forward-price column is present in the scoring frame.

## 5. Forward Returns

Use adjusted-close total-return series where the data vendor provides a reliable adjusted series. If only raw prices are used, the report must state that dividends, splits, and other distributions are excluded.

Baseline definitions:

- 1-month return: price on the first eligible trading day at or after the one-calendar-month anniversary of `T`, divided by the entry price after `T`, minus 1.
- 3-month return: same rule at the three-calendar-month anniversary.
- 6-month return: same rule at the six-calendar-month anniversary.

The entry price should be the next tradable session after `T`, because a recommendation generated after the close cannot be executed at the closing price without an explicit same-close assumption. A simpler alternative is next-session close-to-close; whichever convention is implemented must be fixed before results are generated.

If the anniversary falls on a holiday or weekend, use the next available trading session. Do not silently use a price before the target date. If no future price exists, return `null` and classify the horizon as unavailable.

## 6. New Listings, Delistings, and Corporate Actions

- Newly listed stock: include only if it was a historical constituent at `T`; score only when all frozen model indicators are calculable. Otherwise mark `INSUFFICIENT_HISTORY` and exclude from that date's score.
- Insufficient history: retain in the historical universe snapshot, mark ineligible, and do not impute values.
- Delisted stock: retain it in snapshots before delisting; use its last observable valid price only for horizons that end on or before delisting. Later horizons are `UNAVAILABLE`, not zero.
- Merger: preserve the original security through the last valid observation and record the corporate-action event. Do not fabricate a continuous price series across a merger.
- Renamed symbol: use a stable security identifier where possible and maintain a dated symbol alias map. Yahoo ticker text alone is not a stable identity.
- Missing future prices: mark the affected horizon unavailable and exclude it from that horizon's aggregate statistics, while reporting the missing count.

## 7. Benchmark Methodology

Use official total-return index series where available, with the same entry and horizon convention as stocks.

Recommended comparisons:

- Nifty 100 selection: Nifty 100 TRI.
- Midcap 150 selection: Nifty Midcap 150 TRI.
- Combined 10-stock portfolio: Nifty LargeMidcap 250 TRI, because it represents the combined 100/150 universe and its stated construction resets aggregate large/mid weights to 50/50 quarterly.

Also report the alternate segment benchmark for transparency when a portfolio contains both segments. Benchmark selection must be based on the segment at `T`, not today's segment label.

If only price-return index data is available, label results `price return` and do not call them total returns.

## 8. Portfolio Construction

At each evaluation date:

- Use the exact existing selection output.
- Hold selected stocks with equal weights at the evaluation date.
- Ten stocks means 10% each.
- Fewer than ten means equal weight across the stocks actually selected.
- Zero selected stocks produces a zero-stock portfolio observation, not a forced position.
- Do not add replacements after selection because of a later missing price.

For a missing holding at a horizon, report both the observed holding coverage and the portfolio return convention. The preferred baseline is renormalization only among holdings with an observable exit price, with a separate `coverage` field. A stricter sensitivity should retain missing holdings at zero return; neither approach may invent a price.

## 9. Transaction Assumptions

First implementation baseline:

- No transaction costs.
- No slippage.
- No taxes or brokerage.
- No market-impact model.
- Entry at the next available trading session after `T`.
- Equal-weight rebalance at every evaluation date.

This is a transparent gross-return baseline, not an executable trading result. A later sensitivity can apply explicit round-trip costs and slippage, but those parameters must be fixed before comparison and must not be optimized on the result.

## 10. Performance Metrics

### Security-level

For each selected stock and horizon report:

- Forward return.
- Matching benchmark return.
- Excess return.
- Positive-return hit flag.
- Observable-return flag and missing reason.

Aggregate by horizon:

- Number of observations.
- Average return.
- Median return.
- Hit rate.
- Maximum drawdown.
- Volatility.
- Win/loss ratio, defined as mean positive return divided by the absolute mean negative return; report `null` when either side is absent.

### Portfolio-level

For the equal-weight portfolio report:

- 1M, 3M, and 6M returns.
- Matching benchmark return and excess return.
- Cumulative return and CAGR only when the test span and compounding convention support it.
- Annualized volatility.
- Sharpe ratio using a fixed documented risk-free assumption, initially 0% if no historical risk-free series is supplied.
- Maximum drawdown.
- Hit rate and win/loss ratio.
- Number of rebalances, turnover proxy, and missing-price coverage.

Drawdown must be calculated on the chronological portfolio equity curve, not from independent horizon observations.

## 11. Data Leakage and Bias Audit

Potential leakage points and safeguards:

| Area | Risk | Safeguard |
|---|---|---|
| Membership | Today's constituents used historically | Load dated constituent snapshots effective by `T` |
| Sector | Current sector labels applied to past dates | Store dated sector fields with each snapshot |
| Indicators | Full-series rolling values leak future data | Truncate OHLCV at `T` before calling indicators |
| Scoring | Percentiles computed using future or ineligible stocks | Rank only the eligible cross-section at `T` |
| Benchmark | Benchmark period extends after `T` | Compute benchmark history and returns as-of `T` |
| Selection | Future membership or prices affect ranking | Pass only as-of-`T` scored rows to selector |
| Forward return | Entry price taken from `T` or before `T` inconsistently | Define next-session entry and post-`T` exit dates |
| Corporate actions | Future-adjusted history changes past information | Use vendor-consistent adjusted series and document it |
| Missing data | Missing outcomes treated as zero or success | Preserve nulls and report availability counts |
| Symbols | Renames treated as new companies or collisions | Use stable IDs and dated alias mapping |
| Ties | Unstable ordering changes selections | Use deterministic secondary key, e.g. stable symbol ID |

Each evaluation record should contain an audit block with cutoff date, constituent snapshot ID, maximum market-data date used, benchmark source, and data-quality exclusions.

## 12. Recommended Architecture

```text
Historical constituent snapshots
        |
        v
Evaluation date T and effective snapshot
        |
        v
Historical OHLCV truncated to T
        |
        v
Data validation and eligibility audit
        |
        v
Phase 4 indicators (unchanged)
        |
        v
As-of-T benchmark and Phase 5 scores (unchanged)
        |
        v
Phase 6 market regime and selection (unchanged)
        |
        v
Selected equal-weight portfolio
        |
        +--> Future prices strictly after T
        |        |
        |        v
        |    1M / 3M / 6M returns
        |
        +--> Official benchmark future returns
                 |
                 v
            Excess returns and aggregate metrics
```

Suggested future modules, without changing current production modules:

- `src/backtest/models.py`: dated constituent, evaluation, holding, and result records.
- `src/backtest/universe.py`: load and validate historical snapshots.
- `src/backtest/data.py`: cache OHLCV and benchmark data; enforce cutoff dates.
- `src/backtest/evaluator.py`: run one evaluation date using existing indicators, scoring, regime, and selection.
- `src/backtest/returns.py`: calculate post-date horizon returns and availability.
- `src/backtest/metrics.py`: aggregate security and portfolio metrics.
- `src/backtest/report.py`: write deterministic JSON/CSV artifacts.
- `data/historical_universe/`: immutable dated snapshots plus source metadata and checksums.

The first implementation should use dependency injection for data providers so all unit tests use synthetic data and no test calls Yahoo Finance.

## 13. Risks and Limitations

1. Public current constituent CSVs do not prove historical membership.
2. Historical sector classification may not be available at the required granularity.
3. Yahoo history may contain ticker changes, survivorship, gaps, and corporate-action artifacts.
4. A two-year history is inadequate for a long multi-year study and excludes newer listings by design.
5. Semi-annual snapshots create a smaller sample than monthly evaluations.
6. Next-session execution and calendar-to-trading-day mapping affect measured returns.
7. Equal-weight returns ignore liquidity, turnover, market impact, taxes, and slippage.
8. A 10-stock portfolio selected from a 250-stock universe can have substantial concentration.
9. Historical index benchmark data may be price return rather than total return unless the TRI series is obtained.
10. Results with incomplete forward horizons can be biased if availability is not reported by date and stock.

## 14. Recommended Next Steps

1. Obtain archived/licensed historical Nifty 100 and Midcap 150 constituent snapshots, including effective dates and sectors.
2. Define a stable security identifier and symbol-alias/corporate-action mapping.
3. Acquire point-in-time adjusted OHLCV for all historical members and official TRI benchmark data.
4. Freeze the evaluation-date and next-session execution conventions in configuration.
5. Implement snapshot validation and leakage assertions before implementing the evaluator.
6. Implement one-date evaluation with synthetic fixtures and compare calls to the frozen production modules.
7. Add deterministic tests for cutoff enforcement, membership changes, new listings, delistings, missing exits, forward horizons, and factor-score preservation.
8. Run a small historical pilot only after the data audit passes; then expand to the full available date range.

## 15. Phase 9A Decision

The backtest is not ready to run from the current repository data alone. The model architecture is ready to reuse, but a defensible historical result depends first on point-in-time constituent snapshots, dated sector data, and survivorship-aware security history. The next phase should acquire and validate those inputs before any performance number is generated.
