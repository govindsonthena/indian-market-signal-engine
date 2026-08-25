"""Structural tests for the production universe importer."""

import pytest

from src.production_universe import validate_production_universe


def item(index, segment):
    return {
        'symbol': f'SYMBOL{index}', 'yahoo_symbol': f'SYMBOL{index}.NS',
        'name': f'Company {index}', 'segment': segment,
        'sector': 'Technology', 'mapping_status': 'PENDING_YAHOO_VALIDATION',
    }


def production_universe():
    return {
        'universe_as_of': '2026-08-21',
        'large_cap': [item(i, 'NIFTY100') for i in range(100)],
        'mid_cap': [item(i + 100, 'MIDCAP150') for i in range(150)],
    }


def test_production_counts_and_unique_mappings():
    validate_production_universe(production_universe())


def test_duplicate_symbols_are_rejected():
    data = production_universe()
    data['mid_cap'][0]['symbol'] = data['large_cap'][0]['symbol']
    with pytest.raises(ValueError, match='duplicate'):
        validate_production_universe(data)


def test_missing_required_fields_are_rejected():
    data = production_universe()
    del data['large_cap'][0]['sector']
    with pytest.raises(ValueError, match='Missing required'):
        validate_production_universe(data)
