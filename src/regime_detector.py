"""
Regime detection module using Hidden Markov Models.
"""

import pandas as pd
import numpy as np
from hmmlearn import hmm
from typing import Optional, Tuple


def engineer_features(
    data: pd.DataFrame,
    signals_df: pd.DataFrame,
    vix_symbol: str = '^VIX',
    yield_10y_symbol: str = '^TNX',
    yield_3m_symbol: str = '^IRX',
    dxy_symbol: str = 'DX-Y.NYB',
    equity_symbols: Optional[list] = None,
    fx_symbols: Optional[list] = None,
    rolling_window: int = 60,
    zscore_window: int = 252
) -> pd.DataFrame:
    """
    Engineer features for regime detection.
    
    Features:
    1. VIX level (z-score, 60-day rolling)
    2. Yield curve slope (10Y-3M, z-score, 60-day)
    3. DXY momentum (12-month return, z-score)
    4. Cross-asset correlation (equity vs FX, 60-day rolling)
    5. Equity momentum signal (raw)
    6. FX carry signal (raw)
    
    Parameters
    ----------
    data : pd.DataFrame
        Combined DataFrame with all price data
    signals_df : pd.DataFrame
        DataFrame with 'equity_momentum' and 'fx_carry' columns
    vix_symbol : str
        VIX ticker symbol (default: '^VIX')
    yield_10y_symbol : str
        10-year Treasury yield symbol (default: '^TNX')
    yield_3m_symbol : str
        3-month Treasury yield symbol (default: '^IRX')
    dxy_symbol : str
        DXY symbol (default: 'DX-Y.NYB')
    equity_symbols : Optional[list]
        List of equity symbols for correlation calculation
    fx_symbols : Optional[list]
        List of FX symbols for correlation calculation
    rolling_window : int
        Rolling window for features (default: 60 days)
    zscore_window : int
        Window for z-score normalization (default: 252 days)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with engineered features, normalized using rolling z-scores
    """
    features = {}
    
    # 1. VIX level (z-score, 60-day rolling)
    vix_col = f"{vix_symbol}_close"
    if vix_col in data.columns:
        vix = data[vix_col]
        # Rolling mean and std for z-score
        vix_mean = vix.rolling(window=zscore_window, min_periods=60).mean()
        vix_std = vix.rolling(window=zscore_window, min_periods=60).std()
        features['vix_zscore'] = (vix - vix_mean) / vix_std
    else:
        print(f"Warning: {vix_col} not found")
        features['vix_zscore'] = pd.Series(index=data.index, dtype=float)
    
    # 2. Yield curve slope (10Y - 3M, z-score, 60-day)
    yield_10y_col = f"{yield_10y_symbol}_close"
    yield_3m_col = f"{yield_3m_symbol}_close"
    if yield_10y_col in data.columns and yield_3m_col in data.columns:
        yield_10y = data[yield_10y_col]
        yield_3m = data[yield_3m_col]
        yield_slope = yield_10y - yield_3m
        # Rolling z-score
        slope_mean = yield_slope.rolling(window=zscore_window, min_periods=60).mean()
        slope_std = yield_slope.rolling(window=zscore_window, min_periods=60).std()
        features['yield_slope_zscore'] = (yield_slope - slope_mean) / slope_std
    else:
        print(f"Warning: Yield data not found")
        features['yield_slope_zscore'] = pd.Series(index=data.index, dtype=float)
    
    # 3. DXY momentum (12-month return, z-score)
    dxy_col = f"{dxy_symbol}_close"
    if dxy_col in data.columns:
        dxy = data[dxy_col]
        dxy_momentum = dxy.pct_change(252)  # 12-month return
        # Rolling z-score
        dxy_mean = dxy_momentum.rolling(window=zscore_window, min_periods=60).mean()
        dxy_std = dxy_momentum.rolling(window=zscore_window, min_periods=60).std()
        features['dxy_momentum_zscore'] = (dxy_momentum - dxy_mean) / dxy_std
    else:
        print(f"Warning: {dxy_col} not found")
        features['dxy_momentum_zscore'] = pd.Series(index=data.index, dtype=float)
    
    # 4. Cross-asset correlation (equity vs FX, 60-day rolling)
    if equity_symbols and fx_symbols:
        # Calculate equity portfolio return
        equity_returns = []
        for symbol in equity_symbols:
            col_name = f"{symbol}_close"
            if col_name in data.columns:
                equity_returns.append(data[col_name].pct_change())
        
        # Calculate FX portfolio return
        fx_returns = []
        for symbol in fx_symbols:
            col_name = f"{symbol}_close"
            if col_name in data.columns:
                ret = data[col_name].pct_change()
                if 'JPY' in symbol:
                    ret = -ret  # Inverse for JPY
                fx_returns.append(ret)
        
        if equity_returns and fx_returns:
            equity_portfolio = pd.DataFrame(equity_returns).T.mean(axis=1)
            fx_portfolio = pd.DataFrame(fx_returns).T.mean(axis=1)
            
            # Rolling correlation
            correlation = equity_portfolio.rolling(window=rolling_window).corr(fx_portfolio)
            features['cross_asset_corr'] = correlation
        else:
            features['cross_asset_corr'] = pd.Series(index=data.index, dtype=float)
    else:
        features['cross_asset_corr'] = pd.Series(index=data.index, dtype=float)
    
    # 5. Equity momentum signal (raw)
    if 'equity_momentum' in signals_df.columns:
        features['equity_momentum'] = signals_df['equity_momentum']
    else:
        features['equity_momentum'] = pd.Series(index=data.index, dtype=float)
    
    # 6. FX carry signal (raw)
    if 'fx_carry' in signals_df.columns:
        features['fx_carry'] = signals_df['fx_carry']
    else:
        features['fx_carry'] = pd.Series(index=data.index, dtype=float)
    
    # Create features DataFrame
    features_df = pd.DataFrame(features, index=data.index)
    
    # Drop rows with insufficient data
    features_df = features_df.dropna()
    
    return features_df


def detect_regimes(
    features_df: pd.DataFrame,
    n_states: int = 2,
    n_iter: int = 100,
    random_state: int = 42
) -> Tuple[pd.DataFrame, hmm.GaussianHMM]:
    """
    Detect market regimes using Gaussian HMM.
    
    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame with engineered features (should be normalized)
    n_states : int
        Number of hidden states (default: 2)
    n_iter : int
        Maximum number of iterations for HMM fitting (default: 100)
    random_state : int
        Random seed for reproducibility (default: 42)
    
    Returns
    -------
    Tuple[pd.DataFrame, hmm.GaussianHMM]
        DataFrame with regime labels added, and fitted HMM model
    """
    # Prepare data for HMM (drop NaN, convert to numpy)
    features_clean = features_df.dropna()
    
    if len(features_clean) == 0:
        raise ValueError("No valid features after dropping NaN")
    
    X = features_clean.values
    
    # Fit Gaussian HMM
    model = hmm.GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=n_iter,
        random_state=random_state
    )
    
    print(f"Fitting HMM with {n_states} states on {len(features_clean)} observations...")
    model.fit(X)
    
    # Predict regimes
    regime_labels = model.predict(X)
    
    # Add regime labels to features DataFrame
    result_df = features_clean.copy()
    result_df['regime'] = regime_labels
    
    # Calculate regime probabilities
    regime_probs = model.predict_proba(X)
    for i in range(n_states):
        result_df[f'regime_{i}_prob'] = regime_probs[:, i]
    
    print(f"Regime detection complete. Regime distribution:")
    print(result_df['regime'].value_counts().sort_index())
    
    return result_df, model
