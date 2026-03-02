"""
Visualization module for regime detection and backtest results.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional


def plot_signals(
    signals_df: pd.DataFrame,
    save_path: Optional[str] = None
):
    """
    Plot momentum and carry signals over time.
    
    Parameters
    ----------
    signals_df : pd.DataFrame
        DataFrame with 'equity_momentum' and 'fx_carry' columns
    save_path : Optional[str]
        Path to save the figure (default: None, shows plot)
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(signals_df.index, signals_df['equity_momentum'], 
            label='Equity Momentum', linewidth=1.5, alpha=0.8)
    ax.plot(signals_df.index, signals_df['fx_carry'], 
            label='FX Carry', linewidth=1.5, alpha=0.8)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5, alpha=0.5)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Signal Value', fontsize=12)
    ax.set_title('Momentum and Carry Signals Over Time', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved signals plot to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_features(
    features_df: pd.DataFrame,
    save_path: Optional[str] = None
):
    """
    Plot regime detection features over time.
    
    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame with feature columns
    save_path : Optional[str]
        Path to save the figure
    """
    feature_cols = [col for col in features_df.columns 
                    if col not in ['regime', 'regime_0_prob', 'regime_1_prob']]
    
    n_features = len(feature_cols)
    fig, axes = plt.subplots(n_features, 1, figsize=(14, 3 * n_features), sharex=True)
    
    if n_features == 1:
        axes = [axes]
    
    for i, col in enumerate(feature_cols):
        axes[i].plot(features_df.index, features_df[col], linewidth=1, alpha=0.7)
        axes[i].axhline(y=0, color='black', linestyle='--', linewidth=0.5, alpha=0.5)
        axes[i].set_ylabel(col.replace('_', ' ').title(), fontsize=10)
        axes[i].grid(True, alpha=0.3)
    
    axes[-1].set_xlabel('Date', fontsize=12)
    fig.suptitle('Regime Detection Features', fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved features plot to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_regimes(
    features_df: pd.DataFrame,
    save_path: Optional[str] = None
):
    """
    Plot regime transitions and probabilities over time.
    
    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame with 'regime' column and regime probability columns
    save_path : Optional[str]
        Path to save the figure
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    # Plot 1: Regime labels
    ax1 = axes[0]
    regime_colors = {0: 'green', 1: 'red', 2: 'blue'}
    
    for regime in sorted(features_df['regime'].unique()):
        mask = features_df['regime'] == regime
        ax1.scatter(features_df.index[mask], features_df['regime'][mask],
                   c=regime_colors.get(regime, 'gray'), label=f'Regime {regime}',
                   alpha=0.6, s=10)
    
    ax1.set_ylabel('Regime', fontsize=12)
    ax1.set_title('Regime Transitions Over Time', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_yticks(sorted(features_df['regime'].unique()))
    
    # Plot 2: Regime probabilities
    ax2 = axes[1]
    prob_cols = [col for col in features_df.columns if col.startswith('regime_') and col.endswith('_prob')]
    
    for col in prob_cols:
        regime_num = col.split('_')[1]
        ax2.plot(features_df.index, features_df[col], 
                label=f'Regime {regime_num} Probability', linewidth=1.5, alpha=0.7)
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Probability', fontsize=12)
    ax2.set_title('Regime Probabilities Over Time', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 1])
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved regimes plot to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_equity_curves(
    returns_df: pd.DataFrame,
    save_path: Optional[str] = None
):
    """
    Plot equity curves for all strategies.
    
    Parameters
    ----------
    returns_df : pd.DataFrame
        DataFrame with equity curve columns (ending in '_equity')
    save_path : Optional[str]
        Path to save the figure
    """
    equity_cols = [col for col in returns_df.columns if col.endswith('_equity')]
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    strategy_names = {
        'static_equity_equity': 'Static Equity Momentum',
        'static_fx_equity': 'Static FX Carry',
        'static_5050_equity': 'Static 50/50',
        'dynamic_regime_equity': 'Dynamic Regime-Based',
        'spx_benchmark_equity': 'SPX Benchmark'
    }
    
    # Plot SPX benchmark first (if available) with distinct style
    if 'spx_benchmark_equity' in equity_cols:
        ax.plot(returns_df.index, returns_df['spx_benchmark_equity'], 
               label='SPX Benchmark', linewidth=2.5, alpha=0.9, color='black', linestyle='--')
        equity_cols = [col for col in equity_cols if col != 'spx_benchmark_equity']
    
    for col in equity_cols:
        strategy_name = strategy_names.get(col, col.replace('_equity', '').replace('_', ' ').title())
        ax.plot(returns_df.index, returns_df[col], 
               label=strategy_name, linewidth=2, alpha=0.8)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax.set_title('Strategy Equity Curves', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved equity curves plot to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_feature_distributions(
    features_df: pd.DataFrame,
    save_path: Optional[str] = None
):
    """
    Plot feature distributions by regime (box plots).
    
    Parameters
    ----------
    features_df : pd.DataFrame
        DataFrame with feature columns and 'regime' column
    save_path : Optional[str]
        Path to save the figure
    """
    feature_cols = [col for col in features_df.columns 
                    if col not in ['regime', 'regime_0_prob', 'regime_1_prob']]
    
    n_features = len(feature_cols)
    n_cols = 3
    n_rows = (n_features + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
    axes = axes.flatten() if n_features > 1 else [axes]
    
    for i, col in enumerate(feature_cols):
        ax = axes[i]
        
        # Prepare data for box plot
        data_for_plot = []
        labels = []
        for regime in sorted(features_df['regime'].unique()):
            regime_data = features_df[features_df['regime'] == regime][col].dropna()
            if len(regime_data) > 0:
                data_for_plot.append(regime_data.values)
                labels.append(f'Regime {regime}')
        
        if data_for_plot:
            bp = ax.boxplot(data_for_plot, labels=labels, patch_artist=True)
            for patch in bp['boxes']:
                patch.set_alpha(0.7)
        
        ax.set_ylabel(col.replace('_', ' ').title(), fontsize=10)
        ax.set_title(f'{col.replace("_", " ").title()} by Regime', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
    
    # Hide unused subplots
    for i in range(len(feature_cols), len(axes)):
        axes[i].set_visible(False)
    
    fig.suptitle('Feature Distributions by Regime', fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved feature distributions plot to {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_monthly_returns_heatmap(
    returns_df: pd.DataFrame,
    save_path: Optional[str] = None
):
    """
    Plot monthly returns heatmap by strategy.
    
    Parameters
    ----------
    returns_df : pd.DataFrame
        DataFrame with strategy returns (columns: static_equity, static_fx, static_5050, dynamic_regime)
    save_path : Optional[str]
        Path to save the figure
    """
    strategy_cols = ['static_equity', 'static_fx', 'static_5050', 'dynamic_regime', 'spx_benchmark']
    available_cols = [col for col in strategy_cols if col in returns_df.columns]
    
    if not available_cols:
        print("No strategy columns found for heatmap")
        return
    
    # Calculate monthly returns
    monthly_returns = {}
    for col in available_cols:
        monthly = returns_df[col].resample('M').apply(lambda x: (1 + x).prod() - 1)
        if col == 'spx_benchmark':
            strategy_name = 'SPX Benchmark'
        else:
            strategy_name = col.replace('_', ' ').title()
        monthly_returns[strategy_name] = monthly
    
    monthly_df = pd.DataFrame(monthly_returns)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, max(6, len(monthly_df) * 0.3)))
    
    sns.heatmap(monthly_df.T, annot=True, fmt='.2%', cmap='RdYlGn', 
                center=0, vmin=-0.2, vmax=0.2, cbar_kws={'label': 'Monthly Return'},
                ax=ax, linewidths=0.5)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Strategy', fontsize=12)
    ax.set_title('Monthly Returns Heatmap by Strategy', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved monthly returns heatmap to {save_path}")
    else:
        plt.show()
    
    plt.close()


def print_performance_metrics(metrics_df: pd.DataFrame):
    """
    Print performance metrics table with SPX comparison.
    
    Parameters
    ----------
    metrics_df : pd.DataFrame
        DataFrame with performance metrics
    """
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)
    
    # Reorder to show SPX first if available
    if 'spx_benchmark' in metrics_df.index:
        # Move SPX to first position
        other_strategies = [idx for idx in metrics_df.index if idx != 'spx_benchmark']
        metrics_df = metrics_df.loc[['spx_benchmark'] + other_strategies]
        # Rename for display
        metrics_df.index = metrics_df.index.str.replace('spx_benchmark', 'SPX Benchmark')
        metrics_df.index = metrics_df.index.str.replace('static_equity', 'Static Equity')
        metrics_df.index = metrics_df.index.str.replace('static_fx', 'Static FX')
        metrics_df.index = metrics_df.index.str.replace('static_5050', 'Static 50/50')
        metrics_df.index = metrics_df.index.str.replace('dynamic_regime', 'Dynamic Regime')
    
    print(metrics_df.to_string())
    
    # Add comparison with SPX if available
    if 'SPX Benchmark' in metrics_df.index:
        print("\n" + "-"*80)
        print("COMPARISON WITH SPX BENCHMARK")
        print("-"*80)
        spx_metrics = metrics_df.loc['SPX Benchmark']
        
        for strategy in metrics_df.index:
            if strategy == 'SPX Benchmark':
                continue
            
            strategy_metrics = metrics_df.loc[strategy]
            
            # Extract numeric values for comparison
            try:
                spx_total = float(spx_metrics['Total Return'].rstrip('%')) / 100
                strategy_total = float(strategy_metrics['Total Return'].rstrip('%')) / 100
                outperformance = strategy_total - spx_total
                
                spx_annual = float(spx_metrics['Annualized Return'].rstrip('%')) / 100
                strategy_annual = float(strategy_metrics['Annualized Return'].rstrip('%')) / 100
                annual_outperformance = strategy_annual - spx_annual
                
                spx_sharpe = float(spx_metrics['Sharpe Ratio'])
                strategy_sharpe = float(strategy_metrics['Sharpe Ratio'])
                sharpe_diff = strategy_sharpe - spx_sharpe
                
                print(f"\n{strategy}:")
                print(f"  Total Return: {outperformance:+.2%} vs SPX")
                print(f"  Annual Return: {annual_outperformance:+.2%} vs SPX")
                print(f"  Sharpe Ratio: {sharpe_diff:+.2f} vs SPX")
            except:
                pass
    
    print("="*80 + "\n")


def save_all_plots(
    signals_df: pd.DataFrame,
    features_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    output_dir: str = 'reports/figures'
):
    """
    Save all plots to output directory.
    
    Parameters
    ----------
    signals_df : pd.DataFrame
        DataFrame with signals
    features_df : pd.DataFrame
        DataFrame with features and regimes
    returns_df : pd.DataFrame
        DataFrame with returns and equity curves
    output_dir : str
        Output directory for plots
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    plot_signals(signals_df, f"{output_dir}/signals.png")
    plot_features(features_df, f"{output_dir}/features.png")
    plot_regimes(features_df, f"{output_dir}/regimes.png")
    plot_equity_curves(returns_df, f"{output_dir}/equity_curves.png")
    plot_feature_distributions(features_df, f"{output_dir}/feature_distributions.png")
    plot_monthly_returns_heatmap(returns_df, f"{output_dir}/monthly_returns_heatmap.png")
    
    print(f"\nAll plots saved to {output_dir}/")
