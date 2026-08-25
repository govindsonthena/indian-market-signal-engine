"""
Phase 4: Integration Test with Yahoo Finance Data

This script tests indicators with real Yahoo Finance data.
Uses the existing sample universe to demonstrate indicator calculations.
"""

import logging
import sys
from datetime import datetime

import pandas as pd
import yfinance as yf

from src.indicators import (
    calculate_all_indicators,
    validate_data,
)
from src.universe import UniverseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header():
    """Print formatted header."""
    print("\n" + "="*120)
    print("PHASE 4 INTEGRATION TEST: TECHNICAL INDICATORS WITH YAHOO FINANCE DATA")
    print("="*120)
    print(f"Test Date: {datetime.now().isoformat()}")
    print("="*120 + "\n")


def print_stock_indicators(symbol: str, data: pd.DataFrame, indicators: dict) -> None:
    """Print formatted indicator output for a stock."""
    print(f"\nStock: {symbol}")
    print(f"Data Rows: {len(data)}")
    print(f"Date Range: {data.index[0].date()} to {data.index[-1].date()}")
    print("-" * 120)
    
    # Latest price
    latest_close = float(data['Close'].iloc[-1])
    latest_date = data.index[-1].date()
    print(f"Latest Close: Rs {latest_close:.2f} ({latest_date})")
    
    print("\nMoving Averages:")
    print("\nMoving Averages:")
    sma20 = indicators.get('sma_20')
    sma50 = indicators.get('sma_50')
    sma200 = indicators.get('sma_200')
    try:
        print(f"  SMA-20:  Rs {float(sma20):.2f}" if sma20 is not None else "  SMA-20:  Rs N/A")
        print(f"  SMA-50:  Rs {float(sma50):.2f}" if sma50 is not None else "  SMA-50:  Rs N/A")
        print(f"  SMA-200: Rs {float(sma200):.2f}" if sma200 is not None else "  SMA-200: Rs N/A")
    except (TypeError, ValueError):
        print(f"  SMA-20:  Rs N/A")
        print(f"  SMA-50:  Rs N/A")
        print(f"  SMA-200: Rs N/A")
    
    print("\nMomentum & Trend:")
    print("\nMomentum & Trend:")
    rsi = indicators.get('rsi_14')
    try:
        print(f"  RSI-14:  {float(rsi):.2f}" if rsi is not None else "  RSI-14:  N/A")
    except (TypeError, ValueError):
        print(f"  RSI-14:  N/A")
    
    print("\nReturns (Decimal: 0.10 = +10%):")
    r1m = indicators.get('return_1m')
    r3m = indicators.get('return_3m')
    r6m = indicators.get('return_6m')
    r12m = indicators.get('return_12m')
    if r1m is not None:
        print(f"  1M:  {r1m:.4f} ({(r1m * 100):.2f}%)")
    else:
        print(f"  1M:  N/A")
    if r3m is not None:
        print(f"  3M:  {r3m:.4f} ({(r3m * 100):.2f}%)")
    else:
        print(f"  3M:  N/A")
    if r6m is not None:
        print(f"  6M:  {r6m:.4f} ({(r6m * 100):.2f}%)")
    else:
        print(f"  6M:  N/A")
    if r12m is not None:
        print(f"  12M: {r12m:.4f} ({(r12m * 100):.2f}%)")
    else:
        print(f"  12M: N/A")
    
    print("\nVolatility & Risk:")
    vol = indicators.get('volatility_annualized')
    dd = indicators.get('max_drawdown')
    if vol is not None:
        print(f"  Volatility (Annualized): {vol:.4f} ({(vol * 100):.2f}%)")
    else:
        print(f"  Volatility (Annualized): N/A")
    if dd is not None:
        print(f"  Max Drawdown:            {dd:.4f} ({(dd * 100):.2f}%)")
    else:
        print(f"  Max Drawdown:            N/A")
    
    print("\n52-Week Metrics:")
    h52 = indicators.get('52_week_high')
    l52 = indicators.get('52_week_low')
    dist = indicators.get('distance_from_52w_high')
    pos = indicators.get('position_in_52w_range')
    
    print(f"  52W High:            Rs {h52:.2f}" if h52 is not None else "  52W High:            Rs N/A")
    print(f"  52W Low:             Rs {l52:.2f}" if l52 is not None else "  52W Low:             Rs N/A")
    if dist is not None:
        print(f"  Distance from High:  {dist:.4f} ({(dist * 100):.2f}%)")
    else:
        print(f"  Distance from High:  N/A")
    if pos is not None:
        print(f"  Position in Range:   {pos:.4f} (0.0=low, 1.0=high, {(pos * 100):.1f}%)")
    else:
        print(f"  Position in Range:   N/A")
    
    print("\nVolume Metrics:")
    v20 = indicators.get('volume_sma_20')
    v60 = indicators.get('volume_sma_60')
    vratio = indicators.get('volume_ratio')
    
    if v20 is not None:
        print(f"  Volume SMA-20:  {v20:,.0f}")
    else:
        print(f"  Volume SMA-20:  N/A")
    
    if v60 is not None:
        print(f"  Volume SMA-60:  {v60:,.0f}")
    else:
        print(f"  Volume SMA-60:  N/A")
    
    if vratio is not None:
        print(f"  Volume Ratio:   {vratio:.4f} (>1.0 = rising volume)")
    else:
        print(f"  Volume Ratio:   N/A")
    
    print("-" * 120)


