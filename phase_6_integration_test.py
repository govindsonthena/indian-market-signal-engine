"""Phase 6 development-sample integration: indicators, scores, regime, selection."""

import sys

import pandas as pd
import yfinance as yf

from src.indicators import calculate_all_indicators, validate_data
from src.market_regime import determine_market_regime
from src.scoring import score_universe
from src.selection import select_top_stocks
from src.universe import UniverseManager

VALIDATED_SYMBOLS = [
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'WIPRO.NS',
    'MARUTI.NS', 'BHARTIARTL.NS', 'LT.NS', 'ICICIBANK.NS', 'SBIN.NS',
    'CIPLA.NS', 'ICICIPRULI.NS', 'IRCTC.NS', 'GAIL.NS', 'TITAN.NS', 'DABUR.NS',
]


def main() -> int:
    manager = UniverseManager()
    indicators = {}
    metadata = {}
    for symbol in VALIDATED_SYMBOLS:
        data = yf.download(symbol, period='3y', progress=False)
        if data is None or data.empty:
            print(f'ERROR: no data for validated symbol {symbol}')
            return 1
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = [column[0] for column in data.columns]
        data = data.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        valid, issues = validate_data(data, min_rows=200)
        if not valid:
            print(f'ERROR: invalid data for {symbol}: {issues}')
            return 1
        values = calculate_all_indicators(data)
        values['current_price'] = float(data['Close'].iloc[-1])
        indicators[symbol] = values
        metadata[symbol] = manager.get_stock_info(symbol) or {}

    benchmark = {
        key: sum(values[key] for values in indicators.values()) / len(indicators)
        for key in ('current_price', 'sma_50', 'sma_200', 'return_3m', 'return_6m', 'return_12m')
    }
    benchmark_returns = {key: benchmark[f'return_{key}'] for key in ('3m', '6m', '12m')}
    scored = score_universe(indicators, benchmark_returns)
    scored_rows = []
    for symbol, result in scored.items():
        row = dict(result)
        row.update(metadata[symbol])
        scored_rows.append(row)

    regime = determine_market_regime(benchmark, indicators)
    selection = select_top_stocks(scored_rows, market_regime=regime)

    print('\nDEVELOPMENT SAMPLE - PHASE 6')
    print(f"Market regime: {regime['classification']} ({regime['score']:.2f})")
    print(f"Benchmark trend: {regime['benchmark_trend']:.2f}; breadth 50DMA: {regime['breadth']['percent_above_50dma']:.2f}; breadth 200DMA: {regime['breadth']['percent_above_200dma']:.2f}")
    print('\nSelected candidates')
    print('Rank  Ticker           Segment      Sector                 Score  Signal')
    print('-' * 80)
    for rank, item in enumerate(selection['stocks'], 1):
        print(f"{rank:>4}  {item['symbol']:<16} {item.get('segment', 'UNKNOWN'):<12} {item.get('sector', 'UNKNOWN'):<22} {item['overall_score']:>6.2f}  {item['signal']}")
    print('\nWarnings:')
    for warning in selection['warnings']:
        print(f'- {warning}')
    print(f"Total selected: {selection['total_selected']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
