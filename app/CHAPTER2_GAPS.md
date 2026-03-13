# Chapter 2 Implementation Gaps (v1.5)

> 参考：*Investing for Programmers* Ch.2 — Investment Essentials
> 本文档列出第二章尚未在系统中实现的功能，供代码审查和后续开发使用。
>
> **书籍文件路径：** `doc/Investing_for_Programmers_epub/OEBPS/Text/chapter-2.html`
> 用浏览器直接打开该文件，在 URL 末尾加锚点即可跳转到对应小节，例如：
> `file:///…/chapter-2.html#p19`
>
> | 锚点 | 小节 | 标题 |
> |------|------|------|
> | `#p8`   | 2.1   | Accounting in a nutshell |
> | `#p19`  | 2.1.1 | Income statement |
> | `#p47`  | 2.1.2 | Balance sheet |
> | `#p57`  | 2.1.3 | Free cash flow |
> | `#p69`  | 2.2   | Industry classification |
> | `#p74`  | 2.2.1 | Influences on GICS sectors |
> | `#p81`  | 2.2.2 | Sectors and economic cycles |
> | `#p90`  | 2.3   | Capitalization |
> | `#p103` | 2.4   | Metrics and ratios |
> | `#p112` | 2.4.1 | Liquidity |
> | `#p122` | 2.4.2 | Debt |
> | `#p128` | 2.4.3 | Earnings |
> | `#p137` | 2.4.4 | Valuation |
> | `#p157` | 2.4.5 | Profitability |
> | `#p162` | 2.4.6 | Dividends |
> | `#p186` | 2.4.7 | Ownership |
> | `#p200` | 2.4.8 | Sustainability (ESG) |
> | `#p206` | 2.5   | External assessments |
> | `#p211` | 2.5.1 | Ratings |
> | `#p220` | 2.5.2 | Target prices |

---

## 当前状态总结

| 章节 | 内容 | 状态 |
|------|------|------|
| 2.1 Income Statement | 财务数据多季度趋势 | ✅ 已实现 |
| 2.1 Balance Sheet | 资产负债趋势 | ✅ 已实现 |
| 2.1 Free Cash Flow | FCF 趋势 | ✅ 已实现 |
| 2.2 GICS Sector | 行业分类展示 | ✅ 已实现（含 sector/industry） |
| 2.2 Peer Comparison | 同行业横向对比 | ✅ 已实现（用户输入 + `peer_group` 表 + 自动推荐） |
| 2.2 Economic Cycle | 板块与经济周期 | ✅ 已实现（市场代理信号 + 板块周期框架） |
| 2.3 Market Cap | 市值分类标签 | ✅ 已实现（StockAnalysis + Holdings） |
| 2.4 Metrics | 所有财务比率 | ✅ 已实现 |
| 2.4 ESG | ESG 评分 | ✅ 已实现 |
| 2.5 Analyst Ratings | 评级分布图 | ✅ 已实现 |
| 2.5 Upgrades/Downgrades | 近期评级变动 | ✅ 已实现 |

---

## GAP 1：财务报表多季度趋势（2.1）

> 📖 **书籍参考：** `chapter-2.html#p19`（2.1.1 Income statement）· `#p47`（2.1.2 Balance sheet）· `#p57`（2.1.3 Free cash flow）

### 目标
在 StockAnalysis 页中展示最近 5~8 个季度的财务报表趋势，帮助用户判断公司发展方向（第 2.1 节的核心）：收入是否增长？研发支出是否上升？现金流是否健康？

### 数据来源
yfinance 提供以下接口（多数字段可得，但部分 ticker 或季度可能缺失个别字段，需做 `None` 兜底）：

```python
t = yf.Ticker("AAPL")
t.quarterly_income_stmt    # 季度损益表
t.quarterly_balance_sheet  # 季度资产负债表
t.quarterly_cashflow       # 季度现金流量表
```

### 需要提取的字段

**损益表（Income Statement）**
| yfinance 字段 | 显示名称 | 说明 |
|--------------|----------|------|
| `Total Revenue` | 营业收入 | 核心成长指标 |
| `Gross Profit` | 毛利润 | |
| `Operating Income` | 营业利润 | |
| `Net Income` | 净利润 | |
| `Research And Development` | 研发支出 | 判断成长投入 |
| `EBITDA` | EBITDA | |
| `Diluted EPS` | 摊薄每股收益 | |

