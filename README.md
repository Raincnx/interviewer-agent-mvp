# Interviewer Agent

一个面向技术岗位的智能面试官 Agent 项目，目标不是简单地“调用一次 LLM 出题”，而是完整模拟一场结构化技术面试：
- 候选人上传简历
- Agent 按阶段推进面试流程
- 结合简历与题库进行追问
- 控制节奏与难度
- 生成结构化评分报告
- 将题库同时用于面试 RAG 与候选人复习

当前项目重点覆盖三类岗位：
- AI Agent 开发
- 后端开发
- 机器学习工程师

## 项目亮点
- 真正的 Agent 架构：显式拆分 `state / policies / tools / loop`
- 阶段化面试流程：自我介绍 -> 项目/实习深挖 -> 八股基础 -> 手撕/算法
- 简历驱动提问：支持 PDF、DOCX、TXT、Markdown 简历上传与解析
- 题库驱动提问：题库既能前端浏览，也能作为 Agent 的知识库进行 RAG
- 结构化评分：支持 `provider` 评分链路与 `PydanticAI` 可选评分后端
- 可切换模型：`mock / Gemini / OpenAI`
- Prompt 版本化：支持独立维护与切换 Prompt 版本
- 可持续题库采集：已经具备来源注册、原始文档存储、去重、版本化、批量采集等 ETL 能力

## 适用场景
- 用于候选人进行模拟技术面试
- 用于候选人复习知识点和题库
- 用于构建岗位专属知识库，支撑面试 Agent 的 RAG 检索
- 用于继续演进成更完整的面试平台或 AI 招聘产品

## 当前能力总览
### 面试链路
- 创建一场面试
- 上传并解析简历
- 按面试阶段推进问答
- 根据候选人级别调整问题难度
- 所有轮次入库
- 结束后生成结构化报告
- 查看历史面试与报告

### 题库链路
- 采集互联网网页或 Markdown 内容
- 使用 `PydanticAI` 将非结构化内容提取为结构化题目
- 存储来源、采集任务、原始文档、结构化题目、出现记录
- 做去重与版本化
- 前端直接浏览题库
- 面试 Agent 使用题库进行 RAG 召回

### 运行时能力
- 前端切换 `mock / Gemini / OpenAI`
- 前端切换评分后端 `provider / pydanticai`
- Prompt 版本切换
- 支持本地开发模式，不依赖真实模型即可跑通主链路

## 技术栈
### 后端
- FastAPI
- SQLAlchemy 2.x
- Pydantic / Pydantic Settings
- Uvicorn

### Agent / LLM
- 自研 Agent Runtime：`state / policies / tools / loop`
- Provider Adapter：`mock / Gemini / OpenAI`
- PydanticAI：用于结构化评分与题库抽取

### 数据层
- 默认：SQLite（本地开发）
- 目标主库：PostgreSQL
- 当前已提供 SQLite -> PostgreSQL 迁移脚本

### 前端
- 原生 HTML / CSS / JavaScript
- 由 FastAPI 直接托管页面

### 文档抓取 / ETL
- 内置轻量 HTTP crawler
- 可选 Firecrawl

### 测试
- pytest

## 目录结构
```text
app/
  agent/                  # Agent 核心：状态、策略、工具、循环
  api/                    # FastAPI 路由层
  core/                   # 配置、prompt、runtime settings、lifespan
  db/                     # ORM 模型与数据库会话
  domain/
    schemas/              # Pydantic 模型
    services/             # 业务服务：面试、评分、简历、题库、RAG
  infra/
    llm/                  # mock / gemini / openai provider 适配层
    question_bank/        # 题库 crawler / extractor
    repositories/         # 持久化仓储层
  prompts/
    versions/             # Prompt 版本目录
  main.py
scripts/                  # 迁移、批量注册来源、批量采集等脚本
templates/
  index.html              # 前端工作台
tests/                    # 测试
```

## Python 版本
推荐使用 `Python 3.11`。

原因：
- 项目主链路在 `Python 3.11` 下验证更完整
- `PydanticAI` 需要 `Python 3.10+`
- 题库采集 Agent 和可选的 `pydanticai` 评分都依赖较新的运行时

## 快速开始
### 1. 创建虚拟环境
```powershell
py -3.11 -m venv .venv
```

### 2. 安装依赖
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. 准备环境变量
```powershell
Copy-Item .env.example .env
```

### 4. 启动服务
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开前端：
- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 默认本地模式
如果你只是想快速跑通链路，推荐直接使用 `mock`：

```env
LLM_PROVIDER=mock
LLM_MODEL=mock-interviewer-v1
PROMPT_VERSION=v1
SCORING_BACKEND=provider
DATABASE_URL=sqlite:///./app.db
MAX_TURNS=8
```

这意味着：
- 不需要真实模型 API Key
- 可以完整体验面试、简历、评分、题库浏览等主链路
- 适合本地开发与测试

## 真实模型配置
### Gemini
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-flash-preview
GEMINI_API_KEY=your-key
SCORING_BACKEND=provider
```

### OpenAI
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-key
SCORING_BACKEND=provider
```

