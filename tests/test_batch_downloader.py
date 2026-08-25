"""Unit tests for the Phase 7.5 batch downloader."""

from unittest.mock import patch

import pandas as pd

from src.batch_downloader import (
    BatchDownloadResult,
    _validate_data,
    batch_download_universe,
    download_batch,
    split_into_batches,
)


def make_frame(rows: int = 250) -> pd.DataFrame:
    return pd.DataFrame({
        'Open': [100.0] * rows,
        'High': [105.0] * rows,
        'Low': [95.0] * rows,
        'Close': [100.0] * rows,
        'Volume': [1000000.0] * rows,
    })


def make_multiindex_frame(symbols: list[str], rows: int = 250) -> pd.DataFrame:
    frames = {symbol: make_frame(rows) for symbol in symbols}
    return pd.concat(frames, axis=1)


def test_split_into_batches():
    symbols = [f'S{i}.NS' for i in range(25)]
    batches = split_into_batches(symbols, batch_size=10)
    assert [len(batch) for batch in batches] == [10, 10, 5]


def test_download_batch_parses_yfinance_multiindex():
    symbols = ['S1.NS', 'S2.NS']
    with patch('src.batch_downloader.yf.download', return_value=make_multiindex_frame(symbols)):
        result = download_batch(symbols, retries=1)
    assert list(result) == symbols
    assert all(list(frame.columns) == ['Open', 'High', 'Low', 'Close', 'Volume'] for frame in result.values())


def test_download_batch_empty_response():
    with patch('src.batch_downloader.yf.download', return_value=pd.DataFrame()):
        assert download_batch(['MISSING.NS'], retries=1) == {}


def test_download_batch_retries_then_succeeds():
    response = make_multiindex_frame(['S1.NS'])
    with patch('src.batch_downloader.yf.download', side_effect=[RuntimeError('temporary'), response]) as download:
        result = download_batch(['S1.NS'], retries=2, retry_delay=0)
    assert list(result) == ['S1.NS']
    assert download.call_count == 2


def test_batch_download_universe_classifies_partial_batch():
    response = make_multiindex_frame(['GOOD.NS'])
    with patch('src.batch_downloader.yf.download', return_value=response):
        result = batch_download_universe(['GOOD.NS', 'MISSING.NS'], batch_size=2, retries=1)
    assert list(result.valid) == ['GOOD.NS']
    assert result.no_data == ['MISSING.NS']
    assert result.insufficient_history == []
    assert result.download_errors == {}


def test_batch_download_universe_classifies_insufficient_history():
    response = make_multiindex_frame(['SHORT.NS'], rows=100)
    with patch('src.batch_downloader.yf.download', return_value=response):
        result = batch_download_universe(['SHORT.NS'], batch_size=1, retries=1)
    assert result.valid == {}
    assert result.insufficient_history == ['SHORT.NS']


def test_duplicate_symbols_are_downloaded_once():
    response = make_multiindex_frame(['S1.NS'])
    with patch('src.batch_downloader.yf.download', return_value=response) as download:
        result = batch_download_universe(['S1.NS', 'S1.NS'], batch_size=10, retries=1)
    assert list(result.valid) == ['S1.NS']
    assert download.call_count == 1


def test_validation_rejects_invalid_close():
    data = make_frame()
    data.loc[0, 'Close'] = -1
    valid, status = _validate_data('BAD.NS', data)
    assert not valid
    assert status == 'invalid_prices'


def test_batch_download_result_defaults():
    result = BatchDownloadResult()
    assert result.total_attempted == 0
    assert result.elapsed_seconds == 0.0