**资产负债表（Balance Sheet）**
| yfinance 字段 | 显示名称 |
|--------------|----------|
| `Total Assets` | 总资产 |
| `Total Liabilities Net Minority Interest` | 总负债 |
| `Stockholders Equity` | 股东权益 |
| `Total Debt` | 总债务 |
| `Cash And Cash Equivalents` | 现金及等价物 |
| `Working Capital` | 营运资金 |

**现金流量表（Cash Flow）**
| yfinance 字段 | 显示名称 |
|--------------|----------|
| `Operating Cash Flow` | 经营现金流 |
| `Capital Expenditure` | 资本支出（负值）|
| `Free Cash Flow` | 自由现金流 |

### 后端改动

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/{ticker}/financials
```

返回格式：
```json
{
  "ticker": "AAPL",
  "income_statement": [
    {
      "period": "2024-Q4",
      "period_end": "2024-12-28",
      "total_revenue": 124300000000,
      "gross_profit": 57045000000,
      "operating_income": 34530000000,
      "net_income": 29000000000,
      "research_and_development": 8000000000,
      "ebitda": 38000000000,
      "diluted_eps": 1.89
    }
  ],
  "balance_sheet": [
    {
      "period": "2024-Q4",
      "period_end": "2024-12-28",
      "total_assets": 364840000000,
      "total_liabilities": 308030000000,
      "stockholders_equity": 56810000000,
      "total_debt": 104590000000,
      "cash": 29943000000,
      "working_capital": -15000000000
    }
  ],
  "cash_flow": [
    {
      "period": "2024-Q4",
      "period_end": "2024-12-28",
      "operating_cash_flow": 26814000000,
      "capital_expenditure": -2908000000,
      "free_cash_flow": 23906000000
    }
  ]
}
```

**实现要点：**
- 季度列名是 `Timestamp` 对象，需转换为展示标签 `"YYYY-QN"`（`period` 字段），同时保留原始日期 `"YYYY-MM-DD"`（`period_end` 字段）。注意：`period` 标签基于公司财年（`fiscalYearEnd`），不一定对应自然年季度
- 数值可能为 `NaN`，需用 `None` 替换
- 返回最近 8 个季度（即最多 8 列）
- 建议加入 5 分钟缓存（与 `get_ticker_info` 一致）

**文件：`backend/services/market_data.py`**

新增函数 `get_financials(ticker: str) -> dict`，负责数据提取和格式转换。

### 前端改动

**文件：`frontend/src/pages/StockAnalysis.jsx`**

在股票详情页末尾新增 `FinancialStatements` 组件，包含三个 Tab：
- **Income** — 营收、毛利、净利、研发费用的柱状图（`BarChart`）
- **Balance Sheet** — 资产/负债/权益堆叠面积图（`AreaChart`）
- **Cash Flow** — 经营现金流 vs FCF 柱状图

每个图表的 X 轴为季度（`2024-Q1`, `2024-Q2`...），数值格式化为 `$1.2B`。

**新文件：`frontend/src/components/FinancialStatements.jsx`**

建议组件接口：
```jsx
<FinancialStatements ticker="AAPL" />
// 内部自行调用 GET /api/stocks/AAPL/financials
```

---

## GAP 2：同行业横向对比（2.2 Peer Comparison）

> 📖 **书籍参考：** `chapter-2.html#p69`（2.2 Industry classification）· `#p74`（2.2.1 Influences on GICS sectors）· `#p81`（2.2.2 Sectors and economic cycles）

### 目标
书中第 2.2 节强调：**只有同行业比较才有意义**（苹果的研发支出不能和沃尔玛比）。需要展示同一 GICS 板块内，目标股票与 3~5 个主要竞争对手的关键指标对比。

### 数据来源
yfinance `info` 字段中包含：
- `sector` / `industry` — GICS 分类
- 所有财务比率（P/E、ROE、Margin 等）

竞争对手列表来源（按优先级）：
1. **用户手动输入** — 前端输入框指定对比 ticker
2. **`peer_group` 表** — 数据库存储默认对比组合，支持前端更新（`Save Default`）
3. **内置默认组** — 作为数据库为空时的兜底
4. **同行业自动推荐** — 按 `sector` + `industry` + 市值区间筛选，作为最后回退

> ⚠️ 不要使用 `t.recommendations`，该属性返回的是分析师评级记录，不是竞争对手列表。

