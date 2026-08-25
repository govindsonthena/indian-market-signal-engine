"""Optimized batch downloader for large universes using yfinance multi-ticker support."""

from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import yfinance as yf

from src.config import (
    BATCH_DELAY_SECONDS, BATCH_SIZE, DOWNLOAD_TIMEOUT, HISTORY_PERIOD, MIN_DATA_ROWS,
    MAX_FALLBACK_TICKERS, RETRY_ATTEMPTS, RETRY_BACKOFF_FACTOR, RETRY_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


class BatchDownloadError(RuntimeError):
    """Raised when a batch request fails after all bounded retries."""

    def __init__(self, message: str, classification: str = 'DOWNLOAD_ERROR'):
        super().__init__(message)
        self.classification = classification


class BatchDownloadResult:
    """Result of a batch download operation."""

    def __init__(self):
        self.valid = {}  # symbol -> DataFrame
        self.insufficient_history = []  # list of symbols
        self.no_data = []  # list of symbols
        self.download_errors = {}  # symbol -> error message
        self.fallback_attempted = []
        self.fallback_successful = []
        self.total_attempted = 0
        self.elapsed_seconds = 0.0


def split_into_batches(symbols: list[str], batch_size: int = BATCH_SIZE) -> list[list[str]]:
    """Split symbols into batches of specified size."""
    return [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]


def classify_download_error(error: Exception | str) -> str:
    """Classify transport, rate-limit, malformed-response, and unknown failures."""
    message = str(error).lower()
    if any(token in message for token in ('expecting value', 'jsondecode', 'invalid json', 'rate limit', 'too many requests', '429')):
        return 'YAHOO_RATE_LIMIT_OR_JSON_ERROR'
    if any(token in message for token in ('timeout', 'timed out', 'connection', 'network', 'proxy', 'ssl')):
        return 'NETWORK_ERROR'
    return 'DOWNLOAD_ERROR'


def download_batch(symbols: list[str], period: str = HISTORY_PERIOD, timeout: float = DOWNLOAD_TIMEOUT,
                  retries: int = RETRY_ATTEMPTS, retry_delay: float = RETRY_DELAY_SECONDS,
                  backoff_factor: float = RETRY_BACKOFF_FACTOR) -> dict[str, pd.DataFrame]:
    """Download batch using yfinance multi-ticker support. Returns dict of symbol -> DataFrame."""
    if not symbols:
        return {}
    
    ticker_string = ' '.join(symbols)
    for attempt in range(retries):
        try:
            data = yf.download(
                ticker_string, period=period, progress=False, timeout=timeout,
                threads=False,
            )
            if data is None or data.empty:
                raise BatchDownloadError('Yahoo returned an empty response', 'EMPTY_RESPONSE')

            # yfinance uses (price field, ticker) ordering for batch responses.
            if isinstance(data.columns, pd.MultiIndex):
                ticker_level = 1 if symbols[0] in data.columns.get_level_values(1) else 0
                result = {
                    symbol: data.xs(symbol, axis=1, level=ticker_level).copy()
                    for symbol in symbols
                    if symbol in data.columns.get_level_values(ticker_level)
                }
                if not result:
                    raise BatchDownloadError('Yahoo response contained no requested tickers', 'EMPTY_RESPONSE')
                return result

            if len(symbols) == 1:
                return {symbols[0]: data}
            raise BatchDownloadError('Yahoo returned malformed multi-ticker response', 'YAHOO_RATE_LIMIT_OR_JSON_ERROR')
        except Exception as error:
            classification = error.classification if isinstance(error, BatchDownloadError) else classify_download_error(error)
            logger.warning("Batch attempt %s/%s failed [%s] for %s tickers: %s", attempt + 1, retries, classification, len(symbols), error)
            if attempt < retries - 1:
                time.sleep(retry_delay * (backoff_factor ** attempt))

    message = f"Batch download failed after {retries} attempts for {len(symbols)} tickers"
    logger.error("%s [%s]", message, classification)
    raise BatchDownloadError(message, classification)


def _validate_data(symbol: str, data: pd.DataFrame) -> tuple[bool, str]:
    """Validate downloaded data. Returns (is_valid, status_message)."""
    if len(data) < MIN_DATA_ROWS:
        return False, f'insufficient_history ({len(data)} < {MIN_DATA_ROWS})'
    
    required_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}
    if not required_cols.issubset(data.columns):
        return False, 'missing_columns'
    
    nan_ratio = data.isna().sum().sum() / (len(data) * len(data.columns))
    if nan_ratio > 0.1:
        return False, 'excessive_nans'
    
    if (data['Close'] <= 0).any() or (data['Volume'] < 0).any():
        return False, 'invalid_prices'
    
    return True, 'valid'


