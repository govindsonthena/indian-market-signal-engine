"""Validation and coverage reporting for the development stock universe."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd
import yfinance as yf

from src.config import MIN_SEGMENT_COVERAGE, MIN_UNIVERSE_COVERAGE
from src.universe import UniverseManager

VALID_STATUSES = {
    'VALID', 'INVALID', 'NO_DATA', 'POSSIBLY_RENAMED', 'TEMPORARY_FAILURE'
}


def _is_permanent_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(term in message for term in ('delisted', 'not found', '404', 'quote not found'))


def classify_symbol(symbol: str, fetcher: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Classify one Yahoo symbol without proposing an unverified replacement."""
    fetcher = fetcher or (lambda value: yf.download(value, period='5d', progress=False))
    try:
        data = fetcher(symbol)
    except Exception as error:
        status = 'INVALID' if _is_permanent_error(error) else 'TEMPORARY_FAILURE'
        return {
            'ticker': symbol, 'status': status, 'yahoo_symbol': symbol,
            'replacement_required': status == 'INVALID', 'error': str(error),
        }
    if data is None or not isinstance(data, pd.DataFrame) or data.empty:
        return {
            'ticker': symbol, 'status': 'NO_DATA', 'yahoo_symbol': symbol,
            'replacement_required': True, 'error': 'Yahoo returned no rows',
        }
    required = {'Open', 'High', 'Low', 'Close', 'Volume'}
    columns = set(data.columns.get_level_values(0)) if isinstance(data.columns, pd.MultiIndex) else set(data.columns)
    if not required.issubset(columns):
        return {
            'ticker': symbol, 'status': 'INVALID', 'yahoo_symbol': symbol,
            'replacement_required': True, 'error': 'Missing OHLCV columns',
        }
    return {
        'ticker': symbol, 'status': 'VALID', 'yahoo_symbol': symbol,
        'replacement_required': False, 'error': None,
    }


def validate_universe(manager: UniverseManager | None = None,
                      fetcher: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Validate every current entry and return entries plus coverage summary."""
    manager = manager or UniverseManager()
    entries = []
    for segment_key in ('large_cap', 'mid_cap'):
        for stock in manager.universe_data.get(segment_key, []):
            ticker = stock.get('yahoo_symbol') or stock.get('symbol')
            result = classify_symbol(ticker, fetcher)
            result.update({
                'symbol': stock.get('symbol'), 'name': stock.get('name'),
                'segment': stock.get('segment'), 'sector': stock.get('sector'),
            })
            entries.append(result)

    total = len(entries)
    valid = sum(item['status'] == 'VALID' for item in entries)
    by_segment = {}
    for segment in ('NIFTY100', 'MIDCAP150'):
        segment_entries = [item for item in entries if item['segment'] == segment]
        segment_valid = sum(item['status'] == 'VALID' for item in segment_entries)
        by_segment[segment] = {
            'expected': len(segment_entries), 'valid': segment_valid,
            'coverage': segment_valid / len(segment_entries) if segment_entries else 0.0,
        }
    summary = {
        'expected': total, 'valid': valid,
        'invalid': sum(item['status'] == 'INVALID' for item in entries),
        'no_data': sum(item['status'] == 'NO_DATA' for item in entries),
        'possibly_renamed': sum(item['status'] == 'POSSIBLY_RENAMED' for item in entries),
        'temporary_failure': sum(item['status'] == 'TEMPORARY_FAILURE' for item in entries),
        'coverage': valid / total if total else 0.0,
        'coverage_threshold': MIN_UNIVERSE_COVERAGE,
        'coverage_ok': (valid / total >= MIN_UNIVERSE_COVERAGE) if total else False,
        'segments': by_segment,
    }
    return {'entries': entries, 'summary': summary}


def print_report(report: Mapping[str, Any]) -> None:
    """Print a human-readable validation report."""
    print('Ticker                  Status              Yahoo Symbol          Replacement')
    print('-' * 80)
    for item in report['entries']:
        replacement = 'YES' if item['replacement_required'] else 'NO'
        print(f"{item['ticker']:<24} {item['status']:<19} {item['yahoo_symbol']:<22} {replacement}")
    summary = report['summary']
    print('\nCoverage summary')
    print(f"Expected: {summary['expected']}")
    print(f"Valid: {summary['valid']}")
    print(f"Invalid: {summary['invalid']}")
    print(f"No data: {summary['no_data']}")
    print(f"Possibly renamed: {summary['possibly_renamed']}")
    print(f"Temporary failure: {summary['temporary_failure']}")
    print(f"Coverage: {summary['coverage']:.1%} (threshold {summary['coverage_threshold']:.1%})")
    for segment, values in summary['segments'].items():
        print(f"{segment}: {values['valid']}/{values['expected']} valid ({values['coverage']:.1%})")


if __name__ == '__main__':
    print_report(validate_universe())
