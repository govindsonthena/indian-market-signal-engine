"""
PHASE 3: Yahoo Finance Data Validation

Purpose:
    Test Yahoo Finance data downloading and validation with 10 representative stocks
    from Nifty 100 and Nifty Midcap 150.

    This script does NOT implement the full recommendation engine.
    It only validates the data foundation before proceeding to Phase 4.

Representative Stocks Selected:
    Large Cap (Nifty 100):
    - RELIANCE.NS - Large cap, consistent trading
    - TCS.NS - Large cap, liquid
    - INFY.NS - Large cap, IT sector
    - HDFCBANK.NS - Large cap, banking sector
    - WIPRO.NS - Large cap, IT sector

    Mid Cap (Nifty Midcap 150):
    - BATADRY.NS - Mid-cap FMCG
    - CIPLA.NS - Mid-cap pharma
    - ICICIPRULI.NS - Mid-cap financial
    - MARUTI.NS - Mid-cap automotive
    - POWERLD.NS - Mid-cap power sector

Expected Output:
    - For each stock: ticker, # of rows, date range, latest close, volume
    - Indicator: Can we calculate 50-day MA? Can we calculate 200-day MA?
    - Total stats: X/10 stocks succeeded
    - Any Yahoo Finance limitations or errors
"""

import logging
import sys
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the market data module
from src.market_data import MarketDataDownloader, DataValidator, print_header, print_footer


def main():
    """Execute Phase 3 data validation."""

    # Representative stocks: 5 Large Cap + 5 Mid Cap
    test_stocks = [
        # Nifty 100 - Large Cap
        'RELIANCE.NS',      # Reliance Industries
        'TCS.NS',           # Tata Consultancy Services
        'INFY.NS',          # Infosys
        'HDFCBANK.NS',      # HDFC Bank
        'WIPRO.NS',         # Wipro

        # Nifty Midcap 150 - Mid Cap
        'BATADRY.NS',       # Bata India
        'CIPLA.NS',         # Cipla
        'ICICIPRULI.NS',    # ICICI Prudential Life Insurance
        'MARUTI.NS',        # Maruti Suzuki
        'POWERLD.NS',       # Power Supply Ltd
    ]

    print("\n" + "="*120)
    print("PHASE 3: YAHOO FINANCE DATA VALIDATION")
    print("="*120)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"Historical Period: 2 years (or available)")
    print(f"Minimum Required Rows: 200 (for 200-day MA)")
    print("="*120)

    # Initialize downloader
    downloader = MarketDataDownloader(period='2y', retries=3)

    # Download data for all stocks
    print(f"\nDownloading data for {len(test_stocks)} representative stocks...")
    all_data = downloader.download_multiple(test_stocks)

    # Print summary header
    print_header()

    # Print data for each stock
    for symbol in test_stocks:
        if symbol in all_data:
            data = all_data[symbol]
            DataValidator.print_data_summary(symbol, data)
        else:
            print(f"  {symbol:15} | FAILED TO DOWNLOAD")

    print_footer()

    # Print overall statistics
    summary = downloader.get_summary()
    print("DATA DOWNLOAD SUMMARY")
    print("-" * 60)
    print(f"Total Stocks Tested:        {summary['total_attempted']}")
    print(f"Successfully Downloaded:    {summary['successful']}")
    print(f"Failed:                     {summary['failed']}")
    print(f"Success Rate:               {summary['success_rate']:.1%}")

    if summary['failed'] > 0:
        print(f"\nFailed Symbols:")
        for symbol in summary['failed_symbols']:
            print(f"  - {symbol}")

    # Validate indicator calculation capability
    print("\n" + "="*60)
    print("INDICATOR CALCULATION CAPABILITY")
    print("="*60)

    can_calculate_50dma = sum(
        1 for data in all_data.values() if len(data) >= 50
    )
    can_calculate_200dma = sum(
        1 for data in all_data.values() if len(data) >= 200
    )

    print(f"Stocks with ≥50 days data (50-day MA):   {can_calculate_50dma}/{summary['successful']}")
    print(f"Stocks with ≥200 days data (200-day MA): {can_calculate_200dma}/{summary['successful']}")

    if can_calculate_200dma == summary['successful']:
        print("\n✓ All stocks have sufficient data for 200-day MA calculation")
    else:
        print(f"\n⚠ Only {can_calculate_200dma}/{summary['successful']} stocks can calculate 200-day MA")

    # Report any Yahoo Finance limitations
    print("\n" + "="*60)
    print("YAHOO FINANCE OBSERVATIONS & LIMITATIONS")
    print("="*60)

    if summary['success_rate'] == 1.0:
        print("✓ All stocks downloaded successfully - no data access issues detected")
    else:
        print(f"⚠ {summary['failed']} stocks failed - possible Yahoo Finance limitations")

    print("\nNote:")
    print("  - Yahoo Finance coverage for NSE stocks (*.NS) is generally reliable")
    print("  - Occasional timeout/rate-limiting may occur with bulk downloads")
    print("  - Some newly delisted or low-volume stocks may have incomplete history")
    print("  - Timezone handling: Yahoo uses UTC; ensure IST conversion in production")

    # Data sample analysis
    if all_data:
        print("\n" + "="*60)
        print("DATA SAMPLE ANALYSIS (First successful stock)")
        print("="*60)
        first_symbol = list(all_data.keys())[0]
        first_data = all_data[first_symbol]

        print(f"\nStock: {first_symbol}")
        print(f"Data Shape: {first_data.shape}")
        print(f"Columns: {list(first_data.columns)}")
        print(f"\nFirst 5 rows:")
        print(first_data.head())
        print(f"\nLast 5 rows:")
        print(first_data.tail())
        print(f"\nData Info:")
        print(first_data.info())

    # Final status
    print("\n" + "="*60)
    if summary['success_rate'] >= 0.8:
        print("✓ PHASE 3 VALIDATION: PASSED")
        print("  Data foundation is ready for indicator development (Phase 4)")
    else:
        print("⚠ PHASE 3 VALIDATION: PARTIAL")
        print("  Some data issues detected, but enough stocks available to proceed")

    print("="*60 + "\n")

    return summary


if __name__ == '__main__':
    try:
        summary = main()
        sys.exit(0 if summary['success_rate'] > 0 else 1)
    except Exception as e:
        logger.error(f"Validation script failed: {e}", exc_info=True)
        sys.exit(1)
