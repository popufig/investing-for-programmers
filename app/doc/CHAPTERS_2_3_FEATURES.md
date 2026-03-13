# 第2章 & 第3章 已实现功能对照

## 第2章：Investment Essentials

### 2.1 财务报表 (Accounting)

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **利润表 (Income Statement)** | ✅ | `StockAnalysis` 页 → Financial Statements 组件，展示 Revenue、Gross Profit、Operating Income、Net Income 的多年趋势折线图 |
| **资产负债表 (Balance Sheet)** | ✅ | 同上，展示 Assets、Liabilities、Equity、Cash 趋势 |
| **现金流量表 (Cash Flow)** | ✅ | 同上，展示 Operating/Investing/Financing Cash Flow |

**使用场景**：在搜索栏输入股票代码（如 AAPL）→ 向下滚动到 Financial Statements 区域，查看 3-5 年财务趋势，判断公司收入是否持续增长、现金流是否健康。

---

### 2.2 行业分类 (GICS Sectors)

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **11个GICS行业分类** | ✅ | Stock Screener 支持按 Sector 筛选；Stock Analysis 展示每只股票的 sector/industry |
| **行业周期敏感度** | ✅ | `EconomicCycleSection` 组件：展示当前行业在 Early/Mid/Late Cycle 及 Recession 中的表现倾向（favored/neutral/stressed） |
| **同行业对比** | ✅ | `PeerComparison` 组件：自定义同行业 peer group，归一化对比 P/E、P/B、ROE、股息率、52周涨幅 |

**使用场景**：
- **Screener 页**：筛选特定行业（如 Information Technology）的股票
- **Stock Analysis 页** → Economic Cycle 区域：判断当前经济周期下该行业是否有利
- **Stock Analysis 页** → Peer Comparison 区域：将同行业公司放在一起比较关键指标

---

### 2.3 市值分类 (Capitalization)

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **Mega/Large/Mid/Small/Micro cap** | ✅ | Holdings 页显示市值标签（彩色徽章）；Screener 支持按市值范围筛选；`format.js` 中的 `marketCapLabel()` 自动分类 |

**使用场景**：Screener 页设置 Market Cap 范围（如 >200B 筛选 Mega-cap），或在 Holdings 页一眼看到持仓的市值等级。

---

### 2.4 财务指标与比率 (Metrics & Ratios)

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **流动性比率** (Current Ratio, Quick Ratio) | ✅ | Stock Analysis → Debt & Liquidity 区域 |
| **负债比率** (D/E, Interest Coverage) | ✅ | Stock Analysis → Debt & Liquidity 区域 |
| **盈利指标** (EPS, FCF per Share) | ✅ | Stock Analysis → Valuation + Growth 区域 |
| **估值比率** (P/E, PEG, P/S, P/B) | ✅ | Stock Analysis → Valuation 区域；Screener 支持 P/E 范围筛选 |
| **盈利能力** (ROA, ROE, Profit Margin) | ✅ | Stock Analysis → Profitability 区域 |
| **股息** (Dividend Yield, Payout Ratio) | ✅ | Stock Analysis → Dividends & Risk 区域；Screener 支持最低股息率筛选 |
| **历史比率趋势** | ✅ | `ratio-trends` API 返回多年 P/E、P/B、P/S、ROE、ROA 变化 |
| **持股指标** (Float, Insider %) | ✅ | Stock Analysis → 100+ 指标卡片中展示 |
| **ESG 评分** | ✅ | `/api/stocks/{ticker}/esg` 端点，返回 E/S/G 各项评分 |

**使用场景**：在 Stock Analysis 页输入股票代码后，5 个指标区域（Valuation / Profitability / Growth / Debt & Liquidity / Dividends & Risk）一目了然地展示书中讨论的所有关键比率。可结合 Peer Comparison 在同行业间对比这些指标。

---

### 2.5 外部评估 (Analyst Opinions)

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **分析师评级** (Buy/Hold/Sell) | ✅ | `AnalystSection` 组件：显示 Strong Buy 到 Strong Sell 的分布柱状图 |
| **目标价** (Target Price) | ✅ | 同上，展示目标价 vs 当前价，计算上行/下行百分比 |
| **分析师人数** | ✅ | 同上，显示参与评级的分析师数量 |

