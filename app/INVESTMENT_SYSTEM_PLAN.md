# 投资分析系统 — 构建方案与计划

> 参考：*Investing for Programmers* (Manning, Stefan Papp)
> 范围：股票、ETF、债券、基金、外汇；**不含**高频量化交易和虚拟货币

---

## 一、系统总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        投资分析系统                              │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  数据采集层  │  │  分析引擎层  │  │      AI 研究层           │ │
│  │  (Data)     │  │ (Analytics) │  │    (AI Agents)          │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│  ┌──────▼──────────────────────────────────────▼─────────────┐ │
│  │                     核心数据库 (SQLite / PostgreSQL)        │ │
│  └──────────────────────────────┬────────────────────────────┘ │
│                                 │                               │
│  ┌──────────────────────────────▼────────────────────────────┐ │
│  │              展示层 (Streamlit Dashboard / Google Sheets)   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心设计原则

### 原则 1：跟踪资产自动分析（Auto-Analysis for Tracked Securities）

**所有在 Holdings 和 Watchlist 中的证券，系统应自动获取数据并运行分析逻辑，而非依赖用户手动触发。**

具体体现：
- **自动数据获取**：用户添加资产到 Holdings 或 Watchlist 后，系统自动拉取实时价格、技术指标（RSI、SMA、MACD）、基本面数据等
- **自动信号计算**：系统自动为跟踪资产计算趋势信号（Bullish/Bearish/Neutral）、RSI 超买超卖提示、MACD 方向等
- **内联展示**：分析结果以信号标签（Signal Badges）的形式直接嵌入 Holdings 和 Watchlist 表格中，无需跳转页面即可一览关键指标

### 原则 2：快捷分析入口（Quick Access to Analysis）

**从 Holdings 和 Watchlist 页面应能一键进入某个资产的完整分析，而不是先切换菜单、再手动输入 Ticker。**

具体体现：
- Holdings 和 Watchlist 中的 Ticker 可直接点击，跳转到完整分析页面
- 每行提供「分析」快捷按钮（TrendingUp 图标），一键导航到 `/stocks/{ticker}`
- 系统所有关联分析功能（Risk、Compare、Thesis）均应支持从持仓/观察列表快速发起

---

## 二、功能模块详解

### 模块 1：数据采集层（对应书第 3、6 章）

**目标：** 统一接入多数据源，标准化存储

| 数据源 | 类型 | 用途 |
|--------|------|------|
| yfinance | 免费 | 价格、基本面、财务报表 |
| Alpha Vantage | 免费/付费 | 实时报价、经济指标 |
| EODHD | 付费 | 全球市场更全面数据 |
| OpenBB | 开源框架 | 多数据源聚合 |
| Alpaca API | broker | 账户持仓（程序员友好） |
| Interactive Brokers | broker | 账户持仓（成熟机构级） |
| 手动 / SQLite | 离线 | 无API的资产（房产等） |
| Google Finance | Sheets公式 | 实时价格嵌入报表 |

**核心数据表设计（书第 6 章）：**

```sql
-- 离线/手动资产记录
CREATE TABLE offline_asset (
    ticker     TEXT PRIMARY KEY,
    yield      REAL,         -- 被动收益率 (股息/债券利率)
    avg_price  REAL,         -- 加权平均买入价
    exchange   TEXT,         -- 交易所/托管机构
    amount     REAL,         -- 持有数量
    asset_type TEXT          -- stock/etf/bond/fund
);

-- 统一持仓视图：ticker, shares, avg_price, exchange, broker, asset_type
```

---

### 模块 2：基本面分析（对应书第 2、4、5 章）

**目标：** 量化公司价值，筛选投资标的

#### 2.1 财务报表解析（书第 2.1 节）
- **损益表**：营收、EBITDA、净利润、EPS 增长率
- **资产负债表**：流动比率、速动比率、资产负债率
- **自由现金流（FCF）**：FCF = 经营现金流 - 资本支出

#### 2.2 关键指标与比率（书第 2.4 节）

| 类别 | 指标 | 含义 |
|------|------|------|
| **流动性** | Current Ratio, Quick Ratio | 短期偿债能力 |
| **债务** | D/E Ratio, Interest Coverage | 财务杠杆 |
| **盈利** | EPS, Revenue Growth | 成长性 |
| **估值** | P/E, P/B, P/S, EV/EBITDA | 相对价格水平 |
| **盈利能力** | ROE, ROA, Gross Margin | 资产利用效率 |
| **股息** | Dividend Yield, Payout Ratio | 被动收入潜力 |
| **所有权** | Institutional Ownership % | 机构认可度 |
| **可持续性** | ESG Score | 非财务风险 |

