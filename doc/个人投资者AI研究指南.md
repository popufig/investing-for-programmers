# 个人投资者 AI 研究指南

> 基于《Investing for Programmers》第 8、9 章核心理念，结合 AI Agent 时代的现代实现方式。
> 面向有技术背景的个人投资者，聚焦长期价值投资研究。
>
> **不涉及**：虚拟货币、高频量化交易、对冲基金、私募投资。

---

## 一、书中核心理念（仍然有效）

书中的 Python 代码和框架选择已经过时，但底层的**投资研究理念**仍然有价值。

### 1. LLM 是研究助手，不是投资顾问

书中反复强调：不要问 LLM「推荐三只股票」，而应该用它做**深度研究加速器**。

**有效的用法**：
- 理解公司管理层风格和战略方向
- 分析竞争优势（economic moat）和商业模式
- 评估非财务风险（地缘政治、气候、监管变化）
- 将 60 页财报浓缩为关键事实摘要
- 寻找「类似 Netflix 早期」的公司特征

**无效的用法**：
- 让 LLM 直接给买卖建议
- 把 LLM 的回答当作事实（幻觉问题严重）
- 只用一个模型的观点做决策

书中做了一个对照实验：用相同的投资者画像分别问 GPT-4o、Gemini 和 Finance Chat「巴菲特/林奇风格的选股」，三者推荐的股票几乎没有交集，其中还包含已改名的公司（Square → Block）和疫情特殊标的（Zoom）。**结论：LLM 推荐本身不可靠，但可以作为研究起点。**

### 2. 构建个人投资者画像

书中提出 6 个维度的投资者画像，作为所有 AI 研究的上下文基础：

| 维度 | 说明 | 示例 |
|------|------|------|
| **目标** | 量化的投资目标和时间线 | 5 年内实现财务自由，50 万美元起步 |
| **风险偏好** | 诚实评估自己能承受多大波动 | 对深度研究过的标的可接受中等风险 |
| **经验** | 专业背景和投资年限 | 程序员背景，3 年股票经验 |
| **资产经验** | 熟悉哪些资产类别 | 股票、ETF、债券 |
| **税务** | 税务身份和居住地 | 中国税务居民 |
| **伦理偏好** | 价值观投资限制 | 回避烟草、军工 |

**为什么这很重要**：同样一个问题，带上投资者画像后 LLM 给出的分析会更有针对性。画像定义一次，长期复用。

### 3. 股票聚类发现异常机会

书中用 K-means 聚类分析 S&P 500 成分股：

- **维度**：年化收益率 × 年化波动率
- **方法**：先用 Elbow Curve 确定最优聚类数（一般 3-5 个），再可视化
- **价值**：发现统计特征上偏离同类的股票（outlier），作为**进一步研究的线索**

书中的实际发现：Moderna（低收益高波动）、Palantir（高收益较低波动）、Super Micro Computer（极高波动率）。

**重要警告**：聚类结果只反映历史价格的统计特征，**不能直接推导投资结论**。「高收益低波动」不等于「被低估」，「低收益高波动」也不等于「即将反转」——这些判断需要基本面分析和估值验证才能成立。正确的使用方式是：

1. 聚类 → 发现统计异常的 ticker
2. 对这些 ticker 做基本面研究（财报、竞争格局、管理层）
3. 做估值分析（DCF、相对估值）确认是否真的存在错误定价
4. 只有在基本面和估值都支持时，才构成投资论点

### 4. 结构化分析框架

书中强调：对不同公司执行**相同的分析框架**，才能横向比较。

- **SWOT 分析**：优势、劣势、机会、威胁
- **波特五力**：供应商议价力、买方议价力、新进入者威胁、替代品威胁、行业竞争
- **BCG 矩阵**：明星、现金牛、问号、瘦狗

关键不在于框架本身多复杂，而在于**一致性**——用同一个框架分析 5 家同行业公司，差异自然浮现。

### 5. 用最新数据增强 LLM（RAG 概念）

