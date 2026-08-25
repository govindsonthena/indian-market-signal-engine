"""Deterministic, cross-sectional quantitative stock scoring."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from src.config import MOMENTUM_PERIOD_WEIGHTS, SCORE_WEIGHTS


REQUIRED_INDICATORS = {
    'current_price', 'return_1m', 'return_3m', 'return_6m', 'return_12m',
    'sma_20', 'sma_50', 'sma_200', 'rsi_14', 'volume_ratio',
    'position_in_52w_range', 'distance_from_52w_high',
    'volatility_annualized', 'max_drawdown',
}


def validate_weights(weights: Mapping[str, float] | None = None) -> None:
    """Raise ``ValueError`` unless weights contain the seven factors and total 100."""
    weights = SCORE_WEIGHTS if weights is None else weights
    missing = set(SCORE_WEIGHTS) - set(weights)
    if missing or set(weights) != set(SCORE_WEIGHTS):
        raise ValueError(f"Weights must contain exactly the scoring factors; mismatch: {missing}")
    if not np.isclose(sum(weights.values()), 100.0, atol=1e-9):
        raise ValueError("Scoring weights must sum to 100")
    if any(value < 0 for value in weights.values()):
        raise ValueError("Scoring weights cannot be negative")


def percentile_scores(values: Mapping[str, float] | pd.Series,
                      higher_is_better: bool = True) -> pd.Series:
    """Return deterministic 0.1-1.0 percentile scores; missing values remain NaN."""
    series = pd.Series(values, dtype='float64')
    valid = series.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index, dtype='float64')
    ranks = valid.rank(method='average', pct=True, ascending=higher_is_better)
    result = pd.Series(np.nan, index=series.index, dtype='float64')
    result.loc[ranks.index] = 0.1 + 0.9 * ranks
    return result


def _finite(value: Any) -> bool:
    return value is not None and np.isfinite(value)


def _factor_score(percentile: float, weight: float) -> float:
    return float(np.clip(percentile * weight, 0.0, weight))


def calculate_momentum_scores(indicators: Mapping[str, Mapping[str, Any]],
                              weight: float = SCORE_WEIGHTS['momentum']) -> dict[str, float]:
    """Score the weighted 1M/3M/6M/12M return composite cross-sectionally."""
    composites = {}
    for symbol, values in indicators.items():
        available = [period for period in MOMENTUM_PERIOD_WEIGHTS
                     if _finite(values.get(f'return_{period}'))]
        if set(available) != set(MOMENTUM_PERIOD_WEIGHTS):
            composites[symbol] = np.nan
        else:
            composites[symbol] = sum(MOMENTUM_PERIOD_WEIGHTS[period] * values[f'return_{period}']
                                     for period in MOMENTUM_PERIOD_WEIGHTS)
    ranks = percentile_scores(composites)
    return {symbol: _factor_score(ranks[symbol], weight) if _finite(ranks[symbol]) else np.nan
            for symbol in indicators}


def calculate_trend_score(values: Mapping[str, Any], weight: float = SCORE_WEIGHTS['trend']) -> float:
    """Score four non-binary trend relationships, each contributing one quarter."""
    required = ('current_price', 'sma_20', 'sma_50', 'sma_200')
    if not all(_finite(values.get(key)) for key in required):
        return np.nan
    relationships = (
        values['current_price'] > values['sma_20'],
        values['current_price'] > values['sma_50'],
        values['current_price'] > values['sma_200'],
        values['sma_50'] > values['sma_200'],
    )
    return float(weight * sum(relationships) / len(relationships))


def calculate_relative_strength_scores(
        indicators: Mapping[str, Mapping[str, Any]],
        benchmark_returns: Mapping[str, float],
        weight: float = SCORE_WEIGHTS['relative_strength']) -> dict[str, float]:
    """Rank weighted excess 3M/6M/12M returns versus caller-supplied benchmarks."""
    composites = {}
    for symbol, values in indicators.items():
        periods = ('3m', '6m', '12m')
        if not all(_finite(values.get(f'return_{p}')) and _finite(benchmark_returns.get(p)) for p in periods):
            composites[symbol] = np.nan
        else:
            composites[symbol] = (0.25 * (values['return_3m'] - benchmark_returns['3m'])
                                  + 0.45 * (values['return_6m'] - benchmark_returns['6m'])
                                  + 0.30 * (values['return_12m'] - benchmark_returns['12m']))
    ranks = percentile_scores(composites)
    return {symbol: _factor_score(ranks[symbol], weight) if _finite(ranks[symbol]) else np.nan
            for symbol in indicators}


def calculate_volume_scores(indicators: Mapping[str, Mapping[str, Any]],
                            weight: float = SCORE_WEIGHTS['volume']) -> dict[str, float]:
    """Rank volume participation using volume SMA20/SMA60."""
    ranks = percentile_scores({s: v.get('volume_ratio') for s, v in indicators.items()})
    return {s: _factor_score(ranks[s], weight) if _finite(ranks[s]) else np.nan for s in indicators}


def calculate_rsi_score(values: Mapping[str, Any], weight: float = SCORE_WEIGHTS['rsi']) -> float:
    """Smoothly score RSI, favoring 50-65 and penalizing overheating above 80."""
    rsi = values.get('rsi_14')
    if not _finite(rsi) or not 0 <= rsi <= 100:
        return np.nan
    if rsi <= 50:
        normalized = 0.25 + 0.75 * rsi / 50
    elif rsi <= 65:
        normalized = 1.0
    elif rsi <= 80:
        normalized = 1.0 - 0.35 * (rsi - 65) / 15
    else:
        normalized = max(0.0, 0.65 - 0.65 * (rsi - 80) / 20)
    return float(weight * normalized)


def calculate_52_week_strength_score(values: Mapping[str, Any],
                                     weight: float = SCORE_WEIGHTS['52_week_strength']) -> float:
    """Reward range position primarily and proximity to the high secondarily."""
    position = values.get('position_in_52w_range')
    distance = values.get('distance_from_52w_high')
    if not _finite(position) or not _finite(distance):
        return np.nan
    normalized = 0.7 * np.clip(position, 0, 1) + 0.3 * np.clip(1 + distance, 0, 1)
    return float(weight * normalized)


def calculate_risk_scores(indicators: Mapping[str, Mapping[str, Any]],
                          weight: float = SCORE_WEIGHTS['risk']) -> dict[str, float]:
    """Rank low volatility and shallow drawdown as better risk characteristics."""
    volatility = percentile_scores({s: v.get('volatility_annualized') for s, v in indicators.items()}, False)
    drawdown = percentile_scores({s: v.get('max_drawdown') for s, v in indicators.items()})
    result = {}
    for symbol in indicators:
        if _finite(volatility[symbol]) and _finite(drawdown[symbol]):
            result[symbol] = _factor_score(0.5 * volatility[symbol] + 0.5 * drawdown[symbol], weight)
        else:
            result[symbol] = np.nan
    return result


def _explanations(values: Mapping[str, Any], factor_scores: Mapping[str, float]) -> dict[str, list[str]]:
    strengths, weaknesses = [], []
    if factor_scores['momentum'] >= SCORE_WEIGHTS['momentum'] * 0.75:
        strengths.append('Strong momentum')
    if factor_scores['trend'] >= SCORE_WEIGHTS['trend'] * 0.75:
        strengths.append('Constructive moving-average trend')
    if factor_scores['relative_strength'] >= SCORE_WEIGHTS['relative_strength'] * 0.75:
        strengths.append('Strong relative performance')
    if factor_scores['volume'] >= SCORE_WEIGHTS['volume'] * 0.75:
        strengths.append('Strong volume participation')
    if _finite(values.get('rsi_14')) and 50 <= values['rsi_14'] <= 65:
        strengths.append('Healthy RSI zone')
    if _finite(values.get('volatility_annualized')) and values['volatility_annualized'] > 0.35:
        weaknesses.append('Elevated volatility')
    if _finite(values.get('max_drawdown')) and values['max_drawdown'] < -0.30:
        weaknesses.append('Deep historical drawdown')
    if _finite(values.get('rsi_14')) and values['rsi_14'] > 80:
        weaknesses.append('Overheated RSI')
    return {'strengths': strengths, 'weaknesses': weaknesses}


def score_universe(indicators: Mapping[str, Mapping[str, Any]],
                   benchmark_returns: Mapping[str, float],
                   weights: Mapping[str, float] | None = None) -> dict[str, dict[str, Any]]:
    """Score every stock in a universe; incomplete stocks are never ranked."""
    validate_weights(weights)
    weights = SCORE_WEIGHTS if weights is None else weights
    momentum = calculate_momentum_scores(indicators, weights['momentum'])
    relative = calculate_relative_strength_scores(indicators, benchmark_returns, weights['relative_strength'])
    volume = calculate_volume_scores(indicators, weights['volume'])
    risk = calculate_risk_scores(indicators, weights['risk'])
    results = {}
    for symbol, values in indicators.items():
        missing = sorted(key for key in REQUIRED_INDICATORS if not _finite(values.get(key)))
        factor_scores = {
            'momentum': momentum[symbol],
            'trend': calculate_trend_score(values, weights['trend']),
            'relative_strength': relative[symbol],
            'volume': volume[symbol],
            'rsi': calculate_rsi_score(values, weights['rsi']),
            '52_week_strength': calculate_52_week_strength_score(values, weights['52_week_strength']),
            'risk': risk[symbol],
        }
        incomplete_factors = [name for name, score in factor_scores.items() if not _finite(score)]
        if missing or incomplete_factors:
            results[symbol] = {
                'symbol': symbol, 'overall_score': np.nan, 'score_status': 'INSUFFICIENT_DATA',
                'missing_indicators': missing, 'factor_scores': factor_scores,
                'explanations': {'strengths': [], 'weaknesses': ['Insufficient data']},
            }
            continue
        overall = float(np.clip(sum(factor_scores.values()), 0.0, 100.0))
        results[symbol] = {
            'symbol': symbol, 'overall_score': overall, 'score_status': 'OK',
            'missing_indicators': [], 'factor_scores': factor_scores,
            'explanations': _explanations(values, factor_scores),
        }
    return results


def score_stock(stock_data: Mapping[str, Any], universe: Mapping[str, Mapping[str, Any]] | None = None,
                benchmark_returns: Mapping[str, float] | None = None) -> dict[str, Any]:
    """Compatibility wrapper for one stock; cross-sectional scoring needs a universe."""
    symbol = str(stock_data.get('symbol', 'UNKNOWN'))
    universe = {symbol: stock_data} if universe is None else universe
    if benchmark_returns is None:
        benchmark_returns = {period: 0.0 for period in ('3m', '6m', '12m')}
    return score_universe(universe, benchmark_returns)[symbol]
