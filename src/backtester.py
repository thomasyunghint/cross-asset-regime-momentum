"""
Backtest engine for comparing static vs dynamic regime-based strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from src.data_loader import fetch_data_with_fallback


def load_spx_benchmark(
    start_date: str,
    end_date: str,
    data_sources: list = None,
    fred_api_key: Optional[str] = None,
    data_dir: str = 'data'
) -> Optional[pd.Series]:
    """
    Load SPX (S&P 500 Index) benchmark data.
    
    Parameters
    ----------
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    data_sources : list
        List of data sources to try
    fred_api_key : Optional[str]
        FRED API key
    data_dir : str
        Directory for local CSV files
        
    Returns
    -------
    Optional[pd.Series]
        SPX price series if successful, None otherwise
    """
    # Try different SPX symbols
    spx_symbols = ['^GSPC', 'SPX', 'SP500']
    
    if data_sources is None:
        data_sources = ['cache', 'local', 'yfinance']
    
    for symbol in spx_symbols:
        spx_data = fetch_data_with_fallback(
            symbol,
            start_date,
            end_date,
            data_sources=data_sources,
            fred_api_key=fred_api_key,
            data_dir=data_dir
        )
        if spx_data is not None and len(spx_data) > 0:
            return spx_data
    
    return None


def calculate_returns(
    signals_df: pd.DataFrame,
    data: pd.DataFrame,
    equity_symbols: list,
    fx_symbols: list,
    regime_labels: Optional[pd.Series] = None,
    initial_capital: float = 100000,
    transaction_cost_bps: float = 5,
    slippage_bps: float = 2,
    spx_benchmark: Optional[pd.Series] = None
) -> pd.DataFrame:
    """
    Calculate strategy returns for all four strategies.
    
    Strategies:
    1. Static Equity Momentum: 100% equity momentum
    2. Static FX Carry: 100% FX carry
    3. Static 50/50: Equal-weight momentum + carry
    4. Dynamic Regime-Based:
       - Regime 0 (risk-on): 80% equity, 20% FX
       - Regime 1 (risk-off): 20% equity, 80% FX
    
    Parameters
    ----------
    signals_df : pd.DataFrame
        DataFrame with 'equity_momentum' and 'fx_carry' columns
    data : pd.DataFrame
        DataFrame with actual price data (columns: '{symbol}_close' for each symbol)
    equity_symbols : list
        List of equity symbols to calculate returns from
    fx_symbols : list
        List of FX symbols to calculate returns from
    regime_labels : Optional[pd.Series]
        Series with regime labels (0 or 1). If None, dynamic strategy not calculated.
    initial_capital : float
        Initial capital (default: 100000)
    transaction_cost_bps : float
        Transaction cost in basis points per trade (default: 5 bps = 0.05%)
    slippage_bps : float
        Slippage in basis points (default: 2 bps = 0.02%)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns for each strategy's returns, positions, and equity curve
    """
    # Align data
    equity_momentum = signals_df['equity_momentum']
    fx_carry = signals_df['fx_carry']
    
    # Calculate actual daily returns from price data
    # Equity portfolio: equal-weight of all equity assets
    equity_returns_list = []
    for symbol in equity_symbols:
        col_name = f"{symbol}_close"
        if col_name in data.columns:
            prices = data[col_name]
            daily_returns = prices.pct_change()
            equity_returns_list.append(daily_returns)
    
    if equity_returns_list:
        equity_returns_df = pd.DataFrame(equity_returns_list).T
        equity_returns = equity_returns_df.mean(axis=1)  # Equal-weight portfolio
    else:
        equity_returns = pd.Series(index=data.index, dtype=float)
    
    # FX portfolio: equal-weight of all FX assets
    fx_returns_list = []
    for symbol in fx_symbols:
        col_name = f"{symbol}_close"
        if col_name in data.columns:
            prices = data[col_name]
            daily_returns = prices.pct_change()
            # For JPY (inverse relationship), flip the sign
            if 'JPY' in symbol:
                daily_returns = -daily_returns
            fx_returns_list.append(daily_returns)
    
    if fx_returns_list:
        fx_returns_df = pd.DataFrame(fx_returns_list).T
        fx_returns = fx_returns_df.mean(axis=1)  # Equal-weight portfolio
    else:
        fx_returns = pd.Series(index=data.index, dtype=float)
    
    # Align returns with signals index
    equity_returns = equity_returns.loc[signals_df.index]
    fx_returns = fx_returns.loc[signals_df.index]
    
    # Use momentum/carry signals to determine position direction
    # Signal > 0: long (position = +1), Signal < 0: short (position = -1)
    # Signal = 0 or NaN: no position (position = 0)
    equity_positions = np.sign(equity_momentum.fillna(0))
    fx_positions = np.sign(fx_carry.fillna(0))
    
    # Align regime labels
    if regime_labels is not None:
        regime_labels = regime_labels.loc[signals_df.index]
    
    # Total cost per trade (transaction + slippage)
    total_cost_pct = (transaction_cost_bps + slippage_bps) / 10000
    
    results = {}
    
    # Strategy 1: Static Equity Momentum (100% equity)
    # Returns = actual asset returns * position direction from momentum signal
    equity_strategy_returns = equity_returns * equity_positions
    # Apply costs only when position changes (simplified: assume daily rebalancing)
    # Only apply costs when position actually changes (not when it stays the same)
    position_changes = equity_positions.diff().abs() > 0
    equity_strategy_returns = equity_strategy_returns - (position_changes * total_cost_pct)
    results['static_equity'] = equity_strategy_returns
    
    # Strategy 2: Static FX Carry (100% FX)
    # Returns = actual asset returns * position direction from carry signal
    fx_strategy_returns = fx_returns * fx_positions
    position_changes = fx_positions.diff().abs() > 0
    fx_strategy_returns = fx_strategy_returns - (position_changes * total_cost_pct)
    results['static_fx'] = fx_strategy_returns
    
    # Strategy 3: Static 50/50
    static_5050_returns = 0.5 * equity_strategy_returns + 0.5 * fx_strategy_returns
    results['static_5050'] = static_5050_returns
    
    # Strategy 4: Dynamic Regime-Based
    if regime_labels is not None:
        dynamic_returns = []
        for i, regime in enumerate(regime_labels):
            if regime == 0:  # Risk-on: 80% equity, 20% FX
                ret = 0.8 * equity_strategy_returns.iloc[i] + 0.2 * fx_strategy_returns.iloc[i]
            else:  # Risk-off: 20% equity, 80% FX
                ret = 0.2 * equity_strategy_returns.iloc[i] + 0.8 * fx_strategy_returns.iloc[i]
            dynamic_returns.append(ret)
        results['dynamic_regime'] = pd.Series(dynamic_returns, index=equity_returns.index)
    else:
        results['dynamic_regime'] = pd.Series(index=equity_returns.index, dtype=float)
    
    # Add SPX benchmark if provided
    if spx_benchmark is not None:
        # Align SPX with signals index
        spx_aligned = spx_benchmark.loc[signals_df.index]
        spx_returns = spx_aligned.pct_change()
        results['spx_benchmark'] = spx_returns
    
    # Create results DataFrame
    results_df = pd.DataFrame(results, index=equity_returns.index)
    
    # Calculate equity curves
    for col in results_df.columns:
        equity_curve = (1 + results_df[col]).cumprod() * initial_capital
        results_df[f'{col}_equity'] = equity_curve
    
    return results_df


def calculate_performance_metrics(returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate performance metrics for each strategy.
    
    Metrics:
    - Sharpe ratio (annualized, risk-free rate = 0)
    - Max drawdown
    - Total return
    - Win rate (positive months)
    - Volatility (annualized)
    
    Parameters
    ----------
    returns_df : pd.DataFrame
        DataFrame with strategy returns (columns: static_equity, static_fx, static_5050, dynamic_regime)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with performance metrics for each strategy
    """
    metrics = {}
    trading_days_per_year = 252
    
    # Include SPX benchmark if available
    strategy_cols = ['static_equity', 'static_fx', 'static_5050', 'dynamic_regime', 'spx_benchmark']
    
    for col in strategy_cols:
        if col not in returns_df.columns:
            continue
        
        returns = returns_df[col].dropna()
        
        if len(returns) == 0:
            continue
        
        # Total return
        total_return = (1 + returns).prod() - 1
        
        # Annualized return
        n_years = len(returns) / trading_days_per_year
        annualized_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(trading_days_per_year)
        
        # Sharpe ratio (risk-free rate = 0)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        equity_curve = (1 + returns).cumprod()
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Win rate (positive days)
        win_rate = (returns > 0).sum() / len(returns)
        
        # Monthly returns for monthly win rate
        monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        monthly_win_rate = (monthly_returns > 0).sum() / len(monthly_returns) if len(monthly_returns) > 0 else 0
        
        metrics[col] = {
            'Total Return': f"{total_return:.2%}",
            'Annualized Return': f"{annualized_return:.2%}",
            'Volatility': f"{volatility:.2%}",
            'Sharpe Ratio': f"{sharpe_ratio:.2f}",
            'Max Drawdown': f"{max_drawdown:.2%}",
            'Win Rate (Daily)': f"{win_rate:.2%}",
            'Win Rate (Monthly)': f"{monthly_win_rate:.2%}"
        }
    
    metrics_df = pd.DataFrame(metrics).T
    return metrics_df


