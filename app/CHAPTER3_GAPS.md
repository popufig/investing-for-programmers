# Chapter 3 Implementation Gaps (v1.2)

> 参考：*Investing for Programmers* Ch.3 — Collecting Data
> 本文档列出第三章尚未在系统中实现的功能，供代码审查和后续开发使用。
>
> **书籍文件路径：** `doc/Investing_for_Programmers_epub/OEBPS/Text/chapter-3.html`
> 用浏览器直接打开该文件，在 URL 末尾加锚点即可跳转到对应小节，例如：
> `file:///…/chapter-3.html#p11`
>
> | 锚点 | 小节 | 标题 |
> |------|------|------|
> | `#p11` | 3.1 | Financial data |
> | `#p25` | 3.2 | Financial analysis platforms |
> | `#p38` | 3.3 | Data science notebooks |
> | `#p43` | 3.4 | yfinance |
> | `#p47` | 3.4.1 | Fundamental analysis |
> | `#p73` | 3.4.2 | Technical analysis |
> | `#p103` | 3.4.3 | Limitations of yfinance |
> | `#p108` | 3.5 | Commercial libraries |
> | `#p122` | 3.5.1 | Finviz |
> | `#p136` | 3.5.2 | EODHD |
> | `#p148` | 3.5.3 | Alpha Vantage |
> | `#p161` | 3.5.4 | OpenBB |
> | `#p172` | 3.6 | Other libraries |

---

## 当前状态总结

| 章节 | 内容 | 状态 |
|------|------|------|
| 3.4.1 财务三表 | income_stmt / balance_sheet / cash_flow | ✅ 已实现 |
| 3.4.1 季度三表 | quarterly_income_stmt 等 | ✅ 已实现 |
| 3.4.1 info 属性 | 132+ 个公司指标 | ✅ 已实现 |
| 3.4.1 collect_ratios 多股比率对比 | 多 ticker 横向对比 | ✅ 已实现（Peer Comparison） |
| 3.4.1 比率趋势（D/E 跨年变化） | 关键比率随时间变化 | ❌ 未实现 |
| 3.4.2 历史价格数据 | history() 获取 OHLCV | ✅ 已实现 |
| 3.4.2 技术指标 | SMA/EMA/MACD/RSI/BB | ✅ 已实现 |
| 3.4.2 多股归一化对比图 | 起点 100% 的多股对比线 | ❌ 未实现 |
| 3.4.2 收益率分析 | 对数收益、直方图、统计量 | ❌ 未实现 |
| 3.2 股票筛选器 | 按条件筛选股票 | ❌ 未实现 |
| 3.2/3.5.1 Watchlist | 关注列表（未持有但跟踪） | ❌ 未实现 |
| 3.5.3 新闻情绪 | Alpha Vantage News Sentiment | ❌ 未实现 |
| 3.5 多数据源抽象 | EODHD/Alpha Vantage/OpenBB 切换 | ❌ 未实现 |

---

## GAP 1：多股归一化价格对比图（3.4.2）

> 📖 **书籍参考：** `chapter-3.html#p81`（3.4.2 Technical analysis）· `#p85`（plot_closing_prices）

### 目标

书中核心演示：将多只股票（如 AAPL/KO/SMR）的收盘价归一化到起始日 100%，在同一张图上对比走势。这是投资分析中最常用的可视化之一——不同股票价格量级不同（$10 vs $1000），直接比较无意义，归一化后才能看出真实的相对表现。

书中代码：
```python
close_prices = data["Close"]
price_change_in_percentage = (close_prices / close_prices.iloc[0] * 100)
price_change_in_percentage.plot(figsize=(12,8))
```

