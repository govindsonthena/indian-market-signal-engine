# Indian Market Signal Engine

A free, serverless web application that analyzes the current constituents of Nifty 100 and Nifty Midcap 150 to generate ranked market candidates using quantitative technical analysis.

## Overview

The application analyzes the Nifty LargeMidcap 250 universe (Nifty 100 + Nifty Midcap 150) and generates:
- Up to 5 strong candidates from Nifty 100
- Up to 5 strong candidates from Nifty Midcap 150
- Maximum 10 total candidates (fewer if insufficient quality)

## Architecture

**Serverless Design:**
- GitHub Pages for frontend
- GitHub Actions for scheduled data processing
- Python for data analysis
- Yahoo Finance via yfinance for market data
- Static JSON for data exchange

## Technology Stack

- Python 3.x with pandas, numpy, yfinance
- HTML5, CSS3, Vanilla JavaScript
- No frameworks, databases, or servers required

## Project Structure

```
indian-market-signal-engine/
├── index.html
├── style.css
├── app.js
├── README.md
├── requirements.txt
├── data/
│   ├── latest.json
│   ├── universe.json
│   └── backtest/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── universe.py
│   ├── market_data.py
│   ├── indicators.py
│   ├── scoring.py
│   ├── market_regime.py
│   ├── selection.py
│   ├── generate_report.py
│   └── main.py
├── tests/
│   ├── test_indicators.py
│   ├── test_scoring.py
│   ├── test_selection.py
│   └── test_market_regime.py
└── .github/
    └── workflows/
        ├── daily_analysis.yml
        └── backtest.yml
```

## Development Phases

1. **Phase 1**: Project skeleton (requirements, config, basic tests)
2. **Phase 2**: Universe definition (Nifty 100 + Midcap 150)
3. **Phase 3**: Yahoo Finance data validation
4. **Phase 4**: Technical indicators
5. **Phase 5**: Scoring engine
6. **Phase 6**: Stock selection logic
7. **Phase 7**: Backtesting framework
8. **Phase 8**: Frontend UI
9. **Phase 9**: GitHub Actions automation
10. **Phase 10**: End-to-end testing

## Scoring Model (Version 1)

| Factor | Weight | Description |
|--------|--------|-------------|
| Momentum | 20 | 1m, 3m, 6m, 12m returns |
| Trend | 20 | Price vs DMAs, MA direction |
| Relative Strength | 15 | Stock vs benchmark performance |
| Volume | 10 | Volume confirmation |
| RSI | 10 | 14-period RSI momentum |
| 52-Week Strength | 10 | Distance from 52-week high |
| Risk | 15 | Volatility & drawdown penalty |

## Key Principles

- Cross-sectional ranking (stocks ranked against each other)
- Separate Nifty 100 and Midcap 150 selection (max 5 each)
- Configurable minimum quality threshold
- Maximum 2 stocks per sector
- Deterministic, reproducible scoring
- No hard-coded thresholds; all configurable
- Clear data timestamps and freshness indicators
- Resilient error handling

## Disclaimers

This application provides quantitative market signals for research and educational purposes only. It is **not** financial advice, a guarantee of returns, or a recommendation to buy or sell securities. Verify information independently before making investment decisions.

## Getting Started (Development)

```bash
pip install -r requirements.txt
python src/main.py
```

## Limitations

- End-of-day analysis only (not real-time)
- Yahoo Finance data source (initial implementation)
- Backtesting required before production use
- No guaranteed returns or predictions

---

*Last Updated: 2026-08-22*
