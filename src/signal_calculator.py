"""
Signal calculation module for momentum and carry signals.
"""

import pandas as pd
import numpy as np
from typing import List, Optional


def calculate_equity_momentum(
    data: pd.DataFrame,
    equity_symbols: List[str],
    lookback_days: int = 252,
    lag_days: int = 21
) -> pd.Series:
    """
    Calculate equity momentum signal as equal-weight portfolio of equity indices.
    
    Parameters
    ----------
    data : pd.DataFrame
        DataFrame with price data, columns should include '{symbol}_close' for each equity symbol
    equity_symbols : List[str]
        List of equity ticker symbols (e.g., ['SPY', 'QQQ', 'IWM'])
    lookback_days : int
        Number of trading days for momentum calculation (default: 252 = 12 months)
    lag_days : int
        Number of days to lag the signal (default: 21 = 1 month)
    
    Returns
    -------
    pd.Series
        Equity momentum signal (12-month return with lag)
    """
    momentum_signals = []
    
    for symbol in equity_symbols:
        col_name = f"{symbol}_close"
        if col_name in data.columns:
            prices = data[col_name]
            # Calculate 12-month return
            momentum = prices.pct_change(lookback_days)
            # Apply lag
            momentum = momentum.shift(lag_days)
            momentum_signals.append(momentum)
        else:
            print(f"Warning: {col_name} not found in data")
    
    if not momentum_signals:
        return pd.Series(index=data.index, dtype=float)
    
    # Equal-weight portfolio
    momentum_df = pd.DataFrame(momentum_signals).T
    equity_momentum = momentum_df.mean(axis=1)
    
    return equity_momentum


def calculate_fx_carry(
    data: pd.DataFrame,
    fx_symbols: List[str],
    lookback_days: int = 252
) -> pd.Series:
    """
    Calculate FX carry signal as equal-weight portfolio of FX pairs.
    
    For MVP, uses 12-month momentum as carry proxy.
    Long EUR/GBP/AUD vs USD, short JPY vs USD if negative.
    
    Parameters
    ----------
    data : pd.DataFrame
        DataFrame with price data, columns should include '{symbol}_close' for each FX symbol
    fx_symbols : List[str]
        List of FX ticker symbols (e.g., ['EURUSD=X', 'GBPUSD=X'])
    lookback_days : int
        Number of trading days for momentum calculation (default: 252 = 12 months)
    
    Returns
    -------
    pd.Series
        FX carry signal (12-month return as carry proxy)
    """
    carry_signals = []
    
    for symbol in fx_symbols:
        col_name = f"{symbol}_close"
        if col_name in data.columns:
            prices = data[col_name]
            # Calculate 12-month return (momentum as carry proxy)
            carry = prices.pct_change(lookback_days)
            
            # For JPY (inverse relationship), flip the sign
            if 'JPY' in symbol:
                carry = -carry
            
            carry_signals.append(carry)
        else:
            print(f"Warning: {col_name} not found in data")
    
    if not carry_signals:
        return pd.Series(index=data.index, dtype=float)
    
    # Equal-weight portfolio
    carry_df = pd.DataFrame(carry_signals).T
    fx_carry = carry_df.mean(axis=1)
    
    return fx_carry


def calculate_all_signals(
    data: pd.DataFrame,
    equity_symbols: List[str],
    fx_symbols: List[str],
    momentum_lookback: int = 252,
    momentum_lag: int = 21,
    carry_lookback: int = 252
) -> pd.DataFrame:
    """
    Calculate all trading signals (equity momentum and FX carry).
    
    Parameters
    ----------
    data : pd.DataFrame
        Combined DataFrame with all price data
    equity_symbols : List[str]
        List of equity ticker symbols
    fx_symbols : List[str]
        List of FX ticker symbols
    momentum_lookback : int
        Lookback period for momentum (default: 252 days)
    momentum_lag : int
        Lag period for momentum (default: 21 days)
    carry_lookback : int
        Lookback period for carry (default: 252 days)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns: 'equity_momentum', 'fx_carry', and index as date
    """
    equity_momentum = calculate_equity_momentum(
        data, equity_symbols, momentum_lookback, momentum_lag
    )
    
    fx_carry = calculate_fx_carry(
        data, fx_symbols, carry_lookback
    )
    
    signals_df = pd.DataFrame({
        'equity_momentum': equity_momentum,
        'fx_carry': fx_carry
    }, index=data.index)
    
    return signals_df
