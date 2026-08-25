"""Deterministic tests for the Phase 5 quantitative scoring engine."""

import numpy as np
import pytest

from src.config import SCORE_WEIGHTS
from src.scoring import (
    calculate_52_week_strength_score,
    calculate_risk_scores,
    calculate_rsi_score,
    calculate_trend_score,
    percentile_scores,
    score_universe,
    validate_weights,
)


def stock(**overrides):
    values = {
        'current_price': 120.0, 'return_1m': 0.05, 'return_3m': 0.12,
        'return_6m': 0.20, 'return_12m': 0.30, 'sma_20': 110.0,
        'sma_50': 105.0, 'sma_200': 95.0, 'rsi_14': 58.0,
        'volume_ratio': 1.2, 'position_in_52w_range': 0.8,
        'distance_from_52w_high': -0.05, 'volatility_annualized': 0.20,
        'max_drawdown': -0.15,
    }
    values.update(overrides)
    return values


def universe():
    return {
        'AAA': stock(return_1m=0.10, return_3m=0.20, return_6m=0.35, return_12m=0.50,
                     volume_ratio=1.5, volatility_annualized=0.15, max_drawdown=-0.10),
        'BBB': stock(return_1m=0.05, return_3m=0.10, return_6m=0.20, return_12m=0.30,
                     volume_ratio=1.1, volatility_annualized=0.25, max_drawdown=-0.20),
        'CCC': stock(return_1m=-0.02, return_3m=-0.05, return_6m=-0.10, return_12m=-0.15,
                     volume_ratio=0.8, volatility_annualized=0.40, max_drawdown=-0.40),
    }


def test_weight_validation():
    validate_weights(SCORE_WEIGHTS)
    invalid = dict(SCORE_WEIGHTS)
    invalid['risk'] = 14
    with pytest.raises(ValueError):
        validate_weights(invalid)


def test_percentile_order_ties_and_nan():
    scores = percentile_scores({'high': 3, 'tie_a': 2, 'tie_b': 2, 'low': 1, 'missing': np.nan})
    assert scores['high'] > scores['tie_a'] == scores['tie_b'] > scores['low']
    assert np.isnan(scores['missing'])
    descending = percentile_scores({'a': 1, 'b': 3}, higher_is_better=False)
    assert descending['a'] > descending['b']


def test_trend_bullish_bearish_and_mixed():
    assert calculate_trend_score(stock()) == SCORE_WEIGHTS['trend']
    bearish = stock(current_price=80, sma_20=90, sma_50=100, sma_200=110)
    assert calculate_trend_score(bearish) == 0
    mixed = stock(current_price=105, sma_20=110, sma_50=100, sma_200=95)
    assert 0 < calculate_trend_score(mixed) < SCORE_WEIGHTS['trend']


def test_rsi_zones_are_smooth_and_bounded():
    healthy = calculate_rsi_score(stock(rsi_14=58))
    overbought = calculate_rsi_score(stock(rsi_14=85))
    oversold = calculate_rsi_score(stock(rsi_14=20))
    neutral = calculate_rsi_score(stock(rsi_14=48))
    assert healthy > overbought >= 0
    assert healthy > neutral > oversold
    assert np.isnan(calculate_rsi_score(stock(rsi_14=np.nan)))


def test_52_week_strength_and_risk():
    near_high = calculate_52_week_strength_score(
        stock(position_in_52w_range=0.95, distance_from_52w_high=-0.01))
    middle = calculate_52_week_strength_score(
        stock(position_in_52w_range=0.5, distance_from_52w_high=-0.25))
    assert near_high > middle
    risk = calculate_risk_scores(universe())
    assert risk['AAA'] > risk['BBB'] > risk['CCC']


def test_full_score_is_bounded_and_equals_factor_sum():
    results = score_universe(universe(), {'3m': 0.05, '6m': 0.10, '12m': 0.15})
    for result in results.values():
        assert result['score_status'] == 'OK'
        assert 0 <= result['overall_score'] <= 100
        assert np.isclose(result['overall_score'], sum(result['factor_scores'].values()))
    assert results['AAA']['overall_score'] > results['CCC']['overall_score']
    assert results['AAA']['explanations']['strengths']


def test_missing_data_is_not_scoreable_or_ranked():
    data = universe()
    data['MISSING'] = stock(rsi_14=None)
    result = score_universe(data, {'3m': 0.05, '6m': 0.10, '12m': 0.15})['MISSING']
    assert result['score_status'] == 'INSUFFICIENT_DATA'
    assert np.isnan(result['overall_score'])
    assert 'rsi_14' in result['missing_indicators']
