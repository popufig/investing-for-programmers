# Chapter 5 功能差距分析：Income Portfolios

## 背景

书籍《Investing for Programmers》第5章主题是 **Income Portfolios（收入型投资组合）**，涵盖三大被动收入策略：股息、债券、财务自由计算。根目录 `ch05.ipynb` 包含配套代码实现（Listing 5.1 / 5.2 等）。

当前 InvestIQ app 主要面向成长/价值投资（对应前几章），第5章的收入型投资功能大部分缺失。

> **范围说明**：第5.3节加密货币质押部分不纳入本次实现范围。

---

## 功能差距总览

| # | 功能 | 书中章节 | App 现状 | 优先级 |
|---|------|----------|----------|--------|
| 1A | 股息增长率 CAGR | 5.1 Listing 5.1 | 无 | **高** |
| 1B | 派息频率检测 | 5.1 Listing 5.1 | 无 | 中 |
| 1C | 股息筛选器增强 | 5.1 Listing 5.2 | 部分（仅有 yield 过滤） | **高** |
| 1D | 股息历史图表 | 5.1 | 无 | 中 |
| 1E | REIT 识别标记 | 5.1 sidebar | 无 | 低 |
| 1F | 组合股息收入汇总 | 5.1 + 5.4 | 无 | **高** |
| 2A | 国际债券收益率（EODHD） | 5.2 | 部分（FRED 仅有美国国债） | 中 |
| 2B | 债券 ISIN 查询（OpenFIGI） | 5.2 | 无 | 低 |
| 2C | 债券评级参考 | 5.2 Table 5.1 | 无 | 低 |
| 2D | 股息 vs 债券收益率比较 | 5.1 + 5.2 | 无 | 中 |
| 4A | 财务自由/FIRE 计算器 | 5.4 | 无 | **高** |
| 4B | 收入 vs 支出追踪 | 5.4 | 无 | 中 |

---

## 跨功能依赖：币种处理策略

多个功能涉及跨币种计算，在此统一定义口径：

**现有基础设施**（`market_data.py`）：
- `get_fx_to_usd(currency)` — 通过 yfinance 免费获取实时汇率（如 `EURUSD=X`），带 5 分钟缓存，失败时回退到硬编码汇率（`FX_FALLBACK_TO_USD` 覆盖 19 种货币）
- `get_ticker_info()` 已返回 `fx_to_usd` 和 `currency` 字段
- `Holding` 模型已有 `currency` 字段（默认 "USD"）

**本次功能的币种规则**：

**币种范围**：当前持仓以 HKD 和 USD 为主。`get_fx_to_usd()` 已覆盖 19 种常见货币，未覆盖的币种会返回 None 并进入 `fx_warnings`，如需支持需补充映射。

**核心原则**：单个持仓的所有计算（盈亏、股息收入、市值）均在原始币种下完成，**仅在 Dashboard 汇总层面做 USD 折算**。

| 场景 | 规则 |
|------|------|
| 单个持仓盈亏（gain/loss） | **不做汇率折算**，在持仓原始币种下计算 `(current_price - avg_price) × shares`，前端显示币种标记 |
| 单个持仓股息收入 | **不做汇率折算**，在原始币种下计算 `shares × dividend_rate`，前端显示币种标记 |
| 单个持仓市值 | **不做汇率折算**，`current_price × shares`，原始币种 |
| Dashboard 汇总总市值 | **本次新增** `total_value_usd` 字段到 `/api/portfolio/summary`：对每个持仓的原始币种市值做 `× get_fx_to_usd(currency)` 后求和 |
| Dashboard 汇总总盈亏 | **本次新增** `total_gain_loss_usd` 字段：对每个持仓的原始币种盈亏做 USD 折算后求和 |
| Dashboard 汇总股息收入（1F） | `annual_dividend_income_usd`：对每个持仓原始币种股息收入做 USD 折算后求和 |
| FIRE 计算器（4A）组合总值 | 读取 `total_value_usd` |
| `dividend_rate` 缺失时 | 从 yfinance `trailingAnnualDividendRate` 取值；若仍为空则该持仓股息收入计为 0，不做估算 |
| 非派息资产（ETF/BOND/FUND 无 dividend_rate） | 股息收入计为 0，不影响汇总 |

