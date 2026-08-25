"""Deterministic market-regime classification from benchmark and breadth data."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from src.config import (
    MARKET_REGIME_BEARISH_SCORE,
    MARKET_REGIME_BULLISH_SCORE,
    MARKET_REGIME_WEIGHTS,
)


def _finite(value: Any) -> bool:
    return value is not None and np.isfinite(value)


def calculate_market_breadth(stock_indicators: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    """Calculate the fraction of valid stocks above SMA50 and SMA200."""
    result = {}
    for key, average in (('percent_above_50dma', 'sma_50'), ('percent_above_200dma', 'sma_200')):
        comparisons = [values['current_price'] > values[average]
                       for values in stock_indicators.values()
                       if _finite(values.get('current_price')) and _finite(values.get(average))]
        result[key] = sum(comparisons) / len(comparisons) if comparisons else np.nan
    return result


def _component(values: list[float], weight: float) -> tuple[float, float]:
    if not values:
        return np.nan, 0.0
    return sum(values) / len(values) * weight, weight


def determine_market_regime(
        benchmark_indicators: Mapping[str, Any] | Mapping[str, Mapping[str, Any]],
        stock_indicators: Mapping[str, Mapping[str, Any]] | None = None,
        weights: Mapping[str, float] | None = None) -> dict[str, Any]:
    """Return classification, 0-100 score, components, and breadth diagnostics.

    The benchmark and analyzed-stock indicators are supplied by the caller. Missing
    components are omitted and the remaining configured weights are renormalized.
    """
    weights = MARKET_REGIME_WEIGHTS if weights is None else weights
    if not np.isclose(sum(weights.values()), 1.0, atol=1e-9):
        raise ValueError('Market-regime weights must sum to 1')
    if stock_indicators is None and 'benchmark' in benchmark_indicators:
        stock_indicators = benchmark_indicators.get('stocks', {})
        benchmark_indicators = benchmark_indicators.get('benchmark', {})
    stock_indicators = stock_indicators or {}
    breadth = calculate_market_breadth(stock_indicators)

    trend_values = [float(benchmark_indicators[key]) for key in ('current_price', 'sma_50', 'sma_200')
                    if _finite(benchmark_indicators.get(key))]
    trend_signals = []
    if _finite(benchmark_indicators.get('current_price')) and _finite(benchmark_indicators.get('sma_50')):
        trend_signals.append(float(benchmark_indicators['current_price'] > benchmark_indicators['sma_50']))
    if _finite(benchmark_indicators.get('current_price')) and _finite(benchmark_indicators.get('sma_200')):
        trend_signals.append(float(benchmark_indicators['current_price'] > benchmark_indicators['sma_200']))

    momentum_signals = [float(benchmark_indicators[key] > 0) for key in ('return_3m', 'return_6m', 'return_12m')
                        if _finite(benchmark_indicators.get(key))]
    breadth_signals = [breadth[key] for key in ('percent_above_50dma', 'percent_above_200dma')
                       if _finite(breadth[key])]

    raw_components = {
        'benchmark_trend': sum(trend_signals) / len(trend_signals) if trend_signals else np.nan,
        'market_breadth': sum(breadth_signals) / len(breadth_signals) if breadth_signals else np.nan,
        'market_momentum': sum(momentum_signals) / len(momentum_signals) if momentum_signals else np.nan,
    }
    available_weight = sum(weights[key] for key, value in raw_components.items() if _finite(value))
    if available_weight == 0:
        return {'classification': 'INSUFFICIENT_DATA', 'score': np.nan,
                'components': raw_components, 'breadth': breadth,
                'benchmark_trend': np.nan, 'market_momentum': np.nan}
    score = 100 * sum(weights[key] * value for key, value in raw_components.items() if _finite(value)) / available_weight
    if score >= MARKET_REGIME_BULLISH_SCORE:
        classification = 'BULLISH'
    elif score < MARKET_REGIME_BEARISH_SCORE:
        classification = 'BEARISH'
    else:
        classification = 'NEUTRAL'
    return {
        'classification': classification, 'score': float(score),
        'components': raw_components, 'breadth': breadth,
        'benchmark_trend': raw_components['benchmark_trend'],
        'market_momentum': raw_components['market_momentum'],
    }


if __name__ == '__main__':
    print('Market regime module loaded successfully')