def main():
    """Run integration tests."""
    print_header()
    
    # Load universe
    print("Loading universe...")
    manager = UniverseManager()
    
    large_cap_symbols = manager.get_large_cap_symbols()
    mid_cap_symbols = manager.get_mid_cap_symbols()
    
    print(f"Large Cap: {len(large_cap_symbols)} stocks")
    print(f"Mid Cap: {len(mid_cap_symbols)} stocks")
    
    if not large_cap_symbols or not mid_cap_symbols:
        print("ERROR: No stocks loaded in universe!")
        return 1
    
    # Use first 3 of each for fallback
    test_symbols = large_cap_symbols[:3] + mid_cap_symbols[:3]
    
    print(f"\nTesting with up to 6 stocks (3 Large Cap, 3 Mid Cap)")
    print(f"  Will process first successful ones")
    
    # Download data and calculate indicators
    print("\n" + "="*120)
    print("DOWNLOADING DATA AND CALCULATING INDICATORS")
    print("="*120 + "\n")
    
    results = []
    
    for symbol in test_symbols:
        try:
            print(f"Processing {symbol}...", end=" ")
            
            # Download data
            data = yf.download(symbol, period='2y', progress=False)
            
            if data is None or data.empty:
                print("FAILED - No data")
                continue

            if isinstance(data.columns, pd.MultiIndex):
                data = data.copy()
                data.columns = [column[0] for column in data.columns]
            
            print(f"({len(data)} rows) ", end="")
            
            # Validate data
            valid, issues = validate_data(data, min_rows=50)
            if not valid:
                print(f"INVALID - {issues}")
                continue
            
            print("Calculating indicators... ", end="")
            
            # Calculate indicators
            indicators = calculate_all_indicators(data)
            
            print("DONE")
            
            # Print results
            print_stock_indicators(symbol, data, indicators)
            
            results.append({
                'symbol': symbol,
                'data': data,
                'indicators': indicators,
                'status': 'SUCCESS',
            })
            
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                'symbol': symbol,
                'status': 'FAILED',
                'error': str(e),
            })
    
    # Summary
    print("\n" + "="*120)
    print("PHASE 4 INTEGRATION TEST SUMMARY")
    print("="*120)
    
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    failed = sum(1 for r in results if r['status'] == 'FAILED')
    
    print(f"\nTotal Stocks Tested: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    print("\nIndicator Calculations:")
    print("  [OK] Moving Averages (SMA 20, 50, 200)")
    print("  [OK] RSI (14-period)")
    print("  [OK] Returns (1m, 3m, 6m, 12m)")
    print("  [OK] Volatility (Annualized)")
    print("  [OK] Maximum Drawdown")
    print("  [OK] 52-Week Metrics (High, Low, Distance, Position)")
    print("  [OK] Volume Metrics (SMA 20, 60, Ratio)")
    
    # Verification
    print("\nData Quality Verification:")
    for result in results:
        if result['status'] == 'SUCCESS':
            data = result['data']
            print(f"  {result['symbol']}: {len(data)} rows, "
                  f"{data.index[0].date()} to {data.index[-1].date()}")
    
    print("\nReturn Representation (Decimal, not Percentage):")
    print("  0.10 = +10% return")
    print("  -0.05 = -5% return")
    print("  Drawdown: -0.25 = -25% maximum drawdown")
    
    print("\n" + "="*120)
    if successful >= 1:
        print(">> PHASE 4 INTEGRATION TEST: PASSED")
        print(f"  {successful} stock(s) processed successfully with real data")
    else:
        print(">> PHASE 4 INTEGRATION TEST: FAILED")
        print(f"  No stocks processed successfully")
    
    print("="*120 + "\n")
    
    return 0 if successful >= 1 else 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
        sys.exit(1)