---

## 一、股息分析（Dividends）— 第5.1节

### 1A. 股息增长率 CAGR [高优先级]

**书中内容**：ch05 的 `calc_div_growth_rate()` 函数（Listing 5.1）计算股息的复合年增长率（CAGR）。公式为 `((最后一年股息 / 第一年股息) ^ (1 / 年数)) - 1`。

**使用场景**：投资者比较两只股息股票时，仅看当前收益率不够。例如 KO（可口可乐）2% yield + 15% CAGR 可能优于某只 4% yield + 0% CAGR 的股票，因为前者的股息在快速增长。股息投资者用 CAGR 判断"这只股票的股息在增长还是停滞"。

**App 现状**：StockAnalysis 页面仅显示 dividend yield、dividend rate、payout ratio 三个静态指标，无历史增长率计算。

**预期实现**：
- 后端：`market_data.py` 新增 `get_dividend_analysis(ticker)` 函数，使用 `yf.Ticker(ticker).dividends` 按年聚合并计算 CAGR
- 后端：`stocks.py` 新增 `GET /api/stocks/{ticker}/dividends` 端点
- 前端：StockAnalysis 页面扩展股息区域，显示 CAGR 数值和趋势指标

**API 返回结构**：
```json
{
  "ticker": "KO",
  "dividend_cagr": 0.034,
  "payout_frequency": "Quarterly",
  "consecutive_growth_years": 62,
  "annual_dividends": [
    {"year": 2019, "total": 1.60},
    {"year": 2020, "total": 1.64},
    ...
  ],
  "current_dividend_rate": 1.94,
  "current_yield": 0.0285,
  "payout_ratio": 0.72
}
```

---

### 1B. 派息频率检测 [中优先级]

**书中内容**：ch05 同一函数按年均派息次数分类：季度(>3.5次)、半年(>1.5次)、年度(>0.5次)、不规律(<0.5次)。

**使用场景**：现金流规划。构建收入组合的投资者需要知道股息何时到账。季度派息者提供更平稳的收入流，月度派息者（如某些 REITs）更适合替代工资。投资者可以组合不同频率的股票来平滑全年现金流。

**App 现状**：完全没有派息频率信息。

**预期实现**：与 1A 同一端点返回 `payout_frequency` 字段（见上方 API 结构）。

---

### 1C. 股息筛选器增强 [高优先级]

**书中内容**：ch05 的 `get_stocks_with_dividends_and_high_market_cap()` 函数（Listing 5.2）扫描 S&P 500，按 dividend yield + market cap 阈值过滤，并收集完整股息指标：dividend yield, sector, payout ratio, dividend rate, CAGR, payout frequency。

**使用场景**：系统性发现股息股票。投资者想找"市值大于 2000 亿、股息 CAGR > 5%、派息率 < 60%"的股票。这是 ch05 Listing 5.2 的核心功能——不是一只只手动查，而是批量扫描筛选。

**App 现状**：Screener 有 `dividend_yield_min` 过滤器，但结果表中无 CAGR、派息频率、派息率、dividend rate 等股息相关列。无法按 payout ratio 或 CAGR 过滤。

**预期实现**：

后端新增过滤器（`stocks.py` screen 端点 + `market_data.py` screen_stocks）：
| 过滤器 | 参数名 | 类型 | 说明 |
|--------|--------|------|------|
| 派息率上限 | `payout_ratio_max` | float | 如 0.6 表示 ≤ 60% |
| 股息 CAGR 下限 | `dividend_cagr_min` | float | 如 0.05 表示 ≥ 5% |
| 派息频率 | `payout_frequency` | string | 可选值：Quarterly, Semi-Annual, Annual |

后端 `get_screener_snapshot()` 结果新增字段：
| 字段 | 来源 |
|------|------|
| `dividend_rate` | yfinance `dividendRate` 或 `trailingAnnualDividendRate` |
| `payout_ratio` | yfinance `payoutRatio` |
| `dividend_cagr` | 复用 1A 的 `get_dividend_analysis()` |
| `payout_frequency` | 复用 1A 的 `get_dividend_analysis()` |

