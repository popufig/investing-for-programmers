# 第4章功能需求与技术方案

## 1. 背景

第4章围绕 **投资论文(Investment Thesis)** 展开，以 LiDAR 公司（AEVA, LAZR, INVZ, OUST）为案例，介绍了从假说提出到数据验证的完整投资分析流程。当前应用（FastAPI + React）已实现基础分析功能（情绪分析、财务报表、技术指标、同行对比、经济周期等），但书中描述的以下 7 个功能尚未实现。

### 现有架构

```
Backend:  FastAPI + yfinance + Alpha Vantage API + SQLite
          app/backend/services/market_data.py (核心服务层, 2047行)
          app/backend/routers/stocks.py (REST API路由)
Frontend: React + Tailwind CSS + Recharts
          app/frontend/src/pages/StockAnalysis.jsx (主分析页)
          app/frontend/src/components/ (独立组件)
          app/frontend/src/api/client.js (API客户端)
```

---

## 2. 需求列表

### 需求 1：情绪分布可视化（P1）

**书中参考**: Table 4.7 — 统计新闻中 Bullish/Somewhat-Bullish/Neutral/Somewhat-Bearish/Bearish 各出现多少次

**需求描述**: 当前情绪分析只展示一个"整体情绪"标签（如 Bullish）和一个分数。用户需要看到各情绪等级的**具体数量分布**，以判断市场情绪是一致的还是分化的。

**使用场景**:
- 场景A：用户查看 LAZR 情绪，发现整体标签是"Neutral"，但分布显示 8 篇 Bullish + 7 篇 Bearish → 实际上市场意见严重分化，不是真正的中性
- 场景B：用户看到 INVZ 整体 Bullish，分布显示 15 篇 Bullish + 2 篇 Neutral → 市场共识强烈看涨

**技术方案**:

后端（`market_data.py`）:
- 在 `get_news_sentiment()` 函数中，**先对 API 返回的全量 feed 统计分布**（用 `collections.Counter` 统计每篇的 `sentiment_label`），再截断为最近 20 条用于文章列表展示
- 在返回的 `result` 字典中增加 `"distribution"` 字段（基于全量数据）：
  ```python
  distribution = {"Bullish": 5, "Somewhat-Bullish": 3, "Neutral": 2, "Somewhat-Bearish": 1, "Bearish": 0}
  ```
- `"total_articles"` 字段记录参与统计的文章总数
- 无需新增 API 端点，复用现有 `GET /{ticker}/sentiment`

前端（`StockAnalysis.jsx`）:
- 在情绪 badge（第661行）和文章列表（第662行）之间，插入一个水平柱状图
- 使用已有的 Recharts `BarChart`，5 个柱子分别对应 5 个情绪等级
- 颜色：Bullish=绿, Somewhat-Bullish=浅绿, Neutral=灰, Somewhat-Bearish=橙, Bearish=红

**改动范围**: ~10行后端 + ~30行前端JSX，无新文件，无新依赖

---

### 需求 2：距历史最高点跌幅分析（P1）

**书中参考**: Table 4.2 — 展示每只股票的历史最高价、当前价、跌幅百分比

**需求描述**: 用户需要快速了解一只股票从历史高点下跌了多少，以评估是"深度价值机会"还是"基本面恶化"。

**使用场景**:
- 场景A：用户研究 LAZR，发现从 ATH $47 跌到 $1.5，跌幅 97% → 需要深入分析是市场过度悲观还是公司确实出了问题
- 场景B：用户对比 4 只 LiDAR 股票的 ATH 跌幅，找出哪只跌幅最大（可能反弹空间最大）
- 场景C：配合利率数据，判断跌幅是否主要由宏观因素驱动

**技术方案**:

后端（`market_data.py`）— 新增函数:
```python
@cached(ttl=3600)  # 复用项目已有的缓存装饰器
def get_ath_analysis(ticker: str) -> Dict[str, Any]:
    """
    用 yf.Ticker(ticker).history(period="max") 获取全部历史数据
    超时: 10秒，失败返回 error 字段而非抛异常
    返回: {
        ticker, all_time_high, ath_date, all_time_low, atl_date,
        current_price, down_from_ath_pct, up_from_atl_pct,
        range_position  # 当前价在 ATL-ATH 区间的百分比位置
    }
    """
```

路由（`stocks.py`）— 新增端点:
- `GET /{ticker}/ath` → 调用 `get_ath_analysis(ticker)`

