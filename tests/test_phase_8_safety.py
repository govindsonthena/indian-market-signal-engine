"""Tests for the Phase 8 market-data safety gate."""

import pytest
from pathlib import Path

from phase_8_production_analysis import (
    DataSourceUnavailableError,
    validate_data_source_coverage,
)
from src.batch_downloader import BatchDownloadResult


def test_low_coverage_aborts_before_scoring():
    with pytest.raises(DataSourceUnavailableError, match='DATA_SOURCE_UNAVAILABLE'):
        validate_data_source_coverage(0, 250)


def test_coverage_below_threshold_aborts():
    with pytest.raises(DataSourceUnavailableError, match='DATA_SOURCE_UNAVAILABLE'):
        validate_data_source_coverage(200, 250)


def test_acceptable_coverage_continues():
    validate_data_source_coverage(244, 250)


def test_data_source_failure_preserves_previous_latest_json(tmp_path, monkeypatch):
    import phase_8_production_analysis as production

    output_file = Path(tmp_path) / 'latest.json'
    previous_report = '{"eligible_count": 244, "selected_stocks": []}'
    output_file.write_text(previous_report, encoding='utf-8')
    monkeypatch.setattr(production, 'OUTPUT_FILE', output_file)
    monkeypatch.setattr(production, 'batch_download_universe', lambda symbols, period: BatchDownloadResult())

    with pytest.raises(DataSourceUnavailableError, match='DATA_SOURCE_UNAVAILABLE'):
        production.main()

    assert output_file.read_text(encoding='utf-8') == previous_report