前端 Screener 结果表新增列：Div Rate, Payout Ratio, CAGR, Frequency。

> **缓存与过滤策略**：CAGR 计算需逐只获取历史股息，对 100+ 只 screener universe 全量计算较慢。采用 **预计算+缓存** 方案：
>
> - 后端维护 screener universe 的股息指标缓存（TTL 24h），首次 screener 访问或 universe 变更时触发后台批量计算
> - **缓存就绪时**：`dividend_cagr_min`、`payout_frequency` 过滤器正常生效，结果表 CAGR/Frequency 列正常显示
> - **缓存未就绪时（cache cold）**：`dividend_cagr_min` 和 `payout_frequency` 过滤器 **禁用**（前端灰置，后端忽略该参数），基本结果（yield、payout_ratio 等无需历史数据的字段）正常返回，CAGR/Frequency 列显示 loading 占位符
> - `payout_ratio_max` 过滤器不依赖历史数据，始终可用
> - API response 包含：
>   - `dividend_cache_ready: bool` — 前端据此决定过滤器和列的启用/禁用状态
>   - `applied_filters: list[str]` — 实际生效的过滤器名称列表（如 `["sector", "payout_ratio_max"]`），非前端调用者可据此判断哪些过滤参数被忽略
>   - `ignored_filters: list[str]` — 因缓存未就绪而被忽略的过滤器名称列表（如 `["dividend_cagr_min", "payout_frequency"]`）

---

### 1D. 股息历史图表 [中优先级]

**书中内容**：第5章强调"dividend growth"——连续多少年增加股息（如可口可乐 62 年连续增长）。

**使用场景**：投资者需要直观看到股息支付的历史轨迹——上升（健康，适合买入）、持平（成熟，稳定收入）、或下降（警告信号）。这比单一 CAGR 数字提供更丰富的信息。

**App 现状**：无任何股息历史可视化。

**预期实现**：
- 后端：1A 端点的 `annual_dividends` 数组已包含所需数据
- 前端：StockAnalysis 新增 `DividendHistory` 图表组件（Recharts BarChart，x轴=年份，y轴=年度股息总额），复用现有图表样式

---

### 1E. REIT 识别标记 [低优先级]

**书中内容**：第5.1节 sidebar 介绍 REITs（不动产投资信托）——法定要求将至少 90% 的应税收入作为股息分配。

**使用场景**：REITs 的高收益率是法律要求而非公司健康问题信号。筛选股息股时，REITs 需要特殊对待——不能用和普通公司相同的 payout ratio 标准去评判。

**App 现状**：无 REIT 概念。

**识别方案**：
> ~~利用 yfinance 的 `quoteType` 字段~~ — **不可靠**。yfinance 对 REIT 的 `quoteType` 通常返回 `EQUITY`，无法区分。

改用 **sector + industry 组合识别**：yfinance `info` 中 `sector == "Real Estate"` 且 `industry` 包含 "REIT" 关键词（如 "REIT—Diversified", "REIT—Residential" 等）。这与 Screener 已有的 sector/industry 字段一致，无需新增数据源。

**预期实现**：
- 后端：`get_screener_snapshot()` 中根据 sector+industry 添加 `is_reit: bool` 标记
- 前端：Screener 结果表中对 REIT 显示标签徽章，可选 `is_reit` 过滤器

---

### 1F. 组合股息收入汇总 [高优先级]

**书中内容**：第5章的核心主张——通过被动收入实现财务自由。第5.4节的计算公式以"被动收入"为核心。

**使用场景**：收入投资者最关心的问题："我的组合每年能产生多少被动收入？"。当前 Dashboard 显示总市值、成本、盈亏，但对收入投资者来说，最重要的数字是 **年度股息收入**。例如：持有 100 股 KO × $1.94 dividend rate = $194/年。所有持仓加总即为组合的年度股息收入。

**App 现状**：Dashboard 完全没有被动收入信息。