### 后端改动

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/compare?tickers=AAPL,KO,SMR&period=1y
```

**参数：**
- `tickers` — 逗号分隔的 ticker 列表，最少 2 个，最多 6 个
- `period` — 时间范围（`3mo`, `6mo`, `1y`, `2y`, `5y`），默认 `1y`

**返回格式：**
```json
{
  "period": "1y",
  "tickers": ["AAPL", "KO", "SMR"],
  "skipped": [],
  "data": [
    {
      "date": "2025-03-12",
      "AAPL": 105.3,
      "KO": 98.7,
      "SMR": 230.1
    }
  ]
}
```

**实现要点：**
- 每只股票第一天收盘价设为 100，后续计算 `close / first_close * 100`
- 使用 `yf.Tickers([...]).history()` 一次性获取所有股票数据（比逐个请求快）
- 无效 ticker 放入 `skipped`，不中断请求
- 日期对齐：取所有 ticker 日期的**并集**作为 X 轴，缺失值用前值填充（`ffill`）。不做交集——交集会在跨市场场景下丢失大量数据点
- 5 分钟缓存

**文件：`backend/services/market_data.py`**

新增函数 `get_normalized_comparison(tickers: List[str], period: str) -> dict`。

### 前端改动

**文件：`frontend/src/pages/StockAnalysis.jsx`**（或新建独立页面）

在 StockAnalysis 页面的 Price Chart 区域上方，新增「Compare」按钮和输入框：
- 用户输入 1~5 个对比 ticker（逗号分隔或逐个添加）
- 点击 Compare 后展示归一化折线图
- X 轴为日期，Y 轴为百分比（100% = 起点）
- 每条线颜色不同，带 Legend
- 时间范围选择器复用已有的 PERIODS

**可选：独立页面方案**

考虑新建 `/compare` 页面作为独立的多股对比工具，导航栏添加入口。这样不会让 StockAnalysis 页面过于臃肿，且对比功能天然面向多只股票。

**新文件（如选独立页面）：`frontend/src/pages/Compare.jsx`**

**API 客户端：`frontend/src/api/client.js`**

```js
export const compareStocks = (tickers, period = '1y') =>
  api.get('/stocks/compare', { params: { tickers, period } })
```

---

## GAP 2：收益率分析（3.4.2）

> 📖 **书籍参考：** `chapter-3.html#p91`（simple returns）· `#p93`（log returns）· `#p95`（histogram）· `#p98`（mean/std/var）

### 目标

书中展示了投资分析的基础统计工具：
1. **对数收益率（log returns）**：`np.log(price / price.shift())` — 比简单收益率更适合统计分析，因为对数收益率具有时间可加性
2. **收益率直方图（histogram）**：查看收益分布是否接近正态，识别尾部风险
3. **统计量表（mean / std / var）**：评估不同股票的风险收益特征

书中代码：
```python
log_rets = hist_prices["Close"].apply(lambda x: np.log(x / x.shift())).dropna()
log_rets.hist(bins=35, figsize=(10, 6))
summary = log_rets.agg(["mean", "std", "var"]).T
```

### 后端改动

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/{ticker}/returns?period=1y
```

**返回格式：**
```json
{
  "ticker": "AAPL",
  "period": "1y",
  "stats": {
    "mean": 0.00082,
    "std": 0.01534,
    "var": 0.000235,
    "annual_return": 0.228,
    "annual_volatility": 0.243,
    "skewness": -0.31,
    "kurtosis": 1.85
  },
  "histogram": [
    { "bin_start": -0.06, "bin_end": -0.055, "count": 2 },
    { "bin_start": -0.055, "bin_end": -0.05, "count": 3 }
  ],
  "daily_returns": [
    { "date": "2025-03-11", "simple": 0.012, "log": 0.0119 },
    { "date": "2025-03-12", "simple": -0.005, "log": -0.0050 }
  ]
}
```

**实现要点：**
- 同时计算简单收益率和对数收益率
- `histogram`：服务端预计算直方分箱（35 bins），避免前端处理大量原始数据
- `skewness` / `kurtosis`：衡量分布是否对称及尾部厚度，比书中要求多一步但对风险评估有价值
- 5 分钟缓存

**文件：`backend/services/market_data.py`**

新增函数 `get_return_analysis(ticker: str, period: str) -> dict`。

### 前端改动

**文件：`frontend/src/pages/StockAnalysis.jsx`**

在 Technical 图表区域下方新增「Returns」折叠面板，包含：

1. **统计量卡片** — Mean / Std / Var / Annual Return / Annual Vol / Skewness / Kurtosis
2. **直方图** — 用 Recharts `BarChart` 展示对数收益率分布
   - X 轴：收益率区间
   - Y 轴：频次
   - 叠加正态分布曲线（可选）
3. **日收益率时间序列** — 用 `BarChart` 展示每日收益率（正值绿色/负值红色）

**API 客户端：**
```js
export const getReturns = (ticker, period = '1y') =>
  api.get(`/stocks/${ticker}/returns`, { params: { period } })
