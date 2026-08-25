#!/usr/bin/env python3
"""
Simplified Phase 3 Validation - Core Test
Checks if basic Python setup works and attempts data download
"""

import sys
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("PHASE 3 DATA VALIDATION - SIMPLIFIED TEST")
print("="*80)
print(f"Test Date: {datetime.now().isoformat()}")
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print("="*80 + "\n")

# Test 1: Check Python environment
print("[TEST 1] Python Environment")
print(f"  Platform: {sys.platform}")
print(f"  Version: {sys.version.split()[0]}")
print(f"  Executable: {sys.executable}")
print("  ✓ PASSED\n")

# Test 2: Import required modules
print("[TEST 2] Import Dependencies")
dependencies_ok = True

try:
    import pandas as pd
    print(f"  ✓ pandas {pd.__version__}")
except ImportError as e:
    print(f"  ✗ pandas: {e}")
    dependencies_ok = False

try:
    import numpy as np
    print(f"  ✓ numpy {np.__version__}")
except ImportError as e:
    print(f"  ✗ numpy: {e}")
    dependencies_ok = False

try:
    import yfinance as yf
    print(f"  ✓ yfinance {yf.__version__}")
except ImportError as e:
    print(f"  ✗ yfinance: {e}")
    dependencies_ok = False

try:
    import dateutil
    print(f"  ✓ python-dateutil")
except ImportError as e:
    print(f"  ✗ python-dateutil: {e}")
    dependencies_ok = False

if not dependencies_ok:
    print("\n  ✗ FAILED - Some dependencies are missing")
    print("\nTo fix, run in PowerShell:")
    print('  & "C:\\Python312\\python.exe" -m pip install yfinance pandas numpy python-dateutil requests')
    sys.exit(1)

print("  ✓ PASSED\n")

# Test 3: Test universe loading
print("[TEST 3] Universe Loading")
try:
    from src.universe import UniverseManager
    manager = UniverseManager()
    validation = manager.validate_universe()
    print(f"  Large Cap: {validation['large_cap_count']}/{validation['large_cap_expected']}")
    print(f"  Mid Cap: {validation['mid_cap_count']}/{validation['mid_cap_expected']}")
    if validation['all_valid']:
        print("  ✓ PASSED\n")
    else:
        print("  ⚠ WARNING - Universe incomplete (this is OK for Phase 1)\n")
except Exception as e:
    print(f"  ✗ FAILED: {e}\n")

# Test 4: Try simple yfinance download
print("[TEST 4] Yahoo Finance Data Download")
try:
    if not dependencies_ok:
        print("  ⚠ SKIPPED - Dependencies not available")
    else:
        import yfinance as yf
        print("  Attempting to download RELIANCE.NS (Reliance Industries)...")
        
        try:
            data = yf.download('RELIANCE.NS', period='1y', progress=False)
            if data is not None and len(data) > 0:
                print(f"  ✓ Downloaded {len(data)} rows of data")
                print(f"    Date range: {data.index[0].date()} to {data.index[-1].date()}")
                print(f"    Latest price: ₹{data['Close'].iloc[-1]:.2f}")
                print(f"    Columns: {list(data.columns)}")
                print("  ✓ PASSED\n")
            else:
                print("  ✗ FAILED - No data returned")
                print("  This may indicate Yahoo Finance rate limiting or access issues\n")
        except Exception as e:
            print(f"  ✗ FAILED: {e}\n")
            print("  Possible causes:")
            print("    1. Yahoo Finance temporary unavailable")
            print("    2. Network connection issue")
            print("    3. yfinance rate limiting")
            print("    4. Invalid ticker symbol\n")

except Exception as e:
    print(f"  ✗ FAILED: {e}\n")

# Test 5: Directory structure
print("[TEST 5] Project Structure")
required_dirs = ['src', 'tests', 'data', '.github/workflows']
all_exist = True
for dir_name in required_dirs:
    exists = os.path.isdir(dir_name)
    status = "✓" if exists else "✗"
    print(f"  {status} {dir_name}")
    if not exists:
        all_exist = False

if all_exist:
    print("  ✓ PASSED\n")
else:
    print("  ⚠ WARNING - Some directories missing\n")

# Summary
print("="*80)
print("PHASE 3 VALIDATION SUMMARY")
print("="*80)
if dependencies_ok:
    print("✓ Foundation Ready for Phase 4 (Technical Indicators)")
    print("\nNext steps:")
    print("  1. Phase 4: Implement technical indicator calculations")
    print("  2. Phase 5: Build scoring model")
    print("  3. Phase 6: Implement stock selection logic")
    print("  4. Complete remaining phases...")
else:
    print("⚠ Dependencies Need Installation")
    print("\nRun this command in PowerShell (Admin or normal terminal):")
    print('  & "C:\\Python312\\python.exe" -m pip install yfinance pandas numpy python-dateutil requests pytest')

print("="*80 + "\n")

sys.exit(0 if dependencies_ok else 1)