**计算口径**（遵循"单个持仓原始币种，仅汇总做 USD 折算"原则）：

```
单只持仓年度股息收入 = shares × dividend_rate     （原始币种，不折算）
Dashboard 汇总股息收入（USD）= Σ (每个持仓股息收入 × get_fx_to_usd(currency))
```

**边界情况处理**：
| 情况 | 处理方式 |
|------|----------|
| `dividend_rate` 为 null | 尝试 yfinance `trailingAnnualDividendRate`；仍为空则该持仓收入计为 0 |
| 非派息资产（growth stock, BOND, FUND） | 股息收入计为 0，正常参与汇总 |
| 跨币种折算 | 仅在汇总时使用 `get_fx_to_usd()`，失败时该持仓加入 `fx_warnings` |
| 汇率来源 | 复用现有 `get_fx_to_usd()`，通过 yfinance 免费获取（如 `EURUSD=X`），5 分钟缓存，fallback 到硬编码汇率 |

**预期实现**：
- 后端：增强 `/api/portfolio/summary` 端点（`portfolio.py`），批量获取所有持仓的 `dividend_rate` 和 `fx_to_usd`（通过 `get_ticker_info` 或新增轻量 batch 函数），计算并返回以下新增字段：
  - `total_value_usd`: float — 组合总市值（各持仓原始币种市值 × fx_to_usd 后求和），供 Dashboard 和 4A 使用
  - `total_gain_loss_usd`: float — 组合总盈亏（各持仓原始币种盈亏 × fx_to_usd 后求和）
  - `annual_dividend_income_usd`: float — 组合总年度股息收入（各持仓原始币种股息 × fx_to_usd 后求和）
  - `dividend_income_by_holding`: list — 每个持仓的 `{ticker, shares, dividend_rate, currency, annual_income_native, fx_rate}`
  - `fx_warnings`: list — 汇率不可用的持仓 ticker 列表（空数组表示全部正常）
- 前端：Dashboard 新增 "Annual Dividend Income" StatCard + 可展开的按持仓分解明细

---

## 二、债券分析（Bonds）— 第5.2节

### 2A. 国际债券收益率（EODHD）[中优先级]

**书中内容**：ch05 使用 `fetch("US10Y")` 通过 EODHD API 获取国债收益率历史数据并绘制走势图。

**使用场景**：投资者判断当前债券收益率相对于历史水平是否有吸引力。也用于比较不同国家的债券收益率（美国 vs 德国 vs 日本）。

**App 现状**：FredRateChart 组件已有美国国债收益率（DGS10, DGS2），但 FRED 仅覆盖美国数据。`.env_template` 已有 `datasource.eod.key` 占位符。

**预期实现**：
- 后端：`market_data.py` 新增 EODHD API 调用，支持国际债券收益率查询
- 前端：扩展 FredRateChart 或新建 BondYields 组件，添加国家选择器

---

### 2B. 债券 ISIN 查询（OpenFIGI）[低优先级]

**书中内容**：ch05 演示使用 OpenFIGI API 将 ISIN 代码（如 `US36166NAJ28`）映射为标准化金融工具标识符。

**使用场景**：投资者从券商账单或募集说明书中获得 ISIN 编号，通过查询获取债券的发行方、证券类型、市场等元数据。

**App 现状**：无。`.env_template` 已有 `datasource.figi.key` 占位符。

**预期实现**：新 API 端点 `GET /api/bonds/lookup?isin=xxx` + 前端查询界面。

---

### 2C. 债券评级参考 [低优先级]

**书中内容**：Table 5.1 列出 Moody's/S&P/Fitch 评级量表（Aaa/AAA 到 D），区分投资级和投机级。

**使用场景**：投资者评估债券时理解 Baa2 或 BB+ 在违约风险方面意味着什么。

**预期实现**：静态参考内容（信息提示或参考页面），实现成本很低。

---

### 2D. 股息 vs 债券收益率比较 [中优先级]

**书中内容**：第5章的核心对比——同样是固定收入，股息和债券各有优劣。

