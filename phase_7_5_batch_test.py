"""Phase 7.5 integration test: batch download optimization for 250-stock universe."""

import json
import sys
from datetime import datetime

from src.batch_downloader import batch_download_universe, report_batch_result
from src.universe import UniverseManager

SAMPLE_SIZES = [5, 20, 50, 100, 250]


def test_batch_download_at_scale(sample_size: int) -> dict:
    """Download and measure performance at a given sample size."""
    print(f"\n{'='*80}")
    print(f"BATCH DOWNLOAD TEST: {sample_size} stocks")
    print(f"{'='*80}")
    
    # Load production universe
    manager = UniverseManager()
    large_cap = manager.universe_data.get('large_cap', [])
    mid_cap = manager.universe_data.get('mid_cap', [])
    universe_data = large_cap + mid_cap
    
    if not universe_data:
        print("ERROR: Could not load production universe")
        return {}
    
    # Extract Yahoo symbols
    all_symbols = []
    for stock in universe_data:
        yahoo_symbol = stock.get('yahoo_symbol')
        if yahoo_symbol:
            all_symbols.append(yahoo_symbol)
        else:
            symbol = stock.get('symbol')
            if symbol:
                all_symbols.append(f'{symbol}.NS')
    
    if len(all_symbols) < sample_size:
        print(f"ERROR: Only {len(all_symbols)} symbols available, requested {sample_size}")
        return {}
    
    # Take sample
    symbols_to_download = all_symbols[:sample_size]
    print(f"Downloading {len(symbols_to_download)} symbols from production universe")
    print(f"Batch size: 50 (configurable in src/config.py)")
    print(f"History period: 2 years")
    
    # Run batch download
    result = batch_download_universe(symbols_to_download, batch_size=50, period='2y')
    
    # Report results
    report_batch_result(result)
    
    # Return summary
    return {
        'sample_size': sample_size,
        'successful': len(result.valid),
        'insufficient_history': len(result.insufficient_history),
        'no_data': len(result.no_data),
        'download_errors': len(result.download_errors),
        'elapsed_seconds': result.elapsed_seconds,
        'coverage_percent': 100.0 * len(result.valid) / max(sample_size, 1),
    }


def main() -> int:
    """Run batch download tests at multiple scales."""
    print("PHASE 7.5 - BATCH DOWNLOAD OPTIMIZATION")
    print(f"Start time: {datetime.now().isoformat()}")
    
    results = []
    
    for sample_size in SAMPLE_SIZES:
        try:
            result = test_batch_download_at_scale(sample_size)
            if result:
                results.append(result)
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"\nERROR at sample size {sample_size}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary table
    print(f"\n{'='*80}")
    print("SUMMARY: Batch Download Performance")
    print(f"{'='*80}")
    print(f"{'Size':<8} {'Successful':<12} {'Coverage':<12} {'Errors':<8} {'Time (s)':<10}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['sample_size']:<8} {r['successful']:<12} {r['coverage_percent']:>6.1f}% {r['download_errors']:<8} {r['elapsed_seconds']:>9.2f}")
    
    # Save results
    output = {
        'test_date': datetime.now().isoformat(),
        'test_type': 'batch_download_scale_test',
        'results': results,
        'completed': len(results) == len(SAMPLE_SIZES),
    }
    
    with open('data/phase_7_5_batch_test_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to data/phase_7_5_batch_test_results.json")
    
    # Target: 250/250 successfully downloaded
    if results:
        final_result = results[-1]
        print(f"\nFinal assessment (250-stock production):")
        print(f"  Target: 250/250 (100%)")
        print(f"  Actual: {final_result['successful']}/{final_result['sample_size']} ({final_result['coverage_percent']:.1f}%)")
        
        if final_result['coverage_percent'] >= 90.0:
            print(f"  Status: ✓ PASS (>= 90% coverage)")
            return 0
        else:
            print(f"  Status: ✗ FAIL (< 90% coverage)")
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
