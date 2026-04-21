# Interviewer Agent MVP

一个基于 `FastAPI + SQLAlchemy + Agent Runtime + PydanticAI` 的面试 Agent 项目。

当前已经具备这些核心能力：
- 创建一场面试
- 连续完成 5 轮问答
- 所有轮次入库
- 生成结构化评分报告
- 查看历史面试
- 在 `mock / Gemini / OpenAI` 之间切换 provider
- 对 prompt 做独立版本化
- 通过 `PydanticAI` 作为可选评分后端
- 把互联网零散题库采集为 Agent 可用的结构化知识

## 当前架构

```text
app/
  agent/                  # interviewer agent 核心：state / policies / tools / loop
  api/                    # FastAPI 路由
  core/                   # 配置、prompt、runtime settings、lifespan
  db/                     # SQLAlchemy session 与 ORM 模型
  domain/                 # schemas / services
  infra/
    llm/                  # mock / gemini / openai provider adapter
    question_bank/        # 题库采集 crawler / extractor
    repositories/         # repository 层
    scoring/              # PydanticAI 等评分后端
  prompts/versions/       # prompt 版本目录
  main.py
templates/
  index.html              # 前端工作台
tests/
```

## Python 版本

项目现在以 `Python 3.11` 为主开发版本。

- `Python 3.9` 还能跑现有基础链路
- 但 `PydanticAI` 官方要求 `Python 3.10+`
- 因此如果要启用 `SCORING_BACKEND=pydanticai` 或题库采集 Agent，请使用 `Python 3.11`

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

打开：
- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 默认本地模式

`.env.example` 默认配置为：

```env
LLM_PROVIDER=mock
LLM_MODEL=mock-interviewer-v1
PROMPT_VERSION=v1
SCORING_BACKEND=provider
DATABASE_URL=sqlite:///./app.db
MAX_TURNS=5
```

这意味着：
- 不需要真实模型也能跑完整面试流程
- 默认评分走现有 provider adapter

## 启用 PydanticAI 评分

如果你已经切到 `Python 3.11`，可以把评分后端切到 `PydanticAI`。

### 本地可验证路径

```env
LLM_PROVIDER=mock
SCORING_BACKEND=pydanticai
```

这会使用 `PydanticAI + FunctionModel` 跑一条真实的本地评分链路，不依赖外部 API key。

### OpenAI 路径

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-key
SCORING_BACKEND=pydanticai
```

### Gemini 路径

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3-flash-preview
GEMINI_API_KEY=your-key
SCORING_BACKEND=pydanticai
```

## 题库采集 ETL

题库采集不是简单爬虫，而是一条面向 Agent 的 ETL 管道：

1. 抓取：把网页转成干净 Markdown
2. 提取：用 `PydanticAI` 把题目抽成结构化对象
3. 清洗：去重、补标签、归一化分类
4. 加载：落到结构化数据库，供后续 Agent 检索和使用

### 结构化对象

题库对象定义在 `D:\CS\interviewer-agent-mvp\app\domain\schemas\question_bank.py`，核心字段包括：
- `title`
- `category`
- `difficulty`
- `content`
- `standard_answer`
- `follow_up_suggestions`
- `tags`
- `source_url`

### 采集接口

- `POST /api/question-bank/collect`
- `GET /api/question-bank`
- `GET /api/question-bank/{id}`

### 直接上传 Markdown 采集

```json
{
  "raw_markdown": "# 示例题库\n\n请设计线程安全的 LRU 缓存。",
  "source_title": "示例题库",
  "category_hint": "系统设计",
  "max_questions": 20
}
```

### 从网页 URL 采集

```json
{
  "source_url": "https://example.com/interview-questions",
  "category_hint": "机器学习",
  "max_questions": 20
}
```

默认会使用内置的轻量 HTTP crawler。  
如果你要启用 Firecrawl，请先安装 Firecrawl SDK，并在 `.env` 里配置：

```env
FIRECRAWL_API_KEY=your-key
```

然后在请求里加：

```json
{
  "source_url": "https://example.com/interview-questions",
  "use_firecrawl": true
}
```

## 当前主要接口

- `GET /`
- `GET /health`
- `GET /api/runtime/llm`
- `PUT /api/runtime/llm`
- `GET /api/interviews`
- `POST /api/interviews`
- `POST /api/interviews/{id}/reply`
- `POST /api/interviews/{id}/finish`
- `GET /api/interviews/{id}`
- `GET /api/interviews/{id}/report`
- `GET /api/question-bank`
- `GET /api/question-bank/{id}`
- `POST /api/question-bank/collect`

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 下一步建议

1. 给题库采集加批量 URL 队列和失败重试
2. 把题库检索接进 interviewer agent 的 tools，支持“按岗位和标签选题”
3. 增加向量索引，让 Agent 能做语义检索和相似题召回
4. 为题库 prompt 增加版本化对比与回滚