#### 2.3 成长型组合分析（书第 4 章）
- 构建**投资逻辑（Investment Thesis）**：从行业趋势出发，找到受益公司
- 候选筛选：市值 + 债务 + 管理层 + 技术竞争力 + 预期盈利
- 行业分类：GICS 11大板块 + 经济周期映射

#### 2.4 收益型组合分析（书第 5 章）
- **股息投资**：股息成长股筛选、股息持续性分析
- **债券投资**：到期收益率（YTM）、久期分析
- **早退休（FIRE）测算**：被动收入目标 vs 当前持仓收益

#### 2.5 外部评估（书第 2.5 节）
- 分析师评级聚合（Buy/Hold/Sell 分布）
- 目标价区间（高/中/低）对比当前价格

---

### 模块 3：技术分析（对应书第 10 章）

**目标：** 从价格和成交量数据中识别趋势与信号

#### 3.1 图表类型
- K 线图（Candlestick）— OHLCV 数据可视化
- 蜡烛图形态识别：锤子线、吞没形态、十字星等

#### 3.2 均线与趋势指标
- SMA（简单移动平均）：20日、50日、200日
- EMA（指数移动平均）：12日、26日
- MACD = EMA(12) - EMA(26) + 信号线
- 黄金交叉 / 死亡交叉检测

#### 3.3 动量与波动指标
- RSI（相对强弱指数）：超买 > 70，超卖 < 30
- Bollinger Bands（布林带）：±2σ 通道
- ATR（真实波幅）：波动率参考

#### 3.4 一目均衡表（Ichimoku Cloud，书第 10.2.3 节）
- 转换线、基准线、云图、迟行线
- 支撑/阻力区间识别

#### 3.5 图表形态识别（书第 10.1.2 节）
- 头肩顶/底、双顶/底、三角整理
- 支撑位和阻力位

---

### 模块 4：风险管理（对应书第 7 章）

**目标：** 量化和控制投资组合风险

#### 4.1 止损机制（书第 7.1.1 节）
- 每个持仓自动设置止损价（固定价 or 移动止损）
- 止损策略记录与追踪

#### 4.2 风险分类（书第 7.1.2 节）
- **市场风险**：系统性风险（Beta）
- **公司风险**：特质风险（管理层、竞争、技术）
- **宏观风险**：利率、通胀、地缘政治
- **流动性风险**：买卖价差、交易量

#### 4.3 风险量化（书第 7.2 节）
- **VaR（风险价值）**：历史模拟法 + 参数法
  - 95% / 99% 置信区间
  - 单日 / 月度 VaR
- **最大回撤（Max Drawdown）**
- **Sharpe Ratio**（夏普比率）
- **相关性矩阵（Correlation Matrix）**（书第 7.2.2 节）
  - 识别持仓间的高相关性
  - 避免伪分散化

#### 4.4 对冲策略（书第 7.4 节）
- **多元化（Diversification）**：跨行业、跨地区
- **配对交易（Pair Trading）**：相关股票的多空对冲
- **风险配对（Risk Pairing）**：防御性资产 vs 进攻性资产

#### 4.5 组合优化（书第 7.6 节）
- **Markowitz 有效前沿**：在给定风险下最大化收益
  - 协方差矩阵计算
  - 最优权重分配
- **Shiller CAPE 比率**（书第 7.6.2 节）：市场整体估值判断
- **再平衡（Rebalancing）**（书第 7.6.3 节）：
  - 触发条件：偏离目标权重 > 5%
  - 定期再平衡：季度 / 半年

---

### 模块 5：AI 研究助手（对应书第 8、9 章）

**目标：** 用 LLM 加速定性研究，自动化信息收集

#### 5.1 LLM 集成（书第 8.2 节）
- 支持多模型：Claude（Anthropic）、GPT-4（OpenAI）、Gemini（Google）
- 统一接口封装，按任务选择最合适的模型

#### 5.2 公司定性研究（书第 8.3 节）
- 不直接问"推荐股票"，而是结构化提问：
  - 管理层风格与背景
  - 竞争护城河（Moat）分析
  - 行业趋势与公司定位
  - 近期新闻事件影响
- 生成公司评分卡（Scorecard）

#### 5.3 新闻情绪分析（书第 4.4.3 节）
- 抓取财经新闻
- 用 LLM 打分：正面 / 负面 / 中性（-1 ~ +1）
- 情绪趋势时序图

#### 5.4 Prompt 仓库（书第 9.2 节）
- 建立标准化 Prompt 模板库
- 包含：研究框架、风险评估、行业分析等场景

#### 5.5 AI Agent 工作流（书第 9.3 节）
- **LangChain** 构建多步骤 Agent：
  1. 收集公司基本面数据（Tool: yfinance）
  2. 搜索近期新闻（Tool: Web Search）
  3. 查询分析师评级（Tool: API）
  4. 综合生成研究报告