```

---

## GAP 3：比率趋势图（3.4.1）

> 📖 **书籍参考：** `chapter-3.html#p71`（D/E ratio over time）

### 目标

书中演示了 Apple 的 D/E ratio 跨 4 年变化（2021: 2.16 → 2022: 2.61 → 2023: 1.78 → 2024: 1.87），用于判断某个看起来异常的指标是否属于正常波动范围。

当前 app 的 FinancialStatements 组件展示了原始报表数据，但没有将**关键比率**提取为独立趋势图。用户需要自己心算比率，这不直观。

### 后端改动

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/{ticker}/ratio-trends
```

**返回格式：**
```json
{
  "ticker": "AAPL",
  "periods": ["2024-Q4", "2024-Q3", "2024-Q2", "2024-Q1", "2023-Q4", "2023-Q3", "2023-Q2", "2023-Q1"],
  "ratios": {
    "debt_to_equity": [1.87, 1.95, 2.01, 1.78, 1.78, 1.81, 1.76, 1.72],
    "current_ratio": [0.99, 1.01, 1.04, 1.07, 1.07, 1.06, 0.98, 0.94],
    "roe": [0.38, 0.41, 0.39, 0.42, 0.45, 0.43, 0.44, 0.40],
    "profit_margin": [0.26, 0.25, 0.27, 0.24, 0.26, 0.25, 0.25, 0.24],
    "roa": [0.10, 0.09, 0.10, 0.09, 0.11, 0.10, 0.10, 0.09],
    "asset_turnover": [0.38, 0.37, 0.38, 0.36, 0.40, 0.39, 0.39, 0.38]
  }
}
```

**实现要点：**
- 从 `quarterly_income_stmt`、`quarterly_balance_sheet` 提取原始数据，计算比率
- 比率定义（与书中 Table 3.3 一致）：
  - `debt_to_equity` = Total Debt / Stockholders Equity
  - `roe` = Net Income / Stockholders Equity
  - `profit_margin` = Net Income / Total Revenue
  - `roa` = Net Income / Total Assets
  - `asset_turnover` = Total Revenue / Total Assets
  - `current_ratio` = Current Assets / Current Liabilities（必须从 `quarterly_balance_sheet` 计算，**不得**从 `info` 取值，否则破坏季度趋势可比性）
- 返回最近 8 个季度
- 某些季度可能缺失字段，缺失值设为 `null`
- 5 分钟缓存

**文件：`backend/services/market_data.py`**

新增函数 `get_ratio_trends(ticker: str) -> dict`。

### 前端改动

**文件：`frontend/src/components/FinancialStatements.jsx`**

在现有三表 Tab 旁新增第四个 Tab「Ratios」：
- 每个比率一条折线（`LineChart`）
- X 轴为季度，Y 轴为比率值
- 用户可勾选显示/隐藏特定比率
- 对书中提到的 D/E ratio 着重标注（若突然大幅偏离前期值，用红色高亮）

---

## GAP 4：Watchlist（关注列表）

> 📖 **书籍参考：** `chapter-3.html#p28`（screener 工作流）· `#p129`（Finviz portfolio as tracking list）

### 目标

书中描述的投资工作流是：**筛选 → 跟踪 → 分析 → 买入**。当前 app 只有「已持有」的 Holdings，缺少「关注但未持有」的 Watchlist 功能。

书中 3.5.1 节提到 Finviz 的 portfolio 功能："A portfolio is a list of stocks a user tracks to which they can add the number of shares they own." 这实际上同时包含了 watchlist（跟踪）和 portfolio（持仓）两层含义。

Watchlist 的核心场景：
- 用户在 screener 或外部平台发现感兴趣的股票，先加入 watchlist 跟踪
- 跟踪一段时间后决定是否买入
- Watchlist 中的股票也需要看当前价格、涨跌幅、关键指标

