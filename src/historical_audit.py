"""Audit historical data and determine eligibility for the existing score model."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.indicators import calculate_all_indicators
from src.scoring import REQUIRED_INDICATORS

OHLCV_COLUMNS = ('Open', 'High', 'Low', 'Close', 'Volume')
CALCULABILITY_FIELDS = {
    'SMA20': 'sma_20',
    'SMA50': 'sma_50',
    'SMA200': 'sma_200',
    '1M return': 'return_1m',
    '3M return': 'return_3m',
    '6M return': 'return_6m',
    '12M return': 'return_12m',
    '52-week metrics': 'position_in_52w_range',
}


def _normalise_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Convert either Yahoo MultiIndex orientation to simple OHLCV columns."""
    if not isinstance(data.columns, pd.MultiIndex):
        return data.copy()
    fields = set(OHLCV_COLUMNS)
    if fields.issubset(set(data.columns.get_level_values(0))):
        ticker = data.columns.get_level_values(1)[0]
        return data.xs(ticker, axis=1, level=1).copy()
    if fields.issubset(set(data.columns.get_level_values(1))):
        ticker = data.columns.get_level_values(0)[0]
        return data.xs(ticker, axis=1, level=0).copy()
    return data.copy()


def audit_dataframe(symbol: str, data: pd.DataFrame | None) -> dict[str, Any]:
    """Return observed data quality, indicator calculability, and eligibility."""
    base = {
        'yahoo_symbol': symbol,
        'first_date': None,
        'last_date': None,
        'total_rows': 0,
        'valid_close_rows': 0,
        'valid_volume_rows': 0,
        'missing_ohlcv_percent': 100.0,
        'valid_trading_days': 0,
        'calculable': {name: False for name in CALCULABILITY_FIELDS},
        'eligible_for_scoring': False,
        'classification': 'YAHOO_DATA_PROBLEM',
        'root_cause': 'Yahoo returned no usable rows',
    }
    if data is None or not isinstance(data, pd.DataFrame) or data.empty:
        return base

    data = _normalise_columns(data)
    base['total_rows'] = len(data)
    if len(data.index):
        base['first_date'] = str(data.index[0].date()) if hasattr(data.index[0], 'date') else str(data.index[0])
        base['last_date'] = str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1])
    missing_columns = [column for column in OHLCV_COLUMNS if column not in data.columns]
    if missing_columns:
        base['classification'] = 'DATA_QUALITY_PROBLEM'
        base['root_cause'] = f"Missing OHLCV columns: {', '.join(missing_columns)}"
        return base

    ohlcv = data.loc[:, OHLCV_COLUMNS]
    base['valid_close_rows'] = int(ohlcv['Close'].notna().sum())
    base['valid_volume_rows'] = int(ohlcv['Volume'].notna().sum())
    base['missing_ohlcv_percent'] = float(ohlcv.isna().sum().sum() / ohlcv.size * 100)
    valid_rows = ohlcv.notna().all(axis=1) & (ohlcv['Close'] > 0) & (ohlcv['Volume'] >= 0)
    base['valid_trading_days'] = int(valid_rows.sum())

    clean = ohlcv.loc[valid_rows]
    if clean.empty:
        base['classification'] = 'DATA_QUALITY_PROBLEM'
        base['root_cause'] = 'No trading day has complete valid OHLCV values'
        return base

    indicators = calculate_all_indicators(clean)
    indicators['current_price'] = float(clean['Close'].iloc[-1])
    base['calculable'] = {
        name: indicators.get(field) is not None and np.isfinite(indicators[field])
        for name, field in CALCULABILITY_FIELDS.items()
    }
    missing_indicators = [field for field in REQUIRED_INDICATORS if indicators.get(field) is None]
    base['eligible_for_scoring'] = not missing_indicators
    if base['eligible_for_scoring']:
        base['classification'] = 'VALID'
        base['root_cause'] = 'All required Phase 4 indicators and Phase 5 scoring inputs are calculable'
    elif base['missing_ohlcv_percent'] > 10:
        base['classification'] = 'DATA_QUALITY_PROBLEM'
        base['root_cause'] = f"{base['missing_ohlcv_percent']:.2f}% of OHLCV cells are missing"
    elif base['valid_trading_days'] <= 252 or not base['calculable']['12M return']:
        base['classification'] = 'INSUFFICIENT_HISTORY'
        base['root_cause'] = f"Only {base['valid_trading_days']} valid trading days; complete scoring needs a calculable 12M return (>252 rows)"
    else:
        base['classification'] = 'DATA_QUALITY_PROBLEM'
        base['root_cause'] = f"{len(missing_indicators)} required scoring indicators are not calculable despite sufficient row count"
    return base


def summarize_audits(audits: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the production eligibility summary without changing universe membership."""
    counts = {classification: sum(item['classification'] == classification for item in audits)
              for classification in ('VALID', 'INSUFFICIENT_HISTORY', 'DATA_QUALITY_PROBLEM', 'YAHOO_DATA_PROBLEM')}
    eligible = counts['VALID']
    return {
        'universe': len(audits),
        'yahoo_symbols_valid': sum(item['classification'] != 'YAHOO_DATA_PROBLEM' for item in audits),
        'sufficient_history': eligible,
        'insufficient_history': counts['INSUFFICIENT_HISTORY'],
        'data_quality_problems': counts['DATA_QUALITY_PROBLEM'],
        'yahoo_problems': counts['YAHOO_DATA_PROBLEM'],
        'eligible_for_scoring': eligible,
        'coverage_eligible': eligible / len(audits) if audits else 0.0,
        'classifications': counts,
    }