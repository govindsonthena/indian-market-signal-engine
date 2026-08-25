"""Run Phase 5 scoring against the 20-stock development universe."""

import sys

import pandas as pd
import yfinance as yf

from src.config import SCORE_WEIGHT_TOLERANCE
from src.indicators import calculate_all_indicators, validate_data
from src.scoring import score_universe
from src.universe import UniverseManager


VALIDATED_SYMBOLS = [
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'WIPRO.NS',
    'MARUTI.NS', 'BHARTIARTL.NS', 'LT.NS', 'ICICIBANK.NS', 'SBIN.NS',
    'CIPLA.NS', 'ICICIPRULI.NS', 'IRCTC.NS', 'GAIL.NS', 'TITAN.NS', 'DABUR.NS',
]

UNAVAILABLE_SYMBOLS = ['BATADRY.NS', 'POWERLD.NS', 'ZOMATO.NS', 'SECTORALBANKS.NS']


def main() -> int:
    manager = UniverseManager()
    records = {}
    segments = {}
    names = {}
    sectors = {}

    for symbol in VALIDATED_SYMBOLS:
        data = yf.download(symbol, period='3y', progress=False)
        if data is None or data.empty:
            print(f"ERROR: previously validated symbol returned no data: {symbol}")
            continue
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = [column[0] for column in data.columns]
        data = data.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        valid, issues = validate_data(data, min_rows=200)
        if not valid:
            print(f"Skipping {symbol}: {issues}")
            continue
        indicators = calculate_all_indicators(data)
        indicators['current_price'] = float(data['Close'].iloc[-1])
        records[symbol] = indicators
        info = manager.get_stock_info(symbol) or {}
        segments[symbol] = info.get('segment', 'UNKNOWN')
        names[symbol] = info.get('name', 'UNKNOWN')
        sectors[symbol] = info.get('sector', 'UNKNOWN')

    if len(records) != len(VALIDATED_SYMBOLS):
        print(f"ERROR: expected {len(VALIDATED_SYMBOLS)} valid records, got {len(records)}")
        return 1

    # The benchmark is supplied by this caller, using the eligible sample universe.
    benchmark_returns = {
        period: sum(values[f'return_{period}'] for values in records.values()
                    if pd.notna(values.get(f'return_{period}'))) / sum(
                        pd.notna(values.get(f'return_{period}')) for values in records.values())
        for period in ('3m', '6m', '12m')
    }
    results = score_universe(records, benchmark_returns)
    validation_failures = []
    for result in results.values():
        factor_total = sum(result['factor_scores'].values())
        result['score_valid'] = (
            result['score_status'] == 'OK'
            and 0 <= result['overall_score'] <= 100
            and abs(result['overall_score'] - factor_total) <= SCORE_WEIGHT_TOLERANCE
        )
        if not result['score_valid']:
            validation_failures.append(result['symbol'])
    ranked = sorted(
        list(results.values()),
        key=lambda result: result['overall_score'] if result['score_status'] == 'OK' else float('-inf'),
        reverse=True,
    )

    print('\nPhase 5 sample-universe scores')
    print('Benchmark returns:', ', '.join(f'{key}={value:.4f}' for key, value in benchmark_returns.items()))
    print('-' * 145)
    print(f"{'Rank':<5} {'Ticker':<16} {'Name':<34} {'Segment':<12} {'Sector':<22} {'Overall':>8} {'Momentum':>9} {'Trend':>8} {'Rel.Str.':>9} {'Volume':>8} {'RSI':>7} {'52W':>8} {'Risk':>7} {'Status':<8}")
    print('-' * 145)
    for rank, result in enumerate(ranked, 1):
        scores = result['factor_scores']
        formatted = [f"{scores[name]:.2f}" if pd.notna(scores[name]) else 'N/A'
                     for name in ('momentum', 'trend', 'relative_strength', 'volume', 'rsi', '52_week_strength', 'risk')]
        overall = f"{result['overall_score']:.2f}" if pd.notna(result['overall_score']) else 'N/A'
        print(f"{rank:<5} {result['symbol']:<16} {names.get(result['symbol'], 'UNKNOWN'):<34} {segments.get(result['symbol'], 'UNKNOWN'):<12} {sectors.get(result['symbol'], 'UNKNOWN'):<22} {overall:>8} "
              f"{formatted[0]:>9} {formatted[1]:>8} {formatted[2]:>9} {formatted[3]:>8} {formatted[4]:>7} {formatted[5]:>8} {formatted[6]:>7} {result['score_status']:<20}")
    print('-' * 145)
    print(f"Scored: {sum(result['score_status'] == 'OK' for result in results.values())}/{len(results)} valid records")
    print(f"Unavailable symbols: {', '.join(UNAVAILABLE_SYMBOLS)}")
    print(f"Score validation: {'PASSED' if not validation_failures else 'FAILED'}")
    if validation_failures:
        print(f"Score validation failures: {', '.join(validation_failures)}")
    return 0 if not validation_failures else 1


if __name__ == '__main__':
    sys.exit(main())