**使用场景**：投资者面临选择："买 KO 股票获得 2.85% 的股息率，还是买 10 年期国债获得 4.5%？"。需要并排看到：当前股票股息率 vs 当前国债收益率 vs 历史趋势对比。第5章明确讨论了何时债券优于股息股票。

**App 现状**：StockAnalysis 显示股息率，FredRateChart 显示国债率，但两者完全独立，无对比视图。

**预期实现**：
- StockAnalysis 页面或独立比较小部件，结合 FRED 国债数据 + 股票股息数据，并排可视化

---

## 三、财务自由计算器（Financial Independence）— 第5.4节

### 4A. FIRE 计算器 [高优先级]

**书中内容**：核心公式 `所需资金 = 年度支出 / 预期回报率`。以 5% 预期回报为例，年支出 $50,000 需要 $1,000,000 的投资组合。还讨论了通胀影响（美国 1975-2024 平均 3.5%）和基于年龄的策略调整。

**使用场景**：这是第5章的"终极问题"——"我需要多少钱才能实现财务自由？"以及"我距离目标还有多远？"。它将所有收入概念（股息、债券）连接到个人的财务目标。这是一个有强烈交互性的工具页面。

**输入参数**：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 年度支出 | 无（必填） | 用户手动输入 |
| 每月定投额 | 0 | 用户手动输入，用于计算达标年数 |
| 预期投资回报率 | 5% | 滑动条或输入框 |
| 通胀率 | 3.5% | 滑动条或输入框 |
| 当前投资组合总价值 | 自动获取（见下方说明） | 可手动覆盖 |
| 当前年龄 | 无（必填） | 用户手动输入 |
| 目标退休年龄 | 无（选填） | 用于展示时间维度，同时推导反向计算的目标年限 Y = 目标退休年龄 - 当前年龄 |

**组合总价值自动获取逻辑**：
- 读取 `/api/portfolio/summary` 返回的 **`total_value_usd`** 字段（1F 新增，见上文）
- 若 `fx_warnings` 非空，显示警告："部分持仓（XX、YY）汇率不可用，总值可能不完整，建议手动校正"
- 用户可随时手动覆盖自动填充值

**输出**：
- 所需投资组合规模（考虑通胀调整）
- 距离目标还差多少
- 达标所需年数：基于当前组合 + 每月定投 + 复利增长
- 每月所需储蓄额（反向计算）：给定目标年限，需要多少月定投才能达标
- 成长型 vs 收入型策略对比（ch05 5.4 明确比较了 VOO 192.20% 回报 vs 收入型组合）

**核心公式**：

```
令 real_return = 回报率 - 通胀率

1. 所需资金 (FI Number)
   当 real_return > 0 时：  FI = 年度支出 / real_return
   当 real_return ≤ 0 时：  提示"回报率需高于通胀率"，不计算

令 r = real_return / 12（月实际回报率）
    P = 当前组合价值（total_value_usd）
    FV = FI（目标资金）
    M = 每月定投额

2. 达标年数（正向：已知 M，求年数 N）
   当 r > 0 时：
     月数 n = log((FV × r + M) / (P × r + M)) / log(1 + r)
     年数 N = n / 12
   当 r = 0 时（线性退化）：
     月数 n = (FV - P) / M          （需 M > 0，否则提示"无法达标"）
     年数 N = n / 12

3. 每月所需定投额（反向：已知目标年限 Y，求 M）
   Y = 目标退休年龄 - 当前年龄（需已填写目标退休年龄，否则此项不展示）
   令 n = Y × 12
   当 r > 0 时：
     M = (FV - P × (1 + r)^n) × r / ((1 + r)^n - 1)
   当 r = 0 时：
     M = (FV - P) / n

4. 边界保护
   - 当 P ≥ FV：显示"已达标"
   - 当 M < 0（反向计算结果为负，即复利已足够）：显示"已达标，无需额外定投"
   - 当 r = 0 且 M = 0 且 P < FV：显示"无法达标，需设定每月定投额"
   - 当 Y ≤ 0（目标退休年龄 ≤ 当前年龄）：反向计算项不展示，提示"目标退休年龄需大于当前年龄"
```

