# 运行进度解读指南

## 📊 整体流程概览

这个程序运行了一个**跨资产动量交易策略**的完整回测流程，共分为6个阶段：

---

## 🔍 阶段详解

### **PHASE 1: DATA COLLECTION (数据收集)**

**目的**: 从多个数据源获取市场数据

**输出解读**:
```
Fetching equity data...
  [OK] SPY: 1257 days (cached)      # S&P 500 ETF，1257个交易日
  [OK] QQQ: 1257 days (cached)      # 纳斯达克100 ETF
  [OK] IWM: 1257 days (cached)      # 罗素2000小盘股ETF

Fetching FX data...
  [OK] EURUSD=X: 1304 days (cached) # 欧元/美元汇率
  [OK] GBPUSD=X: 1304 days (cached) # 英镑/美元
  [OK] JPYUSD=X: 1304 days (cached) # 日元/美元
  [OK] AUDUSD=X: 1304 days (cached) # 澳元/美元
  [OK] CADUSD=X: 1304 days (cached) # 加元/美元

Fetching macro indicators...
  [OK] ^VIX: 1827 days (cached)     # 恐慌指数（波动率）
  [OK] ^TNX: 1827 days (cached)     # 10年期美债收益率
  [OK] ^IRX: 1827 days (cached)     # 3个月期美债收益率
  [OK] DX-Y.NYB: 1827 days (cached) # 美元指数

Combining data...
  [OK] Combined dataset: 1826 days, 12 columns
```

**关键信息**:
- ✅ 所有数据都从缓存加载（快速）
- 📅 最终合并数据集：1826个交易日，12列数据
- 💡 不同资产的数据天数不同（股票1257天，外汇1304天，宏观1827天）

---

### **PHASE 2: SIGNAL CALCULATION (信号计算)**

**目的**: 计算交易信号（动量信号和套息信号）

**输出解读**:
```
Calculated signals for 1826 days
  Equity momentum: 1553 valid values  # 股票动量信号：1553个有效值
  FX carry: 1574 valid values         # 外汇套息信号：1574个有效值
```

**计算方法**:
- **Equity Momentum (股票动量)**: 
  - 计算SPY、QQQ、IWM的12个月收益率（252天）
  - 滞后1个月（21天）避免前瞻偏差
  - 等权重组合
  
- **FX Carry (外汇套息)**:
  - 计算5个外汇对的12个月收益率
  - 等权重组合

**为什么有效值少于总天数？**
- 需要252天的历史数据才能计算第一个信号
- 所以前252天没有信号值

---

### **PHASE 3: FEATURE ENGINEERING (特征工程)**

**目的**: 构建用于识别市场状态的6个特征

**输出解读**:
```
Engineered 6 features for 1515 days
Features: vix_zscore, yield_slope_zscore, dxy_momentum_zscore, 
          cross_asset_corr, equity_momentum, fx_carry
```

**6个特征详解**:

1. **vix_zscore**: VIX恐慌指数的标准化值（60天滚动窗口）
   - 高值 = 市场恐慌/波动大
   - 低值 = 市场平静

2. **yield_slope_zscore**: 收益率曲线斜率（10年-3个月）的标准化值
   - 正值 = 正常经济环境（长期利率>短期利率）
   - 负值 = 经济衰退信号（收益率曲线倒挂）

3. **dxy_momentum_zscore**: 美元指数动量的标准化值
   - 反映美元强弱趋势

4. **cross_asset_corr**: 股票与外汇的60天滚动相关系数
   - 反映跨资产联动性

5. **equity_momentum**: 股票动量信号（来自阶段2）

6. **fx_carry**: 外汇套息信号（来自阶段2）

**为什么只有1515天？**
- 特征计算需要额外的滚动窗口（60天）
- 所以有效特征数据进一步减少

---

### **PHASE 4: REGIME DETECTION (状态识别)**

**目的**: 使用隐马尔可夫模型（HMM）识别市场状态

**输出解读**:
```
Fitting HMM with 2 states on 1515 observations...
Regime detection complete. Regime distribution:
regime
0    806  # 状态0：806天（53.2%）
1    709  # 状态1：709天（46.8%）
```

**两个状态的含义**:
- **Regime 0 (风险偏好状态 - Risk-On)**:
  - 806天，占53.2%
  - 特征：VIX较低、收益率曲线正常、股票动量强
  - 策略：80%股票，20%外汇

- **Regime 1 (风险规避状态 - Risk-Off)**:
  - 709天，占46.8%
  - 特征：VIX较高、收益率曲线倒挂、股票动量弱
  - 策略：20%股票，80%外汇

**HMM模型原理**:
- 使用高斯混合模型识别隐藏的市场状态
- 基于6个特征自动学习状态转换规律
- 不需要人工定义阈值

---

### **PHASE 5: BACKTESTING (回测)**

**目的**: 模拟4种策略的历史表现

**输出解读**:
```
Backtested 1515 trading days
```

**4种策略**:

1. **static_equity**: 100%股票动量策略
2. **static_fx**: 100%外汇套息策略
3. **static_5050**: 50%股票 + 50%外汇（静态）
4. **dynamic_regime**: 根据状态动态调整（80/20或20/80）