前端 — 新建 `components/AthAnalysis.jsx`:
- 指标卡行：ATH价格、ATH日期、当前价、跌幅%
- 可视化进度条：当前价在 ATL-ATH 区间中的位置（类似已有的52周范围条）
- 颜色编码：跌幅<20%绿色, 20-50%黄色, >50%红色

集成到 `StockAnalysis.jsx` — 在指标卡区域后添加 `<AthAnalysis ticker={info.ticker} />`

**改动范围**: ~60行后端 + 1个新组件 + 1个API端点，无新依赖

---

### 需求 3：年度 EPS 趋势（P1）

**书中参考**: Table 4.1 — 展示 AEVA/LAZR/INVZ/OUST 2019-2024年的年度 EPS 数据

**需求描述**: 用户需要查看一家公司多年的每股收益（EPS）趋势，特别是对于亏损的成长型公司，判断亏损是在扩大还是收窄。

**使用场景**:
- 场景A：用户分析 LAZR，看到 EPS 从 -13.05 → -9.94 → -6.82 → 确认亏损在逐年收窄24%，是积极信号
- 场景B：对比 4 只 LiDAR 公司的 EPS 轨迹，找出亏损收窄最快的那只
- 场景C：结合 COVID 时间线，识别疫情对盈利的影响和恢复情况

**技术方案**:

后端（`market_data.py`）— 新增函数:
```python
@cached(ttl=86400)  # EPS 年度数据变化慢，缓存24小时
def get_eps_trend(ticker: str) -> Dict[str, Any]:
    """
    用 yf.Ticker(ticker).income_stmt（年度报表）提取 Diluted EPS
    也尝试 yf.Ticker(ticker).earnings 获取 Revenue+Earnings
    超时: 10秒，失败返回 error 字段而非抛异常
    返回: {
        ticker,
        eps_history: [{year: "2024", eps: -1.13, yoy_change: 0.24}, ...],
        earliest_year, latest_year
    }
    """
```

路由（`stocks.py`）— 新增端点:
- `GET /{ticker}/eps-trend` → 调用 `get_eps_trend(ticker)`

前端 — 新建 `components/EpsTrend.jsx`:
- Recharts `BarChart`：每年一个柱子，正值绿色、负值红色
- 下方表格：年份 | EPS | 同比变化%
- Peer comparison 模式：前端对每只 peer 并发调用 `GET /{ticker}/eps-trend`，合并结果后叠加渲染（与现有 peer comparison 模式一致，无需后端批量接口）

集成到 `StockAnalysis.jsx` — 在 `<FinancialStatements>` 和 `<EconomicCycleSection>` 之间添加

**改动范围**: ~80行后端 + 1个新组件 + 1个API端点，无新依赖

---

### 需求 4：盈利预估对比表（P2）

**书中参考**: Table 4.4/4.5 — 分析师对 LAZR 的季度盈利预估（avg/low/high/yearsAgoEps/growth）

**需求描述**: 展示分析师对未来季度/年度的盈利共识预期，帮助用户判断公司何时可能实现盈利。

**使用场景**:
- 场景A：用户查看 LAZR 预估，发现分析师预期未来4个季度 EPS 从 -0.35 → -0.28 → -0.20 → -0.15，确认改善趋势
- 场景B：对比 low 和 high 预估的差距，差距大说明分析师分歧大，不确定性高
- 场景C：对比 `yearsAgoEps` 和当前预估，量化改善幅度

**技术方案**:

后端（`market_data.py`）— 新增函数:
```python
@cached(ttl=3600)  # 预估数据缓存1小时
def get_earnings_estimates(ticker: str) -> Dict[str, Any]:
    """
    用 yf.Ticker(ticker).earnings_estimate（季度预估）
    + yf.Ticker(ticker).revenue_estimate（收入预估）
    超时: 10秒，失败返回 error 字段而非抛异常
    返回: {
        ticker,
        earnings_estimates: [{period, avg, low, high, years_ago_eps, num_analysts, growth}, ...],
        revenue_estimates: [{period, avg, low, high, num_analysts, growth}, ...]
    }
    """
```

路由（`stocks.py`）— 新增端点:
- `GET /{ticker}/earnings-estimates`

前端 — 新建 `components/EarningsEstimates.jsx`:
- 表格：Period | Avg | Low | High | Prior EPS | Analysts | Growth%
- 增长率正值绿色、负值红色
- 可选：小型折线图展示从历史到预估的 EPS 轨迹

集成到 `StockAnalysis.jsx` — 在 `<AnalystSection>` 附近添加