### 后端改动

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/{ticker}/peers?tickers=MSFT,GOOGL,META
GET /api/stocks/{ticker}/peer-group
PUT /api/stocks/{ticker}/peer-group
```

**接口约定：**
- 路径中的 `{ticker}` 为主股票，**自动包含在返回结果中**（无需在 query 中重复）
- `tickers` 参数为逗号分隔的对比列表，去重后 **最多 5 个**（超出截断）
- 无效 ticker 跳过（不中断请求），跳过的 ticker 列入返回结果的 `skipped` 数组，便于联调排查
- 若 `tickers` 为空且数据库有预设 `peer_group`，使用预设列表；否则返回 `{"skipped": [], "peers": [仅主 ticker]}` 结构

返回格式：
```json
{
  "skipped": ["INVALID1"],
  "peers": [
  {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "market_cap": 2900000000000,
    "pe_ratio": 30.5,
    "pb_ratio": 47.2,
    "roe": 1.47,
    "net_margin": 0.26,
    "revenue_growth": 0.08,
    "dividend_yield": 0.006
  },
  { "ticker": "MSFT", ... },
  { "ticker": "GOOGL", ... }
  ]
}
```

### 前端改动

**文件：`frontend/src/pages/StockAnalysis.jsx`**

新增 `PeerComparison` 组件：
- 用户可输入 1~5 个对比 ticker
- 展示横向对比表格：每行一个 ticker，列为各财务指标
- 用颜色高亮最优值（绿色）和最差值（红色），**需定义每个指标的方向**：
- 若返回 `skipped` 非空，显示提示条（如：`Skipped: INVALID1, INVALID2`），便于联调定位输入问题

| 指标 | 方向 | 说明 |
|------|------|------|
| `revenue_growth` | 越高越好 | |
| `net_margin` | 越高越好 | |
| `roe` | 越高越好 | |
| `dividend_yield` | 越高越好 | |
| `pe_ratio` | 越低越好 | 高 P/E 可能高估 |
| `pb_ratio` | 越低越好 | |
| `market_cap` | 中性 | 不着色 |

**新文件：`frontend/src/components/PeerComparison.jsx`**

---

## GAP 3：市值分类标签（2.3）

> 📖 **书籍参考：** `chapter-2.html#p90`（2.3 Capitalization）

### 目标
将市值数字转换为有语义的分类标签（Large / Mid / Small / Micro Cap），并在 Holdings 表格和 StockAnalysis 页中展示。

### 规则
```
>= $200B   → Mega Cap
$10B–$200B → Large Cap
$2B–$10B   → Mid Cap
$300M–$2B  → Small Cap
< $300M    → Micro Cap
```

### 改动范围

#### 必做：StockAnalysis 页（纯前端，无后端改动）

`GET /api/stocks/{ticker}` 已返回 `market_cap` 与 `market_cap_usd` 字段（后者用于非 USD 资产换算后统一分档）。

**文件：`frontend/src/utils/format.js`**

新增工具函数：
```js
export const marketCapLabel = (marketCap) => {
  if (marketCap == null || !Number.isFinite(marketCap)) return null
  if (marketCap >= 200e9) return { label: 'Mega Cap', color: 'text-purple-400' }
  if (marketCap >= 10e9)  return { label: 'Large Cap', color: 'text-blue-400' }
  if (marketCap >= 2e9)   return { label: 'Mid Cap', color: 'text-teal-400' }
  if (marketCap >= 300e6) return { label: 'Small Cap', color: 'text-amber-400' }
  return { label: 'Micro Cap', color: 'text-red-400' }
}
```

**文件：`frontend/src/pages/StockAnalysis.jsx`**

在股票 Header 区域，紧靠 sector/industry 文字下方添加市值标签 badge。

#### 可选：Holdings 表格（需后端改动）

**文件：`frontend/src/pages/Holdings.jsx`**

在 Holdings 表格的 Name 列旁，对 STOCK 类型资产显示市值分类 badge。

**文件：`backend/routers/portfolio.py`**

需要在 `GET /api/portfolio/holdings` 的返回数据中补充 `market_cap` 字段（从 `get_ticker_info` 取值）。

> ⚠️ 建议先只做必做部分，可选部分在 GAP 2 同行对比完成后一并处理（减少排期误判）。

---

## GAP 4：分析师评级分布（2.5）

> 📖 **书籍参考：** `chapter-2.html#p211`（2.5.1 Ratings）· `#p220`（2.5.2 Target prices）

### 目标
书中 2.5.1 节强调不要只看单一评级结论，而要看**所有分析师的分布**（例如：41位分析师中，25人买入、10人持有、6人卖出）以及近期**评级变动（upgrades/downgrades）**趋势。

### 当前状态
当前只显示 `recommendationKey`（如 "buy"）这一个汇总结论。

