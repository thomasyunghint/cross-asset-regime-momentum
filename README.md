# Cross-Asset Momentum Regime Classifier MVP

A complete MVP implementation of a cross-asset momentum trading strategy with regime-based dynamic allocation using Hidden Markov Models (HMM).

## Overview

This project implements a systematic trading strategy that:
1. **Collects** market data from equity indices, FX pairs, and macro indicators
2. **Calculates** momentum signals for equity and carry signals for FX
3. **Detects** market regimes (risk-on vs risk-off) using Gaussian HMM
4. **Backtests** static vs dynamic regime-based allocation strategies

## Methodology

### Data Sources
- **Equity Indices**: SPY (S&P 500), QQQ (Nasdaq 100), IWM (Russell 2000)
- **FX Pairs**: EUR/USD, GBP/USD, JPY/USD, AUD/USD, CAD/USD
- **Macro Indicators**: VIX, 10Y Treasury yield, 3M Treasury yield, DXY

### Signal Calculation
- **Equity Momentum**: 12-month return with 1-month lag (equal-weight portfolio)
- **FX Carry**: 12-month return as carry proxy (equal-weight portfolio)

### Regime Detection
- **Model**: Gaussian HMM with 2 states
- **Features**:
  - VIX z-score (60-day rolling)
  - Yield curve slope z-score (10Y - 3M)
  - DXY momentum z-score
  - Cross-asset correlation (equity vs FX, 60-day rolling)
  - Raw momentum/carry signals

### Strategies
1. **Static Equity Momentum**: 100% equity momentum
2. **Static FX Carry**: 100% FX carry
3. **Static 50/50**: Equal-weight momentum + carry
4. **Dynamic Regime-Based**: 
   - Regime 0 (risk-on): 80% equity, 20% FX
   - Regime 1 (risk-off): 20% equity, 80% FX

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Run the Analysis

**Option 1: Run the complete pipeline (Recommended)**

```bash
python run_mvp.py
```

This will run the entire pipeline end-to-end:
1. Fetch market data
2. Calculate momentum and carry signals
3. Engineer features for regime detection
4. Fit HMM and detect regimes
5. Backtest all strategies
6. Generate visualizations and performance reports

Results will be saved to `reports/figures/` and performance metrics will be printed to console.

**Option 2: Use Jupyter Notebook**

```bash
jupyter notebook notebooks/mvp_exploration.ipynb
```

Run all cells sequentially (Cell → Run All) for interactive exploration.

**Output Files**

Results will be saved to `reports/figures/`:
- `signals.png`: Momentum and carry signals over time
- `features.png`: Regime detection features
- `regimes.png`: Regime transitions and probabilities
- `equity_curves.png`: Strategy performance comparison
- `feature_distributions.png`: Feature distributions by regime
- `monthly_returns_heatmap.png`: Monthly returns heatmap by strategy

## Project Structure

```
cross-asset-regime-momentum/
├── README.md
├── requirements.txt
├── config.yaml
├── run_mvp.py                  # Single entry point for complete pipeline
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # Data fetching from Yahoo Finance
│   ├── signal_calculator.py    # Momentum and carry signal calculation
│   ├── regime_detector.py      # Feature engineering and HMM regime detection
│   ├── backtester.py           # Backtest engine for all strategies
│   └── visualizer.py           # Plotting and visualization functions
├── notebooks/
│   └── mvp_exploration.ipynb   # Interactive exploration notebook
├── data/
│   ├── raw/                    # Raw data (gitignored)
│   └── processed/              # Processed data (gitignored)
└── reports/
    └── figures/                # Generated plots (gitignored)
```

## Configuration

Edit `config.yaml` to customize:
- Data date ranges
- Signal parameters (lookback days, lag)
- Regime detection settings (number of states)
- Backtest parameters (initial capital, transaction costs)

## Results

The pipeline will output:
- **Performance Metrics Table**: Sharpe ratio, max drawdown, total return, win rate for each strategy
- **Regime Statistics**: Distribution and characteristics of each regime
- **Feature Analysis**: How features differ across regimes
- **Visualizations**: All plots saved to `reports/figures/`

## MVP Limitations

This MVP has several simplifications for rapid development:

1. **No walk-forward optimization**: Single train/test split (look-ahead bias)
2. **Simplified FX carry**: Uses momentum proxy instead of true interest rate differential
3. **Fixed transaction costs**: Not market-impact aware
4. **No position sizing optimization**: Equal weights, no Kelly or risk parity
5. **Regime detection uses full history**: Should use expanding/rolling window in production

## Next Steps

- [ ] Walk-forward validation with purging/embargo
- [ ] True FX carry calculation (interest rate data from FRED)
- [ ] Dynamic position sizing (Kelly criterion, risk parity)
- [ ] Alternative regime models (Markov-switching VAR, LSTM)
- [ ] Real-time regime prediction pipeline
- [ ] Risk management (stop-loss, position limits)

## Dependencies

- `yfinance`: Market data fetching
- `pandas`, `numpy`: Data manipulation
- `hmmlearn`: Hidden Markov Model implementation
- `scikit-learn`: Feature scaling
- `matplotlib`, `seaborn`: Visualization
- `pyyaml`: Configuration management

## License

MIT