**注意**: `yf.Ticker.earnings_estimate` 是非官方属性，部分股票可能无数据，需要健壮的错误处理

**改动范围**: ~70行后端 + 1个新组件 + 1个API端点，无新依赖

---

### 需求 5：美联储利率数据 — FRED（P2）

**书中参考**: Figure 4.5 — 联邦基金利率走势图，说明利率下降可能触发 LiDAR 股票反弹

**需求描述**: 叠加宏观经济数据（特别是利率）到个股分析中，帮助用户理解宏观环境对资本密集型行业估值的影响。

**使用场景**:
- 场景A：用户分析 LiDAR 公司时，看到利率从 5.33% 开始下降 → 判断这是利好资本密集型行业的信号
- 场景B：叠加利率走势和股价走势，验证"利率下降→股价反弹"的假说
- 场景C：查看收益率曲线（DGS10 vs DGS2）判断经济衰退风险

**技术方案**:

后端（`market_data.py`）— 新增函数:
```python
def get_fred_series(series_id: str = "DFF", period: str = "5y") -> Dict[str, Any]:
    """
    直接 HTTP 调用 FRED API（无需新pip依赖）:
    https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=...&file_type=json

    数据量大时降采样为周/月频率
    返回: {
        series_id, title, data: [{date: "2024-01-01", value: 5.33}, ...]
    }
    """
```

新建路由（`routers/macro.py`）— 因为是宏观数据，非个股特定:
- 路由装饰器只写相对路径: `@router.get("/fred/{series_id}")`
- 在 `main.py` 中注册前缀: `app.include_router(macro.router, prefix="/api/macro", tags=["macro"])`
- 最终对外路径: `GET /api/macro/fred/{series_id}?period=5y`（避免双重 /api/macro 前缀）

前端 — 新建 `components/FredRateChart.jsx`:
- Recharts `LineChart`：X轴日期、Y轴利率百分比
- 标注当前利率值
- 嵌入 `EconomicCycleSection` 附近

配置:
- `.env_template` 增加 `datasource.fred.key=<your key>`
- API key 未配置时优雅降级（显示提示信息）

**改动范围**: ~100行后端 + 1个新路由文件 + 1个新组件 + .env 更新

**新增依赖**: 无pip依赖，需要免费的 FRED API key

---

### 需求 6：Google Trends 集成（P2）

**书中参考**: Table 4.6 — 用 pytrends 追踪 "Luminar Technologies" 等公司名的搜索兴趣

**需求描述**: 追踪公众对特定公司的搜索兴趣变化，作为股价的潜在领先指标。

**使用场景**:
- 场景A：用户追踪 4 只 LiDAR 公司，发现 "Luminar Technologies" 搜索量突然上升 → 可能有重大消息即将公布
- 场景B：对比竞争对手搜索兴趣，发现 OUST 搜索量持续下降 → 市场关注度在转移
- 场景C：长期趋势分析，识别公众兴趣的季节性模式

**技术方案**:

后端（`market_data.py`）— 新增函数:
```python
def get_google_trends(keywords: list, timeframe: str = "today 12-m") -> Dict[str, Any]:
    """
    用 pytrends.request.TrendReq 获取搜索兴趣数据
    限制: 最多5个关键词（Google限制）
    缓存: 3600秒（搜索趋势变化慢）
    返回: {
        keywords, timeframe,
        data: [{date: "2024-01-07", "Luminar Technologies": 45, "Ouster Inc": 12}, ...]
    }
    """
```

路由（`stocks.py`）— 新增端点:
- `GET /trends?keywords=Luminar+Technologies,Ouster+Inc&timeframe=today+12-m`
- 放在 `/{ticker}` 路由之前避免路径冲突

前端 — 新建 `components/GoogleTrends.jsx`:
- Recharts `LineChart`：每个关键词一条线
- 使用已有的 `COMPARE_COLORS` 调色板
- 可切换的图例
- 关键词输入框（默认预填当前公司名和 peer 公司名）

集成到 `StockAnalysis.jsx` — 在 News Sentiment 附近添加

**新增依赖**: `pytrends>=4.9.0`

**风险**: pytrends 依赖 Google 非官方接口，经常因 Google 端变更而失效。需要:
1. 全面的 try/except 错误处理
2. 失败时返回友好提示（"Google Trends 暂不可用"）
3. 较长的缓存 TTL 减少请求频率

**改动范围**: ~80行后端 + 1个新组件 + 1个API端点 + pip依赖

---

### 需求 7：投资论文构建器（P3）