### 数据来源
yfinance 提供以下接口（多数字段可得，个别 ticker 可能缺失部分字段）：
```python
t.info["recommendationMean"]        # 1.0(强买) ~ 5.0(强卖)
t.info["numberOfAnalystOpinions"]   # 分析师总数
t.upgrades_downgrades               # 近期每位分析师的评级变动 DataFrame
```

**评级分布来源（含回退逻辑）：**
1. 尝试读取 `t.recommendations`（DataFrame）
2. 检测列名是否包含 `strongBuy / buy / hold / sell / strongSell`（不同 yfinance 版本列名可能不同，需用 `col in df.columns` 逐一探测）
3. 若列名存在，优先取 `period == "0m"` 行；若无 `period` 列则取 `iloc[0]`（按 Yahoo 趋势表默认顺序视为最新），不要假设 `iloc[-1]` 为最新
4. 若 DataFrame 为空、列名不符、或抛异常，回退到仅返回 `recommendationMean` + `numberOfAnalystOpinions`，`rating_distribution` 设为 `null`

`upgrades_downgrades` 包含字段：
- `Firm` — 投行名称
- `ToGrade` — 最新评级
- `FromGrade` — 前次评级
- `Action` — up / down / main / init / reit
- `priorPriceTarget` — 前次目标价

### 后端改动

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/{ticker}/analyst
```

返回格式：
```json
{
  "ticker": "AAPL",
  "recommendation_mean": 1.9,
  "recommendation_key": "buy",
  "num_analysts": 41,
  "rating_distribution": {
    "strong_buy": 15,
    "buy": 10,
    "hold": 12,
    "sell": 3,
    "strong_sell": 1
  },
  "target_high": 350.0,
  "target_low": 205.0,
  "target_mean": 295.44,
  "current_price": 225.0,
  "upside_pct": 31.3,
  "recent_changes": [
    {
      "date": "2026-03-05",
      "firm": "Wedbush",
      "from_grade": "Outperform",
      "to_grade": "Outperform",
      "action": "main",
      "price_target": 350.0
    }
  ]
}
```

**文件：`backend/services/market_data.py`**

新增函数 `get_analyst_data(ticker: str) -> dict`。

### 前端改动

**文件：`frontend/src/pages/StockAnalysis.jsx`**

新增 `AnalystSection` 组件，展示：
1. **评级分布柱状图** — Strong Buy / Buy / Hold / Sell / Strong Sell 人数分布（若 `rating_distribution` 缺失则仅显示 `recommendation_mean` 指针）
2. 推荐评分量表（1=强买 → 5=强卖）的可视化进度条
3. 目标价区间（低/均/高 vs 当前价格）的范围条
4. 近期评级变动表格（最近 10 条：机构、变动方向、目标价）

**新文件：`frontend/src/components/AnalystSection.jsx`**

---

## GAP 5：ESG 评分（2.4.8）

> 📖 **书籍参考：** `chapter-2.html#p200`（2.4.8 Sustainability）

### 目标
书中 2.4.8 节将 ESG 作为"可持续性"指标，用于评估非财务风险。

### 数据来源
yfinance `t.sustainability` 返回一个包含 ESG 评分的 DataFrame：
- `totalEsg` — 总体 ESG 评分（越低越好，0~100）
- `environmentScore` — 环境分
- `socialScore` — 社会责任分
- `governanceScore` — 公司治理分
- `esgPerformance` — 相对同行表现（如 "AVG_PERF"）

注意：并非所有 ticker 都有 ESG 数据，需做 `None` 处理。

### 后端改动

**文件：`backend/routers/stocks.py`**

新增独立接口（不合并入 `/api/stocks/{ticker}`，避免增加主接口延迟和失败面）：
```
GET /api/stocks/{ticker}/esg
```

返回格式（统一 schema，始终包含 `available` 字段）：
```json
{
  "ticker": "AAPL",
  "available": true,
  "total_score": 15.3,
  "environment_score": 0.5,
  "social_score": 7.4,
  "governance_score": 7.4,
  "performance": "AVG_PERF"
}
```

无 ESG 数据时，其余字段为 `null`：
```json
{
  "ticker": "AAPL",
  "available": false,
  "total_score": null,
  "environment_score": null,
  "social_score": null,
  "governance_score": null,
  "performance": null
}
```

**文件：`backend/services/market_data.py`**

新增函数 `get_esg(ticker: str) -> dict`，调用 `t.sustainability`，独立 5 分钟缓存。

> ⚠️ `t.sustainability` 调用较慢且不稳定，单独接口便于前端懒加载和降级处理。

### 前端改动

**文件：`frontend/src/pages/StockAnalysis.jsx`**

