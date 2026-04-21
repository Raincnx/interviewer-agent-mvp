# Interviewer Agent Skeleton

一个可扩展的 **FastAPI + SQLAlchemy + Provider Adapter** 项目骨架，适合继续开发“互联网大厂面试官 Agent”。

## 当前特性

- 模块化单体结构，便于后续扩展
- Interview / Turn / Report 三个核心实体
- Provider 适配层：`mock` / `gemini` / `openai`
- 默认使用 `mock`，无需 API Key 就能本地跑通
- SQLite 开箱即用；后续可切 PostgreSQL
- API 已经按面试主链路拆好

## 目录结构

```text
app/
  api/
    deps.py
    router.py
    routes/
      health.py
      interviews.py
      reports.py
  core/
    config.py
    lifespan.py
    logging.py
  db/
    base.py
    session.py
    models/
      interview.py
      report.py
      turn.py
  domain/
    schemas/
      interview.py
      report.py
      turn.py
    services/
      interview_service.py
      report_service.py
      scoring_service.py
  infra/
    llm/
      base.py
      gemini_provider.py
      mock_provider.py
      openai_provider.py
      registry.py
    repositories/
      interview_repo.py
      report_repo.py
      turn_repo.py
  prompts/
    grading_system.txt
    interviewer_system.txt
  main.py
```

## 快速启动

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 复制环境变量

```bash
cp .env.example .env
```

Windows 可以手动复制并改名。

### 3. 启动服务

```bash
uvicorn app.main:app --reload
```

打开：

- `GET /health`
- `POST /api/interviews`
- `POST /api/interviews/{id}/reply`
- `POST /api/interviews/{id}/finish`
- `GET /api/interviews/{id}`
- `GET /api/interviews/{id}/report`

## 默认运行方式

`.env.example` 默认配置为：

- `LLM_PROVIDER=mock`
- `DATABASE_URL=sqlite:///./app.db`

所以即使没有接入 Gemini / OpenAI，也可以直接运行完整链路。

## 切换到 Gemini

1. 安装依赖（`requirements.txt` 已包含）
2. 设置：
   - `LLM_PROVIDER=gemini`
   - `GEMINI_API_KEY=你的key`
3. 重启服务

## 切换到 OpenAI

1. 设置：
   - `LLM_PROVIDER=openai`
   - `OPENAI_API_KEY=你的key`
2. 重启服务

## 建议的下一步

1. 接 PostgreSQL + Alembic
2. 增加用户体系 / 登录
3. 接入简历上传与解析
4. 将 prompt 模板版本化
5. 增加历史面试列表与成长轨迹页面