**书中参考**: 4.1.1-4.1.3 — 从想法到论文到验证的迭代过程

**需求描述**: 提供完整的投资论文管理工具，让用户能够创建投资假说、关联股票、定期检查进展、最终验证或否定论文。

**使用场景**:
- 场景A：用户创建论文"利率下降将推动 LiDAR 公司估值恢复"，关联 AEVA/LAZR/INVZ/OUST，设置6个月后评估日期
- 场景B：每月添加检查点，记录"利率已降 25bp，LAZR 上涨 15%，论文仍然成立"
- 场景C：查看论文快照，一次性看到所有关联股票的当前价格和自论文创建以来的涨跌幅
- 场景D：论文被证伪（如 Tesla Vision 完全取代 LiDAR），标记为 invalidated 并记录原因

**技术方案**:

数据库模型（`models.py`）:
```python
class InvestmentThesis(Base):
    __tablename__ = "investment_theses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)      # 论文标题
    status = Column(String(20), default="active")     # active/validated/invalidated/archived
    summary = Column(Text)                             # 完整描述
    category = Column(String(50))                      # growth/value/macro/sector
    target_date = Column(DateTime)                     # 评估截止日期
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ORM relationships
    tickers = relationship("ThesisTicker", back_populates="thesis", cascade="all, delete-orphan")
    checkpoints = relationship("ThesisCheckpoint", back_populates="thesis", cascade="all, delete-orphan")

class ThesisTicker(Base):
    """独立关联表，避免逗号分隔字符串的筛选/去重/校验问题"""
    __tablename__ = "thesis_tickers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    thesis_id = Column(Integer, ForeignKey("investment_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(10), nullable=False)        # 股票代码: "LAZR"
    baseline_price = Column(Float)                     # 创建论文时该股票的收盘价，用于计算涨跌幅

    thesis = relationship("InvestmentThesis", back_populates="tickers")

    __table_args__ = (UniqueConstraint("thesis_id", "ticker", name="uq_thesis_ticker"),)

class ThesisCheckpoint(Base):
    __tablename__ = "thesis_checkpoints"
    id = Column(Integer, primary_key=True, autoincrement=True)
    thesis_id = Column(Integer, ForeignKey("investment_theses.id", ondelete="CASCADE"), nullable=False, index=True)
    note = Column(Text, nullable=False)                # 检查记录
    status_at_check = Column(String(20))               # on_track/at_risk/invalidated
    created_at = Column(DateTime, server_default=func.now())

    thesis = relationship("InvestmentThesis", back_populates="checkpoints")
```

**涨跌幅基准价决策**: `ThesisTicker.baseline_price` 记录创建论文时该股票的**当日收盘价**。创建论文时后端自动通过 yfinance 获取并填入。选择收盘价是因为最可靠、无歧义，且用户通常在收盘后做分析决策。

Pydantic Schema（`schemas.py`）:
- `ThesisCreate`, `ThesisUpdate`, `ThesisResponse`
- `CheckpointCreate`, `CheckpointResponse`

新建路由（`routers/thesis.py`）:
```
GET    /api/thesis              列出所有论文（可按status过滤）
POST   /api/thesis              创建论文
GET    /api/thesis/{id}         获取论文详情+检查点
PUT    /api/thesis/{id}         更新论文
DELETE /api/thesis/{id}         删除论文
POST   /api/thesis/{id}/checkpoints   添加检查点
GET    /api/thesis/{id}/snapshot      获取关联股票的当前市场快照
```

前端 — 新建 `pages/Thesis.jsx`:
- **列表视图**: 卡片布局，每张卡显示标题、状态标签、关联股票标签、创建时间
- **详情视图**:
  - 论文标题 + 状态 + 编辑按钮
  - 摘要文本
  - 股票网格：每只关联股票的当前价、自创建以来涨跌幅、迷你走势图
  - 检查点时间线：倒序排列，带状态标记
  - "添加检查点"表单
- 状态标签颜色: active=蓝, validated=绿, invalidated=红, archived=灰

导航（`App.jsx`）:
- 新增导航项: `{ to: '/thesis', icon: Lightbulb, label: 'Thesis' }`
- 新增路由: `/thesis` 和 `/thesis/:id`

**改动范围**: ~200行后端（模型+路由+schema） + 1个新页面 + 导航更新

**新增依赖**: 无（使用已有 SQLAlchemy + FastAPI）

---

## 3. 实施顺序

