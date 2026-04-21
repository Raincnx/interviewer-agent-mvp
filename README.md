# Interviewer Agent MVP

一个基于 `FastAPI + SQLAlchemy + Agent Runtime` 的面试智能体项目。

当前项目已经具备这些核心能力：

- 创建一场面试
- 连续完成 5 轮问答
- 所有轮次入库
- 生成结构化评分报告
- 查看历史面试
- 在 `mock / Gemini / OpenAI` 间切换 provider
- 对 prompt 做独立版本化
- 通过 `PydanticAI` 作为可选评分后端

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
- 因此如果要启用 `SCORING_BACKEND=pydanticai`，请使用 `Python 3.11`

## 快速开始（Windows / PowerShell）

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

如果你已经切到 Python 3.11，可以把评分后端切到 `PydanticAI`。

### 本地可验证路径

```env
LLM_PROVIDER=mock
SCORING_BACKEND=pydanticai
```

这会使用 `PydanticAI + FunctionModel` 跑一条真实的 PydanticAI 本地评分链路，不依赖外部 API key。

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
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your-key
SCORING_BACKEND=pydanticai
```

## 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
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

## 下一步建议

1. 把 `scoring_backend` 接到前端运行时配置面板
2. 为 Agent 增加 tool trace / run trace
3. 增加 Alembic migration，替代运行时补列
4. 把 prompt 管理升级成可比较、可回滚的版本体系
