"""Import and validate the official Nifty 100 and Midcap 150 constituent CSVs."""

from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from src.config import NSE_SUFFIX, UNIVERSE_FILE

NIFTY100_CSV_URL = 'https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv'
MIDCAP150_CSV_URL = 'https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv'
SOURCE_AS_OF = '2026-08-21'


def _download_csv(url: str) -> list[dict[str, str]]:
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text)))


def _field(row: dict[str, str], *names: str) -> str:
    normalized = {key.strip().lower().replace(' ', '').replace('_', ''): value.strip()
                  for key, value in row.items() if key}
    for name in names:
        value = normalized.get(name.lower().replace(' ', '').replace('_', ''))
        if value:
            return value
    return ''


def _convert(rows: list[dict[str, str]], segment: str) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        symbol = _field(row, 'Symbol', 'Ticker', 'Security')
        name = _field(row, 'Company Name', 'CompanyName', 'Name')
        sector = _field(row, 'Industry', 'Sector')
        yahoo_symbol = f'{symbol}{NSE_SUFFIX}' if symbol else ''
        mapping_status = 'REQUIRES_VALIDATION' if not symbol else 'PENDING_YAHOO_VALIDATION'
        result.append({
            'symbol': symbol,
            'yahoo_symbol': yahoo_symbol,
            'name': name,
            'segment': segment,
            'sector': sector,
            'mapping_status': mapping_status,
        })
    return result


def build_production_universe(as_of: str = SOURCE_AS_OF) -> dict[str, Any]:
    """Download both official lists and return the normalized production universe."""
    large_cap = _convert(_download_csv(NIFTY100_CSV_URL), 'NIFTY100')
    mid_cap = _convert(_download_csv(MIDCAP150_CSV_URL), 'MIDCAP150')
    universe = {
        'universe_as_of': as_of,
        'source': {
            'provider': 'NSE Indices Limited',
            'nifty100_constituents': NIFTY100_CSV_URL,
            'midcap150_constituents': MIDCAP150_CSV_URL,
            'sector_source': 'Official constituent CSV Industry field',
        },
        'large_cap': large_cap,
        'mid_cap': mid_cap,
    }
    validate_production_universe(universe)
    return universe


def validate_production_universe(universe: dict[str, Any]) -> None:
    """Raise ValueError when production-universe structure is incomplete or duplicated."""
    required = {'symbol', 'yahoo_symbol', 'name', 'segment', 'sector', 'mapping_status'}
    large_cap = universe.get('large_cap', [])
    mid_cap = universe.get('mid_cap', [])
    if len(large_cap) != 100 or len(mid_cap) != 150:
        raise ValueError(f'Expected 100 Nifty 100 and 150 Midcap constituents; got {len(large_cap)} and {len(mid_cap)}')
    entries = large_cap + mid_cap
    if len({item.get('symbol') for item in entries}) != 250:
        raise ValueError('Production universe contains duplicate or empty symbols')
    if len({item.get('yahoo_symbol') for item in entries}) != 250:
        raise ValueError('Production universe contains duplicate or empty Yahoo symbols')
    for item in entries:
        if not required.issubset(item) or not all(item.get(key) for key in required - {'mapping_status'}):
            raise ValueError(f'Missing required constituent field: {item}')
        if item['segment'] not in {'NIFTY100', 'MIDCAP150'}:
            raise ValueError(f"Invalid segment: {item['segment']}")


def refresh_production_universe(output_file: str = UNIVERSE_FILE) -> dict[str, Any]:
    """Fetch, validate, and persist the authoritative production universe."""
    universe = build_production_universe()
    Path(output_file).write_text(json.dumps(universe, indent=2), encoding='utf-8')
    return universe


if __name__ == '__main__':
    refreshed = refresh_production_universe()
    print(f"Production universe written: {len(refreshed['large_cap']) + len(refreshed['mid_cap'])} constituents")