- **RAG（检索增强生成）**（书第 9.3.2 节）：
  - 将历史分析、行业报告向量化存储
  - 研究时自动检索相关历史上下文
- 设计模式（DeepLearning.AI 四大模式）：
  - Reflection（自我评估优化）
  - Tool Use（调用外部工具）
  - Planning（多步骤规划）
  - Multi-agent Collaboration（分析+评审双Agent）

#### 5.6 研究结果导出（书第 9.2.2 节）
- 导出到 **Notion**：结构化研究笔记
- 导出到 **Google Sheets**：量化数据看板

---

### 模块 6：组合监控仪表盘（对应书第 6、10.3 章）

**目标：** 实时掌握组合状态，支持决策

#### 6.1 数据流架构（书第 6.1 节）
```
Broker APIs + 离线数据
       ↓
Jupyter Notebook（数据清洗、聚合）
       ↓
Google Sheets（报表）+ Streamlit（交互仪表盘）
```

#### 6.2 Streamlit 仪表盘（书第 10.3 节）
- **总览页**：资产分布饼图、总价值、总收益率
- **持仓页**：每只股票价格变化、盈亏、Stop-Loss状态
- **收益页**：股息收入、债券利息、年化预期
- **风险页**：VaR展示、相关性热图、Beta分析
- **技术分析页**：按 Ticker 查看 K 线 + 指标
- **AI 报告页**：最新公司研究摘要

#### 6.3 报告与导出
- 每月生成 PDF 报告（被动收入 + 资本增值）
- Google Sheets 实时同步（Google Finance 公式嵌入）
- 邮件 / Slack 通知（重要事件警报）

---

### 模块 7：事件驱动监控（对应书第 11.2 节，非高频）

**目标：** 监控可能影响持仓的重要市场事件

- **财报日期追踪**：Earnings Calendar，提前准备分析
- **并购事件（M&A）**：监控持仓公司的并购公告
- **利率变化**：美联储决议对持仓的影响评估
- **宏观经济数据**：GDP、CPI、就业数据影响分析
- **回测（Backtesting）**（书第 11.3.1 节）：
  - 验证投资策略的历史表现
  - 不用于 HFT，用于中长期仓位策略验证

---

## 三、技术栈

| 层级 | 技术选择 | 说明 |
|------|----------|------|
| 语言 | Python 3.11+ | 主力开发语言 |
| 数据分析 | Pandas, NumPy | 数据处理 |
| 可视化 | Matplotlib, Plotly, Streamlit | 图表和仪表盘 |
| 数据获取 | yfinance, requests | 市场数据 |
| AI / LLM | LangChain, anthropic SDK | Agent 框架 + Claude |
| 向量数据库 | ChromaDB / FAISS | RAG 存储 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | 持仓数据 |
| 工作流 | Jupyter Notebook | 探索性分析 |
| 报表 | Google Sheets API, gspread | 云端报表 |
| 笔记导出 | Notion API | 研究笔记 |
| Broker API | Alpaca / Interactive Brokers | 持仓数据同步 |
| 密钥管理 | python-dotenv / AWS Secrets | 安全凭证管理 |
| 环境 | Anaconda / venv | 依赖管理 |

---

## 四、分阶段实施计划

### 第一阶段：基础框架（2-3 周）
**目标：** 能运行最小可用系统

- [ ] 搭建 Python 环境（Anaconda + 虚拟环境）
- [ ] 配置密钥管理（.env 文件 + gitignore）
- [ ] 实现 yfinance 数据采集（价格 + 基本面）
- [ ] 设计 SQLite 数据库 schema（offline_asset + holdings）
- [ ] 基础数据清洗和标准化 DataFrame 格式
- [ ] 第一个 Jupyter Notebook：单只股票基本面分析

**交付物：** 可以分析任意股票基本面的 Notebook

---

### 第二阶段：投资组合管理（2-3 周）
**目标：** 能够监控真实持仓

- [ ] 实现 Alpaca / IB API 接入（或手动录入持仓）
- [ ] 持仓数据统一化（多来源合并）
- [ ] Google Sheets 导出（gspread 集成）
- [ ] 资产类型分类处理（股票/ETF/债券）
- [ ] 被动收入计算（股息 + 债券利息）
- [ ] Streamlit 基础仪表盘（总览 + 持仓列表）

**交付物：** 可以查看组合总览的 Streamlit App

---

### 第三阶段：基本面分析引擎（3-4 周）
**目标：** 量化筛选投资标的

- [ ] 财务报表自动拉取和解析（yfinance / EODHD）
- [ ] 核心指标计算（P/E, P/B, ROE, D/E, FCF等）
- [ ] 股息分析（股息成长性、可持续性评分）
- [ ] 公司评分卡（Scorecard）系统
- [ ] 行业（GICS）分类和横向对比
- [ ] 分析师评级聚合展示

