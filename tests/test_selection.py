"""Deterministic tests for segment and sector-constrained selection."""

from src.selection import select_top_stocks


def candidate(symbol, segment, score, sector='Technology', status='OK'):
    return {
        'symbol': symbol, 'name': symbol, 'segment': segment, 'sector': sector,
        'overall_score': score, 'score_status': status,
        'factor_scores': {},
    }


def candidates(large=8, mid=8):
    result = []
    for index in range(large):
        result.append(candidate(f'L{index}', 'NIFTY100', 95 - index,
                                ['Technology', 'Finance', 'Energy', 'Healthcare'][index % 4]))
    for index in range(mid):
        result.append(candidate(f'M{index}', 'MIDCAP150', 94 - index,
                                ['Technology', 'Finance', 'Energy', 'Healthcare'][index % 4]))
    return result


def test_segment_limits_and_ordering():
    result = select_top_stocks(candidates())
    assert result['large_cap']['selected_count'] == 5
    assert result['mid_cap']['selected_count'] == 5
    assert result['total_selected'] == 10
    assert [item['symbol'] for item in result['large_cap']['stocks']] == ['L0', 'L1', 'L2', 'L3', 'L4']


def test_sector_cap_and_insufficient_candidates():
    same_sector = [candidate(f'L{index}', 'NIFTY100', 95 - index) for index in range(8)]
    result = select_top_stocks(same_sector)
    assert result['large_cap']['selected_count'] == 2
    assert 'Sector concentration limited selection.' in result['warnings']

    few = select_top_stocks([candidate('L1', 'NIFTY100', 80, 'Finance')])
    assert few['total_selected'] == 1
    assert any('Only 0 Midcap' in warning for warning in few['warnings'])


def test_threshold_missing_scores_and_sector():
    data = candidates(2, 2)
    data.extend([
        candidate('LOW', 'NIFTY100', 59, 'Finance'),
        candidate('MISSING', 'NIFTY100', None, 'Energy', 'INSUFFICIENT_DATA'),
        candidate('UNKNOWN', 'MIDCAP150', 90, None),
    ])
    result = select_top_stocks(data)
    assert all(item['overall_score'] >= 60 for item in result['stocks'])
    assert result['large_cap']['eligible_count'] == 2
    assert result['mid_cap']['eligible_count'] == 3
    assert result['stocks'][-1]['signal'] in {'STRONG', 'POSITIVE', 'WATCH'}


def test_all_below_threshold_and_bearish_context():
    result = select_top_stocks(
        [candidate('LOW', 'NIFTY100', 20)],
        market_regime={'classification': 'BEARISH', 'score': 20},
    )
    assert result['total_selected'] == 0
    assert any('BEARISH' in warning for warning in result['warnings'])
