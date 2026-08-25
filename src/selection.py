"""Post-score stock selection with segment and sector constraints."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from src.config import (
    MAX_STOCKS_PER_SECTOR,
    MINIMUM_SCORE_THRESHOLD,
    SIGNAL_CATEGORIES,
    TARGET_LARGE_CAP_COUNT,
    TARGET_MID_CAP_COUNT,
)


def _signal(score: float) -> str:
    for name, (lower, upper) in SIGNAL_CATEGORIES.items():
        if lower <= score <= upper:
            return name
    return 'WATCH'


def _select_segment(candidates: list[dict[str, Any]], target: int,
                    sector_limit: int) -> tuple[list[dict[str, Any]], int]:
    selected, sector_counts, skipped_sector = [], {}, 0
    for candidate in sorted(candidates, key=lambda item: item['overall_score'], reverse=True):
        sector = candidate.get('sector') or 'UNKNOWN'
        if sector_counts.get(sector, 0) >= sector_limit:
            skipped_sector += 1
            continue
        item = dict(candidate)
        item['signal'] = _signal(item['overall_score'])
        item['selection_reason'] = [
            f"Score {item['overall_score']:.2f}",
            'Top-ranked within segment',
            'Sector limit satisfied',
        ]
        selected.append(item)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        if len(selected) == target:
            break
    return selected, skipped_sector


def select_top_stocks(scored_data: Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
                      large_cap_limit: int = TARGET_LARGE_CAP_COUNT,
                      mid_cap_limit: int = TARGET_MID_CAP_COUNT,
                      minimum_score: float = MINIMUM_SCORE_THRESHOLD,
                      sector_limit: int = MAX_STOCKS_PER_SECTOR,
                      market_regime: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Select qualifying stocks separately by segment, without filling quotas weakly."""
    if isinstance(scored_data, Mapping):
        candidates = [dict(value, symbol=key) if 'symbol' not in value else dict(value)
                      for key, value in scored_data.items()]
    else:
        candidates = [dict(value) for value in scored_data]
    if sector_limit < 1:
        raise ValueError('sector_limit must be positive')

    eligible = [item for item in candidates
                if item.get('score_status', 'OK') == 'OK'
                and item.get('overall_score') is not None
                and np.isfinite(item.get('overall_score'))
                and item['overall_score'] >= minimum_score]
    large = [item for item in eligible if item.get('segment') == 'NIFTY100']
    mid = [item for item in eligible if item.get('segment') == 'MIDCAP150']
    selected_large, large_skipped = _select_segment(large, large_cap_limit, sector_limit)
    selected_mid, mid_skipped = _select_segment(mid, mid_cap_limit, sector_limit)
    warnings = []
    if len(selected_large) < large_cap_limit:
        warnings.append(f'Only {len(selected_large)} Large Cap stocks meet the minimum score threshold.')
    if len(selected_mid) < mid_cap_limit:
        warnings.append(f'Only {len(selected_mid)} Midcap stocks meet the minimum score threshold.')
    if large_skipped or mid_skipped:
        warnings.append('Sector concentration limited selection.')
    if market_regime and market_regime.get('classification') == 'BEARISH':
        warnings.append('Market regime is BEARISH; selections are candidates, not suppressed.')
    selected = selected_large + selected_mid
    for item in selected:
        item['selection_reason'].append('Selected after minimum score filter')
    return {
        'market_regime': dict(market_regime) if market_regime else None,
        'large_cap': {'eligible_count': len(large), 'selected_count': len(selected_large), 'stocks': selected_large},
        'mid_cap': {'eligible_count': len(mid), 'selected_count': len(selected_mid), 'stocks': selected_mid},
        'total_selected': len(selected), 'warnings': warnings,
        'stocks': selected,
    }
