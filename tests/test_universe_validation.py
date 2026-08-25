"""Deterministic tests for universe and Yahoo-symbol validation."""

import pandas as pd

from src.universe_validation import classify_symbol, validate_universe


def market_frame():
    return pd.DataFrame({
        'Open': [1.0], 'High': [1.1], 'Low': [0.9],
        'Close': [1.0], 'Volume': [100],
    })


def test_classifies_valid_symbol():
    result = classify_symbol('GOOD.NS', lambda symbol: market_frame())
    assert result['status'] == 'VALID'
    assert not result['replacement_required']


def test_classifies_empty_and_permanent_failures():
    empty = classify_symbol('EMPTY.NS', lambda symbol: pd.DataFrame())
    invalid = classify_symbol('BAD.NS', lambda symbol: (_ for _ in ()).throw(Exception('quote not found 404')))
    assert empty['status'] == 'NO_DATA'
    assert empty['replacement_required']
    assert invalid['status'] == 'INVALID'
    assert invalid['replacement_required']


def test_classifies_transient_failure():
    result = classify_symbol('RETRY.NS', lambda symbol: (_ for _ in ()).throw(Exception('connection reset')))
    assert result['status'] == 'TEMPORARY_FAILURE'
    assert not result['replacement_required']


def test_validates_every_entry_and_reports_coverage(tmp_path):
    universe_file = tmp_path / 'universe.json'
    universe_file.write_text('''{
      "large_cap": [{"symbol": "GOOD.NS", "name": "Good", "segment": "NIFTY100", "sector": "Tech"}],
      "mid_cap": [{"symbol": "BAD.NS", "name": "Bad", "segment": "MIDCAP150", "sector": "Other"}]
    }''')
    from src.universe import UniverseManager
    manager = UniverseManager(str(universe_file))
    report = validate_universe(manager, lambda symbol: market_frame() if symbol == 'GOOD.NS' else pd.DataFrame())
    assert len(report['entries']) == 2
    assert report['summary']['expected'] == 2
    assert report['summary']['valid'] == 1
    assert report['summary']['no_data'] == 1
    assert report['summary']['coverage'] == 0.5
    assert report['summary']['segments']['NIFTY100']['valid'] == 1


def test_explicit_yahoo_symbol_is_supported(tmp_path):
    universe_file = tmp_path / 'universe.json'
    universe_file.write_text('''{
      "large_cap": [{"symbol": "LOCAL", "yahoo_symbol": "REMOTE.NS", "segment": "NIFTY100"}],
      "mid_cap": []
    }''')
    from src.universe import UniverseManager
    manager = UniverseManager(str(universe_file))
    seen = []
    validate_universe(manager, lambda symbol: seen.append(symbol) or market_frame())
    assert seen == ['REMOTE.NS']
