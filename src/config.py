"""
Configuration file for Indian Market Signal Engine

All thresholds, weights, and parameters are defined here for easy modification
and backtesting.
"""

import os
from datetime import datetime, timedelta

# ==============================================================================
# DATA SOURCES & STORAGE
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UNIVERSE_FILE = os.path.join(DATA_DIR, 'universe.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'latest.json')
BACKTEST_DIR = os.path.join(DATA_DIR, 'backtest')

# ==============================================================================
# YAHOO FINANCE SETTINGS
# ==============================================================================

# NSE Yahoo Finance suffix
NSE_SUFFIX = '.NS'

# Minimum data coverage required for a production universe analysis.
MIN_UNIVERSE_COVERAGE = 0.90
MIN_SEGMENT_COVERAGE = 0.90

# Historical period to download
# This should be sufficient for 200-day MA calculation plus some buffer
HISTORY_PERIOD = '2y'  # approximately 2 years of trading days

# Minimum rows of data required for analysis
MIN_DATA_ROWS = 200  # Minimum for 200-day MA

# Retry settings for data download
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

# Batch download settings for Phase 7.5 optimization
BATCH_SIZE = 50  # Tickers per batch
DOWNLOAD_TIMEOUT = 60  # Seconds per batch request

# ==============================================================================
# UNIVERSE DEFINITION
# ==============================================================================

# Target number of stocks per segment
NIFTY_100_COUNT = 100
NIFTY_MIDCAP_150_COUNT = 150

# ==============================================================================
# SCORING MODEL WEIGHTS
# ==============================================================================

# Total should equal 100
SCORE_WEIGHTS = {
    'momentum': 20,           # 1m, 3m, 6m, 12m returns
    'trend': 20,              # Price vs DMAs
    'relative_strength': 15,  # Stock vs benchmark
    'volume': 10,             # Volume confirmation
    'rsi': 10,                # 14-period RSI
    '52_week_strength': 10,   # Distance from 52-week high
    'risk': 15,               # Volatility & drawdown penalty
}

SCORE_WEIGHT_TOLERANCE = 1e-9
if abs(sum(SCORE_WEIGHTS.values()) - 100.0) > SCORE_WEIGHT_TOLERANCE:
    raise ValueError("Scoring weights must sum to 100")

# ==============================================================================
# MOMENTUM SCORE (0-20)
# ==============================================================================

# Return periods to consider (in days)
MOMENTUM_PERIODS = {
    '1m': 21,
    '3m': 63,
    '6m': 126,
    '12m': 252,
}

# How to weight each period
MOMENTUM_PERIOD_WEIGHTS = {
    '1m': 0.15,
    '3m': 0.30,
    '6m': 0.35,
    '12m': 0.2,
}

# Percentile ranges for scoring (cross-sectional ranking)
MOMENTUM_PERCENTILES = {
    'top_10': 20.0,      # Top 10% = 20 points
    'top_25': 16.0,      # 10-25% = 16 points
    'top_50': 12.0,      # 25-50% = 12 points
    'top_75': 8.0,       # 50-75% = 8 points
    'top_90': 4.0,       # 75-90% = 4 points
    'bottom': 0.0,       # Bottom 10% = 0 points
}

# ==============================================================================
# TREND SCORE (0-20)
# ==============================================================================

# Moving average periods
DMA_20 = 20
DMA_50 = 50
DMA_200 = 200

# Trend scoring conditions
# Score is built on proximity to and alignment of moving averages
TREND_EXCELLENT = 20.0  # Price > 50 DMA > 200 DMA, all rising
TREND_STRONG = 16.0     # Price above both DMAs
TREND_POSITIVE = 12.0   # Price above 50 DMA
TREND_NEUTRAL = 8.0     # Price between 50 & 200 DMA
TREND_WEAK = 4.0        # Price below 50 DMA but above 200 DMA
TREND_POOR = 0.0        # Price below 200 DMA

# ==============================================================================
# RELATIVE STRENGTH SCORE (0-15)
# ==============================================================================

# Benchmark: Nifty LargeMidcap 250 (or we can use segment-specific benchmarks)
# For now, we'll calculate relative to the average of the universe

# ==============================================================================
# VOLUME SCORE (0-10)
# ==============================================================================

# Volume periods
VOLUME_20_DAY_PERIOD = 20
VOLUME_60_DAY_PERIOD = 60

# Score multiplier if volume is strong
VOLUME_EXPANSION_THRESHOLD = 1.1  # 10% above 60-day average = good
VOLUME_STRONG_MULTIPLIER = 1.2    # 20% above = excellent

# ==============================================================================
# RSI SCORE (0-10)
# ==============================================================================

RSI_PERIOD = 14

# RSI thresholds for scoring
RSI_SCORE_MAP = {
    'overheating': (80, 100, -5.0),
    'strong': (65, 80, 10.0),
    'positive': (50, 65, 8.0),
    'neutral': (45, 50, 5.0),
    'weak': (30, 45, 2.0),
    'oversold': (0, 30, 0.0),
}

# ==============================================================================
# 52-WEEK STRENGTH SCORE (0-10)
# ==============================================================================

# Ratio of current price to 52-week high
FIFTY_TWO_WEEK_EXCELLENT = (0.95, 1.00, 10.0)   # Within 5% of high = 10 points
FIFTY_TWO_WEEK_STRONG = (0.90, 0.95, 8.0)       # 5-10% from high = 8 points
FIFTY_TWO_WEEK_POSITIVE = (0.85, 0.90, 6.0)     # 10-15% from high = 6 points
FIFTY_TWO_WEEK_NEUTRAL = (0.80, 0.85, 4.0)      # 15-20% from high = 4 points
FIFTY_TWO_WEEK_WEAK = (0.70, 0.80, 2.0)         # 20-30% from high = 2 points
FIFTY_TWO_WEEK_POOR = (0.0, 0.70, 0.0)          # More than 30% from high = 0

# ==============================================================================
# RISK SCORE (0-15)
# ==============================================================================

# Volatility thresholds (annualized standard deviation)
VOLATILITY_LOW = 0.15       # < 15% = high risk score
VOLATILITY_MODERATE = 0.25  # 15-25% = moderate penalty
VOLATILITY_HIGH = 0.35      # > 35% = significant penalty

# Maximum drawdown thresholds
MAX_DRAWDOWN_EXCELLENT = -0.10   # -10% or less = good
MAX_DRAWDOWN_GOOD = -0.20        # -10% to -20% = acceptable
MAX_DRAWDOWN_MODERATE = -0.30    # -20% to -30% = moderate risk
MAX_DRAWDOWN_SEVERE = -1.00      # Beyond -30% = severe penalty

# Risk score calculation: higher is better
# Score penalizes high volatility and drawdown

# ==============================================================================
# MARKET REGIME
# ==============================================================================

# Market regime classification thresholds
MARKET_REGIME_BULLISH = {
    'nifty_above_200dma': 0.70,              # 70% of Nifty above 200 DMA
    'universe_above_200dma': 0.60,           # 60% of universe above 200 DMA
    'universe_above_50dma': 0.75,            # 75% above 50 DMA
    'nifty_momentum_positive': True,         # Nifty showing positive momentum
}

MARKET_REGIME_BEARISH = {
    'nifty_below_200dma': 0.50,              # 50% of Nifty below 200 DMA
    'universe_below_50dma': 0.50,            # 50% below 50 DMA
    'nifty_momentum_negative': True,         # Nifty showing negative momentum
}

# Between BULLISH and BEARISH = NEUTRAL

# Market-regime score weights and classification thresholds.
MARKET_REGIME_WEIGHTS = {
    'benchmark_trend': 0.40,
    'market_breadth': 0.30,
    'market_momentum': 0.30,
}
MARKET_REGIME_BULLISH_SCORE = 70.0
MARKET_REGIME_BEARISH_SCORE = 40.0

# ==============================================================================
# STOCK SELECTION THRESHOLDS
# ==============================================================================

# Minimum score to be considered for recommendation
MINIMUM_SCORE_THRESHOLD = 60.0

# Target number of stocks to select from each segment
TARGET_LARGE_CAP_COUNT = 5
TARGET_MID_CAP_COUNT = 5
MAX_TOTAL_CANDIDATES = 10

# Sector concentration limit
MAX_STOCKS_PER_SECTOR = 2

# ==============================================================================
# SIGNAL CATEGORIES
# ==============================================================================

# Score ranges and signal labels
SIGNAL_CATEGORIES = {
    'STRONG': (80, 100),
    'POSITIVE': (70, 79),
    'WATCH': (60, 69),
    'WEAK': (0, 59),
}

# ==============================================================================
# DATA FRESHNESS
# ==============================================================================

# Maximum age of data before showing a warning (in hours)
DATA_FRESHNESS_WARNING_HOURS = 24
DATA_FRESHNESS_ERROR_HOURS = 48

# ==============================================================================
# LOGGING & DEBUG
# ==============================================================================

LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True
LOG_FILE = os.path.join(BASE_DIR, 'analysis.log')

# ==============================================================================
# INDICATOR PARAMETERS
# ==============================================================================

# Trading days per year (for annualizing volatility)
TRADING_DAYS_PER_YEAR = 252

# Return periods (in trading days) - already defined in MOMENTUM_PERIODS
# But repeated here for clarity:
# 1M  = 21 trading days
# 3M  = 63 trading days
# 6M  = 126 trading days
# 12M = 252 trading days

# Lookback period for volatility calculation (in trading days)
VOLATILITY_LOOKBACK_DAYS = 252  # Use full year or available data

# 52-week period in trading days
FIFTY_TWO_WEEK_DAYS = 252

# ==============================================================================
# BACKTESTING
# ==============================================================================

# Backtest date ranges
BACKTEST_START_DATE = '2023-01-01'
BACKTEST_END_DATE = None  # None = today

# How often to re-score and generate recommendations (for backtesting)
BACKTEST_FREQUENCY = 'M'  # 'D' = daily, 'W' = weekly, 'M' = monthly

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================


def ensure_data_directories():
    """Create required data directories if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKTEST_DIR, exist_ok=True)


if __name__ == '__main__':
    # Validate configuration on import
    ensure_data_directories()
    print("Configuration loaded successfully")
