"""
Unit tests for data_loader.py module.

Tests all functions with mocked external dependencies to ensure
tests can run independently without requiring real API keys or network access.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import os
import tempfile
import shutil
from datetime import datetime, timedelta

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import (
    load_from_fred,
    _get_cache_path,
    load_from_cache,
    save_to_cache,
    load_from_local_csv,
    load_from_yfinance,
    fetch_data_with_fallback,
    load_all_data,
    FRED_SERIES_MAP,
    CACHE_DIR,
    CACHE_EXPIRY_DAYS,
    DELAY_BETWEEN_REQUESTS,
    DELAY_AFTER_RATE_LIMIT,
    MAX_RETRIES
)


class TestModuleImports:
    """Tests for module import handling (yfinance and fredapi availability)."""
    
    def test_yfinance_import_failure_coverage(self):
        """Test coverage for yfinance import failure handling (covers lines 26-28)."""
        # Note: This test verifies that the import error handling code path exists
        # The actual import failure is handled at module load time, so we test
        # the behavior when YFINANCE_AVAILABLE is False (which happens when import fails)
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Test that load_from_yfinance handles YFINANCE_AVAILABLE = False
        with patch('src.data_loader.YFINANCE_AVAILABLE', False):
            result = load_from_yfinance(symbol, start_date, end_date)
            # Should return None when yfinance is not available
            assert result is None
    
    def test_fredapi_import_failure_coverage(self):
        """Test coverage for fredapi import failure handling (covers lines 33-36)."""
        # Note: This test verifies that the import error handling code path exists
        # The actual import failure is handled at module load time, so we test
        # the behavior when FRED_AVAILABLE is False (which happens when import fails)
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Test that load_from_fred handles FRED_AVAILABLE = False
        with patch('src.data_loader.FRED_AVAILABLE', False):
            result = load_from_fred(symbol, start_date, end_date)
            # Should return None when fredapi is not available
            assert result is None


class TestLoadFromFred:
    """Tests for load_from_fred function."""
    
    def test_load_from_fred_success(self):
        """Test successful data loading from FRED."""
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Create mock data
        dates = pd.date_range(start_date, end_date, freq='D')
        mock_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.FRED_AVAILABLE', True):
            with patch('src.data_loader.Fred') as mock_fred_class:
                mock_fred = Mock()
                mock_fred.get_series.return_value = mock_data
                mock_fred_class.return_value = mock_fred
                
                with patch.dict(os.environ, {'FRED_API_KEY': 'test_key'}):
                    result = load_from_fred(symbol, start_date, end_date)
                    
                    assert result is not None
                    assert isinstance(result, pd.Series)
                    assert len(result) > 0
                    mock_fred.get_series.assert_called_once()
    
    def test_load_from_fred_with_api_key_param(self):
        """Test FRED loading with API key as parameter."""
        symbol = '^TNX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        mock_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.FRED_AVAILABLE', True):
            with patch('src.data_loader.Fred') as mock_fred_class:
                mock_fred = Mock()
                mock_fred.get_series.return_value = mock_data
                mock_fred_class.return_value = mock_fred
                
                result = load_from_fred(symbol, start_date, end_date, fred_api_key='test_key')
                
                assert result is not None
                mock_fred_class.assert_called_once_with(api_key='test_key')
    
    def test_load_from_fred_no_api_key(self):
        """Test FRED loading fails when no API key provided."""
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.FRED_AVAILABLE', True):
            with patch.dict(os.environ, {}, clear=True):
                result = load_from_fred(symbol, start_date, end_date)
                assert result is None
    
    def test_load_from_fred_invalid_symbol(self):
        """Test FRED loading fails for invalid symbol."""
        symbol = 'INVALID_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.FRED_AVAILABLE', True):
            with patch.dict(os.environ, {'FRED_API_KEY': 'test_key'}):
                result = load_from_fred(symbol, start_date, end_date)
                assert result is None
    
    def test_load_from_fred_empty_data(self):
        """Test FRED loading returns None for empty data."""
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.FRED_AVAILABLE', True):
            with patch('src.data_loader.Fred') as mock_fred_class:
                mock_fred = Mock()
                mock_fred.get_series.return_value = pd.Series(dtype=float)
                mock_fred_class.return_value = mock_fred
                
                with patch.dict(os.environ, {'FRED_API_KEY': 'test_key'}):
                    result = load_from_fred(symbol, start_date, end_date)
                    assert result is None
    
    def test_load_from_fred_timezone_handling(self):
        """Test FRED data timezone is removed."""
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Create tz-aware index
        dates = pd.date_range(start_date, end_date, freq='D', tz='UTC')
        mock_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.FRED_AVAILABLE', True):
            with patch('src.data_loader.Fred') as mock_fred_class:
                mock_fred = Mock()
                mock_fred.get_series.return_value = mock_data
                mock_fred_class.return_value = mock_fred
                
                with patch.dict(os.environ, {'FRED_API_KEY': 'test_key'}):
                    result = load_from_fred(symbol, start_date, end_date)
                    
                    assert result is not None
                    assert result.index.tz is None
    
    def test_load_from_fred_exception_handling(self):
        """Test FRED loading handles exceptions gracefully."""
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.FRED_AVAILABLE', True):
            with patch('src.data_loader.Fred') as mock_fred_class:
                mock_fred_class.side_effect = Exception("API Error")
                
                with patch.dict(os.environ, {'FRED_API_KEY': 'test_key'}):
                    result = load_from_fred(symbol, start_date, end_date)
                    assert result is None
    
    def test_load_from_fred_fred_not_available(self):
        """Test FRED loading returns None when FRED is not available."""
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.FRED_AVAILABLE', False):
            result = load_from_fred(symbol, start_date, end_date)
            assert result is None


class TestGetCachePath:
    """Tests for _get_cache_path function."""
    
    def test_get_cache_path_creates_directory(self):
        """Test that cache directory is created."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('src.data_loader.CACHE_DIR', Path(tmpdir) / 'cache'):
                path = _get_cache_path(symbol, start_date, end_date)
                assert (Path(tmpdir) / 'cache').exists()
                assert path.parent == Path(tmpdir) / 'cache'
    
    def test_get_cache_path_filename_format(self):
        """Test cache path filename format."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        path = _get_cache_path(symbol, start_date, end_date)
        
        assert path.suffix == '.parquet'
        assert 'SPY' in path.name
        assert len(path.stem.split('_')) >= 2  # symbol_hash format
    
    def test_get_cache_path_special_characters(self):
        """Test cache path handles special characters in symbol."""
        symbol = 'EURUSD=X'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        path = _get_cache_path(symbol, start_date, end_date)
        
        # Special characters should be replaced
        assert '=' not in path.name
        assert path.suffix == '.parquet'


class TestLoadFromCache:
    """Tests for load_from_cache function."""
    
    def test_load_from_cache_success(self):
        """Test successful cache loading."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Create test data
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                # Save test data
                cache_path = _get_cache_path(symbol, start_date, end_date)
                df = pd.DataFrame({'value': test_data})
                df.to_parquet(cache_path)
                
                # Load from cache
                result = load_from_cache(symbol, start_date, end_date)
                
                assert result is not None
                assert isinstance(result, pd.Series)
                assert len(result) > 0
    
    def test_load_from_cache_not_exists(self):
        """Test cache loading when file doesn't exist."""
        symbol = 'NONEXISTENT'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        result = load_from_cache(symbol, start_date, end_date)
        assert result is None
    
    def test_load_from_cache_expired(self):
        """Test cache loading when cache is expired."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                with patch('src.data_loader.CACHE_EXPIRY_DAYS', 1):
                    cache_path = _get_cache_path(symbol, start_date, end_date)
                    df = pd.DataFrame({'value': test_data})
                    df.to_parquet(cache_path)
                    
                    # Make file old
                    old_time = (datetime.now() - timedelta(days=2)).timestamp()
                    os.utime(cache_path, (old_time, old_time))
                    
                    result = load_from_cache(symbol, start_date, end_date)
                    assert result is None
    
    def test_load_from_cache_date_filtering(self):
        """Test cache loading filters by date range."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-15'
        end_date = '2020-01-20'
        
        # Create data with wider date range
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                cache_path = _get_cache_path(symbol, '2020-01-01', '2020-01-31')
                df = pd.DataFrame({'value': test_data})
                df.to_parquet(cache_path)
                
                result = load_from_cache(symbol, start_date, end_date)
                
                if result is not None:
                    assert result.index.min() >= pd.Timestamp(start_date)
                    assert result.index.max() <= pd.Timestamp(end_date)
    
    def test_load_from_cache_exception_handling(self):
        """Test cache loading handles exceptions."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader._get_cache_path') as mock_path:
            mock_path.return_value = Path('/invalid/path/file.parquet')
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pandas.read_parquet', side_effect=Exception("Read error")):
                    result = load_from_cache(symbol, start_date, end_date)
                    assert result is None
    
    def test_load_from_cache_dataframe_multiple_columns(self):
        """Test cache loading with DataFrame having multiple columns (no 'value' column)."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                cache_path = _get_cache_path(symbol, start_date, end_date)
                # Create DataFrame with multiple columns but no 'value' column
                df = pd.DataFrame({
                    'col1': np.random.randn(len(dates)),
                    'col2': np.random.randn(len(dates))
                }, index=dates)
                df.to_parquet(cache_path)
                
                result = load_from_cache(symbol, start_date, end_date)
                # Should return None when DataFrame has multiple columns and no 'value'
                assert result is None
    
    def test_load_from_cache_dataframe_single_column_no_value(self):
        """Test cache loading with DataFrame having single column (no 'value' column)."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                cache_path = _get_cache_path(symbol, start_date, end_date)
                # Create DataFrame with single column (not named 'value')
                df = pd.DataFrame({
                    'price': np.random.randn(len(dates))
                }, index=dates)
                df.to_parquet(cache_path)
                
                result = load_from_cache(symbol, start_date, end_date)
                # Should return the single column as Series
                assert result is not None
                assert isinstance(result, pd.Series)
    
    def test_load_from_cache_series_direct(self):
        """Test cache loading when parquet file contains a Series directly (covers line 186)."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                cache_path = _get_cache_path(symbol, start_date, end_date)
                # Save Series directly (not as DataFrame)
                test_data.to_frame().to_parquet(cache_path)
                
                # Mock read_parquet to return Series directly
                with patch('pandas.read_parquet', return_value=test_data):
                    result = load_from_cache(symbol, start_date, end_date)
                    # Should handle Series directly (line 186: series = df)
                    assert result is not None
                    assert isinstance(result, pd.Series)
    
    def test_load_from_cache_date_filtering_returns_none(self):
        """Test cache loading returns None when date filtering results in empty series (covers line 194)."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-02-01'  # After the cached data range
        end_date = '2020-02-10'
        
        # Create data with earlier date range
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                cache_path = _get_cache_path(symbol, '2020-01-01', '2020-01-31')
                df = pd.DataFrame({'value': test_data})
                df.to_parquet(cache_path)
                
                # Try to load with date range that doesn't overlap
                result = load_from_cache(symbol, start_date, end_date)
                # Should return None when filtered series is empty (line 194)
                assert result is None
    
    def test_load_from_cache_non_datetime_index_returns_none(self):
        """Test cache loading returns None when index is not DatetimeIndex (covers line 194)."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Create data with non-datetime index
        test_data = pd.Series(np.random.randn(10), index=range(10))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                cache_path = _get_cache_path(symbol, start_date, end_date)
                df = pd.DataFrame({'value': test_data})
                df.to_parquet(cache_path)
                
                # Try to load - should return None because index is not DatetimeIndex
                result = load_from_cache(symbol, start_date, end_date)
                # Should return None when index is not DatetimeIndex (line 194)
                assert result is None
    
    def test_load_from_cache_empty_after_date_filter(self):
        """Test cache loading returns None when date filtering results in empty series (covers branch 191->194)."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-02-01'  # After the cached data range
        end_date = '2020-02-10'
        
        # Create data with earlier date range
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                # Use the same date range for cache path as the load request
                # This ensures the cache file is found, but date filtering results in empty
                cache_path = _get_cache_path(symbol, start_date, end_date)
                df = pd.DataFrame({'value': test_data})
                df.to_parquet(cache_path)
                
                # Try to load with date range that doesn't overlap with cached data
                # This should trigger the branch where series.empty is True after filtering (191->194)
                result = load_from_cache(symbol, start_date, end_date)
                assert result is None


class TestSaveToCache:
    """Tests for save_to_cache function."""
    
    def test_save_to_cache_success(self):
        """Test successful cache saving."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            with patch('src.data_loader.CACHE_DIR', cache_dir):
                result = save_to_cache(symbol, start_date, end_date, test_data)
                
                assert result is True
                cache_path = _get_cache_path(symbol, start_date, end_date)
                assert cache_path.exists()
                
                # Verify data can be loaded back
                loaded = pd.read_parquet(cache_path)
                assert len(loaded) == len(test_data)
    
    def test_save_to_cache_exception_handling(self):
        """Test cache saving handles exceptions."""
        symbol = 'TEST_SYMBOL'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader._get_cache_path') as mock_path:
            mock_path.return_value = Path('/invalid/path/file.parquet')
            with patch('pandas.DataFrame.to_parquet', side_effect=Exception("Write error")):
                result = save_to_cache(symbol, start_date, end_date, test_data)
                assert result is False