### 数据模型

**文件：`backend/models.py`**

新增 `Watchlist` 表：
```python
class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, unique=True)
    name = Column(String(200))
    notes = Column(Text)
    target_price = Column(Float)          # 目标买入价（可选）
    created_at = Column(DateTime, server_default=func.now())
```

**设计说明：**
- `ticker` 唯一约束，同一只股票只能加入一次
- `target_price` 可选，记录用户期望的买入价位
- `notes` 记录关注原因
- 不需要 shares / avg_price，与 Holding 区分

### 后端改动

**文件：`backend/routers/watchlist.py`（新建）**

路由文件内部使用**相对路径**，`prefix` 由 `main.py` 统一注册：

| 方法 | 路由文件内路径 | 完整路径（main.py 注册后） | 说明 |
|------|---------------|---------------------------|------|
| GET | `/` | `/api/watchlist` | 列出所有关注股票（含当前价格、涨跌幅） |
| POST | `/` | `/api/watchlist` | 添加股票到 watchlist |
| PUT | `/{id}` | `/api/watchlist/{id}` | 更新 notes / target_price |
| DELETE | `/{id}` | `/api/watchlist/{id}` | 从 watchlist 移除 |
| POST | `/{id}/convert` | `/api/watchlist/{id}/convert` | 原子化转为 Holding（见下方说明） |

**GET `/api/watchlist` 返回格式：**
```json
[
  {
    "id": 1,
    "ticker": "SMR",
    "name": "NuScale Power",
    "notes": "小型核反应堆概念，关注政策动向",
    "target_price": 15.0,
    "current_price": 22.5,
    "change_pct": 3.2,
    "sector": "Utilities",
    "market_cap": 3200000000,
    "created_at": "2026-03-10T08:30:00"
  }
]
```

**`POST /{id}/convert` — Move to Holdings（原子化转换）：**

请求体：
```json
{
  "shares": 100,
  "avg_price": 22.5,
  "portfolio": "Tech"
}
```

实现逻辑（单个数据库事务内完成）：
1. 读取 watchlist 条目，获取 ticker / name
2. 调用 `get_ticker_info(ticker)` 推断 `asset_type`（复用 stocks router 中已有的 `_infer_asset_type` 逻辑：ETF / FUND / BOND / STOCK）。Watchlist 表本身**不存储** asset_type——关注阶段无需分类，仅在转换时实时推断
3. 创建 Holding 记录（使用请求体中的 shares / avg_price / portfolio + 推断出的 asset_type）
4. 删除 watchlist 条目
5. 提交事务；任一步失败则整体回滚

返回：
```json
{
  "holding_id": 42,
  "ticker": "SMR",
  "message": "Converted to holding"
}
```

> ⚠️ 不可拆为前端两次独立请求（先 POST holding 再 DELETE watchlist），否则中间失败会导致数据不一致。

**其他实现要点：**
- GET 请求需要实时拉取每只股票的当前价格和涨跌幅（通过 `get_multiple_prices` 或 `get_ticker_info`）
- 若 watchlist 数量较多（>10），使用并发获取价格避免超时
- POST 时自动填充 `name`（从 yfinance info 获取）

**文件：`backend/main.py`**

注册新路由：
```python
from .routers import watchlist
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
```

### 前端改动

**新文件：`frontend/src/pages/Watchlist.jsx`**

- 表格展示 watchlist 中的股票（Ticker / Name / Price / Change% / Sector / Target Price / Notes）
- 「Add to Watchlist」按钮 + ticker 搜索输入框
- 每行有「Remove」和「Move to Holdings」操作
- 「Move to Holdings」弹出对话框输入 shares、avg_price 和 portfolio，调用 `POST /api/watchlist/{id}/convert` 原子化完成转换
- 价格与 target_price 对比：当前价 ≤ 目标价时高亮提示
- 点击 ticker 跳转到 `/stocks/{ticker}` 详情页

**文件：`frontend/src/App.jsx`**

新增路由 `/watchlist` 和导航栏入口。

