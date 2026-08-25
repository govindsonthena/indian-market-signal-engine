"""Deterministic tests for market-regime classification."""

import numpy as np

from src.market_regime import calculate_market_breadth, determine_market_regime


def benchmark(**overrides):
    values = {
        'current_price': 120, 'sma_50': 110, 'sma_200': 100,
        'return_3m': 0.10, 'return_6m': 0.20, 'return_12m': 0.30,
    }
    values.update(overrides)
    return values


def stocks(above_50=True, above_200=True):
    return {
        str(index): {
            'current_price': 120 if above_50 else 90,
            'sma_50': 100,
            'sma_200': 100 if above_200 else 130,
        }
        for index in range(10)
    }


def test_bullish_regime():
    result = determine_market_regime(benchmark(), stocks(True, True))
    assert result['classification'] == 'BULLISH'
    assert result['score'] >= 70


def test_bearish_regime():
    result = determine_market_regime(
        benchmark(current_price=80, sma_50=100, sma_200=110,
                  return_3m=-0.1, return_6m=-0.2, return_12m=-0.3),
        stocks(False, False))
    assert result['classification'] == 'BEARISH'
    assert result['score'] < 40


def test_neutral_regime_and_boundary():
    neutral = determine_market_regime(
        benchmark(current_price=105, sma_50=100, sma_200=110,
                  return_3m=0.1, return_6m=-0.1, return_12m=0.1),
        stocks(True, False))
    assert neutral['classification'] == 'NEUTRAL'
    boundary = determine_market_regime(
        benchmark(current_price=100, sma_50=100, sma_200=100,
                  return_3m=0, return_6m=0, return_12m=0),
        stocks(False, False))
    assert boundary['classification'] == 'BEARISH'


def test_breadth_and_missing_data():
    breadth = calculate_market_breadth({
        'a': {'current_price': 110, 'sma_50': 100, 'sma_200': 100},
        'b': {'current_price': 90, 'sma_50': 100, 'sma_200': 100},
        'c': {'current_price': 110, 'sma_50': np.nan, 'sma_200': 100},
    })
    assert breadth['percent_above_50dma'] == 0.5
    assert breadth['percent_above_200dma'] == 2 / 3
    missing = determine_market_regime({}, {})
    assert missing['classification'] == 'INSUFFICIENT_DATA'
    assert np.isnan(missing['score'])


def test_nested_input_and_custom_weights():
    result = determine_market_regime({
        'benchmark': benchmark(), 'stocks': stocks(True, True)
    }, weights={'benchmark_trend': 0.5, 'market_breadth': 0.25, 'market_momentum': 0.25})
    assert result['classification'] == 'BULLISH'