**预期实现**：
- 前端：新页面 `/independence`，纯前端计算逻辑（上述公式全部在前端 JS 实现）
- 后端：复用 `/api/portfolio/summary` 的 `total_value_usd` 和 `fx_warnings` 字段（1F 中新增）
- 路由：`App.jsx` 添加导航项

---

### 4B. 收入 vs 支出追踪 [中优先级]

**书中内容**：第5.4节将被动收入与年度支出关联。

**使用场景**：将组合的实际被动收入（来自 1F 的股息汇总 + 债券利息）与用户设定的年度支出比较。显示"财务自由进度"：例如 "组合年产 $12,000 被动收入 / $50,000 年支出 = 24% 覆盖率"。

**预期实现**：Dashboard 进度条或 FIRE 页面内的实时追踪小部件，依赖 1F 的数据。

---

## 建议实现顺序

### 第一批（高优先级，核心功能）
1. **GAP 1A + 1B** — 股息 CAGR + 派息频率（一个后端函数 + 一个端点 + 前端展示，直接对应 Listing 5.1）
2. **GAP 1F** — 组合股息收入汇总（扩展现有 Dashboard，让收入投资者立刻看到价值）
3. **GAP 1C** — 股息筛选器增强（扩展现有 Screener，对应 Listing 5.2）
4. **GAP 4A** — FIRE 计算器（新页面，主要是前端逻辑，是第5章的"灵魂"功能）

### 第二批（中优先级，增强功能）
5. **GAP 2D** — 股息 vs 债券收益率比较（利用现有 FRED 数据 + 新股息数据）
6. **GAP 1D** — 股息历史图表（可视化增强）
7. **GAP 2A** — 国际债券收益率 EODHD 集成（需要 API key）
8. **GAP 4B** — 收入 vs 支出追踪（依赖 1F 完成）

### 第三批（低优先级，锦上添花）
9. **GAP 2B** — 债券 ISIN 查询
10. **GAP 2C** — 债券评级参考
11. **GAP 1E** — REIT 识别

---

## 涉及的关键文件

| 文件 | 改动类型 |
|------|----------|
| `app/backend/services/market_data.py` | 新增 `get_dividend_analysis()` 函数；增强 `get_screener_snapshot()` 添加股息字段；增强 `screen_stocks()` 添加 CAGR/payout 过滤器 |
| `app/backend/routers/stocks.py` | 新增 `GET /api/stocks/{ticker}/dividends` 端点；screen 端点添加 `dividend_cagr_min`, `payout_ratio_max`, `payout_frequency` 参数 |
| `app/backend/routers/portfolio.py` | 扩展 summary 端点，添加股息收入计算（含跨币种 USD 折算） |
| `app/backend/schemas.py` | 新增 dividend analysis response schema；扩展 portfolio summary schema 添加 dividend income 字段 |
| `app/frontend/src/pages/StockAnalysis.jsx` | 扩展股息分析区域（CAGR、频率、连续增长年数） |
| `app/frontend/src/components/DividendHistory.jsx` | **新建** 股息历史柱状图组件 |
| `app/frontend/src/pages/Dashboard.jsx` | 新增 "Annual Dividend Income" StatCard + 分项明细 |
| `app/frontend/src/pages/Screener.jsx` | 新增股息列（Div Rate, Payout Ratio, CAGR, Frequency）和过滤条件 |
| `app/frontend/src/pages/Independence.jsx` | **新建** FIRE 计算器页面 |
| `app/frontend/src/utils/format.js` | 增强货币格式化：支持按 holding currency 显示符号（当前硬编码 `$`），新增 `formatCurrency(value, currencyCode)` |
| `app/frontend/src/api/client.js` | 新增 `getDividendAnalysis(ticker)` 调用；screener API 添加新过滤参数 |
| `app/frontend/src/App.jsx` | 添加 `/independence` 页面路由和导航项 |

---

## 验收标准

> 以下覆盖第一批（高优先级）+ 1E。第二批（2D/1D/2A/4B）和第三批（2B/2C）的验收标准在对应功能开发前补充。