也可以直接在前端通过“运行时模型配置”切换 Provider、模型名和评分后端。

## 启用 PydanticAI 评分
### 本地验证路径
```env
LLM_PROVIDER=mock
SCORING_BACKEND=pydanticai
```

这条链路会使用 `PydanticAI + FunctionModel`，不依赖外部模型服务，适合验证结构化评分逻辑。

### 真实模型路径
```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-flash-preview
GEMINI_API_KEY=your-key
SCORING_BACKEND=pydanticai
```

或：

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-key
SCORING_BACKEND=pydanticai
```

## 主要页面与能力
### 面试工作台
- 创建面试
- 上传并解析简历
- 查看结构化简历画像
- 在聊天区完成多轮面试
- 查看每轮参考的简历片段与题库条目
- 查看结构化评分报告

### 题库浏览
- 查看结构化题目列表
- 查看题目详情、标准答案、追问建议、来源信息
- 作为候选人复习知识点使用
- 同时作为 Agent 的知识库使用

## 面试流程设计
当前 Agent 的默认面试节奏是约 `60 分钟` 的结构化技术面试，分为四个阶段：
1. 自我介绍
2. 项目 / 实习深挖
3. 八股基础
4. LeetCode / 手撕题

特点：
- Agent 会显式切阶段，而不是无休止追同一话题
- 切换阶段时会给出 wrap-up 过渡语
- 不同级别会影响问题深度和追问方式
- 每轮会结合当前阶段、简历内容、题库知识进行生成

## 简历能力
支持文件类型：
- PDF
- DOCX
- TXT
- Markdown

当前简历链路：
- 提取文本
- 清洗中文内容
- 解析结构化画像（项目、技能、教育、经历）
- 将结构化画像与原始片段同时供 Agent 使用

## 题库 ETL 设计
题库不是单张表，而是一套可持续采集的 ETL 原始库。

### 已实现的对象
- `question_sources`：来源注册
- `question_collection_jobs`：采集任务
- `raw_question_documents`：原始文档
- `structured_questions`：结构化题目
- `question_occurrences`：题目出现记录

### 已实现的能力
- 来源追溯
- 原始 Markdown 存储
- 结构化题目存储
- `canonical_hash` 去重
- `content_hash` 版本识别
- occurrence 记录
- 批量来源注册
- 批量采集
- 启用来源的定时采集

### 当前覆盖的岗位方向
- AI Agent
- 后端开发
- 机器学习工程师

### 当前题库来源类型
- 小林面试笔记 / 小林 coding
- GitHub 开源面试仓库
- Markdown README / 专题文档
- 手动提交的 Markdown 内容

## 常用接口
### 系统
- `GET /`
- `GET /health`
- `GET /api/runtime/llm`
- `PUT /api/runtime/llm`

### 面试
- `GET /api/interviews`
- `POST /api/interviews`
- `GET /api/interviews/{id}`
- `POST /api/interviews/{id}/reply`
- `POST /api/interviews/{id}/finish`
- `GET /api/interviews/{id}/report`

### 简历
- `POST /api/resume/parse`

### 题库
- `GET /api/question-bank`
- `GET /api/question-bank/{id}`
- `POST /api/question-bank/collect`
- `GET /api/question-bank/sources`
- `POST /api/question-bank/sources`
- `POST /api/question-bank/sources/bootstrap`
- `GET /api/question-bank/jobs`
- `GET /api/question-bank/raw-documents`
- `POST /api/question-bank/collect/enabled`

## 常用脚本
### 1. SQLite -> PostgreSQL 迁移
```powershell
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py `
  --source-url sqlite:///./app.db `
  --target-url postgresql+psycopg://postgres:postgres@localhost:5432/interviewer_agent `
  --truncate-target
```

### 2. 批量注册默认来源
```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_question_sources.py
```

按岗位筛选：
```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_question_sources.py --job-track ai-agent --job-track backend
```

### 3. 批量采集已启用来源
```powershell
.\.venv\Scripts\python.exe scripts\collect_registered_sources.py
```

按岗位筛选：
```powershell
.\.venv\Scripts\python.exe scripts\collect_registered_sources.py --job-track ml-engineer
```

> 注意：命令行脚本读取 `.env` 中的配置。如果你要在脚本里使用真实模型，请确保 `.env` 已写入有效的 `GEMINI_API_KEY` 或 `OPENAI_API_KEY`。

## 运行测试
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 当前项目状态
当前已经完成从“可运行骨架”到“Interviewer Agent MVP”的第一阶段建设：
- Agent 架构已成型
- 面试主链路可用
- 简历链路可用
- 题库浏览与题库 RAG 可用
- ETL 原始库可持续扩展

## 下一阶段建议
1. 引入正式的数据库迁移体系（Alembic）
2. 为题库页补搜索、筛选、来源与版本展示
3. 将题库检索升级为向量检索
4. 为采集任务补失败重试和运营入口
5. 将面试节奏从“按轮次估算”继续升级到“按真实时间动态控制”

## 相关文档
- 架构说明：`docs/architecture.md`
