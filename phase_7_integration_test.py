"""Production-universe pipeline validation. Not an investment recommendation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.batch_downloader import batch_download_universe
from src.config import HISTORY_PERIOD, MIN_DATA_ROWS, MIN_UNIVERSE_COVERAGE
from src.indicators import calculate_all_indicators, validate_data
from src.market_regime import determine_market_regime
from src.production_universe import validate_production_universe
from src.scoring import score_universe
from src.selection import select_top_stocks
from src.universe import UniverseManager
from src.universe_validation import validate_universe

REPORT_FILE = Path('data/production_pipeline_validation.json')


def main() -> int:
    manager = UniverseManager()
    validate_production_universe(manager.universe_data)
    validation = validate_universe(manager)
    summary = validation['summary']
    report = {'validation': validation, 'pipeline_status': 'INCOMPLETE'}
    REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print('PRODUCTION UNIVERSE VALIDATION')
    print(f"Expected: {summary['expected']}; Valid: {summary['valid']}; Coverage: {summary['coverage']:.1%}")
    print(f"NIFTY100: {summary['segments']['NIFTY100']['valid']}/{summary['segments']['NIFTY100']['expected']}")
    print(f"MIDCAP150: {summary['segments']['MIDCAP150']['valid']}/{summary['segments']['MIDCAP150']['expected']}")
    if summary['coverage'] < MIN_UNIVERSE_COVERAGE:
        print('DATA QUALITY: INCOMPLETE')
        print(f"Recommendations blocked below {MIN_UNIVERSE_COVERAGE:.1%} coverage.")
        print(f"Validation report: {REPORT_FILE}")
        return 2

    entries = [entry for entry in validation['entries'] if entry['status'] == 'VALID']
    download = batch_download_universe(
        [entry['yahoo_symbol'] for entry in entries],
        period=HISTORY_PERIOD,
    )
    report['historical_download'] = {
        'expected': download.total_attempted,
        'successful': len(download.valid),
        'insufficient_history': download.insufficient_history,
        'no_data': download.no_data,
        'download_errors': download.download_errors,
        'elapsed_seconds': download.elapsed_seconds,
    }

    indicators = {}
    metadata = {}
    for entry in entries:
        data = download.valid.get(entry['yahoo_symbol'])
        if data is None:
            continue
        data = data.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        valid, _ = validate_data(data, min_rows=MIN_DATA_ROWS)
        if not valid:
            continue
        values = calculate_all_indicators(data)
        values['current_price'] = float(data['Close'].iloc[-1])
        indicators[entry['symbol']] = values
        metadata[entry['symbol']] = entry

    if not indicators:
        print('DATA QUALITY: INCOMPLETE - no valid historical datasets')
        return 2
    benchmark = {key: np.nanmean([values[key] for values in indicators.values()])
                 for key in ('current_price', 'sma_50', 'sma_200', 'return_3m', 'return_6m', 'return_12m')}
    scored = score_universe(indicators, {key: benchmark[f'return_{key}'] for key in ('3m', '6m', '12m')})
    rows = [dict(result, **metadata[symbol]) for symbol, result in scored.items()]
    regime = determine_market_regime(benchmark, indicators)
    selection = select_top_stocks(rows, market_regime=regime)
    report.update({'pipeline_status': 'COMPLETE', 'regime': regime, 'selection': selection})
    REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print(f"Market regime: {regime['classification']} ({regime['score']:.2f})")
    print(f"Selected: {selection['total_selected']}")
    for rank, item in enumerate(selection['stocks'], 1):
        print(f"{rank}. {item['symbol']} | {item.get('name')} | {item.get('segment')} | {item.get('sector')} | {item['overall_score']:.2f} | {item['signal']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
