"""Deterministic tests for Phase 7.6 historical-data auditing."""

import pandas as pd

from src.historical_audit import audit_dataframe, summarize_audits


def frame(rows: int = 253) -> pd.DataFrame:
    close = [100.0 + (index % 7) * 0.5 + index * 0.02 for index in range(rows)]
    return pd.DataFrame({
        'Open': close, 'High': [value + 1 for value in close],
        'Low': [value - 1 for value in close], 'Close': close,
        'Volume': [1000.0] * rows,
    }, index=pd.date_range('2025-01-01', periods=rows))


def test_sufficient_history_is_valid():
    result = audit_dataframe('VALID.NS', frame())
    assert result['classification'] == 'VALID'
    assert result['eligible_for_scoring']
    assert all(result['calculable'].values())


def test_new_listing_is_insufficient_history():
    result = audit_dataframe('NEW.NS', frame(180))
    assert result['classification'] == 'INSUFFICIENT_HISTORY'
    assert not result['eligible_for_scoring']
    assert not result['calculable']['12M return']


def test_missing_close_is_data_quality_problem():
    data = frame()
    data = data.drop(columns=['Close'])
    result = audit_dataframe('MISSING.NS', data)
    assert result['classification'] == 'DATA_QUALITY_PROBLEM'
    assert 'Close' in result['root_cause']


def test_excessive_nans_are_data_quality_problem():
    data = frame()
    data.iloc[:151, data.columns.get_loc('Close')] = None
    result = audit_dataframe('NANS.NS', data)
    assert result['classification'] == 'DATA_QUALITY_PROBLEM'
    assert result['missing_ohlcv_percent'] > 10


def test_empty_data_is_yahoo_problem():
    result = audit_dataframe('EMPTY.NS', pd.DataFrame())
    assert result['classification'] == 'YAHOO_DATA_PROBLEM'
    assert result['total_rows'] == 0


def test_summary_counts_only_valid_as_eligible():
    audits = [audit_dataframe('VALID.NS', frame()), audit_dataframe('NEW.NS', frame(180))]
    summary = summarize_audits(audits)
    assert summary['universe'] == 2
    assert summary['sufficient_history'] == 1
    assert summary['insufficient_history'] == 1
    assert summary['eligible_for_scoring'] == 1
    assert summary['coverage_eligible'] == 0.5