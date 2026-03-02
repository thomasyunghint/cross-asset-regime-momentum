"""
Data loading module for cross-asset momentum regime classifier.

Supports multiple data sources:
1. FRED (Federal Reserve Economic Data) - Free, stable, best for macro indicators
2. Local CSV files - Most reliable, requires pre-downloaded data
3. Yahoo Finance (yfinance) - Free but rate-limited, fallback option
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Literal
import warnings
import time
import os
from pathlib import Path
import hashlib
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# Try importing optional dependencies
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[INFO] yfinance not available. Install with: pip install yfinance")

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    print("[INFO] fredapi not available. Install with: pip install fredapi")
    print("[INFO] FRED API key is free: https://fred.stlouisfed.org/docs/api/api_key.html")

# Rate limiting configuration for yfinance
DELAY_BETWEEN_REQUESTS = 3.0  # Seconds to wait between requests
DELAY_AFTER_RATE_LIMIT = 15.0  # Seconds to wait after rate limit error
MAX_RETRIES = 5  # Maximum number of retries for rate-limited requests

# FRED series mapping for macro indicators
FRED_SERIES_MAP = {
    '^VIX': 'VIXCLS',  # VIX volatility index
    '^TNX': 'DGS10',   # 10-year Treasury yield
    '^IRX': 'DGS3MO',  # 3-month Treasury yield
    'DX-Y.NYB': 'DTWEXBGS',  # US Dollar Index (Broad Trade Weighted)
}

# Data source priority: 'cache' > 'fred' > 'local' > 'yfinance'
DATA_SOURCE_PRIORITY = ['cache', 'fred', 'local', 'yfinance']

# Cache configuration
CACHE_DIR = Path('data_cache')
CACHE_EXPIRY_DAYS = 7  # Cache expires after 7 days (update weekly)


def load_from_fred(symbol: str, start_date: str, end_date: str, fred_api_key: Optional[str] = None) -> Optional[pd.Series]:
    """
    Load data from FRED (Federal Reserve Economic Data).
    
    Best for: Macro indicators (VIX, Treasury yields, Dollar Index)
    
    Parameters
    ----------
    symbol : str
        Symbol to look up in FRED_SERIES_MAP
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    fred_api_key : Optional[str]
        FRED API key (free from https://fred.stlouisfed.org/docs/api/api_key.html)
        If None, will try FRED_API_KEY environment variable
        
    Returns
    -------
    Optional[pd.Series]
        Data series if successful, None otherwise
    """
    if not FRED_AVAILABLE:
        return None
    
    if symbol not in FRED_SERIES_MAP:
        return None
    
    try:
        # Get API key from parameter or environment
        api_key = fred_api_key or os.getenv('FRED_API_KEY')
        if not api_key:
            return None
        
        fred = Fred(api_key=api_key)
        fred_series = FRED_SERIES_MAP[symbol]
        
        data = fred.get_series(fred_series, start=start_date, end=end_date)
        
        if data.empty:
            return None
        
        # Convert to daily frequency (FRED data might be weekly/monthly)
        data = data.resample('D').ffill()
        
        # Ensure timezone-naive index
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)
        
        return data
        
    except Exception as e:
        return None


def _get_cache_path(symbol: str, start_date: str, end_date: str) -> Path:
    """
    Generate cache file path based on symbol and date range.
    
    Parameters
    ----------
    symbol : str
        Symbol name
    start_date : str
        Start date
    end_date : str
        End date
        
    Returns
    -------
    Path
        Cache file path
    """
    # Create cache directory if it doesn't exist
    CACHE_DIR.mkdir(exist_ok=True)
    
    # Generate unique filename based on symbol and date range
    cache_key = f"{symbol}_{start_date}_{end_date}"
    cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]
    safe_symbol = symbol.replace('=', '_').replace('^', '').replace('.', '_')
    filename = f"{safe_symbol}_{cache_hash}.parquet"
    
    return CACHE_DIR / filename


def load_from_cache(symbol: str, start_date: str, end_date: str) -> Optional[pd.Series]:
    """
    Load data from local cache (Parquet format).
    
    Parameters
    ----------
    symbol : str
        Symbol name
    start_date : str
        Start date
    end_date : str
        End date
        
    Returns
    -------
    Optional[pd.Series]
        Cached data if available and fresh, None otherwise
    """
    cache_path = _get_cache_path(symbol, start_date, end_date)
    
    if not cache_path.exists():
        return None
    
    try:
        # Check if cache is expired
        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        if cache_age.days > CACHE_EXPIRY_DAYS:
            return None
        
        # Load cached data
        df = pd.read_parquet(cache_path)
        
        # Ensure it's a Series with datetime index
        if isinstance(df, pd.DataFrame):
            if 'value' in df.columns:
                series = df['value']
            elif len(df.columns) == 1:
                series = df.iloc[:, 0]
            else:
                return None
        else:
            series = df
        
        # Filter by date range
        if isinstance(series.index, pd.DatetimeIndex):
            series = series[(series.index >= start_date) & (series.index <= end_date)]
            if not series.empty:
                return series
        
        return None
        
    except Exception as e:
        return None


def save_to_cache(symbol: str, start_date: str, end_date: str, data: pd.Series) -> bool:
    """
    Save data to local cache (Parquet format).
    
    Parameters
    ----------
    symbol : str
        Symbol name
    start_date : str
        Start date
    end_date : str
        End date
    data : pd.Series
        Data to cache
        
    Returns
    -------
    bool
        True if successful, False otherwise
    """
    try:
        cache_path = _get_cache_path(symbol, start_date, end_date)
        
        # Convert Series to DataFrame for Parquet
        df = pd.DataFrame({'value': data})
        df.to_parquet(cache_path, compression='snappy')
        
        return True
        
    except Exception as e:
        return False


def load_from_local_csv(symbol: str, data_dir: str = 'data') -> Optional[pd.Series]:
    """
    Load data from local CSV file.
    
    Expected format: CSV file with 'Date' column and 'Close' column
    File naming: {symbol}.csv (e.g., SPY.csv, EURUSD=X.csv)
    
    Parameters
    ----------
    symbol : str
        Symbol name (used to find CSV file)
    data_dir : str
        Directory containing CSV files
        
    Returns
    -------
    Optional[pd.Series]
        Close price series if file exists, None otherwise
    """
    data_path = Path(data_dir)
    
    # Try different file name formats
    possible_names = [
        f"{symbol}.csv",
        f"{symbol.replace('=', '_').replace('^', '')}.csv",
        f"{symbol.replace('=', '_').replace('^', '').replace('.NYB', '')}.csv",
    ]
    
    for filename in possible_names:
        file_path = data_path / filename
        if file_path.exists():
            try:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                
                # Handle different column names
                if 'Close' in df.columns:
                    series = df['Close']
                elif 'close' in df.columns:
                    series = df['close']
                elif 'CLOSE' in df.columns:
                    series = df['CLOSE']
                elif len(df.columns) == 1:
                    series = df.iloc[:, 0]
                else:
                    continue
                
                return series
                
            except Exception as e:
                continue
    
    return None


def load_from_yfinance_batch(symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.Series]:
    """
    Load data from Yahoo Finance using yfinance with batch download.
    
    This function uses yf.download() to fetch multiple symbols in a single API call,
    which is much more efficient and reduces rate limiting issues.
    
    Parameters
    ----------
    symbols : List[str]
        List of ticker symbols to download
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
        
    Returns
    -------
    Dict[str, pd.Series]
        Dictionary mapping symbol to Close price series.
        Only includes symbols that were successfully downloaded.
    """
    if not YFINANCE_AVAILABLE:
        return {}
    
    if not symbols:
        return {}
    
    for attempt in range(MAX_RETRIES):
        try:
            # Use yf.download() for batch download - much more efficient
            data = yf.download(symbols, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                return {}
            
            # Handle different data structures from yf.download()
            result = {}
            
            # If single symbol, data.columns might be just ['Open', 'High', 'Low', 'Close', 'Volume']
            # If multiple symbols, data.columns is MultiIndex with (symbol, metric) tuples
            if isinstance(data.columns, pd.MultiIndex):
                # Multiple symbols case
                for symbol in symbols:
                    if (symbol, 'Close') in data.columns:
                        series = data[(symbol, 'Close')].copy()
                        # Remove timezone info to match FRED data (tz-naive)
                        if series.index.tz is not None:
                            series.index = series.index.tz_localize(None)
                        if not series.empty:
                            result[symbol] = series
            else:
                # Single symbol case - columns are just ['Open', 'High', 'Low', 'Close', 'Volume']
                if len(symbols) == 1:
                    symbol = symbols[0]
                    if 'Close' in data.columns:
                        series = data['Close'].copy()
                        # Remove timezone info to match FRED data (tz-naive)
                        if series.index.tz is not None:
                            series.index = series.index.tz_localize(None)
                        if not series.empty:
                            result[symbol] = series
            
            return result
                
        except Exception as e:
            error_msg = str(e).lower()
            error_type = type(e).__name__
            
            # Check if it's a rate limit error (various formats)
            is_rate_limit = (
                'rate limit' in error_msg or 
                'too many requests' in error_msg or
                '429' in error_msg or
                error_type == 'HTTPError' and '429' in str(e)
            )
            
            if is_rate_limit:
                if attempt < MAX_RETRIES - 1:
                    wait_time = DELAY_AFTER_RATE_LIMIT * (attempt + 1)
                    print(f"    [WARNING] Rate limited. Waiting {wait_time:.1f}s before retry {attempt + 2}/{MAX_RETRIES}...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"    [X] Rate limit error after {MAX_RETRIES} attempts")
                    return {}
            else:
                # Other errors - don't retry
                return {}
    
    return {}


def load_from_yfinance(symbol: str, start_date: str, end_date: str) -> Optional[pd.Series]:
    """
    Load data from Yahoo Finance using yfinance.
    
    This function uses the batch download function internally for efficiency.
    
    Parameters
    ----------
    symbol : str
        Ticker symbol
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
        
    Returns
    -------
    Optional[pd.Series]
        Close price series if successful, None otherwise
    """
    if not YFINANCE_AVAILABLE:
        return None
    
    # Use batch download for single symbol (still more efficient)
    result = load_from_yfinance_batch([symbol], start_date, end_date)
    return result.get(symbol)


def fetch_data_with_fallback(
    symbol: str,
    start_date: str,
    end_date: str,
    data_sources: List[Literal['cache', 'fred', 'local', 'yfinance']] = None,
    fred_api_key: Optional[str] = None,
    data_dir: str = 'data',
    use_cache: bool = True
) -> Optional[pd.Series]:
    """
    Fetch data using multiple sources with fallback.
    
    Parameters
    ----------
    symbol : str
        Symbol to fetch
    start_date : str
        Start date
    end_date : str
        End date
    data_sources : List[str]
        List of data sources to try in order (default: ['cache', 'fred', 'local', 'yfinance'])
    fred_api_key : Optional[str]
        FRED API key (or use FRED_API_KEY env var)
    data_dir : str
        Directory for local CSV files
    use_cache : bool
        Whether to use cache (default: True)
        
    Returns
    -------
    Optional[pd.Series]
        Data series if successful, None otherwise
    """
    if data_sources is None:
        data_sources = DATA_SOURCE_PRIORITY.copy()
    
    # Try cache first if enabled
    if use_cache and 'cache' in data_sources:
        cached_data = load_from_cache(symbol, start_date, end_date)
        if cached_data is not None:
            return cached_data
    
    # Try other sources
    fetched_data = None
    for source in data_sources:
        if source == 'cache':
            continue  # Already tried above
            
        elif source == 'fred':
            data = load_from_fred(symbol, start_date, end_date, fred_api_key)
            if data is not None:
                fetched_data = data
                break
        
        elif source == 'local':
            data = load_from_local_csv(symbol, data_dir)
            if data is not None:
                # Filter by date range
                if isinstance(data.index, pd.DatetimeIndex):
                    data = data[(data.index >= start_date) & (data.index <= end_date)]
                    if not data.empty:
                        fetched_data = data
                        break
        
        elif source == 'yfinance':
            data = load_from_yfinance(symbol, start_date, end_date)
            if data is not None:
                fetched_data = data
                break
            # Add delay between yfinance requests
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Save to cache if we fetched new data
    if fetched_data is not None and use_cache:
        save_to_cache(symbol, start_date, end_date, fetched_data)
    
    return fetched_data


def load_all_data(
    equity_symbols: List[str],
    fx_symbols: List[str],
    macro_symbols: List[str],
    start_date: str = '2020-01-01',
    end_date: str = '2024-12-31',
    data_sources: List[Literal['cache', 'fred', 'local', 'yfinance']] = None,
    fred_api_key: Optional[str] = None,
    data_dir: str = 'data',
    use_cache: bool = True
) -> pd.DataFrame:
    """
    Load and combine all market data from multiple sources.
    
    Parameters
    ----------
    equity_symbols : List[str]
        List of equity ticker symbols (e.g., ['SPY', 'QQQ', 'IWM'])
    fx_symbols : List[str]
        List of FX pair ticker symbols (e.g., ['EURUSD=X', 'GBPUSD=X'])
    macro_symbols : List[str]
        List of macro indicator ticker symbols (e.g., ['^VIX', '^TNX'])
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    data_sources : List[str]
        List of data sources to try in order (default: ['cache', 'fred', 'local', 'yfinance'])
        For macro indicators, 'fred' is recommended
        For equity/FX, 'local' or 'yfinance' work best
        'cache' will be tried first if use_cache=True
    fred_api_key : Optional[str]
        FRED API key (free from https://fred.stlouisfed.org/docs/api/api_key.html)
        Can also set FRED_API_KEY environment variable
    data_dir : str
        Directory containing local CSV files (default: 'data')
    use_cache : bool
        Whether to use local cache (default: True)
        Cache files are stored in 'data_cache' directory
        
    Returns
    -------
    pd.DataFrame
        Combined DataFrame with columns for all prices/indicators.
        Index is datetime, columns are named by symbol.
        Missing values are forward-filled to handle market holidays.
    """
    all_data = {}
    
    # Determine data sources for each asset type
    if data_sources is None:
        data_sources = DATA_SOURCE_PRIORITY.copy()
    
    # For macro indicators, prioritize FRED
    macro_sources = ['fred'] + [s for s in data_sources if s != 'fred']
    
    # Fetch equity data
    print("Fetching equity data...")
    # Try batch download for symbols that need yfinance
    equity_needing_yfinance = []
    for symbol in equity_symbols:
        # Try cache first if enabled (regardless of data_sources list)
        if use_cache:
            cached_data = load_from_cache(symbol, start_date, end_date)
            if cached_data is not None:
                all_data[f"{symbol}_close"] = cached_data
                print(f"  [OK] {symbol}: {len(cached_data)} days (cached)")
                continue
        
        # Try other sources before yfinance
        data = None
        for source in data_sources:
            if source == 'cache':
                continue
            elif source == 'fred':
                data = load_from_fred(symbol, start_date, end_date, fred_api_key)
                if data is not None:
                    break
            elif source == 'local':
                data = load_from_local_csv(symbol, data_dir)
                if data is not None:
                    if isinstance(data.index, pd.DatetimeIndex):
                        data = data[(data.index >= start_date) & (data.index <= end_date)]
                        if not data.empty:
                            break
                    else:
                        data = None
        
        if data is not None:
            all_data[f"{symbol}_close"] = data
            if use_cache:
                save_to_cache(symbol, start_date, end_date, data)
            print(f"  [OK] {symbol}: {len(data)} days")
        elif 'yfinance' in data_sources:
            # Collect symbols that need yfinance for batch download
            equity_needing_yfinance.append(symbol)
    
    # Batch download equity symbols that need yfinance
    if equity_needing_yfinance:
        print(f"  Batch downloading {len(equity_needing_yfinance)} equity symbols from yfinance...")
        batch_data = load_from_yfinance_batch(equity_needing_yfinance, start_date, end_date)
        for symbol in equity_needing_yfinance:
            if symbol in batch_data:
                data = batch_data[symbol]
                all_data[f"{symbol}_close"] = data
                if use_cache:
                    save_to_cache(symbol, start_date, end_date, data)
                print(f"  [OK] {symbol}: {len(data)} days")
            else:
                print(f"  [X] {symbol}: Failed to fetch data from yfinance")
        # Add delay after batch download
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Fetch FX data
    print("\nFetching FX data...")
    fx_needing_yfinance = []
    for symbol in fx_symbols:
        # Try cache first if enabled (regardless of data_sources list)
        if use_cache:
            cached_data = load_from_cache(symbol, start_date, end_date)
            if cached_data is not None:
                all_data[f"{symbol}_close"] = cached_data
                print(f"  [OK] {symbol}: {len(cached_data)} days (cached)")
                continue
        
        # Try other sources before yfinance
        data = None
        for source in data_sources:
            if source == 'cache':
                continue
            elif source == 'fred':
                data = load_from_fred(symbol, start_date, end_date, fred_api_key)
                if data is not None:
                    break
            elif source == 'local':
                data = load_from_local_csv(symbol, data_dir)
                if data is not None:
                    if isinstance(data.index, pd.DatetimeIndex):
                        data = data[(data.index >= start_date) & (data.index <= end_date)]
                        if not data.empty:
                            break
                    else:
                        data = None
        
        if data is not None:
            all_data[f"{symbol}_close"] = data
            if use_cache:
                save_to_cache(symbol, start_date, end_date, data)
            print(f"  [OK] {symbol}: {len(data)} days")
        elif 'yfinance' in data_sources:
            # Collect symbols that need yfinance for batch download
            fx_needing_yfinance.append(symbol)
    
    # Batch download FX symbols that need yfinance
    if fx_needing_yfinance:
        print(f"  Batch downloading {len(fx_needing_yfinance)} FX symbols from yfinance...")
        batch_data = load_from_yfinance_batch(fx_needing_yfinance, start_date, end_date)
        for symbol in fx_needing_yfinance:
            if symbol in batch_data:
                data = batch_data[symbol]
                all_data[f"{symbol}_close"] = data
                if use_cache:
                    save_to_cache(symbol, start_date, end_date, data)
                print(f"  [OK] {symbol}: {len(data)} days")
            else:
                print(f"  [X] {symbol}: Failed to fetch data from yfinance")
        # Add delay after batch download
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Fetch macro data (prefer FRED)
    print("\nFetching macro indicators...")
    macro_needing_yfinance = []
    for symbol in macro_symbols:
        # Try cache first if enabled (regardless of data_sources list)
        if use_cache:
            cached_data = load_from_cache(symbol, start_date, end_date)
            if cached_data is not None:
                all_data[f"{symbol}_close"] = cached_data
                print(f"  [OK] {symbol}: {len(cached_data)} days (cached)")
                continue
        
        # Try other sources before yfinance
        data = None
        for source in macro_sources:
            if source == 'cache':
                continue
            elif source == 'fred':
                data = load_from_fred(symbol, start_date, end_date, fred_api_key)
                if data is not None:
                    break
            elif source == 'local':
                data = load_from_local_csv(symbol, data_dir)
                if data is not None:
                    if isinstance(data.index, pd.DatetimeIndex):
                        data = data[(data.index >= start_date) & (data.index <= end_date)]
                        if not data.empty:
                            break
                    else:
                        data = None
        
        if data is not None:
            all_data[f"{symbol}_close"] = data
            if use_cache:
                save_to_cache(symbol, start_date, end_date, data)
            print(f"  [OK] {symbol}: {len(data)} days")
        elif 'yfinance' in macro_sources:
            # Collect symbols that need yfinance for batch download
            macro_needing_yfinance.append(symbol)
    
    # Batch download macro symbols that need yfinance
    if macro_needing_yfinance:
        print(f"  Batch downloading {len(macro_needing_yfinance)} macro symbols from yfinance...")
        batch_data = load_from_yfinance_batch(macro_needing_yfinance, start_date, end_date)
        for symbol in macro_needing_yfinance:
            if symbol in batch_data:
                data = batch_data[symbol]
                all_data[f"{symbol}_close"] = data
                if use_cache:
                    save_to_cache(symbol, start_date, end_date, data)
                print(f"  [OK] {symbol}: {len(data)} days")
            else:
                print(f"  [X] {symbol}: Failed to fetch data from yfinance")
        # Add delay after batch download
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Combine all data
    print("\nCombining data...")
    
    # Normalize timezone for all series before combining
    # Convert all tz-aware indices to tz-naive to avoid merge errors
    for key, series in all_data.items():
        if isinstance(series.index, pd.DatetimeIndex):
            if series.index.tz is not None:
                all_data[key] = series.copy()
                all_data[key].index = all_data[key].index.tz_localize(None)
    
    combined = pd.DataFrame(all_data)
    
    if combined.empty:
        print("  [ERROR] No data loaded!")
        return combined
    
    # Sort by date
    combined = combined.sort_index()
    
    # Forward fill missing values (handle market holidays)
    combined = combined.ffill()
    
    # Drop rows with insufficient data (less than 252 days for momentum calculation)
    min_required_days = 252
    if len(combined) < min_required_days:
        print(f"Warning: Only {len(combined)} days of data available, need at least {min_required_days}")
    else:
        # Drop initial rows with NaN (before forward fill can work)
        combined = combined.dropna()
        print(f"  [OK] Combined dataset: {len(combined)} days, {len(combined.columns)} columns")
    
    return combined