**使用场景**：Stock Analysis 页 → Analyst 区域，看华尔街分析师对该股票的共识评级和目标价，辅助判断市场预期。

---

## 第3章：Collecting Data

### 3.1-3.2 数据分类与平台

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **基本面数据** (Fundamental) | ✅ | 财务报表、比率、行业分类全部实现 |
| **技术面数据** (Technical) | ✅ | 价格历史 OHLCV、SMA 20/50/200、布林带、RSI(14)、MACD |
| **非财务数据** (Sentiment) | ✅ | `/api/stocks/{ticker}/sentiment` 端点，通过 Alpha Vantage 获取新闻情感分析 |
| **Stock Screener** | ✅ | Screener 页：按行业、市值、P/E、股息率、52周涨幅筛选，覆盖 96 只大盘股 |

---

### 3.4 yfinance 库的使用

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **yfinance 基本面获取** | ✅ | `market_data.py` 的 `get_ticker_info()` 通过 `yf.Ticker().info` 获取 100+ 指标 |
| **yfinance 财务报表** | ✅ | `get_financials()` 获取 `income_stmt`、`balance_sheet`、`cash_flow` |
| **yfinance 历史价格** | ✅ | `get_price_history()` 使用 `yf.Ticker().history()` |
| **收益率计算** (Simple & Log Returns) | ✅ | `get_return_analysis()` 计算对数收益率，返回直方图、均值、标准差、方差、偏度、峰度 |
| **标准化比较** (Base=100) | ✅ | Compare 页 → `get_normalized_comparison()` 将多只股票起始价格归一化为 100 进行对比 |
| **统计指标** (Mean, Std, Variance) | ✅ | Stock Analysis → Returns 区域展示完整统计数据 |

**使用场景**：
- **Compare 页**：输入 2-6 只股票代码，选择时间段，查看归一化后的价格走势对比（正是书中 3.4.2 节讨论的标准化比较方法）
- **Stock Analysis 页** → Returns 区域：查看日收益率分布直方图和统计数据（均值、标准差、方差、偏度、峰度）

---

### 3.5 商业数据源

| 书中概念 | 实现状态 | 在App中如何使用 |
|---------|---------|---------------|
| **Alpha Vantage (新闻情感)** | ✅ | 可选配置 API key，提供新闻情感分析功能 |
| **EODHD / OpenBB / Finviz** | ❌ | 未集成，仅使用 yfinance 为主数据源 |
| **Tushare (中国股票)** | ✅ | 支持 A 股和港股数据（额外扩展，非书中内容） |

---

## 超出书本的额外实现

以下功能超出了第2-3章范围，属于进阶实现：

| 功能 | 说明 |
|------|------|
| **Portfolio 管理** | 多组合管理、持仓增删改、实时盈亏计算 |
| **Watchlist** | 目标价预警、一键转为持仓 |
| **风险分析** | VaR (95%/99%)、Sharpe Ratio、最大回撤、相关性矩阵（属于后续章节内容） |
| **技术指标可视化** | SMA/Bollinger/RSI/MACD 图表（属于后续章节内容） |
| **12个月组合表现图** | Dashboard 展示组合价值 vs 成本基线 |

---

## 典型使用流程

1. **选股**：Screener 页 → 按行业/市值/P/E/股息率筛选 → 感兴趣的加入 Watchlist
2. **研究**：Stock Analysis 页 → 查看估值/盈利/负债/股息等100+指标 + 财务报表趋势 + 分析师评级 + 经济周期定位 + 同业对比
3. **对比**：Compare 页 → 2-6只候选股票归一化价格走势对比
4. **决策**：综合以上信息 → 在 Watchlist 设定目标价 → 达到目标后一键转为 Holdings
5. **监控**：Dashboard 查看组合表现 → Risk 页监控风险敞口

---

## 总结

**第2章和第3章的核心概念已全部实现**：财务三表、行业分类、市值分类、估值/流动性/负债/盈利/股息比率、ESG、分析师评级、yfinance数据获取、收益率统计、标准化对比、Stock Screener、新闻情感——并以可视化 Web 应用的形式呈现。
