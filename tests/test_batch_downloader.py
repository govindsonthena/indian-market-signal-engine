"""Unit tests for the Phase 7.5 batch downloader."""

from unittest.mock import patch

import pandas as pd
import pytest

from src.batch_downloader import (
    BatchDownloadResult,
    _validate_data,
    batch_download_universe,
    download_batch,
    split_into_batches,
    classify_download_error,
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


def test_download_batch_disables_yfinance_threads():
    symbols = ['S1.NS']
    with patch('src.batch_downloader.yf.download', return_value=make_multiindex_frame(symbols)) as download:
        download_batch(symbols, retries=1)
    assert download.call_args.kwargs['threads'] is False


def test_download_batch_empty_response():
    with patch('src.batch_downloader.yf.download', return_value=pd.DataFrame()):
        with pytest.raises(Exception, match='failed after 1 attempts') as error:
            download_batch(['MISSING.NS'], retries=1)
    assert error.value.classification == 'EMPTY_RESPONSE'


def test_download_error_classification():
    assert classify_download_error('Expecting value: line 1 column 1') == 'YAHOO_RATE_LIMIT_OR_JSON_ERROR'
    assert classify_download_error('connection timed out') == 'NETWORK_ERROR'
    assert classify_download_error('unexpected response') == 'DOWNLOAD_ERROR'


def test_download_batch_retries_then_succeeds():
    response = make_multiindex_frame(['S1.NS'])
    with patch('src.batch_downloader.yf.download', side_effect=[RuntimeError('temporary'), response]) as download:
        result = download_batch(['S1.NS'], retries=2, retry_delay=0)
    assert list(result) == ['S1.NS']
    assert download.call_count == 2


def test_download_batch_retries_empty_response_with_exponential_backoff():
    response = make_multiindex_frame(['S1.NS'])
    with patch('src.batch_downloader.yf.download', side_effect=[pd.DataFrame(), pd.DataFrame(), response]) as download, \
            patch('src.batch_downloader.time.sleep') as sleep:
        result = download_batch(['S1.NS'], retries=3, retry_delay=2, backoff_factor=2)
    assert list(result) == ['S1.NS']
    assert download.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [2, 4]


def test_batch_download_universe_classifies_partial_batch():
    response = make_multiindex_frame(['GOOD.NS'])
    with patch('src.batch_downloader.yf.download', return_value=response):
        result = batch_download_universe(['GOOD.NS', 'MISSING.NS'], batch_size=2, retries=1)
    assert list(result.valid) == ['GOOD.NS']
    assert result.no_data == ['MISSING.NS']
    assert result.insufficient_history == []
    assert result.download_errors == {}


def test_failed_batch_uses_capped_individual_fallback():
    symbols = [f'S{i}.NS' for i in range(4)]
    with patch('src.batch_downloader.download_batch', side_effect=[
            RuntimeError('batch unavailable'), make_multiindex_frame([symbols[0]]),
            make_multiindex_frame([symbols[1]])]):
        result = batch_download_universe(symbols, batch_size=4, retries=1, batch_delay=0, max_fallback_tickers=2)
    assert result.fallback_attempted == symbols[:2]
    assert result.fallback_successful == symbols[:2]
    assert len(result.valid) == 2


def test_failed_batch_does_not_fallback_beyond_global_cap():
    symbols = [f'S{i}.NS' for i in range(4)]
    with patch('src.batch_downloader.download_batch', side_effect=RuntimeError('batch unavailable')) as download:
        result = batch_download_universe(symbols, batch_size=4, retries=1, batch_delay=0, max_fallback_tickers=2)
    assert len(result.fallback_attempted) == 2
    assert download.call_count == 3


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