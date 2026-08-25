"""Audit the 14 Phase 7.5 data-quality failures without altering the universe."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.batch_downloader import BatchDownloadError, download_batch
from src.historical_audit import audit_dataframe, summarize_audits

FLAGGED_SYMBOLS = [
    'ENRIN.NS', 'TATACAP.NS', 'TMCV.NS', 'ANTHEM.NS', 'GROWW.NS', 'HDBFS.NS',
    'HEXT.NS', 'ICICIAMC.NS', 'ITCHOTELS.NS', 'LGEINDIA.NS', 'LENSKART.NS',
    'NTPCGREEN.NS', 'SWIGGY.NS', 'VMM.NS',
]
REPORT_FILE = Path('data/phase_7_6_historical_audit.json')


def main() -> int:
    audits = []
    for symbol in FLAGGED_SYMBOLS:
        try:
            data = download_batch([symbol], retries=3)
            audit = audit_dataframe(symbol, data.get(symbol))
        except BatchDownloadError as error:
            audit = audit_dataframe(symbol, None)
            audit['root_cause'] = str(error)
        audits.append(audit)
        calculable = ', '.join(name for name, value in audit['calculable'].items() if value) or 'none'
        print(f"{symbol}: {audit['classification']} | dates={audit['first_date']}..{audit['last_date']} | rows={audit['total_rows']} | valid_days={audit['valid_trading_days']} | missing={audit['missing_ohlcv_percent']:.2f}% | calculable={calculable}")

    affected_summary = summarize_audits(audits)
    report = {
        'summary': {
            'universe': 250,
            'yahoo_symbols_valid': 250,
            'sufficient_history': 236 + affected_summary['sufficient_history'],
            'insufficient_history': affected_summary['insufficient_history'],
            'data_quality_problems': affected_summary['data_quality_problems'],
            'yahoo_problems': affected_summary['yahoo_problems'],
            'eligible_for_scoring': 236 + affected_summary['eligible_for_scoring'],
            'coverage_eligible': (236 + affected_summary['eligible_for_scoring']) / 250,
            'baseline_phase_7_5_valid': 236,
            'affected_symbols_audited': affected_summary,
        },
        'audits': audits,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    print(json.dumps(report['summary'], indent=2))
    print(f'Report: {REPORT_FILE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())