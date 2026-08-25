"""Run the complete production analysis without changing model methodology."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.batch_downloader import BatchDownloadError, batch_download_universe, download_batch
from src.config import HISTORY_PERIOD, MAX_FALLBACK_TICKERS, MIN_UNIVERSE_COVERAGE
from src.historical_audit import audit_dataframe
from src.indicators import calculate_all_indicators
from src.market_regime import determine_market_regime
from src.production_universe import validate_production_universe
from src.scoring import score_universe
from src.selection import select_top_stocks
from src.universe import UniverseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_FILE = Path('data/latest.json')
FACTOR_NAMES = ('momentum', 'trend', 'relative_strength', 'volume', 'rsi', '52_week_strength', 'risk')


class DataSourceUnavailableError(RuntimeError):
    """Raised when market-data coverage is too low to produce a safe analysis."""


def validate_data_source_coverage(eligible_count: int, universe_count: int) -> None:
    """Abort before scoring when market-data coverage is unavailable or unexpectedly low."""
    coverage = eligible_count / universe_count if universe_count else 0.0
    if eligible_count == 0 or coverage < MIN_UNIVERSE_COVERAGE:
        raise DataSourceUnavailableError(
            f'DATA_SOURCE_UNAVAILABLE: only {eligible_count}/{universe_count} '
            f'eligible stocks ({coverage:.1%}) reached scoring inputs.'
        )
PRESENTATION_INDICATORS = (
    'current_price', 'return_1m', 'return_3m', 'return_6m', 'rsi_14',
    'sma_20', 'sma_50', 'sma_200', 'volatility_annualized', 'max_drawdown',
    '52_week_high', '52_week_low', 'distance_from_52w_high',
    'position_in_52w_range', 'volume_sma_20', 'volume_sma_60', 'volume_ratio',
)


def _json_value(value):
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _frontend_stock(item: dict) -> dict:
    factors = item.get('factor_scores', {})
    indicators = {key: item.get(key) for key in PRESENTATION_INDICATORS}
    return {
        **item,
        'score': item.get('overall_score'),
        'indicators': indicators,
        'metrics': {
            'price': indicators['current_price'],
            'return_1m': indicators['return_1m'],
            'return_3m': indicators['return_3m'],
            'return_6m': indicators['return_6m'],
            'rsi': indicators['rsi_14'],
        },
        'factor_scores': factors,
    }


def main() -> int:
    started = datetime.now(timezone.utc)
    manager = UniverseManager()
    validate_production_universe(manager.universe_data)
    entries = manager.universe_data['large_cap'] + manager.universe_data['mid_cap']
    entry_by_yahoo = {entry['yahoo_symbol']: entry for entry in entries}
    symbols = list(entry_by_yahoo)

    batch = batch_download_universe(symbols, period=HISTORY_PERIOD)
    logger.info(
        'Market-data source result: batch=%s fallback=%s/%s errors=%s no_data=%s insufficient=%s',
        len(batch.valid) - len(batch.fallback_successful), len(batch.fallback_successful),
        len(batch.fallback_attempted), len(batch.download_errors), len(batch.no_data),
        len(batch.insufficient_history),
    )
    historical = dict(batch.valid)
    fallback = {
        'successful': len(batch.fallback_successful),
        'insufficient_history': [],
        'data_quality_problems': [],
        'yahoo_problems': {},
    }
    ambiguous = set(batch.insufficient_history) | set(batch.no_data) | set(batch.download_errors)
    already_attempted = set(batch.fallback_attempted)
    fallback_candidates = sorted(ambiguous - already_attempted)
    remaining_fallback_budget = max(0, MAX_FALLBACK_TICKERS - len(batch.fallback_attempted))
    if len(fallback_candidates) > remaining_fallback_budget:
        logger.warning(
            'Fallback budget exhausted: %s unresolved symbols remain after %s controlled attempts',
            len(fallback_candidates), len(batch.fallback_attempted),
        )
    for symbol in fallback_candidates[:remaining_fallback_budget]:
        try:
            individual = download_batch([symbol], period=HISTORY_PERIOD)
            data = individual.get(symbol)
            audit = audit_dataframe(symbol, data)
            if audit['classification'] == 'VALID':
                historical[symbol] = data
                fallback['successful'] += 1
            elif audit['classification'] == 'INSUFFICIENT_HISTORY':
                fallback['insufficient_history'].append(symbol)
            elif audit['classification'] == 'DATA_QUALITY_PROBLEM':
                fallback['data_quality_problems'].append(symbol)
            else:
                fallback['yahoo_problems'][symbol] = audit['root_cause']
        except BatchDownloadError as error:
            fallback['yahoo_problems'][symbol] = str(error)

    indicators = {}
    indicator_failures = {}
    for yahoo_symbol, data in historical.items():
        entry = entry_by_yahoo[yahoo_symbol]
        audit = audit_dataframe(yahoo_symbol, data)
        if audit['classification'] != 'VALID':
            indicator_failures[entry['symbol']] = audit['root_cause']
            continue
        clean_data = data.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        values = calculate_all_indicators(clean_data)
        values['current_price'] = float(clean_data['Close'].iloc[-1])
        required = ('current_price', 'return_1m', 'return_3m', 'return_6m', 'return_12m', 'sma_20', 'sma_50', 'sma_200', 'rsi_14', 'volume_ratio', 'position_in_52w_range', 'distance_from_52w_high', 'volatility_annualized', 'max_drawdown')
        missing = [key for key in required if values.get(key) is None or not np.isfinite(values[key])]
        if missing:
            indicator_failures[entry['symbol']] = f'Missing indicators: {", ".join(missing)}'
        else:
            indicators[entry['symbol']] = values

    validate_data_source_coverage(len(indicators), len(entries))

    benchmark_keys = ('current_price', 'sma_50', 'sma_200', 'return_3m', 'return_6m', 'return_12m')
    benchmark = {key: float(np.mean([values[key] for values in indicators.values()])) for key in benchmark_keys}
    scored = score_universe(indicators, {key: benchmark[f'return_{key}'] for key in ('3m', '6m', '12m')})
    scored_rows = []
    for symbol, result in scored.items():
        row = dict(result)
        row.update({key: indicators[symbol].get(key) for key in PRESENTATION_INDICATORS})
        row.update(entry_by_yahoo[next(key for key, entry in entry_by_yahoo.items() if entry['symbol'] == symbol)])
        scored_rows.append(row)

    score_failures = [row['symbol'] for row in scored_rows if row.get('score_status') != 'OK']
    factor_sum_failures = [row['symbol'] for row in scored_rows if row.get('score_status') == 'OK' and not np.isclose(row['overall_score'], sum(row['factor_scores'].values()), atol=1e-9)]
    regime = determine_market_regime(benchmark, indicators)
    selection = select_top_stocks(scored_rows, market_regime=regime)
    eligible = [row for row in scored_rows if row.get('score_status') == 'OK']
    top_large = sorted((row for row in eligible if row.get('segment') == 'NIFTY100'), key=lambda row: row['overall_score'], reverse=True)[:10]
    top_mid = sorted((row for row in eligible if row.get('segment') == 'MIDCAP150'), key=lambda row: row['overall_score'], reverse=True)[:10]
    sector_analysis = []
    for sector in sorted({row.get('sector') or 'UNKNOWN' for row in eligible}):
        sector_rows = [row for row in eligible if (row.get('sector') or 'UNKNOWN') == sector]
        selected_rows = [row for row in selection['stocks'] if (row.get('sector') or 'UNKNOWN') == sector]
        highest = max(sector_rows, key=lambda row: row['overall_score'])
        sector_analysis.append({'sector': sector, 'eligible_count': len(sector_rows), 'selected_count': len(selected_rows), 'highest_scoring_stock': highest['symbol'], 'highest_score': highest['overall_score']})

    selected = [_frontend_stock(item) for item in selection['stocks']]
    report = {
        'analysis_timestamp': started.isoformat(), 'universe_as_of': manager.universe_data.get('universe_as_of'),
        'universe_count': len(entries), 'yahoo_valid_count': len(entries), 'eligible_count': len(indicators),
        'insufficient_history': sorted(set(fallback['insufficient_history'])),
        'data_quality_problems': sorted(set(fallback['data_quality_problems'])), 'yahoo_problems': fallback['yahoo_problems'],
        'indicator_calculations': {'successful': len(indicators), 'failed': indicator_failures},
        'scoring': {'successful': len(scored) - len(score_failures), 'failed': score_failures, 'factor_sum_failures': factor_sum_failures},
        'market_regime': regime['classification'], 'regime_details': regime, 'benchmark_metrics': benchmark,
        'large_cap': [_frontend_stock(item) for item in selection['large_cap']['stocks']],
        'mid_cap': [_frontend_stock(item) for item in selection['mid_cap']['stocks']],
        'selected_stocks': selected, 'top_10_nifty100': [_frontend_stock(item) for item in top_large],
        'top_10_midcap150': [_frontend_stock(item) for item in top_mid], 'sector_analysis': sector_analysis,
        'selection_summary': {key: selection[key] for key in ('large_cap', 'mid_cap', 'total_selected')},
        'warnings': selection['warnings'] + [f'{len(fallback["insufficient_history"])} stocks excluded from scoring for insufficient history.'],
        'data_quality_status': 'COMPLETE' if len(indicators) == 244 else 'INCOMPLETE',
        'download': {'batch_successful': len(batch.valid), 'fallback_successful': fallback['successful'], 'elapsed_seconds': batch.elapsed_seconds},
    }
    OUTPUT_FILE.write_text(json.dumps(_json_value(report), indent=2), encoding='utf-8')
    print(f"Eligible: {len(indicators)}/250")
    print(f"Regime: {regime['classification']} ({regime['score']:.2f})")
    print(f"Selected: {selection['total_selected']}")
    print(f"Output: {OUTPUT_FILE}")
    return 0 if len(indicators) == 244 and not score_failures and not factor_sum_failures else 1


if __name__ == '__main__':
    sys.exit(main())