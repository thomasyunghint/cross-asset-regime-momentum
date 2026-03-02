"""
Single entry point for Cross-Asset Momentum Regime Classifier MVP.

Runs the complete pipeline:
1. Data collection
2. Signal calculation
3. Feature engineering
4. Regime detection
5. Backtesting
6. Visualization and reporting
"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import os

from src.data_loader import load_all_data
from src.signal_calculator import calculate_all_signals
from src.regime_detector import engineer_features, detect_regimes
from src.backtester import run_backtest, load_spx_benchmark
from src.visualizer import save_all_plots, print_performance_metrics

warnings.filterwarnings('ignore')


def main():
    """Run the complete MVP pipeline."""
    
    print("="*80)
    print("CROSS-ASSET MOMENTUM REGIME CLASSIFIER - MVP")
    print("="*80)
    print()
    
    # Load configuration
    print("Loading configuration...")
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"Data range: {config['data']['start_date']} to {config['data']['end_date']}")
    print(f"Regime states: {config['regime']['n_states']}")
    print()
    
    # Phase 1: Data Collection
    print("="*80)
    print("PHASE 1: DATA COLLECTION")
    print("="*80)
    
    # Get data source configuration
    data_sources = config['data'].get('sources', ['fred', 'local', 'yfinance'])
    fred_api_key = config['data'].get('fred_api_key') or os.getenv('FRED_API_KEY')
    data_dir = config['data'].get('data_dir', 'data')
    
    print(f"Data sources (priority order): {', '.join(data_sources)}")
    if fred_api_key:
        print("FRED API key: Configured")
    elif 'fred' in data_sources:
        print("FRED API key: Not configured (set FRED_API_KEY env var or in config.yaml)")
    
    data = load_all_data(
        equity_symbols=config['data']['equity']['symbols'],
        fx_symbols=config['data']['fx']['symbols'],
        macro_symbols=config['data']['macro']['symbols'],
        start_date=config['data']['start_date'],
        end_date=config['data']['end_date'],
        data_sources=data_sources,
        fred_api_key=fred_api_key,
        data_dir=data_dir
    )
    
    # Validate data was loaded successfully
    if data.empty or len(data) < 252:
        print("\n" + "="*80)
        print("ERROR: Insufficient data loaded!")
        print("="*80)
        print("\nPossible reasons:")
        print("  1. Data source API rate limiting (yfinance) - try again in a few minutes")
        print("  2. Network connectivity issues")
        print("  3. Invalid date range or symbols")
        print("  4. FRED API key not configured (for macro data)")
        print("  5. Local CSV files not found in data/ directory")
        print(f"\nLoaded {len(data)} days of data, need at least 252 days.")
        print("\nSuggestions:")
        print("  - Configure FRED API key (free): https://fred.stlouisfed.org/docs/api/api_key.html")
        print("  - Add FRED_API_KEY to environment or config.yaml")
        print("  - Download data to local CSV files in data/ directory")
        print("  - Wait 5-10 minutes and try again (if using yfinance)")
        print("  - Check your internet connection")
        print("  - Try reducing the date range in config.yaml")
        print("="*80)
        return
    print()
    
    # Phase 2: Signal Calculation
    print("="*80)
    print("PHASE 2: SIGNAL CALCULATION")
    print("="*80)
    signals_df = calculate_all_signals(
        data,
        equity_symbols=config['data']['equity']['symbols'],
        fx_symbols=config['data']['fx']['symbols'],
        momentum_lookback=config['signals']['momentum']['lookback_days'],
        momentum_lag=config['signals']['momentum']['lag_days'],
        carry_lookback=config['signals']['carry']['lookback_days']
    )
    print(f"Calculated signals for {len(signals_df)} days")
    print(f"  Equity momentum: {signals_df['equity_momentum'].notna().sum()} valid values")
    print(f"  FX carry: {signals_df['fx_carry'].notna().sum()} valid values")
    print()
    
    # Phase 3: Feature Engineering
    print("="*80)
    print("PHASE 3: FEATURE ENGINEERING")
    print("="*80)
    features_df = engineer_features(
        data,
        signals_df,
        vix_symbol='^VIX',
        yield_10y_symbol='^TNX',
        yield_3m_symbol='^IRX',
        dxy_symbol='DX-Y.NYB',
        equity_symbols=config['data']['equity']['symbols'],
        fx_symbols=config['data']['fx']['symbols']
    )
    print(f"Engineered {len(features_df.columns)} features for {len(features_df)} days")
    print(f"Features: {', '.join(features_df.columns)}")
    print()
    
    # Phase 4: Regime Detection
    print("="*80)
    print("PHASE 4: REGIME DETECTION")
    print("="*80)
    features_with_regime, hmm_model = detect_regimes(
        features_df,
        n_states=config['regime']['n_states'],
        n_iter=config['regime']['n_iter'],
        random_state=config['regime']['random_state']
    )
    print()
    
    # Align signals with regime labels
    regime_labels = features_with_regime['regime']
    # Align signals_df with features_with_regime index
    signals_aligned = signals_df.loc[features_with_regime.index]
    
    # Phase 5: Backtesting
    print("="*80)
    print("PHASE 5: BACKTESTING")
    print("="*80)
    
    # Load SPX benchmark
    print("Loading SPX benchmark...")
    spx_benchmark = load_spx_benchmark(
        start_date=config['data']['start_date'],
        end_date=config['data']['end_date'],
        data_sources=config['data'].get('sources', ['fred', 'local', 'yfinance']),
        fred_api_key=config['data'].get('fred_api_key') or os.getenv('FRED_API_KEY'),
        data_dir=config['data'].get('data_dir', 'data')
    )
    if spx_benchmark is not None:
        print(f"  [OK] SPX benchmark: {len(spx_benchmark)} days")
    else:
        print("  [WARNING] SPX benchmark not available")
    
    # Align data with signals index
    data_aligned = data.loc[signals_aligned.index]
    backtest_results = run_backtest(
        signals_aligned,
        data_aligned,
        equity_symbols=config['data']['equity']['symbols'],
        fx_symbols=config['data']['fx']['symbols'],
        regime_labels=regime_labels,
        initial_capital=config['backtest']['initial_capital'],
        transaction_cost_bps=config['backtest']['transaction_cost_bps'],
        slippage_bps=config['backtest']['slippage_bps'],
        spx_benchmark=spx_benchmark
    )
    
    returns_df = backtest_results['returns_df']
    metrics_df = backtest_results['metrics_df']
    
    print(f"Backtested {len(returns_df)} trading days")
    print()
    
    # Phase 6: Visualization & Reporting
    print("="*80)
    print("PHASE 6: VISUALIZATION & REPORTING")
    print("="*80)
    
    # Save all plots
    save_all_plots(
        signals_aligned,
        features_with_regime,
        returns_df,
        output_dir='reports/figures'
    )
    
    # Print performance metrics
    print_performance_metrics(metrics_df)
    
    # Print regime statistics
    print("="*80)
    print("REGIME STATISTICS")
    print("="*80)
    for regime in sorted(features_with_regime['regime'].unique()):
        regime_mask = features_with_regime['regime'] == regime
        regime_data = features_with_regime[regime_mask]
        print(f"\nRegime {regime}:")
        print(f"  Days: {regime_mask.sum()} ({regime_mask.sum()/len(features_with_regime)*100:.1f}%)")
        print(f"  Date range: {regime_data.index.min()} to {regime_data.index.max()}")
        
        # Average feature values
        feature_cols = [col for col in features_with_regime.columns 
                       if col not in ['regime', 'regime_0_prob', 'regime_1_prob']]
        print(f"  Average feature values:")
        for col in feature_cols:
            avg_val = regime_data[col].mean()
            print(f"    {col}: {avg_val:.3f}")
    
    print()
    print("="*80)
    print("MVP PIPELINE COMPLETE!")
    print("="*80)
    print(f"\nResults saved to:")
    print(f"  - reports/figures/signals.png")
    print(f"  - reports/figures/features.png")
    print(f"  - reports/figures/regimes.png")
    print(f"  - reports/figures/equity_curves.png")
    print(f"  - reports/figures/feature_distributions.png")
    print(f"  - reports/figures/monthly_returns_heatmap.png")
    print()


if __name__ == '__main__':
    main()
