"""
Technical Indicators Module

Calculates technical indicators for market analysis.
All calculations are deterministic and do not depend on live API calls.

Returns are represented as decimal values internally:
    0.10 = 10%
    -0.05 = -5%

Volatility is annualized (standard deviation).

Drawdown is represented as negative decimals:
    -0.25 = -25% maximum drawdown
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple

from src.config import (
    DMA_20, DMA_50, DMA_200,
    RSI_PERIOD,
    VOLUME_20_DAY_PERIOD, VOLUME_60_DAY_PERIOD,
    TRADING_DAYS_PER_YEAR,
    VOLATILITY_LOOKBACK_DAYS,
    FIFTY_TWO_WEEK_DAYS,
    MOMENTUM_PERIODS,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# MOVING AVERAGES
# ==============================================================================

def calculate_sma(data: pd.DataFrame, period: int, column: str = 'Close') -> pd.Series:
    """
    Calculate Simple Moving Average.

    Args:
        data: DataFrame with OHLCV data. Date should be in index.
        period: Number of days for the moving average
        column: Column name to use (default: 'Close')

    Returns:
        Series with SMA values. NaN where insufficient data.
    """
    if data is None or len(data) == 0:
        return pd.Series(dtype=float)

    if column not in data.columns:
        raise ValueError(f"Column '{column}' not found in data")

    return data[column].rolling(window=period, min_periods=1).mean()


def calculate_moving_averages(data: pd.DataFrame) -> Dict[str, Optional[float]]:
    """
    Calculate all standard moving averages (20, 50, 200).

    Args:
        data: DataFrame with OHLCV data (Close price in 'Close' column)

    Returns:
        Dictionary with keys 'sma_20', 'sma_50', 'sma_200' (or None if insufficient data)
    """
    result = {
        'sma_20': None,
        'sma_50': None,
        'sma_200': None,
    }

    if data is None or len(data) == 0:
        return result

    try:
        sma_20 = calculate_sma(data, DMA_20)
        sma_50 = calculate_sma(data, DMA_50)
        sma_200 = calculate_sma(data, DMA_200)

        # Extract scalar values safely
        if len(sma_20) > 0:
            val = sma_20.iloc[-1]
            if not pd.isna(val):
                result['sma_20'] = float(val)
        
        if len(sma_50) > 0:
            val = sma_50.iloc[-1]
            if not pd.isna(val):
                result['sma_50'] = float(val)
        
        if len(sma_200) > 0:
            val = sma_200.iloc[-1]
            if not pd.isna(val):
                result['sma_200'] = float(val)
    except Exception as e:
        logger.warning(f"Error calculating moving averages: {e}")

    return result

# ==============================================================================
# RSI (RELATIVE STRENGTH INDEX)
# ==============================================================================

def calculate_rsi(data: pd.DataFrame, period: int = RSI_PERIOD, column: str = 'Close') -> pd.Series:
    """
    Calculate RSI (Relative Strength Index) using Wilder's Smoothing Method.

    Args:
        data: DataFrame with OHLCV data
        period: RSI period (default: 14)
        column: Column to use (default: 'Close')

    Returns:
        Series with RSI values (0-100). NaN where insufficient data.

    Formula:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss

    Uses Wilder's smoothing (exponential moving average).
    """
    if data is None or len(data) == 0 or len(data) < period + 1:
        return pd.Series(dtype=float)

    if column not in data.columns:
        raise ValueError(f"Column '{column}' not found in data")

    close = data[column]

    # Calculate price changes
    delta = close.diff()

    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Use Wilder's smoothing (EMA with alpha = 1/period)
    alpha = 1.0 / period
    avg_gain = gains.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = losses.ewm(alpha=alpha, adjust=False).mean()

    # Avoid division by zero
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    # RSI should be between 0 and 100
    rsi = rsi.clip(0, 100)

    return rsi


def calculate_rsi_value(data: pd.DataFrame, period: int = RSI_PERIOD) -> Optional[float]:
    """
    Get the latest RSI value.

    Args:
        data: DataFrame with OHLCV data
        period: RSI period (default: 14)

    Returns:
        Latest RSI value (0-100) or None if insufficient data
    """
    if data is None or len(data) == 0 or len(data) < period + 1:
        return None

    try:
        rsi_series = calculate_rsi(data, period)
        return rsi_series.iloc[-1] if len(rsi_series) > 0 and not pd.isna(rsi_series.iloc[-1]) else None
    except Exception as e:
        logger.warning(f"Error calculating RSI: {e}")
        return None


# ==============================================================================
# RETURNS
# ==============================================================================

def calculate_returns(data: pd.DataFrame, periods: Optional[Dict[str, int]] = None) -> Dict[str, Optional[float]]:
    """
    Calculate returns for specified periods.

    Returns are calculated as: (price_now - price_then) / price_then
    Represented as decimals: 0.10 = 10% return, -0.05 = -5% return

    Args:
        data: DataFrame with OHLCV data
        periods: Dict mapping period name to number of days.
                If None, uses MOMENTUM_PERIODS from config.

    Returns:
        Dictionary with return values for each period.
        Returns None for insufficient data periods.

    Examples:
        {'1m': 0.05, '3m': 0.12, '6m': -0.03, '12m': 0.25}
    """
    if periods is None:
        periods = MOMENTUM_PERIODS

    result = {}

    if data is None or len(data) == 0:
        return {key: None for key in periods.keys()}

    try:
        current_price = float(data['Close'].iloc[-1])

        for period_name, num_days in periods.items():
            if len(data) > num_days:
                past_price = float(data['Close'].iloc[-num_days - 1])
                if past_price > 0:
                    ret = (current_price - past_price) / past_price
                    result[period_name] = float(ret)
                else:
                    result[period_name] = None
            else:
                result[period_name] = None

    except Exception as e:
        logger.warning(f"Error calculating returns: {e}")
        result = {key: None for key in periods.keys()}

    return result


# ==============================================================================
# VOLATILITY (ANNUALIZED)
# ==============================================================================

def calculate_volatility(data: pd.DataFrame, lookback_days: int = VOLATILITY_LOOKBACK_DAYS) -> Optional[float]:
    """
    Calculate annualized historical volatility.

    Uses daily log returns and annualizes by multiplying by sqrt(252).

    Args:
        data: DataFrame with OHLCV data
        lookback_days: Number of days to use (default: 252, full year)

    Returns:
        Annualized volatility as decimal (0.15 = 15% volatility)
        Returns None if insufficient data or error.

    Formula:
        Daily returns = log(price_t / price_t-1)
        Volatility = std(daily_returns) * sqrt(252)
    """
    if data is None or len(data) == 0 or len(data) < 2:
        return None

    try:
        # Use available data up to lookback_days
        close_prices = data['Close'].iloc[-lookback_days:] if len(data) > lookback_days else data['Close']

        if len(close_prices) < 2:
            return None

        # Calculate log returns
        log_returns = np.log(close_prices / close_prices.shift(1))

        # Remove NaN from first row
        log_returns = log_returns.dropna()

        if len(log_returns) < 1:
            return None

        # Calculate standard deviation
        daily_volatility = log_returns.std()

        # Annualize
        annualized_volatility = daily_volatility * np.sqrt(TRADING_DAYS_PER_YEAR)

        return float(annualized_volatility)

    except Exception as e:
        logger.warning(f"Error calculating volatility: {e}")
        return None


# ==============================================================================
# MAXIMUM DRAWDOWN
# ==============================================================================

def calculate_max_drawdown(data: pd.DataFrame) -> Optional[float]:
    """
    Calculate maximum drawdown over the available period.

    Drawdown is represented as negative decimal:
        -0.25 = -25% maximum drawdown

    Args:
        data: DataFrame with OHLCV data

    Returns:
        Maximum drawdown as negative decimal, or None if error.

    Formula:
        Drawdown_t = (Price_t - MaxPrice_0_to_t) / MaxPrice_0_to_t
        Max Drawdown = min(Drawdown_t)
    """
    if data is None or len(data) == 0 or len(data) < 1:
        return None

    try:
        close_prices = data['Close']

        # Calculate cumulative maximum
        cummax = close_prices.cummax()

        # Calculate drawdown at each point
        drawdown = (close_prices - cummax) / cummax

        # Maximum drawdown is the minimum value
        max_dd = drawdown.min()

        return float(max_dd) if not pd.isna(max_dd) else None

    except Exception as e:
        logger.warning(f"Error calculating max drawdown: {e}")
        return None


# ==============================================================================
# 52-WEEK METRICS
# ==============================================================================

def calculate_52_week_metrics(data: pd.DataFrame, weeks: int = 52) -> Dict[str, Optional[float]]:
    """
    Calculate 52-week (or custom period) high, low, and related metrics.

    Args:
        data: DataFrame with OHLCV data
        weeks: Number of weeks to consider (default: 52)

    Returns:
        Dictionary with:
            - '52_week_high': Highest close in period
            - '52_week_low': Lowest close in period
            - 'distance_from_52w_high': (current / high) - 1
              (0.00 = at high, -0.05 = 5% below high)
            - 'position_in_52w_range': (current - low) / (high - low)
              (0.0 = at low, 1.0 = at high, 0.5 = midpoint)
    """
    result = {
        '52_week_high': None,
        '52_week_low': None,
        'distance_from_52w_high': None,
        'position_in_52w_range': None,
    }

    if data is None or len(data) == 0 or len(data) < 1:
        return result

    try:
        # Use 52 weeks = ~252 trading days
        lookback_days = weeks * 5  # Approximate trading days

        # Use available data or lookback period
        if len(data) > lookback_days:
            close_data = data['Close'].iloc[-lookback_days:]
        else:
            close_data = data['Close']

        current_price = float(close_data.iloc[-1])
        high_52w = float(close_data.max())
        low_52w = float(close_data.min())

        result['52_week_high'] = float(high_52w)
        result['52_week_low'] = float(low_52w)

        # Distance from high: (current / high) - 1
        if high_52w > 0:
            result['distance_from_52w_high'] = float((current_price / high_52w) - 1)

        # Position in range: (current - low) / (high - low)
        range_width = high_52w - low_52w
        if range_width > 0:
            result['position_in_52w_range'] = float((current_price - low_52w) / range_width)
        elif range_width == 0:
            # All prices were the same
            result['position_in_52w_range'] = 0.5

    except Exception as e:
        logger.warning(f"Error calculating 52-week metrics: {e}")

    return result


# ==============================================================================
# VOLUME METRICS
# ==============================================================================

def calculate_volume_metrics(data: pd.DataFrame) -> Dict[str, Optional[float]]:
    """
    Calculate volume-based metrics.

    Args:
        data: DataFrame with OHLCV data

    Returns:
        Dictionary with:
            - 'volume_sma_20': 20-day average volume
            - 'volume_sma_60': 60-day average volume
            - 'volume_ratio': volume_sma_20 / volume_sma_60
    """
    result = {
        'volume_sma_20': None,
        'volume_sma_60': None,
        'volume_ratio': None,
    }

    if data is None or len(data) == 0 or 'Volume' not in data.columns:
        return result

    try:
        volume = data['Volume']

        # Calculate SMAs
        vol_sma_20 = calculate_sma(data, VOLUME_20_DAY_PERIOD, column='Volume')
        vol_sma_60 = calculate_sma(data, VOLUME_60_DAY_PERIOD, column='Volume')

        # Get latest values
        if len(vol_sma_20) > 0 and not pd.isna(vol_sma_20.iloc[-1]):
            result['volume_sma_20'] = float(vol_sma_20.iloc[-1])

        if len(vol_sma_60) > 0 and not pd.isna(vol_sma_60.iloc[-1]):
            result['volume_sma_60'] = float(vol_sma_60.iloc[-1])

        # Calculate ratio (handle division by zero)
        if result['volume_sma_60'] and result['volume_sma_60'] > 0:
            result['volume_ratio'] = float(result['volume_sma_20'] / result['volume_sma_60'])

    except Exception as e:
        logger.warning(f"Error calculating volume metrics: {e}")

    return result


# ==============================================================================
# ALL INDICATORS - CONVENIENCE FUNCTION
# ==============================================================================

def calculate_all_indicators(data: pd.DataFrame) -> Dict[str, any]:
    """
    Calculate all technical indicators for a stock.

    Args:
        data: DataFrame with OHLCV data (Date in index, OHLCV in columns)
               Handles both simple column names and MultiIndex columns from Yahoo Finance

    Returns:
        Dictionary with all indicator values:
        {
            'sma_20': float or None,
            'sma_50': float or None,
            'sma_200': float or None,
            'rsi_14': float or None,
            'return_1m': float or None,
            'return_3m': float or None,
            'return_6m': float or None,
            'return_12m': float or None,
            'volatility_annualized': float or None,
            'max_drawdown': float or None,
            '52_week_high': float or None,
            '52_week_low': float or None,
            'distance_from_52w_high': float or None,
            'position_in_52w_range': float or None,
            'volume_sma_20': float or None,
            'volume_sma_60': float or None,
            'volume_ratio': float or None,
        }
    """
    result = {}

    # Handle Yahoo Finance MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        # Convert MultiIndex to simple columns by taking the first level
        data = data.copy()
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]

    # Moving averages
    mas = calculate_moving_averages(data)
    result.update(mas)

    # RSI
    result['rsi_14'] = calculate_rsi_value(data)

    # Returns
    returns = calculate_returns(data)
    for period, value in returns.items():
        result[f'return_{period}'] = value

    # Volatility
    result['volatility_annualized'] = calculate_volatility(data)

    # Drawdown
    result['max_drawdown'] = calculate_max_drawdown(data)

    # 52-week metrics
    week52_metrics = calculate_52_week_metrics(data)
    result.update(week52_metrics)

    # Volume metrics
    volume_metrics = calculate_volume_metrics(data)
    result.update(volume_metrics)

    return result


# ==============================================================================
# VALIDATION & HELPER FUNCTIONS
# ==============================================================================

def validate_data(data: pd.DataFrame, min_rows: int = 50) -> Tuple[bool, list]:
    """
    Validate data structure and quality.

    Args:
        data: DataFrame to validate
        min_rows: Minimum number of rows required

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    if data is None:
        issues.append("Data is None")
        return False, issues

    if data.empty:
        issues.append("Data is empty")
        return False, issues

    if len(data) < min_rows:
        issues.append(f"Insufficient rows: {len(data)} < {min_rows}")

    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_cols = [col for col in required_columns if col not in data.columns]
    if missing_cols:
        issues.append(f"Missing columns: {missing_cols}")

    # Check for all NaN rows
    if data.isnull().all().any():
        issues.append("Found rows with all NaN values")

    # Check date index
    if not isinstance(data.index, pd.DatetimeIndex):
        issues.append("Index is not DatetimeIndex")

    return len(issues) == 0, issues


if __name__ == '__main__':
    print("Indicators module loaded successfully")