**交付物：** 输入 Ticker 输出完整基本面评分卡

---

### 第四阶段：技术分析（2-3 周）
**目标：** 图表分析辅助入场出场时机

- [ ] K 线图（plotly 交互式）
- [ ] 移动平均线（SMA 20/50/200, EMA 12/26）
- [ ] MACD + RSI + Bollinger Bands
- [ ] 黄金/死亡交叉信号检测
- [ ] 一目均衡表（Ichimoku Cloud）
- [ ] 集成进 Streamlit 技术分析页面

**交付物：** Streamlit 技术分析仪表盘

---

### 第五阶段：风险管理（2-3 周）
**目标：** 量化风险，优化组合权重

- [ ] VaR 计算（历史法 + 参数法，95%/99%）
- [ ] 最大回撤（Max Drawdown）计算
- [ ] Sharpe Ratio 计算
- [ ] 相关性矩阵热图
- [ ] Markowitz 有效前沿优化
- [ ] Shiller CAPE 比率监控
- [ ] 再平衡建议算法
- [ ] 止损价格管理

**交付物：** 风险报告 + 组合优化建议

---

### 第六阶段：AI 研究助手（3-4 周）
**目标：** 用 LLM 自动化定性研究

- [ ] Claude API 集成（anthropic SDK）
- [ ] Prompt 仓库设计（公司分析、行业分析模板）
- [ ] 新闻抓取 + 情绪分析
- [ ] LangChain Agent 搭建（多工具调用）
- [ ] RAG：向量化存储历史分析报告
- [ ] 自动生成公司研究摘要
- [ ] 导出研究结果至 Notion

**交付物：** 输入股票代码，AI 自动生成综合研究报告

---

### 第七阶段：事件监控与警报（1-2 周）
**目标：** 不错过重要市场事件

- [ ] 财报日历订阅（持仓公司）
- [ ] 宏观经济数据更新监控
- [ ] 价格警报（突破关键位）
- [ ] 邮件 / Slack 通知集成
- [ ] 事件影响快速评估 Prompt

**交付物：** 自动化事件监控 + 推送通知

---

## 五、项目目录结构（建议）

```
investing/
├── data/                    # 数据存储
│   ├── db/                  # SQLite 数据库
│   └── cache/               # API 缓存
├── notebooks/               # Jupyter 探索性分析
│   ├── 01_data_collection.ipynb
│   ├── 02_fundamental_analysis.ipynb
│   ├── 03_technical_analysis.ipynb
│   ├── 04_risk_management.ipynb
│   └── 05_portfolio_monitor.ipynb
├── src/
│   ├── data/                # 数据采集模块
│   │   ├── yfinance_client.py
│   │   ├── broker_alpaca.py
│   │   └── offline_assets.py
│   ├── analysis/            # 分析引擎
│   │   ├── fundamental.py   # 基本面指标
│   │   ├── technical.py     # 技术指标
│   │   └── risk.py          # 风险指标
│   ├── ai/                  # AI 模块
│   │   ├── llm_client.py    # LLM 统一接口
│   │   ├── agents.py        # LangChain agents
│   │   ├── prompts/         # Prompt 模板库
│   │   └── rag.py           # RAG 实现
│   ├── portfolio/           # 组合管理
│   │   ├── monitor.py       # 持仓监控
│   │   ├── optimizer.py     # Markowitz优化
│   │   └── rebalancer.py    # 再平衡逻辑
│   └── export/              # 导出模块
│       ├── sheets.py        # Google Sheets
│       └── notion.py        # Notion
├── dashboard/               # Streamlit 应用
│   └── app.py
├── config/                  # 配置
│   └── settings.py
├── .env                     # 密钥（不入git）
├── .env.example             # 密钥模板
└── requirements.txt
```

---

## 六、关键风险与注意事项

1. **API 限制**：yfinance 免费但不稳定，生产环境建议用 EODHD 或 Alpha Vantage
2. **数据质量**：财务数据可能有延迟或错误，关键决策前需交叉验证
3. **LLM 幻觉**：AI 输出仅供参考，不能替代独立研究和判断
4. **密钥安全**：Broker API Key 绝不提交 git，使用 .env + Secrets Manager
5. **法律合规**：不同国家对自动化交易有不同监管要求，自动执行交易前须确认合规
6. **回测偏差**：历史表现不代表未来，注意前视偏差（Look-ahead Bias）

---

## 七、参考资源

- 书籍：*Investing for Programmers* GitHub 仓库：https://github.com/StefanPapp/investing-for-programmers
- yfinance 文档
- LangChain 文档
- Streamlit 文档
- OpenBB 文档
- Alpaca API 文档

---

*方案制定日期：2026-03-11*