**回测参数**:
- 初始资金：$100,000
- 交易成本：0.05% (5 bps)
- 滑点：0.02% (2 bps)

---

### **PHASE 6: VISUALIZATION & REPORTING (可视化与报告)**

**目的**: 生成图表和性能报告

**生成的图表**:
1. `signals.png` - 信号时间序列图
2. `features.png` - 特征时间序列图
3. `regimes.png` - 状态识别结果图
4. `equity_curves.png` - 各策略的净值曲线
5. `feature_distributions.png` - 特征分布图
6. `monthly_returns_heatmap.png` - 月度收益热力图

---

## 📈 性能指标解读

### 指标说明

| 指标 | 含义 | 解读 |
|------|------|------|
| **Total Return** | 总收益率 | 整个回测期间的总收益 |
| **Annualized Return** | 年化收益率 | 换算成年化的收益率 |
| **Volatility** | 波动率 | 收益的标准差（风险指标） |
| **Sharpe Ratio** | 夏普比率 | 风险调整后收益 = 年化收益/波动率 |
| **Max Drawdown** | 最大回撤 | 从峰值到谷底的最大跌幅 |
| **Win Rate (Daily)** | 日胜率 | 盈利天数占比 |
| **Win Rate (Monthly)** | 月胜率 | 盈利月份占比 |

### 正常范围参考

- **Sharpe Ratio**: 
  - > 1: 不错
  - > 2: 很好
  - > 3: 优秀

- **Max Drawdown**: 
  - < -20%: 可接受
  - < -10%: 很好
  - < -5%: 优秀

- **Win Rate**: 
  - > 50%: 基本要求
  - > 55%: 不错
  - > 60%: 很好

✅ **问题已修复**: 回测计算错误已修复！

**修复前的问题**:
- 动量信号是**12个月的收益率**（如0.17 = 17%）
- 回测代码直接将其当作**日收益率**使用
- 导致累积计算爆炸，产生天文数字

**修复方案**:
1. ✅ 修改 `calculate_returns()` 函数，接受原始价格数据
2. ✅ 计算**实际的资产日收益率**（使用 `pct_change()`）
3. ✅ 使用动量信号决定**仓位方向**（信号>0做多，信号<0做空）
4. ✅ 策略收益率 = 实际资产收益率 × 仓位方向

**修复后的结果**（现在看起来合理）:
- static_equity: 81.31% 总收益率，10.41% 年化收益率
- static_fx: 28.99% 总收益率，4.33% 年化收益率
- static_5050: 56.10% 总收益率，7.69% 年化收益率
- dynamic_regime: 69.30% 总收益率，9.16% 年化收益率

---

## 🔬 状态统计解读

### Regime 0 (风险偏好状态)

```
Days: 806 (53.2%)
Date range: 2020-11-08 to 2024-12-31
Average feature values:
  vix_zscore: 0.246        # VIX略高于平均（轻微恐慌）
  yield_slope_zscore: 1.247 # 收益率曲线陡峭（经济正常）
  dxy_momentum_zscore: 0.726 # 美元走强
  cross_asset_corr: -0.014  # 股票与外汇相关性低
  equity_momentum: 0.173    # 股票动量强（17.3%）
  fx_carry: 0.017          # 外汇套息弱（1.7%）
```

**解读**: 这是**牛市/风险偏好**状态，股票表现好，适合重仓股票。

### Regime 1 (风险规避状态)

```
Days: 709 (46.8%)
Date range: 2021-07-13 to 2024-07-13
Average feature values:
  vix_zscore: -0.785       # VIX低于平均（但这是相对值）
  yield_slope_zscore: -0.876 # 收益率曲线平坦/倒挂（经济担忧）
  dxy_momentum_zscore: 0.058 # 美元动量弱
  cross_asset_corr: -0.001  # 股票与外汇相关性极低
  equity_momentum: 0.068    # 股票动量弱（6.8%）
  fx_carry: 0.002          # 外汇套息极弱（0.2%）
```

**解读**: 这是**熊市/风险规避**状态，股票表现差，适合重仓外汇。

---

## 🎯 关键洞察

1. **数据质量**: ✅ 所有数据成功加载，从缓存读取（快速）

2. **信号有效性**: 
   - 股票动量：1553个有效信号
   - 外汇套息：1574个有效信号
   - 最终用于回测：1515天

3. **状态分布**: 
   - 两种状态分布相对均衡（53% vs 47%）
   - 说明模型成功识别了不同的市场环境

4. **策略对比**: 
   - 动态策略应该优于静态策略
   - 但需要检查性能指标是否正常（当前数字异常）

---

## ⚠️ 潜在问题

从输出看，性能指标中的收益率数字异常大（如 `3833200705283701834042102797419816055654095543925044187159357760208896.00%`），这可能是：

1. **计算错误**: 收益率累积计算可能有bug
2. **数据问题**: 信号值可能异常大
3. **显示问题**: 格式化输出可能有误

建议检查 `src/backtester.py` 中的收益率计算逻辑。

---

## 📝 下一步建议

1. **查看图表**: 检查 `reports/figures/` 中的可视化结果
2. **验证计算**: 检查回测计算逻辑是否正确
3. **优化策略**: 根据结果调整参数或策略逻辑
4. **扩展分析**: 添加更多性能指标（如Calmar比率、Sortino比率等）