**API 客户端：`frontend/src/api/client.js`**

```js
export const getWatchlist = () => api.get('/watchlist')
export const addToWatchlist = (data) => api.post('/watchlist', data)
export const updateWatchlistItem = (id, data) => api.put(`/watchlist/${id}`, data)
export const removeFromWatchlist = (id) => api.delete(`/watchlist/${id}`)
export const convertToHolding = (id, data) => api.post(`/watchlist/${id}/convert`, data)
```

---

## GAP 5：股票筛选器 / Stock Screener（3.2）

> 📖 **书籍参考：** `chapter-3.html#p25`（3.2 Financial analysis platforms）· `#p28`（stock screener 定义）· `#p31`（Finviz screener 示例）

### 目标

书中 3.2 节的核心功能："A stock screener is a tool that allows investors to filter listed stocks based on customizable criteria and displays relevant information onscreen to support informed decision-making."

书中 Finviz 示例：按 sector=Technology、country≠US、market cap > $200B 筛选，返回 3 个结果。

### 实现方案

**方案选择：轻量 yfinance 方案**

完整的 screener（如 Finviz）需要维护全量股票数据库，工作量大。建议采用**轻量方案**：基于预定义的股票宇宙（参考 `PEER_AUTOREC_UNIVERSE` 的扩展版，约 200~500 只主要股票），用 yfinance 批量获取 info 后在内存中筛选。

> ⚠️ 此方案的局限：只能筛选预定义的股票池，无法搜索全部 47,000+ 上市公司。书中也是在介绍 Finviz 这种外部平台的筛选能力，不是要求从零实现。

### 后端改动

**文件：`backend/services/market_data.py`**

新增股票宇宙列表 `SCREENER_UNIVERSE`（约 200~500 只主要股票），覆盖：
- 美股：S&P 500 主要成分股
- 可选：国际主要市值股票（书中 Finviz 示例筛选非美股）

新增函数 `screen_stocks(filters: dict) -> List[dict]`：
- 批量获取宇宙中所有股票的 `info`（需要缓存策略，首次加载较慢）
- 支持的筛选条件：

| 筛选器 | 参数 | 示例 |
|--------|------|------|
| Sector | `sector` | `"Technology"` |
| Industry | `industry` | `"Semiconductors"` |
| Market Cap 下限 | `market_cap_min` | `200000000000`（$200B） |
| Market Cap 上限 | `market_cap_max` | `10000000000`（$10B） |
| Country | `country` | `"United States"` |
| P/E 范围 | `pe_min` / `pe_max` | `10` / `30` |
| Dividend Yield 下限 | `dividend_yield_min` | `0.02` |
| 52w Change 下限 | `change_52w_min` | `0.1`（+10%） |

**缓存策略：**
- screener 数据较重（200+ 股票的 info），建议缓存时间延长到 30 分钟
- 首次加载可能需要 30~60 秒，前端需显示 loading 状态
- 可考虑后台定时刷新（后续优化）

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/screen?sector=Technology&market_cap_min=200000000000
```

**返回格式：**
```json
{
  "total": 3,
  "filters_applied": {
    "sector": "Technology",
    "market_cap_min": 200000000000
  },
  "results": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "country": "United States",
      "market_cap": 2900000000000,
      "pe_ratio": 30.5,
      "dividend_yield": 0.006,
      "price": 178.5,
      "change_52w": 0.15
    }
  ]
}
```

### 前端改动

**新文件：`frontend/src/pages/Screener.jsx`**

- 左侧：筛选面板（下拉选择 sector、输入 market cap 范围、P/E 范围等）
- 右侧：结果表格（可排序、可点击跳转到详情页）
- 「Add to Watchlist」按钮（每行或批量选择）— 与 GAP 4 联动
- Loading 状态提示（首次加载可能较慢）

**文件：`frontend/src/App.jsx`**

新增路由 `/screener` 和导航栏入口。

---

## GAP 6：新闻情绪分析（3.5.3）

> 📖 **书籍参考：** `chapter-3.html#p158`（Alpha Vantage News Sentiment）

### 目标

