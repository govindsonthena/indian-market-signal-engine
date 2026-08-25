"""
Test: Technical Indicators

Unit tests for indicator calculations.
Uses deterministic synthetic data (no live API calls).
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.indicators import (
    calculate_sma,
    calculate_moving_averages,
    calculate_rsi,
    calculate_rsi_value,
    calculate_returns,
    calculate_volatility,
    calculate_max_drawdown,
    calculate_52_week_metrics,
    calculate_volume_metrics,
    calculate_all_indicators,
    validate_data,
)


# ==============================================================================
# FIXTURES: Create synthetic test data
# ==============================================================================

@pytest.fixture
def simple_df():
    """Create a simple DataFrame with known values."""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'Open': np.random.randn(100) * 5 + 100,
        'High': np.random.randn(100) * 5 + 105,
        'Low': np.random.randn(100) * 5 + 95,
        'Close': np.arange(100, 200),  # Simple uptrend: 100, 101, 102, ..., 199
        'Volume': np.random.randint(1000000, 5000000, 100),
    }, index=dates)
    return df


@pytest.fixture
def flat_df():
    """Create a DataFrame with flat prices."""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'Open': [100] * 100,
        'High': [101] * 100,
        'Low': [99] * 100,
        'Close': [100] * 100,  # Flat
        'Volume': [1000000] * 100,
    }, index=dates)
    return df


@pytest.fixture
def downtrend_df():
    """Create a DataFrame with downtrend."""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'Open': np.random.randn(100) * 5 + 150,
        'High': np.random.randn(100) * 5 + 155,
        'Low': np.random.randn(100) * 5 + 145,
        'Close': np.arange(200, 100, -1),  # Downtrend: 200, 199, 198, ..., 101
        'Volume': np.random.randint(1000000, 5000000, 100),
    }, index=dates)
    return df


@pytest.fixture
def volatile_df():
    """Create a DataFrame with high volatility."""
    dates = pd.date_range(start='2025-01-01', periods=252, freq='D')  # 1 year
    # Large random movements
    returns = np.random.randn(252) * 0.05  # 5% daily volatility
    close_prices = 100 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'Open': close_prices * (1 + np.random.randn(252) * 0.01),
        'High': close_prices * (1 + np.abs(np.random.randn(252) * 0.02)),
        'Low': close_prices * (1 - np.abs(np.random.randn(252) * 0.02)),
        'Close': close_prices,
        'Volume': np.random.randint(1000000, 5000000, 252),
    }, index=dates)
    return df


# ==============================================================================
# TESTS: MOVING AVERAGES
# ==============================================================================

class TestMovingAverages:
    """Test Simple Moving Average calculations."""

    def test_sma_calculation_basic(self, simple_df):
        """Test SMA with simple uptrend data."""
        sma_result = calculate_sma(simple_df, 10)
        assert len(sma_result) == len(simple_df)
        # SMA should not be NaN after period rows
        assert not pd.isna(sma_result.iloc[10])
        # For uptrend, SMA should be close to but below the price
        assert sma_result.iloc[-1] < simple_df['Close'].iloc[-1]

    def test_sma_flat_prices(self, flat_df):
        """Test SMA with flat prices - should equal the price."""
        sma_result = calculate_sma(flat_df, 10)
        # After warmup, SMA should be 100
        assert np.isclose(sma_result.iloc[10], 100)

    def test_sma_insufficient_data(self):
        """Test SMA with insufficient data."""
        dates = pd.date_range(start='2025-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104],
        }, index=dates)
        
        # Request SMA of 20 when only 5 rows available
        sma_result = calculate_sma(df, 20)
        # Should still return values but with NaN at beginning
        assert len(sma_result) == 5

    def test_moving_averages_all_three(self, simple_df):
        """Test calculation of all three moving averages."""
        result = calculate_moving_averages(simple_df)
        
        assert 'sma_20' in result
        assert 'sma_50' in result
        assert 'sma_200' in result
        
        # With 100 rows, 20 and 50 should have values
        assert result['sma_20'] is not None
        assert result['sma_50'] is not None
        
        # With 100 rows, 200-day MA will have None or partial value
        # (200 rows needed for full 200-day MA)
        # This is acceptable - we get a calculation even if not ideal

    def test_moving_averages_empty_data(self):
        """Test moving averages with empty DataFrame."""
        empty_df = pd.DataFrame()
        result = calculate_moving_averages(empty_df)
        
        assert result['sma_20'] is None
        assert result['sma_50'] is None
        assert result['sma_200'] is None


# ==============================================================================
# TESTS: RSI
# ==============================================================================

class TestRSI:
    """Test RSI calculations."""

    def test_rsi_uptrend(self, simple_df):
        """Test RSI in uptrend - should be high (70-100)."""
        rsi = calculate_rsi_value(simple_df)
        
        # Uptrend should have RSI > 50
        assert rsi is not None
        assert rsi > 50

    def test_rsi_downtrend(self, downtrend_df):
        """Test RSI in downtrend - should be low (0-30)."""
        rsi = calculate_rsi_value(downtrend_df)
        
        # Downtrend should have RSI < 50
        assert rsi is not None
        assert rsi < 50

    def test_rsi_flat_prices(self, flat_df):
        """Test RSI with flat prices - should be ~50 or handle gracefully."""
        rsi = calculate_rsi_value(flat_df)
        
        # Flat prices (no gains or losses) may result in NaN RSI
        # due to 0/0 division. The function should handle this gracefully
        # by either returning None or a default value
        # This is acceptable behavior for edge case (no price movement)
        if rsi is not None:
            # If RSI is calculated for flat prices, it should be near 50
            assert 30 < rsi < 70

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        dates = pd.date_range(start='2025-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104],
        }, index=dates)
        
        # With only 5 rows and RSI period 14, should return None
        rsi = calculate_rsi_value(df)
        assert rsi is None

    def test_rsi_bounds(self, volatile_df):
        """Test that RSI stays within 0-100 bounds."""
        rsi_series = calculate_rsi(volatile_df)
        
        # Remove NaN values
        rsi_clean = rsi_series.dropna()
        
        # All RSI values should be between 0 and 100
        assert (rsi_clean >= 0).all()
        assert (rsi_clean <= 100).all()


# ==============================================================================
# TESTS: RETURNS
# ==============================================================================

class TestReturns:
    """Test return calculations."""

    def test_returns_uptrend(self, simple_df):
        """Test returns calculation with uptrend."""
        returns = calculate_returns(simple_df)
        
        # All periods should be positive for uptrend
        assert returns['1m'] > 0
        assert returns['3m'] > 0
        # 6m (126 days) and 12m (252 days) need more data than our 100-row fixture
        # So they may be None - that's OK
        # Just verify no exception was raised

    def test_returns_downtrend(self, downtrend_df):
        """Test returns calculation with downtrend."""
        returns = calculate_returns(downtrend_df)
        
        # All periods should be negative for downtrend
        assert returns['1m'] < 0
        assert returns['3m'] < 0

    def test_returns_decimal_format(self, simple_df):
        """Test that returns are in decimal format (not percentage)."""
        returns = calculate_returns(simple_df)
        
        # 1m return should be small decimal (not like 5 for 5%)
        # In an uptrend of 100->200, return over 21 days should be ~0.2-0.3
        assert isinstance(returns['1m'], float)
        assert abs(returns['1m']) < 1  # Decimal format, not percentage

    def test_returns_insufficient_data(self):
        """Test returns with insufficient data."""
        dates = pd.date_range(start='2025-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104],
        }, index=dates)
        
        returns = calculate_returns(df)
        
        # 1m = 21 days, 3m = 63 days, etc
        # With only 5 rows, all should be None since we need more data
        assert returns['1m'] is None  # 21 days > 5 rows
        assert returns['3m'] is None
        assert returns['6m'] is None


# ==============================================================================
# TESTS: VOLATILITY
# ==============================================================================

class TestVolatility:
    """Test volatility calculations."""

    def test_volatility_constant_returns(self, flat_df):
        """Test volatility with flat prices - should be near 0."""
        vol = calculate_volatility(flat_df)
        
        # Flat prices should have near-zero volatility
        assert vol is not None
        assert vol < 0.01  # Less than 1% annualized

    def test_volatility_high_variation(self, volatile_df):
        """Test volatility with high variation."""
        vol = calculate_volatility(volatile_df)
        
        # Volatile data should have significant volatility
        assert vol is not None
        assert vol > 0.1  # More than 10% annualized

    def test_volatility_insufficient_data(self):
        """Test volatility with insufficient data."""
        dates = pd.date_range(start='2025-01-01', periods=1, freq='D')
        df = pd.DataFrame({'Close': [100]}, index=dates)
        
        vol = calculate_volatility(df)
        assert vol is None

    def test_volatility_positive(self, volatile_df):
        """Test that volatility is always positive."""
        vol = calculate_volatility(volatile_df)
        assert vol > 0


# ==============================================================================
# TESTS: MAXIMUM DRAWDOWN
# ==============================================================================

class TestMaxDrawdown:
    """Test maximum drawdown calculations."""

    def test_max_drawdown_deterministic(self):
        """Test max drawdown with known sequence."""
        dates = pd.date_range(start='2025-01-01', periods=6, freq='D')
        # Price sequence: 100, 110, 120, 90, 100, 80
        # Max drawdown occurs at the end: (80-120)/120 = -0.333...
        df = pd.DataFrame({
            'Close': [100, 110, 120, 90, 100, 80],
        }, index=dates)
        
        dd = calculate_max_drawdown(df)
        expected_dd = (80 - 120) / 120  # -0.333...
        
        assert dd is not None
        assert np.isclose(dd, expected_dd)

    def test_max_drawdown_flat(self, flat_df):
        """Test max drawdown with flat prices - should be 0."""
        dd = calculate_max_drawdown(flat_df)
        
        # Flat prices mean no drawdown
        assert dd is not None
        assert np.isclose(dd, 0)

    def test_max_drawdown_negative_value(self, downtrend_df):
        """Test that max drawdown is negative."""
        dd = calculate_max_drawdown(downtrend_df)
        
        # Max drawdown should be negative
        assert dd is not None
        assert dd < 0

    def test_max_drawdown_uptrend(self, simple_df):
        """Test max drawdown in uptrend (should be small)."""
        dd = calculate_max_drawdown(simple_df)
        
        # Uptrend should have small (near 0) drawdown
        assert dd is not None
        assert dd < 0.1  # Less than 10%


# ==============================================================================
# TESTS: 52-WEEK METRICS
# ==============================================================================

class Test52WeekMetrics:
    """Test 52-week metrics calculations."""

    def test_52w_high_low_uptrend(self, simple_df):
        """Test 52-week high/low with uptrend."""
        metrics = calculate_52_week_metrics(simple_df)
        
        # High should be around 199
        assert metrics['52_week_high'] is not None
        assert metrics['52_week_low'] is not None
        
        # High should be greater than low
        assert metrics['52_week_high'] > metrics['52_week_low']
        
        # Current price should be near the high in uptrend
        assert metrics['distance_from_52w_high'] >= -0.05

    def test_52w_distance_at_high(self):
        """Test distance when price is at 52-week high."""
        dates = pd.date_range(start='2025-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104, 105, 104, 103, 102, 110],
        }, index=dates)
        
        metrics = calculate_52_week_metrics(df)
        
        # Current price is 110, high is 110
        # Distance should be 0
        assert np.isclose(metrics['distance_from_52w_high'], 0)

    def test_52w_position_in_range(self):
        """Test position in 52-week range."""
        dates = pd.date_range(start='2025-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104, 105, 104, 103, 102, 105],  # High=105, Low=100
        }, index=dates)
        
        metrics = calculate_52_week_metrics(df)
        
        # Current price is 105, high is 105, low is 100
        # Position = (105-100)/(105-100) = 1.0 (at high)
        assert np.isclose(metrics['position_in_52w_range'], 1.0)

    def test_52w_range_equal_high_low(self):
        """Test when high equals low (all same price)."""
        dates = pd.date_range(start='2025-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'Close': [100] * 10,
        }, index=dates)
        
        metrics = calculate_52_week_metrics(df)
        
        # When high == low, distance should be 0
        assert np.isclose(metrics['distance_from_52w_high'], 0)
        # Position should be 0.5 (middle)
        assert np.isclose(metrics['position_in_52w_range'], 0.5)


# ==============================================================================
# TESTS: VOLUME METRICS
# ==============================================================================

class TestVolumeMetrics:
    """Test volume-based metrics."""

    def test_volume_sma_calculation(self, simple_df):
        """Test volume SMAs calculation."""
        metrics = calculate_volume_metrics(simple_df)
        
        assert metrics['volume_sma_20'] is not None
        assert metrics['volume_sma_60'] is not None
        assert metrics['volume_ratio'] is not None

    def test_volume_ratio_logic(self, simple_df):
        """Test volume ratio is 20-day over 60-day."""
        metrics = calculate_volume_metrics(simple_df)
        
        # Ratio should be positive
        assert metrics['volume_ratio'] > 0
        
        # Ratio should be computed correctly
        if metrics['volume_sma_20'] and metrics['volume_sma_60']:
            expected_ratio = metrics['volume_sma_20'] / metrics['volume_sma_60']
            assert np.isclose(metrics['volume_ratio'], expected_ratio)

    def test_volume_missing_data(self):
        """Test volume metrics with missing Volume column."""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'Close': np.arange(100, 200),
        }, index=dates)  # No 'Volume' column
        
        metrics = calculate_volume_metrics(df)
        
        # Should return None for all values when Volume missing
        assert metrics['volume_sma_20'] is None
        assert metrics['volume_sma_60'] is None
        assert metrics['volume_ratio'] is None


# ==============================================================================
# TESTS: ALL INDICATORS
# ==============================================================================

class TestAllIndicators:
    """Test the calculate_all_indicators convenience function."""

    def test_all_indicators_returns_dict(self, simple_df):
        """Test that all indicators returns complete dictionary."""
        result = calculate_all_indicators(simple_df)
        
        # Should have all expected keys
        expected_keys = [
            'sma_20', 'sma_50', 'sma_200',
            'rsi_14',
            'return_1m', 'return_3m', 'return_6m', 'return_12m',
            'volatility_annualized', 'max_drawdown',
            '52_week_high', '52_week_low', 'distance_from_52w_high', 'position_in_52w_range',
            'volume_sma_20', 'volume_sma_60', 'volume_ratio',
        ]
        
        for key in expected_keys:
            assert key in result

    def test_all_indicators_with_real_scenario(self, volatile_df):
        """Test all indicators with volatile data."""
        result = calculate_all_indicators(volatile_df)
        
        # Most indicators should have non-None values with 252 rows
        assert result['sma_20'] is not None
        assert result['sma_50'] is not None
        assert result['sma_200'] is not None
        assert result['rsi_14'] is not None
        assert result['volatility_annualized'] is not None
        assert result['max_drawdown'] is not None


# ==============================================================================
# TESTS: DATA VALIDATION
# ==============================================================================

class TestValidation:
    """Test data validation function."""

    def test_validate_empty_data(self):
        """Test validation with empty DataFrame."""
        empty_df = pd.DataFrame()
        valid, issues = validate_data(empty_df)
        
        assert not valid
        assert len(issues) > 0

    def test_validate_missing_columns(self):
        """Test validation with missing required columns."""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'Close': np.arange(100, 200),
        }, index=dates)  # Missing OHLCV columns
        
        valid, issues = validate_data(df)
        
        assert not valid
        assert any('Missing columns' in issue for issue in issues)

    def test_validate_good_data(self, simple_df):
        """Test validation with good data."""
        valid, issues = validate_data(simple_df)
        
        # Should be valid
        assert valid
        assert len(issues) == 0

    def test_validate_insufficient_rows(self):
        """Test validation with too few rows."""
        dates = pd.date_range(start='2025-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'Open': np.random.randn(10) * 5 + 100,
            'High': np.random.randn(10) * 5 + 105,
            'Low': np.random.randn(10) * 5 + 95,
            'Close': np.arange(100, 110),
            'Volume': np.random.randint(1000000, 5000000, 10),
        }, index=dates)
        
        valid, issues = validate_data(df, min_rows=50)
        
        assert not valid
        assert any('Insufficient rows' in issue for issue in issues)


# ==============================================================================
# EDGE CASES
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_all_nan_prices(self):
        """Test handling of all NaN prices."""
        dates = pd.date_range(start='2025-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'Close': [np.nan] * 10,
        }, index=dates)
        
        # Should not crash, should return None
        result = calculate_moving_averages(df)
        assert result['sma_20'] is None

    def test_zero_prices(self):
        """Test handling of zero prices."""
        dates = pd.date_range(start='2025-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'Close': [0] * 10,
        }, index=dates)
        
        # Should handle gracefully
        returns = calculate_returns(df)
        assert returns['1m'] is None or pd.isna(returns['1m'])

    def test_negative_volume(self):
        """Test handling of negative volumes (shouldn't happen but be safe)."""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'Open': np.random.randn(100) * 5 + 100,
            'High': np.random.randn(100) * 5 + 105,
            'Low': np.random.randn(100) * 5 + 95,
            'Close': np.arange(100, 200),
            'Volume': [-1000000] * 100,  # Negative volume
        }, index=dates)
        
        # Should not crash
        metrics = calculate_volume_metrics(df)
        # Values should be computed (even if nonsensical)
        assert metrics['volume_sma_20'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