### 1A + 1B: 股息 CAGR + 派息频率
- [ ] `GET /api/stocks/KO/dividends` 返回 CAGR ≈ 3-5%，frequency = "Quarterly"，consecutive_growth_years > 50
- [ ] `GET /api/stocks/MSFT/dividends` 返回有效数据
- [ ] 无股息股票（如 BRK-B）返回 `dividend_cagr: null, payout_frequency: null`
- [ ] StockAnalysis 页面正确展示新指标
- [ ] 非 USD 股票（如港股）返回数据正常，股息金额为原始币种

### 1F: 组合股息收入汇总
- [ ] `/api/portfolio/summary` 返回 `annual_dividend_income_usd` 和 `dividend_income_by_holding`
- [ ] 非 USD 持仓的 `fx_rate` 正确（如 HKD 持仓，汇率 ≈ 0.128）
- [ ] 无股息的持仓 `annual_income_native = 0`，不影响汇总
- [ ] `dividend_rate` 为空时 fallback 到 `trailingAnnualDividendRate`，仍为空则收入 = 0
- [ ] Dashboard 显示 "Annual Dividend Income" 卡片，金额带 USD 标记
- [ ] 分项明细中每个持仓显示原始币种金额 + USD 折算金额

### 1C: 股息筛选器增强
- [ ] Screener 结果表包含 Div Rate, Payout Ratio, CAGR, Frequency 列
- [ ] `payout_ratio_max=0.6` 过滤有效（排除高派息率股票）— 此过滤器始终可用
- [ ] **缓存就绪时**：`dividend_cagr_min=0.05` 过滤有效（仅显示 CAGR >= 5%）；`payout_frequency=Quarterly` 过滤有效
- [ ] **缓存未就绪时**：`dividend_cagr_min` 和 `payout_frequency` 过滤器前端灰置不可用；CAGR/Frequency 列显示 loading；基本结果正常返回
- [ ] API response 包含 `dividend_cache_ready: bool`，前端据此切换过滤器状态
- [ ] **缓存未就绪时**：API response 的 `ignored_filters` 包含被忽略的参数名（如 `["dividend_cagr_min"]`），`applied_filters` 仅包含实际生效的过滤器
- [ ] **缓存就绪时**：`ignored_filters` 为空数组，`applied_filters` 包含所有传入的过滤器

### 4A: FIRE 计算器
- [ ] 输入年支出 50000、回报率 5%、通胀率 0% → 所需资金 = $1,000,000
- [ ] 输入年支出 50000、回报率 5%、通胀率 3.5% → 所需资金 = $3,333,333（= 50000 / 0.015）
- [ ] 回报率 ≤ 通胀率时，提示"回报率需高于通胀率"，不显示无穷大
- [ ] 回报率 = 通胀率（r=0）且定投 > 0 时，达标年数使用线性公式 `(FV - P) / M / 12`
- [ ] 回报率 = 通胀率且定投 = 0 且未达标时，提示"无法达标，需设定每月定投额"
- [ ] 每月定投额 = 0 时，仅基于现有组合 + 复利计算达标年数
- [ ] 每月定投额 > 0 时，达标年数正确缩短
- [ ] 反向计算：给定目标年限 20 年，正确算出每月所需定投额
- [ ] 当前组合 ≥ 目标时，显示"已达标"
- [ ] 组合总价值自动读取 portfolio summary 的 `total_value_usd` 字段，可手动覆盖
- [ ] 若 `fx_warnings` 非空，显示汇率警告并允许手动校正

### 1E: REIT 识别
- [ ] 已知 REIT（如 O, VNQ 成分股）被正确识别为 `is_reit: true`
- [ ] 识别基于 `sector == "Real Estate"` + `industry` 包含 "REIT"，不依赖 `quoteType`

---

## 参考代码

- `ch05.ipynb` — Listing 5.1 (`calc_div_growth_rate`)、Listing 5.2 (`get_stocks_with_dividends_and_high_market_cap`)、EODHD fetch、OpenFIGI 调用
- `app/backend/services/market_data.py` 中已有的 `get_fx_to_usd()`、`FX_TICKERS`、`FX_FALLBACK_TO_USD` — FX 基础设施