LLM 有知识截止日期。书中用 RAG（检索增强生成）解决这个问题：

- 加载财报电话会议记录（earnings call transcripts）
- 加载最新行业新闻和分析师报告
- 加载公司 EDGAR 文件

**核心思路**：把最新数据作为上下文提供给 LLM，让它基于新信息做分析，而不是依赖训练数据中的旧信息。

### 6. 多视角决策（Multi-Agent 概念）

书中用「法庭辩论」模型来避免单一视角的确认偏差：

- **乐观派（Bull Case）**：分析增长潜力、盈利能力、行业趋势
- **怀疑派（Bear Case）**：分析下行风险、宏观逆风、估值过高
- **裁判（Adjudicator）**：综合两方论点，给出权衡后的结论

书中还做了一个有趣的实验：用不同的上下文（支持 LiDAR vs 反对 LiDAR）问同样的问题，LLM 给出了完全不同的推荐。这证明了：**有意识地切换视角比依赖单一 prompt 更可靠**。

---

## 二、现代实现方式：Skills + Tools + ACP

### 核心思路

书中的方法是：手动写 Python 调 LLM API，一次性 prompt 调用，LangChain 搭管道。这些在 AI Agent 时代已经不是最佳实践。

现代方式的关键转变不是「换一个 Agent 来用」，而是**把投资研究能力封装为 Skills 和 CLI Tools，通过开放协议让任何 Agent 调用**。

```
你（投资者）
  │
  ├── ACPX（Agent 调度层）
  │     ├── Claude Code
  │     ├── Codex
  │     ├── Gemini CLI
  │     └── 其他 ACP 兼容 Agent ...
  │
  ├── Skills（Markdown 定义的分析框架）
  │     ├── investor-profile    ← 投资者画像
  │     ├── company-analysis    ← 结构化公司分析
  │     ├── bull-bear-debate    ← 多视角辩论
  │     └── ...
  │
  ├── Tools（CLI 脚本，Agent 通过 bash 调用）
  │     ├── tools/cluster.py         ← 聚类分析
  │     ├── tools/analyst-targets.py ← 分析师目标价
  │     ├── tools/fetch-financials.py← 财务数据获取
  │     └── ...
  │
  └── research/（研究档案，git 版本控制）
```

**为什么这样设计**：

1. **Agent 可替换**：Skills 和 Tools 是你的资产，不绑定任何特定 Agent。今天用 Claude Code，明天换 Codex，研究能力不丢失。
2. **计算可复现**：CLI 工具的数据处理部分是确定性的（固定种子、固定参数）。但注意：Agent 的推理输出（Skill 生成的分析文本）本质上不可复现——不同模型、不同温度、不同上下文窗口都会产生不同结果。因此每次研究需要落盘输入快照（见「研究归档」一节）。
3. **可审计**：每次分析输出写入 `research/` 目录，git 追踪变更历史。配合输入快照，可以回溯「当时基于什么数据得出了什么结论」。
4. **渐进式建设**：从一个 Skill 开始，逐步积累。不需要一次搭完整个系统。

### 与书中方法的对比

| 书中方法 | 问题 | Skills + Tools + ACP |
|----------|------|----------------------|
| 手写 Python 调 OpenAI/Gemini API | 样板代码多，模型绑定 | Agent 负责 LLM 交互，你只定义 Skill |
| LangChain 搭 RAG pipeline | 维护成本高 | Agent 直接读文件/搜网页；大规模时再加向量库 |
| SQLite 存 Prompt 模板 | 手动管理 | Skill = Markdown 文件，git 管理，通过项目指令/ACPX 让不同 Agent 发现 |
| 手写聚类代码 + notebook | 每次调试 | 固化为 `tools/cluster.py`，Agent 传参调用 |
| Notion API 导出 | 大量对接代码 | Agent 写入 `research/` 目录，git 自动留痕 |
| 多脚本串联 | 脆弱 | Agent 多轮 tool calling 编排，失败时自动诊断 |

