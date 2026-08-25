"""
Market Data Module

Handles downloading and validating market data from Yahoo Finance.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

from src.config import (
    HISTORY_PERIOD, MIN_DATA_ROWS, RETRY_ATTEMPTS, RETRY_DELAY_SECONDS, NSE_SUFFIX
)

logger = logging.getLogger(__name__)


class MarketDataDownloader:
    """Handles downloading market data from Yahoo Finance."""

    def __init__(self, period: str = HISTORY_PERIOD, retries: int = RETRY_ATTEMPTS):
        """
        Initialize the downloader.

        Args:
            period: Historical period to download (e.g., '2y')
            retries: Number of retry attempts for failed downloads
        """
        self.period = period
        self.retries = retries
        self.failed_symbols = []
        self.successful_symbols = []

    def download_symbol(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Download historical data for a single symbol.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        for attempt in range(self.retries):
            try:
                data = yf.download(
                    symbol,
                    period=self.period,
                    progress=False,
                )

                if data is None or data.empty:
                    logger.warning(f"{symbol}: Empty data returned")
                    continue

                # Validate data
                if not self._validate_data(symbol, data):
                    logger.warning(f"{symbol}: Data validation failed")
                    continue

                self.successful_symbols.append(symbol)
                return data

            except Exception as e:
                logger.debug(
                    f"{symbol}: Download attempt {attempt + 1}/{self.retries} failed: {e}"
                )
                if attempt < self.retries - 1:
                    import time
                    time.sleep(RETRY_DELAY_SECONDS)

        self.failed_symbols.append(symbol)
        logger.error(f"{symbol}: Failed after {self.retries} attempts")
        return None

    def download_multiple(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Download data for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        results = {}

        for symbol in symbols:
            data = self.download_symbol(symbol)
            if data is not None:
                results[symbol] = data

        return results

    @staticmethod
    def _validate_data(symbol: str, data: pd.DataFrame) -> bool:
        """
        Validate downloaded data.

        Args:
            symbol: Stock symbol
            data: Downloaded DataFrame

        Returns:
            True if data is valid
        """
        # Check minimum rows
        if len(data) < MIN_DATA_ROWS:
            logger.warning(
                f"{symbol}: Insufficient data rows ({len(data)} < {MIN_DATA_ROWS})"
            )
            return False

        # Check for required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_cols):
            logger.warning(f"{symbol}: Missing required OHLCV columns")
            return False

        # Check for excessive NaN values
        nan_ratio = data.isna().sum().sum() / (len(data) * len(data.columns))
        if nan_ratio > 0.1:  # More than 10% NaN
            logger.warning(
                f"{symbol}: Excessive NaN values ({nan_ratio:.2%})"
            )
            return False

        # Check for non-positive prices
        if (data['Close'] <= 0).any() or (data['Volume'] < 0).any():
            logger.warning(f"{symbol}: Invalid price or volume values")
            return False

        return True

    def get_summary(self) -> Dict:
        """
        Get download summary statistics.

        Returns:
            Dictionary with summary information
        """
        return {
            'total_attempted': len(self.successful_symbols) + len(self.failed_symbols),
            'successful': len(self.successful_symbols),
            'failed': len(self.failed_symbols),
            'success_rate': (
                len(self.successful_symbols) /
                (len(self.successful_symbols) + len(self.failed_symbols))
                if (len(self.successful_symbols) + len(self.failed_symbols)) > 0
                else 0
            ),
            'failed_symbols': self.failed_symbols,
        }


class DataValidator:
    """Validates and analyzes downloaded market data."""

    @staticmethod
    def print_data_summary(symbol: str, data: pd.DataFrame) -> None:
        """
        Print a summary of downloaded data for a symbol.

        Args:
            symbol: Stock symbol
            data: DataFrame with market data
        """
        if data is None or data.empty:
            print(f"  {symbol}: NO DATA")
            return

        first_date = data.index[0].strftime('%Y-%m-%d')
        last_date = data.index[-1].strftime('%Y-%m-%d')
        rows = len(data)
        missing_values = data.isna().sum().sum()
        latest_close = data['Close'].iloc[-1]
        latest_volume = data['Volume'].iloc[-1]

        # Calculate 50-day and 200-day moving averages (verify they're possible)
        can_calc_50dma = len(data) >= 50
        can_calc_200dma = len(data) >= 200

        print(f"  {symbol:15} | Rows: {rows:4} | "
              f"From: {first_date} To: {last_date} | "
              f"Close: ₹{latest_close:8.2f} | Vol: {latest_volume:12.0f} | "
              f"50DMA: {'✓' if can_calc_50dma else '✗'} | "
              f"200DMA: {'✓' if can_calc_200dma else '✗'}")

        if missing_values > 0:
            print(f"    ⚠ {missing_values} missing values detected")

    @staticmethod
    def can_calculate_indicators(data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Check if sufficient data is available for indicator calculation.

        Args:
            data: Market data DataFrame

        Returns:
            Tuple of (is_valid, list_of_missing_requirements)
        """
        issues = []

        if len(data) < 50:
            issues.append("Insufficient data for 50-day MA")
        if len(data) < 200:
            issues.append("Insufficient data for 200-day MA")

        return len(issues) == 0, issues


def print_header():
    """Print a formatted header for data summary."""
    print("\n" + "="*120)
    print("YAHOO FINANCE DATA VALIDATION - 10 REPRESENTATIVE STOCKS")
    print("="*120)
    print(f"{'Symbol':<15} | {'Rows':<4} | {'Date Range':<27} | "
          f"{'Price':<10} | {'Volume':<12} | 50DMA | 200DMA |")
    print("-"*120)


def print_footer():
    """Print a formatted footer."""
    print("-"*120)
    print()


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Test with a single stock
    downloader = MarketDataDownloader()
    data = downloader.download_symbol('RELIANCE.NS')
    if data is not None:
        DataValidator.print_data_summary('RELIANCE.NS', data)