def batch_download_universe(symbols: list[str], batch_size: int = BATCH_SIZE, period: str = HISTORY_PERIOD,
                            timeout: float = DOWNLOAD_TIMEOUT, retries: int = RETRY_ATTEMPTS,
                            retry_delay: float = RETRY_DELAY_SECONDS,
                            batch_delay: float = BATCH_DELAY_SECONDS,
                            backoff_factor: float = RETRY_BACKOFF_FACTOR,
                            max_fallback_tickers: int = MAX_FALLBACK_TICKERS) -> BatchDownloadResult:
    """Download all symbols using batch strategy. Measures performance and classifies each symbol."""
    result = BatchDownloadResult()
    unique_symbols = list(dict.fromkeys(symbols))
    result.total_attempted = len(unique_symbols)
    start_time = time.time()
    
    batches = split_into_batches(unique_symbols, batch_size)
    logger.info(f"Downloading {len(unique_symbols)} symbols in {len(batches)} batches of ~{batch_size} each")
    
    failed_batches = []
    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"Batch {batch_num}/{len(batches)}: downloading {len(batch)} symbols")
        
        try:
            batch_data = download_batch(batch, period, timeout, retries, retry_delay, backoff_factor=backoff_factor)
        except Exception as error:
            classification = error.classification if isinstance(error, BatchDownloadError) else classify_download_error(error)
            for symbol in batch:
                result.download_errors[symbol] = f'{classification}: {error}'
            failed_batches.append(batch)
            logger.error(
                "Batch %s/%s unavailable [%s]; individual fallback will be capped at %s tickers",
                batch_num, len(batches), classification, max_fallback_tickers,
            )
            continue
        
        for symbol in batch:
            if symbol in batch_data:
                data = batch_data[symbol]
                is_valid, status = _validate_data(symbol, data)
                if is_valid:
                    result.valid[symbol] = data
                    logger.debug(f"{symbol}: VALID")
                elif status.startswith('insufficient'):
                    result.insufficient_history.append(symbol)
                    logger.warning(f"{symbol}: {status}")
                else:
                    result.download_errors[symbol] = status
                    logger.warning(f"{symbol}: {status}")
            else:
                result.no_data.append(symbol)
                logger.warning(f"{symbol}: no data from batch download")
        if batch_num < len(batches):
            time.sleep(batch_delay)

    fallback_symbols = [symbol for failed_batch in failed_batches for symbol in failed_batch]
    fallback_symbols = fallback_symbols[:max_fallback_tickers]
    if fallback_symbols:
        logger.info("Starting controlled individual fallback for %s failed-batch tickers", len(fallback_symbols))
    for index, symbol in enumerate(fallback_symbols):
        result.fallback_attempted.append(symbol)
        try:
            individual_data = download_batch(
                [symbol], period, timeout, retries, retry_delay,
                backoff_factor=backoff_factor,
            ).get(symbol)
        except Exception as error:
            classification = error.classification if isinstance(error, BatchDownloadError) else classify_download_error(error)
            result.download_errors[symbol] = f'{classification}: {error}'
            logger.error("Fallback failed for %s [%s]", symbol, classification)
        else:
            is_valid, status = _validate_data(symbol, individual_data)
            if is_valid:
                result.valid[symbol] = individual_data
                result.fallback_successful.append(symbol)
                result.download_errors.pop(symbol, None)
                logger.info("Fallback succeeded for %s", symbol)
            elif status.startswith('insufficient'):
                result.insufficient_history.append(symbol)
                result.download_errors.pop(symbol, None)
                logger.warning("Fallback data insufficient for %s: %s", symbol, status)
            else:
                result.download_errors[symbol] = status
                logger.warning("Fallback data-quality failure for %s: %s", symbol, status)
        if index < len(fallback_symbols) - 1:
            time.sleep(batch_delay)
    
    result.elapsed_seconds = time.time() - start_time
    return result


def report_batch_result(result: BatchDownloadResult) -> None:
    """Print a summary of batch download results."""
    print('\nBATCH DOWNLOAD SUMMARY')
    print('-' * 60)
    print(f"Expected: {result.total_attempted}")
    print(f"Successful: {len(result.valid)}")
    print(f"Insufficient history: {len(result.insufficient_history)}")
    print(f"No data: {len(result.no_data)}")
    print(f"Download errors: {len(result.download_errors)}")
    print(f"Total elapsed: {result.elapsed_seconds:.2f} seconds")
    avg_per_ticker = result.elapsed_seconds / max(result.total_attempted, 1)
    print(f"Average per ticker: {avg_per_ticker:.3f} seconds")
    print(f"Coverage: {len(result.valid)}/{result.total_attempted} ({100.0 * len(result.valid) / max(result.total_attempted, 1):.1f}%)")
    
    if result.download_errors:
        print(f"\nDownload errors ({len(result.download_errors)}):")
        for symbol, error in list(result.download_errors.items())[:10]:
            print(f"  {symbol}: {error}")
        if len(result.download_errors) > 10:
            print(f"  ... and {len(result.download_errors) - 10} more")
    
    if result.no_data:
        print(f"\nNo data returned ({len(result.no_data)}):")
        for symbol in result.no_data[:10]:
            print(f"  {symbol}")
        if len(result.no_data) > 10:
            print(f"  ... and {len(result.no_data) - 10} more")
