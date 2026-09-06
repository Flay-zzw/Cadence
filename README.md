# Cadence 创作工作台

本地科普文章 → 统一风格 HTML 讲解页 + 逐页口播稿。前后端分为两个项目文件夹：`backend`（Python / FastAPI）与 `frontend`（React / TypeScript / Vite）。

## 本地启动

需要 Python 3.11+（推荐 3.12）、uv、Node.js 20+。在两个终端分别运行：

```powershell
cd backend
uv sync
Copy-Item .env.example .env
# 编辑 .env，填写 OPENAI_API_KEY 与 OPENAI_MODEL
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`.env` 只需首次复制，已有配置时不要覆盖。也可以先不填写密钥，直接体验固定示例。

```powershell
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。API 文档位于 http://127.0.0.1:8000/docs 。前端通过 Vite 代理访问后端。

依赖安装后，也可以分别双击根目录的 `start-backend.cmd` 和 `start-frontend.cmd` 启动。

## 使用

1. 点击「体验示例」查看内置的蓝天科普内容，它不调用模型、不改写输入文章。
2. 在「模型设置」填写 API Key、可用的模型 ID 和 Base URL。密钥输入隐藏，保存在本机 `backend/.env`，不回传前端；留空保留原密钥，输入新值则替换。也可手动编辑 `.env`。
3. 粘贴 100–20,000 字文章，选择受众、语气、语速，然后生成。模型需要支持 Chat Completions 的 `json_schema` 结构化输出。
4. 选择页面，编辑标题、正文、重点和口播稿，保存当前页。也可输入修改指示重新生成该页。
5. 导出 HTML、Markdown 口播稿或 JSON 项目。导出前会保存当前修改。HTML 无外部资源，可离线浏览和打印。

项目保存在 `backend/data/projects`，刷新后可从最近项目列表重新打开。JSON 导出用于备份，本版尚无 JSON 导入。任务状态保存在 `backend/data/jobs`；浏览器刷新会重新连接最近任务，后端重启时未完成任务会标记失败并提示重试。服务仅面向本地单进程使用，不启动多个 worker。

原文不持久化，但真实生成时会发往你配置的模型服务。失败输出保存在 `backend/data/diagnostics` 供调试，其中可能包含文章片段。密钥不返回前端，也不写入导出文件。

## 验证

```powershell
cd backend
uv run pytest
```

```powershell
cd frontend
npm run build
```

自动化覆盖项目保存、修订冲突、离线导出转义、模型成功/失败模拟、设置保护和中断恢复。真实模型质量需配置密钥后用实际文章验收；尚未完成设计文档中的十篇真实生成回归。

## 实现说明

- 两步调用：先清洗与规划叙事，再按 Pydantic JSON Schema 生成内容；内容或口播长度不合格时修订一次。
- 页数按模型判断，在首期设为 4–12 页；口播时长由字数和语速估算。
- 预览和导出使用同一版本的卡片 CSS。后端 `app/templates/deck.css` 为源文件，改动后同步到 `frontend/src/deck.css`。
- 无图片生成、联网检索、配音或视频导出。视觉以排版和重点节点为主，视觉建议作为编辑字段保留。
- 首期仅实现自然科普主题。没有背景自动保存，修改后请点击保存。

OpenAI 接入参考：[结构化输出官方文档](https://developers.openai.com/api/docs/guides/structured-outputs)。完整产品边界见 [开发设计](docs/MVP-开发设计.md)。