书中演示了 Alpha Vantage 的免费 News Sentiment API，为 NuScale (SMR) 获取新闻情绪数据。这是第三章唯一涉及「非财务数据」（3.1 节第三类数据）的实操功能。

书中代码：
```python
url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={key}'
r = requests.get(url)
data = r.json()['feed']
```

### 前提

- 需要 Alpha Vantage API key（免费注册即可获取）
- 免费版限制：25 次/天，5 次/分钟
- `.env_template` 中已预留 `datasource.alphavantage.secret` 字段

### 后端改动

**文件：`backend/routers/stocks.py`**

新增接口：
```
GET /api/stocks/{ticker}/sentiment
```

**返回格式：**
```json
{
  "ticker": "SMR",
  "available": true,
  "overall_sentiment": "Bullish",
  "overall_score": 0.35,
  "articles": [
    {
      "title": "NuScale Wins New Contract for SMR Deployment",
      "url": "https://...",
      "source": "Reuters",
      "published": "2026-03-11T14:30:00",
      "sentiment_score": 0.42,
      "sentiment_label": "Bullish",
      "relevance_score": 0.95
    }
  ]
}
```

无 API key 或请求失败时：
```json
{
  "ticker": "SMR",
  "available": false,
  "message": "Alpha Vantage API key not configured"
}
```

**实现要点：**
- 从环境变量读取 `datasource.alphavantage.secret`（与 `.env_template` 一致）
- 若 key 未配置，直接返回 `available: false`，不报错
- Alpha Vantage 返回的 `feed` 数组中每条 article 包含 `ticker_sentiment` 子数组，需筛选目标 ticker 的 sentiment
- 情绪标签映射：score < -0.35 → Bearish, -0.35~-0.15 → Somewhat-Bearish, -0.15~0.15 → Neutral, 0.15~0.35 → Somewhat-Bullish, > 0.35 → Bullish
- 返回最近 20 篇相关文章
- 缓存 15 分钟（新闻更新频率较低）

**文件：`backend/services/market_data.py`**

新增函数 `get_news_sentiment(ticker: str) -> dict`。

### 前端改动

**文件：`frontend/src/pages/StockAnalysis.jsx`**

在页面底部新增「News Sentiment」折叠面板：
- **情绪仪表盘**：Overall Sentiment 标签 + 分数条
- **文章列表**：标题（可点击跳转）、来源、日期、单篇情绪标签
- 若 `available: false`，显示提示："News sentiment requires Alpha Vantage API key. Set datasource.alphavantage.secret in .env"

---

## 接口变更汇总

| 方法 | 路径 | 状态 | 说明 | GAP |
|------|------|------|------|-----|
| GET | `/api/stocks/compare` | **新增** | 多股归一化对比 | 1 |
| GET | `/api/stocks/{ticker}/returns` | **新增** | 收益率分析（对数收益、直方图、统计量） | 2 |
| GET | `/api/stocks/{ticker}/ratio-trends` | **新增** | 关键比率季度趋势 | 3 |
| GET | `/api/watchlist` | **新增** | 关注列表 | 4 |
| POST | `/api/watchlist` | **新增** | 添加关注 | 4 |
| PUT | `/api/watchlist/{id}` | **新增** | 更新关注备注/目标价 | 4 |
| DELETE | `/api/watchlist/{id}` | **新增** | 移除关注 | 4 |
| POST | `/api/watchlist/{id}/convert` | **新增** | 原子化转为 Holding | 4 |
| GET | `/api/stocks/screen` | **新增** | 股票筛选器 | 5 |
| GET | `/api/stocks/{ticker}/sentiment` | **新增** | 新闻情绪（Alpha Vantage） | 6 |

---

## 前端路由变更

| 路径 | 页面 | 说明 | GAP |
|------|------|------|-----|
| `/compare` | Compare.jsx | 多股价格对比（可选独立页面） | 1 |
| `/watchlist` | Watchlist.jsx | 关注列表 | 4 |
| `/screener` | Screener.jsx | 股票筛选器 | 5 |

---

## 数据模型变更

| 表名 | 操作 | 说明 | GAP |
|------|------|------|-----|
| `watchlist` | **新增** | 关注列表（ticker/name/notes/target_price） | 4 |

