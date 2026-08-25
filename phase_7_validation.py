"""Production universe validation and gated full-pipeline report."""

import json
from pathlib import Path

from src.config import MIN_UNIVERSE_COVERAGE
from src.universe import UniverseManager
from src.universe_validation import validate_universe

REPORT_FILE = Path('data/production_universe_validation.json')


def main() -> int:
    report = validate_universe(UniverseManager())
    REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
    summary = report['summary']
    print('PRODUCTION UNIVERSE VALIDATION')
    print(f"Expected: {summary['expected']}")
    print(f"Valid: {summary['valid']}")
    print(f"Unavailable: {summary['expected'] - summary['valid']}")
    print(f"Coverage: {summary['coverage']:.1%}")
    print(f"Minimum coverage: {MIN_UNIVERSE_COVERAGE:.1%}")
    for segment, values in summary['segments'].items():
        print(f"{segment}: {values['valid']}/{values['expected']} ({values['coverage']:.1%})")
    if not summary['coverage_ok']:
        print('DATA QUALITY: INCOMPLETE')
        print('Normal production recommendations are blocked below the coverage threshold.')
        return 2
    print('DATA QUALITY: COMPLETE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