### ACP：Agent 调度层

[ACPX](https://github.com/openclaw/acpx) 是 Agent Client Protocol 的 CLI 实现，解决的问题是：**用统一的方式调度不同的 Agent 来执行你的 Skills**。

核心能力：
- **持久会话**：以 repo 为单位维护会话状态，跨多次 CLI 调用不丢失上下文
- **多 Agent 后端**：内置适配 Claude Code、Codex、Gemini CLI 等，通过 adapter 桥接
- **结构化消息**：Agent 的 thinking、tool 调用、结果以 JSON 事件流输出，不是解析终端文本
- **命名会话**：可以并行维护多个研究工作流（`-s nvda-research`、`-s sp500-screening`）

**典型用法**：

```bash
# 用 Claude Code 对 NVDA 做公司分析（会自动加载项目中的 Skills）
acpx -a claude "用 company-analysis 分析 NVDA"

# 用 Codex 跑聚类分析（调用 tools/cluster.py）
acpx -a codex "运行 tools/cluster.py --period 1y --clusters auto，分析结果中的 outlier"

# 多视角：先用一个 Agent 做 bull case，再用另一个做 bear case
acpx -a claude -s nvda-bull "以乐观视角分析 NVDA 的增长前景"
acpx -a codex  -s nvda-bear "以怀疑视角分析 NVDA 的风险"
```

不同 Agent 有不同的强项（推理深度、代码执行、网页搜索），通过 ACP 统一调度可以扬长避短。

### Skills：可复用的分析框架

Skills 是 Markdown 文件，放在项目的 `skills/` 目录中。任何 ACP 兼容的 Agent 进入项目时都能自动发现并使用。

#### Skill 1：投资者画像

```markdown
---
name: investor-profile
description: 个人投资者画像和分析偏好，所有投资研究时自动加载为上下文
---

# 投资者画像

## 基本信息
- 目标：5年内建立被动收入组合，年化目标 8-12%
- 风险偏好：中等，深度研究后可接受较高波动
- 经验：程序员背景，3 年股票投资经验
- 资产类型：股票、ETF、债券
- 税务：中国税务居民
- 回避：烟草、军工、博彩

## 分析偏好
- 偏好有技术壁垒（moat）的公司
- 关注行业：AI、清洁能源、医疗科技
- 估值方法：DCF + 相对估值
- 持有周期：1-5 年
```

#### Skill 2：公司分析框架

```markdown
---
name: company-analysis
description: 对目标公司执行标准化投资分析（SWOT/五力/护城河/风险/估值），输出带证据链的结构化报告
---

# 公司分析框架

对目标公司依次执行以下分析，每个部分独立输出。

## 证据链要求

每条关键判断必须附带：
- **来源**：数据出处（财报页码、新闻链接、数据库名）
- **日期**：数据截止日期
- **置信度**：高/中/低（基于来源可靠性和数据新鲜度）
- **待验证项**：标记需要人工核实的内容（尤其是 LLM 生成的定性判断）

## 第一步：公司概况
- 商业模式、收入结构、主要客户群
- 管理层背景和风格
- 近期战略方向和重大事件

## 第二步：SWOT 分析
按表格输出优势、劣势、机会、威胁。每项附来源。

## 第三步：波特五力
评估五个维度的竞争强度（高/中/低），附简要理由和数据来源

## 第四步：护城河评估
- 网络效应、转换成本、规模经济、品牌、专利/牌照
- 护城河宽度评级：宽/中/窄/无
- 标注评级依据的具体证据

## 第五步：风险清单
- 财务风险、监管风险、竞争风险、技术替代风险
- 非财务风险：ESG、地缘政治、管理层变动
- 每项风险标注发生概率（高/中/低）和影响程度

## 第六步：估值参考
- 当前 PE/PS/PB 与行业中位数对比（标注数据日期和来源）
- 分析师共识目标价范围（标注覆盖分析师数量和日期）

## 第七步：待验证清单
汇总以上分析中所有标记为「待验证」的项目，作为后续人工核实的 checklist

## 输出
将完整报告写入 `research/companies/{TICKER}_{DATE}.md`
```

#### Skill 3：多视角辩论

```markdown
---
name: bull-bear-debate
description: 对目标公司执行多视角分析（乐观/怀疑/裁判），输出结构化的投资论点对比
---

# 多视角辩论框架

## 第一轮：Bull Case
以乐观投资者的视角分析目标公司。重点关注增长潜力、市场地位、技术壁垒。
每个论点附具体数据来源。

## 第二轮：Bear Case
以怀疑论者视角分析目标公司。重点关注估值泡沫风险、竞争威胁、周期性下行。
每个论点附具体数据来源。

## 第三轮：裁判
综合以上两个视角，给出权衡后的结论：
- 哪些 bull/bear 论点更有说服力
- 整体置信度评级（强看多/弱看多/中性/弱看空/强看空）
- 需要人工验证的关键假设清单

## 输出
将辩论记录写入 `research/decisions/{TICKER}-bull-bear-{DATE}.md`
```

### Tools：确定性的 CLI 脚本

Skills 负责「怎么思考」，Tools 负责「怎么取数据和计算」。Tools 是普通的 Python 脚本，Agent 通过 bash 调用。数据处理逻辑确定（固定种子、固定算法），但输入数据本身会随时间变化（行情、成分股调整等），因此每次运行需要落盘输入快照（见「研究归档」一节）。

#### Tool 1：聚类分析

```bash
# Agent 这样调用：
python tools/cluster.py --period 1y --clusters auto --output research/screening/
```

脚本内部做的事：
1. 从 Wikipedia 获取 S&P 500 成分股列表（含 ticker 清洗：BRK.B → BRK-B）
2. 用 yfinance 下载历史价格（处理下载失败和 NaN）
3. 计算年化收益率和波动率（252 交易日）
4. Elbow Curve 确定最优 k 值（或使用 `--clusters N` 手动指定）
5. K-means 聚类（固定 `random_state=42` 保证可复现）
6. 生成交互式散点图（plotly HTML）
7. 输出 outlier 列表（CSV + Markdown 摘要）

**与书中的区别**：书中的 notebook 代码每次需要手动执行和调试。封装为 CLI 工具后，Agent 只需传参调用。同时因为是独立脚本，也可以脱离 Agent 直接运行或纳入 CI 定期执行。

#### Tool 2：分析师目标价

```bash
python tools/analyst-targets.py NVDA --output research/companies/
```

输出：当前价、高/均/低目标价、涨跌幅百分比、覆盖分析师数量、对比图表。

#### Tool 3：财务数据获取

```bash
python tools/fetch-financials.py NVDA --metrics pe,ps,pb,roe,debt-equity --peers INTC,AMD,AVGO
```

输出：目标公司与同行的财务指标对比表（Markdown + CSV）。

### 最新数据：文件 + 搜索，按需升级

书中为此搭建了完整的 RAG pipeline（chunking → embedding → 向量数据库 → retrieval）。对个人投资者，分阶段处理：

**起步阶段**（推荐）：
- 财报 PDF、电话会议记录放在 `data/` 目录，Agent 直接读取分析
- Agent 搜索网页获取最新新闻
- Agent 执行 Python 调用 yfinance 获取近实时行情数据（有延迟，非盘中实时）

**积累阶段**（数百份文档后按需搭建）：
- 向量数据库用于跨文档语义检索（如「哪些公司在最近财报中提到了 AI capex 削减」）
- 此时搭建 RAG 有明确价值，因为 Agent 的上下文窗口无法一次装入所有文档

### 研究归档

每次分析输出写入 `research/` 目录，git 追踪。为了事后可回溯「当时基于什么数据得出了什么结论」，每份研究报告应包含**输入快照元数据**：

```markdown
# NVDA 公司分析 — 2026-03-18

## 元数据
- 运行时间：2026-03-18T14:30:00+08:00
- Agent：Claude Code (claude-opus-4-6)
- Skill：company-analysis v1.2
- Tools 调用：
  - `tools/fetch-financials.py NVDA --metrics pe,ps,pb` → data/snapshots/NVDA_financials_20260318.csv
  - `tools/analyst-targets.py NVDA` → data/snapshots/NVDA_targets_20260318.json
- 外部数据源：yfinance 0.2.x，数据截止 2026-03-17 收盘
- 额外上下文：data/earnings/NVDA_Q4_2025_transcript.txt

## 分析内容
...
```

Tools 脚本应自动将拉取的原始数据保存到 `data/snapshots/`，文件名含日期，确保输入可追溯。

```bash
# Agent 分析完成后自动写入
research/companies/NVDA_2026-03-18.md

# 原始数据快照同步保存
data/snapshots/NVDA_financials_20260318.csv
data/snapshots/sp500_prices_20260318.parquet

# 你可以随时 git log 查看研究历史
git log --oneline research/companies/NVDA_*
```

长期积累形成个人研究档案库，可审计、可回溯。

---

## 三、实践清单

### 值得做的

**搭建阶段**（一次性）：
- [ ] **创建 `investor-profile` Skill**——定义你的目标、风险偏好、回避领域
- [ ] **创建 `company-analysis` Skill**——SWOT / 五力 / 护城河 / 估值的标准化框架
- [ ] **创建 `bull-bear-debate` Skill**——多视角辩论模板
- [ ] **封装 `tools/cluster.py`**——聚类分析 CLI 工具（处理好 ticker 清洗、NaN、随机种子）
- [ ] **封装 `tools/analyst-targets.py`**——分析师目标价获取和可视化
- [ ] **初始化 `research/` 目录结构**——git 追踪

**日常研究**（持续）：
- [ ] **公司尽职调查**——通过 Skill 研究管理层、竞争格局、非财务风险
- [ ] **聚类筛选**——定期运行 `tools/cluster.py`，对 outlier 做基本面验证
- [ ] **多视角评估**——用 bull-bear-debate Skill 避免确认偏差
- [ ] **对比分析师共识 vs 自己的判断**——量化你与市场的分歧
- [ ] **多 Agent 对比**——同一 Skill 让不同 Agent 执行，关注分歧点
- [ ] **维护研究档案**——每次分析输出到 `research/`，git commit 留痕

### 不建议做的

- **ML 短期股价预测**——书中明确指出：市场是随机游走的，Random Forest 预测误差随时间漂移，不可靠
- **盲目跟随 LLM 推荐**——幻觉问题无法根除，LLM 会自信地给出错误信息
- **日内交易 / 高频交易**——需要极低延迟和专业基础设施，不适合个人投资者
- **过度依赖技术指标预测**——历史模式在经济结构变化（AI 颠覆、政策转向）面前会失效
- **过早建设重型基础设施**——起步阶段不需要自建 RAG pipeline 或向量数据库，Agent 可以覆盖大部分探索性研究需求；等研究资料积累到一定规模再考虑

### 关于 ML 预测的特别说明

书中第 8 章用 Random Forest 做了苹果股价预测实验（RMSE = 3.99），并诚实地总结了 ML 预测失败的原因：

1. **有效市场假说**：公开信息已被价格反映
2. **随机游走**：短期价格受群体心理驱动，无可预测模式
3. **社会/技术变革**：AI 颠覆、ESG 兴起等结构性变化让历史数据失效
4. **会计灵活性**：公司可以调整财报呈现方式
5. **过拟合/欠拟合**：特征太少欠拟合，太多则拟合噪声
6. **泡沫**：郁金香狂热、dot-com 泡沫——非理性繁荣无法被模型捕捉

**结论**：把精力花在理解公司基本面上，而不是预测股价走势。

---

## 四、项目结构与工具建议

### 推荐的项目目录结构

```
investing-research/
├── skills/                          # Agent 可发现的 Skill 定义
│   ├── investor-profile/
│   │   └── SKILL.md
│   ├── company-analysis/
│   │   └── SKILL.md
│   └── bull-bear-debate/
│       └── SKILL.md
├── tools/                           # 确定性 CLI 脚本
│   ├── cluster.py
│   ├── analyst-targets.py
│   └── fetch-financials.py
├── data/                            # 原始数据（财报 PDF、会议记录等）
│   ├── earnings/
│   ├── filings/
│   └── snapshots/                   # Tools 自动保存的输入数据快照（含日期）
├── research/                        # 研究输出（git 追踪）
│   ├── companies/
│   │   ├── NVDA_2026-03-18.md
│   │   └── MSFT_2026-03-15.md
│   ├── screening/
│   │   └── sp500-clustering-2026Q1.md
│   └── decisions/
│       └── NVDA-bull-bear-2026-03-18.md
├── CLAUDE.md                        # Claude Code 项目指令
├── codex.md                         # Codex 项目指令（如使用）
├── .gemini/                         # Gemini CLI 配置（如使用）
└── .gitignore
```

Skills 和 Tools 是你的核心资产，Agent 是可替换的执行层。

### 跨 Agent 的 Skill 发现与适配

不同 Agent 发现项目 Skills 的方式不同：

| Agent | Skill 发现机制 | 项目指令文件 |
|-------|---------------|-------------|
| **Claude Code** | 自动扫描 `skills/` 目录下的 `SKILL.md` | `CLAUDE.md`（在其中引用 skills） |
| **Codex** | 通过项目指令文件引导读取 | `codex.md` |
| **Gemini CLI** | 通过项目指令文件引导读取 | `.gemini/settings.json` 或指令文件 |
| **ACPX 兼容 Agent** | ACPX 层统一注入 Skill 内容到 Agent 上下文 | 由 ACPX 配置管理 |

**实践建议**：
- `skills/` 目录结构保持 Agent 无关（纯 Markdown），这是你的可移植资产
- 为你实际使用的 Agent 各维护一份项目指令文件，内容主要是：指向 `skills/` 的引用 + 该 Agent 的特定配置
- 如果通过 ACPX 调度，ACPX 负责将 Skill 注入到 Agent 会话中，减少逐个 Agent 适配的工作量

### Agent 选型

| Agent | 强项 | 适合的研究任务 |
|-------|------|----------------|
| **Claude Code** | 深度推理、长文件读取、多轮 tool calling | 公司尽职调查、多视角辩论、框架分析 |
| **Codex** | 代码生成和执行 | 聚类分析、数据可视化、Tools 脚本开发 |
| **Gemini CLI** | 网页搜索、多模态 | 最新新闻收集、财报 PDF 解读 |

通过 ACPX 统一调度，可以在同一个研究工作流中混合使用不同 Agent。核心要求：Agent 必须支持 **tool calling**（能执行代码、读写文件）和 **多轮对话**（能迭代追问）。单轮问答式的 chatbot 无法完成深度研究。

### 数据源

| 数据 | 来源 | 成本 | 注意事项 |
|------|------|------|----------|
| 历史价格 | Yahoo Finance（yfinance） | 免费 | 非官方 API，可能限速或变更；数据有延迟，不适合实时交易 |
| 分析师目标价 | Yahoo Finance | 免费 | 覆盖范围有限，部分市场（如 A 股）数据不全 |
| 财报文件 | SEC EDGAR | 免费 | 仅覆盖美股上市公司 |
| 财报电话会议记录 | Seeking Alpha / Motley Fool | 免费至付费 | 完整记录通常需要订阅（$20-30/月），免费版可能有延迟或摘要 |
| 实时新闻 | Agent 网页搜索 | 免费 | 搜索质量取决于 Agent 能力；付费新闻源（Bloomberg、Reuters）有更高质量内容 |

> **注意**：以上成本为截至 2026 年初的情况，各平台的免费额度和 API 政策可能随时变更。非美股市场（A 股、港股等）的免费数据源选择更少，可能需要额外付费服务。

### 可视化

由 Tools 脚本内置（plotly 生成交互式 HTML，matplotlib 生成静态 PNG），Agent 传参即可。常用图表：

- 聚类散点图（收益率 × 波动率，hover 显示 ticker）
- 分析师目标价对比图
- 同行财务指标雷达图
- 历史价格走势图

---

## 附录：从书中代码到 Skills + Tools 的迁移示例

### 示例 1：聚类分析

**书中方式**（ch08.ipynb，约 80 行 notebook 代码，每次手动执行）：
```python
# 需要处理 ticker 清洗（如 BRK.B → BRK-B）、下载失败、NaN、随机种子
tickers = pd.read_html(url)[0]['Symbol'].tolist()
data = yf.download(tickers, period='1y')
returns = data['Close'].pct_change().mean() * 252
volatility = data['Close'].pct_change().std() * np.sqrt(252)
kmeans = KMeans(n_clusters=5, random_state=42)
# ... 数十行代码
```

**Skills + Tools 方式**：
```bash
# 封装为 CLI 工具后，Agent 或人都可以直接调用
python tools/cluster.py --period 1y --clusters auto

# 通过 ACPX 让 Agent 调用并解读结果
acpx -a claude "运行 tools/cluster.py --period 1y，分析 outlier 并对前 5 个做初步基本面筛选"
```

关键区别：数据处理逻辑固化在 `tools/cluster.py` 中（确定性、可复现），Agent 负责解读和后续研究。

### 示例 2：多 Agent 多视角

**书中方式**（ch08.ipynb，4 段 API 调用代码分别调 OpenAI、Gemini、Claude、Mistral）：
```python
client = OpenAI()
response = client.chat.completions.create(model="gpt-4o", messages=[...])
# ... 对每个模型重复类似代码
```

**ACP 方式**：
```bash
# 同一个 Skill，不同 Agent 后端 → 天然的多视角
acpx -a claude -s nvda "用 company-analysis 分析 NVDA，输出到 research/companies/NVDA_2026-03-18_claude.md"
acpx -a codex  -s nvda "用 company-analysis 分析 NVDA，输出到 research/companies/NVDA_2026-03-18_codex.md"
# 对比两份输出的分歧点
acpx -a claude "对比 research/companies/NVDA_2026-03-18_claude.md 和 research/companies/NVDA_2026-03-18_codex.md 的主要分歧"
```

关键区别：不需要为每个模型写 API 调用代码，ACP 统一调度。分析框架（Skill）保持一致，差异来自不同 Agent 的推理能力。

### 示例 3：财报分析（替代 RAG pipeline）

**书中方式**（ch09.ipynb，约 40 行 pipeline 搭建代码）：
```python
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
splits = text_splitter.split_documents(docs)
vector_store = InMemoryVectorStore(OpenAIEmbeddings())
vector_store.add_documents(splits)
# ... 构建 LangGraph state machine
```

**Skills + Tools 方式**：
```bash
# 财报放入 data/ 目录，Agent 直接读取（无需向量化）
acpx -a claude "读取 data/earnings/NVDA_Q4_2025_transcript.txt，\
  结合 investor-profile 的偏好，分析增长前景和管理层信心，\
  输出到 research/companies/NVDA_2026-03-18.md"
```

关键区别：对于单份或少量文档，Agent 直接读取比搭 RAG pipeline 效率高得多。向量数据库留到文档积累到数百份、需要跨文档语义检索时再引入。

---

*本指南的核心信息：书中的投资研究**理念**值得学习和实践。**实现方式**应该从「手写 Python 调 API」升级为「Skills 定义研究框架 + Tools 封装数据处理 + ACP 调度 Agent 执行」。你的精力应该花在定义好的分析框架和验证投资论点上，而不是搭建技术管道。Skills 和 Tools 是你的长期资产，Agent 是可替换的执行层。*