---

## 建议实现顺序

1. **GAP 4 Watchlist** — 数据模型简单，是筛选 → 跟踪 → 分析 → 买入工作流的关键环节，也为 GAP 5 提供「Add to Watchlist」的落点
2. **GAP 1 多股对比图** — 高频使用，改动范围可控（一个后端接口 + 一个前端组件/页面）
3. **GAP 3 比率趋势** — 增强已有 FinancialStatements 组件，后端数据源已就绪
4. **GAP 2 收益率分析** — 核心投资分析功能，一个后端接口 + 前端面板
5. **GAP 6 新闻情绪** — 需 API key，做为可选增强功能
6. **GAP 5 股票筛选器** — 工作量最大（股票宇宙维护 + 批量获取 + 缓存策略），建议最后做

> **不纳入本轮的功能：**
> - **多数据源抽象**（EODHD/Alpha Vantage/OpenBB 切换）— 架构层重构，当前 yfinance 已满足需求，书中也以 yfinance 为主。若后续 yfinance 出现稳定性问题再考虑。

---

## 注意事项

- **Alpha Vantage 免费额度**：25 次/天，5 次/分钟。GAP 6 需做好限流和降级处理
- **Screener 性能**：批量获取 200+ 股票 info 较慢，需要合理的缓存和异步加载策略
- **Watchlist 与 Holdings 联动**：`POST /api/watchlist/{id}/convert` 在单个数据库事务内完成创建 Holding + 删除 Watchlist，失败时整体回滚
- **归一化对比图日期对齐**：取所有 ticker 日期并集 + `ffill`（见 GAP 1 实现要点），不做交集，避免跨市场场景丢失数据
- **路由冲突**：`/api/stocks/compare` 和 `/api/stocks/screen` 是固定路径，需放在 `/{ticker}` 之前注册，否则 FastAPI 会将 `compare`/`screen` 当作 ticker 参数

---

## 设计决策（已确认）

1. **Watchlist 是全局单列表，不按 portfolio 隔离。**
   - 理由：Watchlist 的语义是"还没买、在关注"，不属于任何 portfolio。按 portfolio 隔离会增加操作摩擦（添加时还得选 portfolio）。若后续需要分组，用 `tag` 字段比 portfolio 关联更灵活。

2. **`/stocks/compare` 接口不自动包含当前股票，但前端按入口自动拼接。**
   - 接口层面：`tickers` 参数接收完整的对比列表（含主股票），接口逻辑简单统一。
   - 前端层面：
     - 从 **StockAnalysis 页面**发起对比时，前端自动将当前 ticker 加入 `tickers`，用户只需输入对比对象。
     - 从 **独立 `/compare` 页面**进入时，所有 ticker 都由用户输入。
   - 这样接口保持无状态，对比入口的差异由前端处理。

---

## 开放问题

1. **多股对比：独立页面 vs StockAnalysis 内嵌？** — 独立页面更清晰，但增加导航复杂度。建议 reviewer 给出偏好。
2. **Screener 股票宇宙范围？** — 50 只（`PEER_AUTOREC_UNIVERSE`）太少，S&P 500 全量（500 只）更实用但首次加载慢。是否可接受 30~60 秒的首次加载时间？
3. **Watchlist 是否需要分组？** — 当前设计为全局平面列表（见设计决策 #1）。v1 先做平面列表，后续按需扩展 `tag` 字段支持分组。

---

*文档版本：v1.2 | 更新日期：2026-03-12*
*v1.0 — 初版 (2026-03-12)*
*v1.1 — 确认 Watchlist 全局单列表、compare 接口前端拼接策略 (2026-03-12)*
*v1.2 — Review 修复：Move to Holdings 原子化 convert 接口、ratio-trends current_ratio 统一从季度报表计算、52w 参数名合法化、Alpha Vantage 环境变量名与 .env_template 对齐、Watchlist 路由消除双前缀、日期对齐策略统一为并集+ffill、版本标识修正 (2026-03-12)*
*v1.2.1 — convert 流程澄清：asset_type 不存于 watchlist 表，转换时从 yfinance info 实时推断 (2026-03-12)*
