"""
Universe Definition Module

Manages the current Nifty 100 and Nifty Midcap 150 constituents.
This allows the universe to be easily updated as index constituents change.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from src.config import UNIVERSE_FILE, NIFTY_100_COUNT, NIFTY_MIDCAP_150_COUNT


class UniverseManager:
    """Manages the stock universe for analysis."""

    def __init__(self, universe_file: str = UNIVERSE_FILE):
        """
        Initialize the universe manager.

        Args:
            universe_file: Path to universe.json file
        """
        self.universe_file = universe_file
        self.universe_data = None
        self._load_universe()

    def _load_universe(self):
        """Load universe from JSON file, or create default if not exists."""
        if os.path.exists(self.universe_file):
            with open(self.universe_file, 'r') as f:
                self.universe_data = json.load(f)
        else:
            # Initialize with empty structure
            self.universe_data = {
                'updated_at': datetime.now().isoformat(),
                'large_cap': [],
                'mid_cap': [],
            }
            self._save_universe()

    def _save_universe(self):
        """Save universe to JSON file."""
        os.makedirs(os.path.dirname(self.universe_file), exist_ok=True)
        with open(self.universe_file, 'w') as f:
            json.dump(self.universe_data, f, indent=2)

    def add_large_cap_stock(self, symbol: str, name: str, sector: str = '') -> None:
        """
        Add a Nifty 100 stock to the universe.

        Args:
            symbol: NSE symbol with .NS suffix
            name: Company name
            sector: Sector classification
        """
        stock = {'symbol': symbol, 'name': name, 'segment': 'NIFTY100', 'sector': sector}
        # Avoid duplicates
        if not any(s['symbol'] == symbol for s in self.universe_data['large_cap']):
            self.universe_data['large_cap'].append(stock)
            self._save_universe()

    def add_mid_cap_stock(self, symbol: str, name: str, sector: str = '') -> None:
        """
        Add a Nifty Midcap 150 stock to the universe.

        Args:
            symbol: NSE symbol with .NS suffix
            name: Company name
            sector: Sector classification
        """
        stock = {'symbol': symbol, 'name': name, 'segment': 'MIDCAP150', 'sector': sector}
        # Avoid duplicates
        if not any(s['symbol'] == symbol for s in self.universe_data['mid_cap']):
            self.universe_data['mid_cap'].append(stock)
            self._save_universe()

    def get_large_cap_symbols(self) -> List[str]:
        """Get list of Nifty 100 symbols."""
        return [stock['symbol'] for stock in self.universe_data['large_cap']]

    def get_mid_cap_symbols(self) -> List[str]:
        """Get list of Nifty Midcap 150 symbols."""
        return [stock['symbol'] for stock in self.universe_data['mid_cap']]

    def get_all_symbols(self) -> List[str]:
        """Get all symbols from both segments."""
        return self.get_large_cap_symbols() + self.get_mid_cap_symbols()

    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """Get information for a specific stock."""
        for stock in self.universe_data['large_cap']:
            if stock['symbol'] == symbol:
                return stock
        for stock in self.universe_data['mid_cap']:
            if stock['symbol'] == symbol:
                return stock
        return None

    def get_yahoo_symbol(self, symbol: str) -> Optional[str]:
        """Return an explicit Yahoo symbol, or the legacy symbol field as fallback."""
        info = self.get_stock_info(symbol)
        if info is None:
            return None
        return info.get('yahoo_symbol') or info.get('symbol')

    def validate_universe(self) -> Dict:
        """
        Validate universe configuration.

        Returns:
            Dictionary with validation results
        """
        large_cap_count = len(self.universe_data['large_cap'])
        mid_cap_count = len(self.universe_data['mid_cap'])
        total_count = large_cap_count + mid_cap_count

        return {
            'large_cap_count': large_cap_count,
            'large_cap_expected': NIFTY_100_COUNT,
            'large_cap_valid': large_cap_count == NIFTY_100_COUNT,
            'mid_cap_count': mid_cap_count,
            'mid_cap_expected': NIFTY_MIDCAP_150_COUNT,
            'mid_cap_valid': mid_cap_count == NIFTY_MIDCAP_150_COUNT,
            'total_count': total_count,
            'total_expected': NIFTY_100_COUNT + NIFTY_MIDCAP_150_COUNT,
            'all_valid': (large_cap_count == NIFTY_100_COUNT
                          and mid_cap_count == NIFTY_MIDCAP_150_COUNT),
            'updated_at': self.universe_data.get('updated_at'),
        }

    def __repr__(self):
        return (f"UniverseManager(large_cap={len(self.universe_data['large_cap'])}, "
                f"mid_cap={len(self.universe_data['mid_cap'])})")


if __name__ == '__main__':
    manager = UniverseManager()
    validation = manager.validate_universe()
    print("Universe Validation:")
    for key, value in validation.items():
        print(f"  {key}: {value}")