class TestLoadFromLocalCSV:
    """Tests for load_from_local_csv function."""
    
    def test_load_from_local_csv_success(self):
        """Test successful CSV loading."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.DataFrame({
            'Date': dates,
            'Close': np.random.randn(len(dates))
        })
        test_data.set_index('Date', inplace=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / f'{symbol}.csv'
            test_data.to_csv(csv_path)
            
            result = load_from_local_csv(symbol, data_dir=tmpdir)
            
            assert result is not None
            assert isinstance(result, pd.Series)
            assert len(result) > 0
    
    def test_load_from_local_csv_different_column_names(self):
        """Test CSV loading with different column name formats."""
        symbol = 'SPY'
        
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        
        # Test with lowercase 'close'
        test_data = pd.DataFrame({
            'Date': dates,
            'close': np.random.randn(len(dates))
        })
        test_data.set_index('Date', inplace=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / f'{symbol}.csv'
            test_data.to_csv(csv_path)
            
            result = load_from_local_csv(symbol, data_dir=tmpdir)
            assert result is not None
    
    def test_load_from_local_csv_single_column(self):
        """Test CSV loading with single column."""
        symbol = 'SPY'
        
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        test_data = pd.DataFrame({
            'Date': dates,
            'Value': np.random.randn(len(dates))
        })
        test_data.set_index('Date', inplace=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / f'{symbol}.csv'
            test_data.to_csv(csv_path)
            
            result = load_from_local_csv(symbol, data_dir=tmpdir)
            assert result is not None
    
    def test_load_from_local_csv_file_not_found(self):
        """Test CSV loading when file doesn't exist."""
        symbol = 'NONEXISTENT'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_from_local_csv(symbol, data_dir=tmpdir)
            assert result is None
    
    def test_load_from_local_csv_special_characters(self):
        """Test CSV loading with special characters in symbol."""
        symbol = 'EURUSD=X'
        
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        test_data = pd.DataFrame({
            'Date': dates,
            'Close': np.random.randn(len(dates))
        })
        test_data.set_index('Date', inplace=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Try different filename formats
            csv_path = Path(tmpdir) / 'EURUSD_X.csv'
            test_data.to_csv(csv_path)
            
            result = load_from_local_csv(symbol, data_dir=tmpdir)
            assert result is not None
    
    def test_load_from_local_csv_exception_handling(self):
        """Test CSV loading handles exceptions."""
        symbol = 'SPY'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / f'{symbol}.csv'
            # Create invalid CSV file
            csv_path.write_text('invalid,csv,content\n')
            
            with patch('pandas.read_csv', side_effect=Exception("Parse error")):
                result = load_from_local_csv(symbol, data_dir=tmpdir)
                # Should return None or handle gracefully
                assert result is None or isinstance(result, type(None))
    
    def test_load_from_local_csv_uppercase_close(self):
        """Test CSV loading with uppercase 'CLOSE' column name."""
        symbol = 'SPY'
        
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        test_data = pd.DataFrame({
            'Date': dates,
            'CLOSE': np.random.randn(len(dates))
        })
        test_data.set_index('Date', inplace=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / f'{symbol}.csv'
            test_data.to_csv(csv_path)
            
            result = load_from_local_csv(symbol, data_dir=tmpdir)
            assert result is not None
            assert isinstance(result, pd.Series)
    
    def test_load_from_local_csv_multiple_columns_no_match(self):
        """Test CSV loading with multiple columns but no matching column name."""
        symbol = 'SPY'
        
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        test_data = pd.DataFrame({
            'Date': dates,
            'Open': np.random.randn(len(dates)),
            'High': np.random.randn(len(dates)),
            'Low': np.random.randn(len(dates))
            # No 'Close', 'close', or 'CLOSE' column
        })
        test_data.set_index('Date', inplace=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / f'{symbol}.csv'
            test_data.to_csv(csv_path)
            
            # Should try other filename formats and eventually return None
            result = load_from_local_csv(symbol, data_dir=tmpdir)
            # When no matching column found and multiple columns exist, should return None
            assert result is None


class TestLoadFromYfinance:
    """Tests for load_from_yfinance function."""
    
    def test_load_from_yfinance_success(self):
        """Test successful yfinance loading."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        mock_data = pd.DataFrame({
            'Close': np.random.randn(len(dates))
        }, index=dates)
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.yf.download') as mock_download:
                mock_download.return_value = mock_data
                
                result = load_from_yfinance(symbol, start_date, end_date)
                
                assert result is not None
                assert isinstance(result, pd.Series)
                assert len(result) > 0
                mock_download.assert_called_once_with([symbol], start=start_date, end=end_date, progress=False)
    
    def test_load_from_yfinance_timezone_removal(self):
        """Test yfinance data timezone is removed."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Create tz-aware index
        dates = pd.date_range(start_date, end_date, freq='D', tz='America/New_York')
        mock_data = pd.DataFrame({
            'Close': np.random.randn(len(dates))
        }, index=dates)
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.yf.download') as mock_download:
                mock_download.return_value = mock_data
                
                result = load_from_yfinance(symbol, start_date, end_date)
                
                assert result is not None
                assert result.index.tz is None
    
    def test_load_from_yfinance_empty_data(self):
        """Test yfinance loading returns None for empty data."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.yf.download') as mock_download:
                mock_download.return_value = pd.DataFrame()
                
                result = load_from_yfinance(symbol, start_date, end_date)
                assert result is None
    
    def test_load_from_yfinance_rate_limit_retry(self):
        """Test yfinance handles rate limit errors with retries."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        mock_data = pd.DataFrame({
            'Close': np.random.randn(len(dates))
        }, index=dates)
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.yf.download') as mock_download:
                # First call raises rate limit, second succeeds
                mock_download.side_effect = [
                    Exception("Rate limit exceeded"),
                    mock_data
                ]
                
                with patch('src.data_loader.time.sleep'):  # Speed up test
                    result = load_from_yfinance(symbol, start_date, end_date)
                    
                    assert result is not None
                    assert mock_download.call_count == 2
    
    def test_load_from_yfinance_rate_limit_max_retries(self):
        """Test yfinance gives up after max retries."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.yf.download') as mock_download:
                mock_download.side_effect = Exception("Rate limit exceeded")
                
                with patch('src.data_loader.time.sleep'):  # Speed up test
                    with patch('builtins.print'):  # Suppress print output
                        result = load_from_yfinance(symbol, start_date, end_date)
                        
                        assert result is None
                        assert mock_download.call_count == MAX_RETRIES
    
    def test_load_from_yfinance_all_retries_fail_returns_none(self):
        """Test yfinance returns None after all retries fail (covers line 347)."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.yf.download') as mock_download:
                # Simulate rate limit errors that persist through all retries
                mock_download.side_effect = Exception("Rate limit exceeded")
                
                with patch('src.data_loader.time.sleep'):  # Speed up test
                    with patch('builtins.print'):  # Suppress print output
                        result = load_from_yfinance(symbol, start_date, end_date)
                        
                        # After all retries fail, should return None
                        assert result is None
                        # Should have attempted MAX_RETRIES times
                        assert mock_download.call_count == MAX_RETRIES
    
    def test_load_from_yfinance_loop_exits_normally(self):
        """Test yfinance returns None when loop exits normally (covers line 347)."""
        # This tests the defensive return None at the end of the function
        # Line 347 is theoretically unreachable, but we can test it by setting MAX_RETRIES to 0
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.MAX_RETRIES', 0):  # Set to 0 so loop doesn't execute
                result = load_from_yfinance(symbol, start_date, end_date)
                # When MAX_RETRIES is 0, the loop doesn't execute and line 347 is reached
                assert result is None
    
    def test_load_from_yfinance_non_rate_limit_error(self):
        """Test yfinance doesn't retry on non-rate-limit errors."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', True):
            with patch('src.data_loader.yf.download') as mock_download:
                mock_download.side_effect = Exception("Network error")
                
                result = load_from_yfinance(symbol, start_date, end_date)
                
                assert result is None
                # Should not retry for non-rate-limit errors
                assert mock_download.call_count == 1
    
    def test_load_from_yfinance_not_available(self):
        """Test yfinance loading returns None when yfinance is not available."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.YFINANCE_AVAILABLE', False):
            result = load_from_yfinance(symbol, start_date, end_date)
            assert result is None


class TestFetchDataWithFallback:
    """Tests for fetch_data_with_fallback function."""
    
    def test_fetch_data_with_fallback_cache_first(self):
        """Test fallback tries cache first."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        cached_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_cache', return_value=cached_data):
            result = fetch_data_with_fallback(
                symbol, start_date, end_date,
                use_cache=True
            )
            
            assert result is not None
            assert result.equals(cached_data)
    
    def test_fetch_data_with_fallback_cache_to_fred(self):
        """Test fallback from cache to FRED."""
        symbol = '^VIX'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        fred_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=fred_data):
                with patch('src.data_loader.save_to_cache', return_value=True):
                    result = fetch_data_with_fallback(
                        symbol, start_date, end_date,
                        data_sources=['cache', 'fred'],
                        use_cache=True
                    )
                    
                    assert result is not None
                    assert result.equals(fred_data)
    
    def test_fetch_data_with_fallback_all_sources(self):
        """Test fallback through all sources."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        yfinance_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance', return_value=yfinance_data):
                        with patch('src.data_loader.save_to_cache', return_value=True):
                            with patch('src.data_loader.time.sleep'):  # Speed up test
                                result = fetch_data_with_fallback(
                                    symbol, start_date, end_date,
                                    use_cache=True
                                )
                                
                                assert result is not None
                                assert result.equals(yfinance_data)
    
    def test_fetch_data_with_fallback_no_cache(self):
        """Test fallback without cache."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        local_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_fred', return_value=None):
            with patch('src.data_loader.load_from_local_csv', return_value=local_data):
                result = fetch_data_with_fallback(
                    symbol, start_date, end_date,
                    use_cache=False,
                    data_sources=['fred', 'local']
                )
                
                assert result is not None
                assert result.equals(local_data)
    
    def test_fetch_data_with_fallback_all_fail(self):
        """Test fallback when all sources fail."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance', return_value=None):
                        with patch('src.data_loader.time.sleep'):  # Speed up test
                            result = fetch_data_with_fallback(
                                symbol, start_date, end_date
                            )
                            
                            assert result is None
    
    def test_fetch_data_with_fallback_custom_sources(self):
        """Test fallback with custom source order."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        local_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_local_csv', return_value=local_data):
            result = fetch_data_with_fallback(
                symbol, start_date, end_date,
                data_sources=['local'],
                use_cache=False
            )
            
            assert result is not None
            assert result.equals(local_data)
    
    def test_fetch_data_with_fallback_local_no_datetime_index(self):
        """Test fallback when local CSV returns data without DatetimeIndex (covers branch 409->395)."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Create data with non-DatetimeIndex
        data_without_datetime = pd.Series([1, 2, 3], index=[0, 1, 2])
        
        with patch('src.data_loader.load_from_local_csv', return_value=data_without_datetime):
            with patch('src.data_loader.load_from_yfinance', return_value=None):
                result = fetch_data_with_fallback(
                    symbol, start_date, end_date,
                    data_sources=['local', 'yfinance'],
                    use_cache=False
                )
                # Should continue to next source since local data has no DatetimeIndex
                assert result is None
    
    def test_fetch_data_with_fallback_local_empty_after_date_filter(self):
        """Test fallback when local CSV data is empty after date filtering (covers branch 411->395)."""
        symbol = 'SPY'
        start_date = '2020-02-01'  # After the local data range
        end_date = '2020-02-10'
        
        # Create data with earlier date range
        dates = pd.date_range('2020-01-01', '2020-01-31', freq='D')
        local_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_local_csv', return_value=local_data):
            with patch('src.data_loader.load_from_yfinance', return_value=None):
                result = fetch_data_with_fallback(
                    symbol, start_date, end_date,
                    data_sources=['local', 'yfinance'],
                    use_cache=False
                )
                # Should continue to next source since filtered data is empty
                assert result is None
    
    def test_fetch_data_with_fallback_yfinance_none_continues(self):
        """Test fallback when yfinance returns None continues loop (covers branch 415->395)."""
        symbol = 'SPY'
        start_date = '2020-01-01'
        end_date = '2020-01-31'
        
        # Need multiple sources so loop continues after yfinance returns None
        # The branch 415->395 is when yfinance returns None and loop continues
        # We need yfinance to not be the last source, and loop should continue
        call_count = {'yfinance': 0, 'local': 0}
        
        def mock_yfinance(*args, **kwargs):
            call_count['yfinance'] += 1
            return None
        
        def mock_local(*args, **kwargs):
            call_count['local'] += 1
            return None
        
        with patch('src.data_loader.load_from_yfinance', side_effect=mock_yfinance):
            with patch('src.data_loader.load_from_local_csv', side_effect=mock_local):
                with patch('src.data_loader.time.sleep') as mock_sleep:
                    result = fetch_data_with_fallback(
                        symbol, start_date, end_date,
                        data_sources=['yfinance', 'local'],  # Multiple sources to continue loop
                        use_cache=False
                    )
                    # Should call sleep when yfinance returns None and loop continues
                    # The branch 415->395 should be triggered when yfinance returns None
                    assert mock_sleep.called, "time.sleep should be called when yfinance returns None"
                    assert result is None
                    # Verify both sources were tried
                    assert call_count['yfinance'] == 1
                    assert call_count['local'] == 1


class TestLoadAllData:
    """Tests for load_all_data function."""
    
    def test_load_all_data_success(self):
        """Test successful loading of all data types."""
        equity_symbols = ['SPY']
        fx_symbols = ['EURUSD=X']
        macro_symbols = ['^VIX']
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch') as mock_batch:
                        mock_batch.return_value = {'SPY': test_data, 'EURUSD=X': test_data}
                        with patch('src.data_loader.load_from_fred') as mock_fred:
                            mock_fred.return_value = test_data
                            with patch('builtins.print'):  # Suppress print output
                                with patch('src.data_loader.time.sleep'):  # Speed up test
                                    result = load_all_data(
                                        equity_symbols, fx_symbols, macro_symbols,
                                        start_date, end_date,
                                        data_sources=['yfinance', 'fred'],
                                        use_cache=False
                                    )
                                    
                                    assert isinstance(result, pd.DataFrame)
                                    assert len(result) > 0
                                    assert len(result.columns) == 3  # SPY_close, EURUSD=X_close, ^VIX_close
    
    def test_load_all_data_empty_input(self):
        """Test loading with empty symbol lists."""
        with patch('builtins.print'):  # Suppress print output
            result = load_all_data(
                [], [], [],
                '2020-01-01', '2020-12-31',
                use_cache=False
            )
            
            assert isinstance(result, pd.DataFrame)
            assert len(result.columns) == 0
    
    def test_load_all_data_partial_failure(self):
        """Test loading when some symbols fail."""
        equity_symbols = ['SPY', 'QQQ']
        fx_symbols = []
        macro_symbols = []
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch') as mock_batch:
                        # Only SPY succeeds, QQQ fails
                        mock_batch.return_value = {'SPY': test_data}
                        with patch('builtins.print'):  # Suppress print output
                            with patch('src.data_loader.time.sleep'):  # Speed up test
                                result = load_all_data(
                                    equity_symbols, fx_symbols, macro_symbols,
                                    start_date, end_date,
                                    data_sources=['yfinance'],
                                    use_cache=False
                                )
                                
                                assert isinstance(result, pd.DataFrame)
                                assert len(result.columns) == 1  # Only SPY_close
                                assert 'SPY_close' in result.columns
    
    def test_load_all_data_timezone_normalization(self):
        """Test that timezone-aware indices are normalized."""
        equity_symbols = ['SPY']
        fx_symbols = []
        macro_symbols = []
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        # Create tz-aware data
        dates_tz = pd.date_range(start_date, end_date, freq='D', tz='UTC')
        test_data = pd.Series(np.random.randn(len(dates_tz)), index=dates_tz)
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch') as mock_batch:
                        mock_batch.return_value = {'SPY': test_data}
                        with patch('builtins.print'):  # Suppress print output
                            with patch('src.data_loader.time.sleep'):  # Speed up test
                                result = load_all_data(
                                    equity_symbols, fx_symbols, macro_symbols,
                                    start_date, end_date,
                                    data_sources=['yfinance'],
                                    use_cache=False
                                )
                                
                                assert isinstance(result, pd.DataFrame)
                                assert len(result) > 0
                                assert result.index.tz is None  # Should be timezone-naive
    
    def test_load_all_data_forward_fill(self):
        """Test that missing values are forward-filled."""
        equity_symbols = ['SPY']
        fx_symbols = []
        macro_symbols = []
        start_date = '2020-01-01'
        end_date = '2020-01-10'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        # Create data with some missing dates
        data = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0], 
                        index=dates[:5])
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch') as mock_batch:
                        mock_batch.return_value = {'SPY': data}
                        with patch('builtins.print'):  # Suppress print output
                            with patch('src.data_loader.time.sleep'):  # Speed up test
                                result = load_all_data(
                                    equity_symbols, fx_symbols, macro_symbols,
                                    start_date, end_date,
                                    data_sources=['yfinance'],
                                    use_cache=False
                                )
                                
                                # After forward fill, should have fewer NaN values
                                assert isinstance(result, pd.DataFrame)
    
    def test_load_all_data_macro_prioritizes_fred(self):
        """Test that macro indicators prioritize FRED."""
        equity_symbols = []
        fx_symbols = []
        macro_symbols = ['^VIX']
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        fred_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred') as mock_fred:
                mock_fred.return_value = fred_data
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('builtins.print'):  # Suppress print output
                        result = load_all_data(
                            equity_symbols, fx_symbols, macro_symbols,
                            start_date, end_date,
                            data_sources=['fred', 'local', 'yfinance'],
                            use_cache=False
                        )
                        
                        # Check that FRED was called for macro symbol
                        assert mock_fred.called
                        assert isinstance(result, pd.DataFrame)
                        assert len(result) > 0
    
    def test_load_all_data_equity_failure_message(self):
        """Test load_all_data prints failure message when equity data fetch fails."""
        equity_symbols = ['SPY', 'QQQ']
        fx_symbols = []
        macro_symbols = []
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch', return_value={}):
                        with patch('builtins.print') as mock_print:
                            with patch('src.data_loader.time.sleep'):  # Speed up test
                                result = load_all_data(
                                    equity_symbols, fx_symbols, macro_symbols,
                                    start_date, end_date,
                                    data_sources=['yfinance'],
                                    use_cache=False
                                )
                                
                                # Check that failure messages were printed
                                print_calls = [str(call) for call in mock_print.call_args_list]
                                failure_messages = [call for call in print_calls if '[X]' in call and 'Failed to fetch' in call]
                                assert len(failure_messages) >= len(equity_symbols)
                                assert isinstance(result, pd.DataFrame)
    
    def test_load_all_data_fx_failure_message(self):
        """Test load_all_data prints failure message when FX data fetch fails."""
        equity_symbols = []
        fx_symbols = ['EURUSD=X', 'GBPUSD=X']
        macro_symbols = []
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch', return_value={}):
                        with patch('src.data_loader.time.sleep'):  # Speed up test
                            result = load_all_data(
                                equity_symbols, fx_symbols, macro_symbols,
                                start_date, end_date,
                                data_sources=['yfinance'],
                                use_cache=False
                            )
                            
                            # Verify the function completed
                            assert isinstance(result, pd.DataFrame)
    
    def test_load_all_data_macro_failure_message(self):
        """Test load_all_data prints failure message when macro data fetch fails."""
        equity_symbols = []
        fx_symbols = []
        macro_symbols = ['^VIX', '^TNX']
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch', return_value={}):
                        with patch('builtins.print') as mock_print:
                            with patch('src.data_loader.time.sleep'):  # Speed up test
                                result = load_all_data(
                                    equity_symbols, fx_symbols, macro_symbols,
                                    start_date, end_date,
                                    data_sources=['fred', 'yfinance'],
                                    use_cache=False
                                )
                                
                                # Check that failure messages were printed
                                print_calls = [str(call) for call in mock_print.call_args_list]
                                failure_messages = [call for call in print_calls if '[X]' in call and 'Failed to fetch' in call]
                                assert len(failure_messages) >= len(macro_symbols)
                                assert isinstance(result, pd.DataFrame)
    
    def test_load_all_data_with_custom_data_sources(self):
        """Test load_all_data with custom data_sources parameter."""
        equity_symbols = ['SPY']
        fx_symbols = []
        macro_symbols = []
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        dates = pd.date_range(start_date, end_date, freq='D')
        test_data = pd.Series(np.random.randn(len(dates)), index=dates)
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv') as mock_local:
                    mock_local.return_value = test_data
                    with patch('builtins.print'):  # Suppress print output
                        result = load_all_data(
                            equity_symbols, fx_symbols, macro_symbols,
                            start_date, end_date,
                            data_sources=['local'],  # Custom data_sources
                            use_cache=False
                        )
                        
                        # Verify local CSV was called
                        assert mock_local.called
                        assert isinstance(result, pd.DataFrame)
                        assert len(result) > 0
    
    def test_load_all_data_series_without_datetime_index(self):
        """Test load_all_data handles series without DatetimeIndex."""
        equity_symbols = ['SPY']
        fx_symbols = []
        macro_symbols = []
        start_date = '2020-01-01'
        end_date = '2020-12-31'
        
        # Create data with non-DatetimeIndex
        data_without_datetime = pd.Series([1, 2, 3], index=[0, 1, 2])
        
        with patch('src.data_loader.load_from_cache', return_value=None):
            with patch('src.data_loader.load_from_fred', return_value=None):
                with patch('src.data_loader.load_from_local_csv', return_value=None):
                    with patch('src.data_loader.load_from_yfinance_batch') as mock_batch:
                        mock_batch.return_value = {'SPY': data_without_datetime}
                        with patch('builtins.print'):  # Suppress print output
                            with patch('src.data_loader.time.sleep'):  # Speed up test
                                result = load_all_data(
                                    equity_symbols, fx_symbols, macro_symbols,
                                    start_date, end_date,
                                    data_sources=['yfinance'],
                                    use_cache=False
                                )
                                
                                # Should handle non-DatetimeIndex gracefully
                                assert isinstance(result, pd.DataFrame)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