```
Phase 1 (P1 — 快速见效)
  ├── 需求1: 情绪分布可视化 (最小改动)
  ├── 需求2: ATH 跌幅分析
  └── 需求3: 年度 EPS 趋势

Phase 2 (P2 — 中等复杂)
  ├── 需求4: 盈利预估对比表
  ├── 需求5: FRED 利率数据
  └── 需求6: Google Trends

Phase 3 (P3 — 完整功能)
  └── 需求7: 投资论文构建器
```

## 4. 文件影响矩阵

| 文件 | 需求1 | 需求2 | 需求3 | 需求4 | 需求5 | 需求6 | 需求7 |
|------|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|
| `backend/services/market_data.py` | ✏️ | ✏️ | ✏️ | ✏️ | ✏️ | ✏️ | |
| `backend/routers/stocks.py` | | ✏️ | ✏️ | ✏️ | | ✏️ | |
| `backend/routers/macro.py` | | | | | 🆕 | | |
| `backend/routers/thesis.py` | | | | | | | 🆕 |
| `backend/models.py` | | | | | | | ✏️ |
| `backend/schemas.py` | | | | | | | ✏️ |
| `backend/main.py` | | | | | ✏️ | | ✏️ |
| `backend/requirements.txt` | | | | | | ✏️ | |
| `frontend/src/api/client.js` | | ✏️ | ✏️ | ✏️ | ✏️ | ✏️ | ✏️ |
| `frontend/src/pages/StockAnalysis.jsx` | ✏️ | ✏️ | ✏️ | ✏️ | ✏️ | ✏️ | |
| `frontend/src/pages/Thesis.jsx` | | | | | | | 🆕 |
| `frontend/src/components/AthAnalysis.jsx` | | 🆕 | | | | | |
| `frontend/src/components/EpsTrend.jsx` | | | 🆕 | | | | |
| `frontend/src/components/EarningsEstimates.jsx` | | | | 🆕 | | | |
| `frontend/src/components/FredRateChart.jsx` | | | | | 🆕 | | |
| `frontend/src/components/GoogleTrends.jsx` | | | | | | 🆕 | |
| `frontend/src/App.jsx` | | | | | | | ✏️ |
| `.env_template` | | | | | ✏️ | | |
| `tests/test_api/` | | 🆕 | 🆕 | 🆕 | 🆕 | 🆕 | 🆕 |
| `tests/test_services/` | 🆕 | 🆕 | 🆕 | 🆕 | 🆕 | | |

✏️ = 修改已有文件 | 🆕 = 新建文件

## 5. 风险项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| `pytrends` 因 Google 接口变更失效 | 需求6不可用 | try/except + 优雅降级提示 |
| `yf.earnings_estimate` 部分股票无数据 | 需求4显示空白 | fallback 到空数据 + 提示信息 |
| FRED API 需要注册 key | 需求5初始不可用 | 清晰的配置提示 + 环境检查 |
| SQLite 并发写入限制 | 需求7多用户场景 | 当前单用户可接受，后续可迁移 PostgreSQL |
| yfinance 重查询超时/限流（需求2/3/4） | 页面加载慢或失败 | 统一 TTL 缓存（ATH: 3600s, EPS: 86400s, Estimates: 3600s）+ 10秒超时 + 失败返回 error 字段而非抛异常，前端显示降级提示 |

## 6. 验证方式

### 6.1 自动化测试（每个需求交付前必须通过）

后端 API contract tests（`tests/test_api/`）:
- 每个新端点至少 1 个正常路径 + 1 个异常路径（无效 ticker、无数据股票）的 pytest 用例
- 使用 `TestClient` (FastAPI) 直接调用，无需启动服务器
- 需求7: CRUD 全流程测试（创建→查看→更新→添加检查点→删除→确认级联清理）

核心服务单测（`tests/test_services/`）:
- `get_ath_analysis`、`get_eps_trend`、`get_earnings_estimates`: mock yfinance 响应，验证计算逻辑（如跌幅百分比、YoY 变化）
- `get_fred_series`: mock HTTP 响应，验证降采样和错误处理
- 情绪分布统计: 验证全量 vs 截断的正确性

### 6.2 手工验收

每个功能完成后:
1. 启动后端 `uvicorn`，用 curl 测试新 API 端点（正常数据 + 边界情况）
2. 启动前端 dev server，在 StockAnalysis 页面搜索 LAZR/AEVA 等验证组件渲染
3. 测试降级场景：无数据的股票、API key 未配置时的友好提示
4. 需求7额外测试: CRUD 全流程（创建→查看→更新→添加检查点→删除→确认无孤儿数据）