def run_backtest(
    signals_df: pd.DataFrame,
    data: pd.DataFrame,
    equity_symbols: list,
    fx_symbols: list,
    regime_labels: Optional[pd.Series] = None,
    initial_capital: float = 100000,
    transaction_cost_bps: float = 5,
    slippage_bps: float = 2,
    spx_benchmark: Optional[pd.Series] = None
) -> Dict:
    """
    Run complete backtest and return results.
    
    Parameters
    ----------
    signals_df : pd.DataFrame
        DataFrame with 'equity_momentum' and 'fx_carry' columns
    data : pd.DataFrame
        DataFrame with actual price data (columns: '{symbol}_close' for each symbol)
    equity_symbols : list
        List of equity symbols to calculate returns from
    fx_symbols : list
        List of FX symbols to calculate returns from
    regime_labels : Optional[pd.Series]
        Series with regime labels
    initial_capital : float
        Initial capital
    transaction_cost_bps : float
        Transaction cost in basis points
    slippage_bps : float
        Slippage in basis points
    
    Returns
    -------
    Dict
        Dictionary with 'returns_df' and 'metrics_df' keys
    """
    returns_df = calculate_returns(
        signals_df, data, equity_symbols, fx_symbols, regime_labels, initial_capital,
        transaction_cost_bps, slippage_bps, spx_benchmark
    )
    
    metrics_df = calculate_performance_metrics(returns_df)
    
    return {
        'returns_df': returns_df,
        'metrics_df': metrics_df
    }