在 Dividends & Risk 指标卡区域末尾，懒加载调用 `/api/stocks/{ticker}/esg`，如果数据可用则展示：
- `totalEsg` 分值 + RadialBar 可视化（低分绿色，高分红色）
- E / S / G 三项分值小标签
- 若接口返回 `available: false`，显示 "ESG data not available" 占位

---

## 接口变更汇总

| 方法 | 路径 | 状态 | 说明 |
|------|------|------|------|
| GET | `/api/stocks/{ticker}/financials` | **新增** | 季度三表趋势 |
| GET | `/api/stocks/{ticker}/peers` | **新增** | 同行横向对比 |
| GET | `/api/stocks/{ticker}/peer-group` | **新增** | 读取默认同行组（数据库） |
| PUT | `/api/stocks/{ticker}/peer-group` | **新增** | 更新默认同行组（数据库） |
| GET | `/api/stocks/{ticker}/analyst` | **新增** | 分析师评级详情 + 分布 |
| GET | `/api/stocks/{ticker}/esg` | **新增** | ESG 评分（独立接口） |
| GET | `/api/stocks/{ticker}/economic-cycle` | **新增** | 板块与经济周期框架 + 市场代理信号 |
| GET | `/api/portfolio/holdings` | **可选修改** | 补充每条持仓的 `market_cap` / `market_cap_usd` 字段（GAP 3 可选部分） |

> 注：`GET /api/stocks/{ticker}` 已返回 `market_cap` 与 `market_cap_usd`，无需额外改动该主接口。

---

## 建议实现顺序

1. **GAP 3 必做部分**（市值标签）— 最简单，纯前端改动：`format.js` 新增函数 + StockAnalysis Header badge
2. **GAP 5**（ESG）— 新增独立后端接口 + 前端懒加载展示，改动范围小
3. **GAP 4**（分析师评级分布）— 新增一个后端接口 + 一个前端组件，独立性强
4. **GAP 1**（财务报表趋势）— 工作量最大，但价值最高，建议拆分：先做 Income Statement，再做 Balance Sheet 和 Cash Flow
5. **GAP 2**（同行对比）— 依赖数据质量，建议最后做，先手动维护几组常见对比组合
6. **GAP 3 可选部分**（Holdings 市值标签）— 随 GAP 2 一并处理

---

## 注意事项

- **yfinance 稳定性**：`quarterly_income_stmt` 等接口偶尔返回空数据，所有调用需 `try/except` 保护
- **数值量级**：财务报表数据为原始值（单位：美元），前端显示需格式化（`$1.2B`，`$45.6M`）
- **NaN 处理**：pandas DataFrame 中的 `NaN` 不能序列化为 JSON，需在后端统一替换为 `None`
- **缓存**：相关接口（`/financials`、`/peers`、`/peer-group`、`/analyst`、`/esg`、`/economic-cycle`、`/portfolio/holdings` 可选扩展字段）建议统一使用现有的 5 分钟 TTL 缓存机制（`_get_cached` / `_set_cached`）
- **季度格式**：yfinance 返回的季度列名是 `Timestamp` 类型。API 需同时返回 `period`（展示标签 `"2024-Q4"`，基于公司财年）和 `period_end`（原始日期 `"2024-12-28"`），避免与自然年季度混淆

---

## 开放问题

1. **自动推荐质量** — 当前自动推荐基于行业与市值近似规则，后续可引入更稳定的同业图谱/指数成分数据源提升质量。

---

*文档版本：v1.5 | 更新日期：2026-03-12*
*v1.0 — 初版 (2026-03-11)*
*v1.1 — 根据 Review 反馈修订：修复 GAP 4 评级分布缺失、GAP 2 数据源错误、季度格式财年风险、ESG 独立接口、GAP 3 拆分必做/可选、peers 接口约定、指标方向配置、数据可得性表述 (2026-03-11)*
*v1.2 — 二次 Review 收口：评级分布字段探测回退逻辑、ESG 统一 schema、缓存描述修正、marketCapLabel 空值判断、peers 增加 skipped 字段 (2026-03-12)*
*v1.3 — 三次 Review 收口：修复 peers 契约文字不一致、评级分布“最新行”规则明确化、前端补充 skipped 展示要求 (2026-03-12)*
*v1.4 — 实装收口：新增 Economic Cycle 接口与前端模块、peers 自动推荐回退、非 USD 市值换算（`market_cap_usd`）、状态表回填 (2026-03-12)*
*v1.5 — `peer_group` 数据库接入：新增 PeerGroup 表、GET/PUT 管理接口、peers 查询优先读库、前端支持 Save Default (2026-03-12)*
