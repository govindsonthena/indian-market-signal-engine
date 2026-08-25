"""Tests for the Phase 8 frontend output contract."""

from phase_8_production_analysis import _frontend_stock


REQUIRED_METRICS = ('current_price', 'return_1m', 'return_3m', 'return_6m', 'rsi_14')


def test_frontend_stock_contains_phase4_indicators_and_metric_aliases():
    item = {
        'symbol': 'DIVISLAB',
        'overall_score': 94.2,
        'current_price': 6500.0,
        'return_1m': 0.05,
        'return_3m': 0.10,
        'return_6m': 0.20,
        'rsi_14': 58.0,
        'sma_20': 6400.0,
        'sma_50': 6300.0,
        'sma_200': 5600.0,
        'volatility_annualized': 0.18,
        'max_drawdown': -0.12,
        '52_week_high': 6600.0,
        '52_week_low': 4500.0,
        'distance_from_52w_high': -0.015,
        'position_in_52w_range': 0.95,
        'volume_sma_20': 1000000.0,
        'volume_sma_60': 900000.0,
        'volume_ratio': 1.11,
        'factor_scores': {},
    }

    output = _frontend_stock(item)
    assert all(output['indicators'][key] is not None for key in REQUIRED_METRICS)
    assert output['metrics'] == {
        'price': 6500.0,
        'return_1m': 0.05,
        'return_3m': 0.10,
        'return_6m': 0.20,
        'rsi': 58.0,
    }
    assert output['indicators']['sma_200'] == 5600.0


def test_frontend_stock_preserves_unavailable_values_as_null():
    output = _frontend_stock({'symbol': 'NEW', 'factor_scores': {}})
    assert output['indicators']['current_price'] is None
    assert output['metrics']['price'] is None
