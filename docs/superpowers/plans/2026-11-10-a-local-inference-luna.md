# Sprint 2 A Local Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Windows 本机运行 Qwen3.5-0.8B Q4 GGUF，并提供一个网页：输入 Prompt 后显示该次请求的回答、输入/输出 token、端到端延迟和生成速度，同时保存真实 JSON 给 B/C。

**Architecture:** `llama-server` 在 `127.0.0.1:8080` 加载模型。一个小型 Flask 应用在 `127.0.0.1:7860` 提供网页和 `POST /api/infer`；Python 标准库 HTTP 客户端向 llama-server 发同一次请求，规范化 `usage`/`timings`，持久化 `latest.json` 与 `history.jsonl`。页面只显示 A 的推理结果，不实现 B 的 Dashboard 或 C 的 Agent。

**Tech Stack:** Python 3.11+、Flask 3.1.x、Python 标准库 `urllib`/`unittest`、原生 HTML/JS、llama.cpp Windows x64 CPU 预编译包、Qwen3.5-0.8B Q4_K_M GGUF。Windows PowerShell 命令为首要验证路径。

**Spec:** `docs/superpowers/specs/2026-11-10-a-sprint2-design-cn.md`。执行时必须先读该文件，那里记录 Sprint 2 范围、模型来源、指标口径和可选 GPU/mmproj 实验。

## Global Constraints

- 仓库是 `https://github.com/RainaQiu/local-llm-telemetry-dashboard`；2026-11-10 检查时默认分支 `main` 只有一行 README，没有产品代码。开始前重新检查仓库，以实际状态为准。
- 只做成员 A 的 Sprint 2 本地模型/推理/极简网页/真实指标。不要实现训练、B 的 CPU/RAM Dashboard 或 C 的 Agent；GPU 与图片输入只在必做功能验收通过后做。
- 两个服务都只绑定 `127.0.0.1`。不需要管理员权限，不使用外部托管模型 API，不把模型、projector、运行时压缩包或虚拟环境提交 Git。
- 默认模型：同一 Hugging Face 仓库 `notschmee/Qwen3.5-0.8B-GGUF` 的 `Qwen3.5-0.8B-Q4_K_M.gguf`。图片加分项才下载其 `Qwen3.5-0.8B-mmproj-F16.gguf`。记录 repo revision 与文件 SHA-256；不要下载整个仓库。
- llama.cpp Windows CPU 运行时先固定为官方 release `b12242` 的 `llama-b12242-bin-win-cpu-x64.zip`。该 asset 在 2026-11-10 官方 release API 中存在；若执行时不可得，改用一个可核对的 release 并在 README/证据中同时更新版本。模型与 GPU 对照测试使用同一 runtime release。
- JSON `schema_version` 固定为字符串 `"1.0"`；所有时间是 UTC ISO 8601；秒为浮点数。输入/输出 token 使用该次服务端响应的 `usage`，生成 TPS 用 `timings.predicted_per_second`，端到端延迟用客户端 `time.perf_counter()`；字段缺失不能编造。
- `POST /api/infer` 只接收 `{ "prompt": string }`，去掉首尾空白后长度允许 1–4000 个 Unicode 字符；发给 llama-server 的 `max_tokens=128`、`temperature=0`、`stream=false`。浏览器展示必须与保存的 JSON 属于同一个 `run_id`。
- Python 依赖仅 Flask；运行时第三方模型权重不进入测试夹具。先用模拟 HTTP 响应跑自动测试，再做真实模型端到端验证。

## Review Focus

1. 含中文、引号和换行的 Prompt 必须原样通过 JSON 编码发送，页面用 `textContent` 显示回答，不能插入为 HTML；归属 Task 1/4 测试。
2. llama-server 未启动、仍在加载、超时或返回非 2xx 时，网页显示可理解错误，不生成 `status=success` 的记录；归属 Task 1/3 测试。
3. `usage` 缺失、token 非整数、`choices` 为空、response 为空时，返回明确上游格式错误，不把空值当测量值；归属 Task 1 测试。
4. `timings.predicted_per_second` 缺失时 JSON 存 `null` 且页面显示“暂不可用”，不能用 `output_tokens / latency_seconds` 替代；归属 Task 1/4 测试。
5. 写 `latest.json` 中途失败或连续两次请求时，读者不能看到半截 JSON；`history.jsonl` 每行是独立有效 JSON，并且 `run_id` 能与页面结果对应；归属 Task 2/3 测试。

---

## 文件职责和固定接口

| 路径 | 职责 | 后续任务依赖的接口 |
|---|---|---|
| `.gitignore` | 排除 `.venv/`、`local_assets/`、`inference/runs/`、`*.gguf`、大日志 | 无 |
| `inference/__init__.py` | 标记 Python 包 | 无 |
| `inference/requirements.txt` | `Flask>=3.1,<3.2` | 无 |
| `inference/llama_client.py` | HTTP 调用、计时、响应验证、规范化记录 | `infer(prompt: str, server_url: str, timeout_seconds: float = 120.0) -> dict[str, object]`；`InferenceError(kind: str, message: str)` |
| `inference/store.py` | 原子更新 latest、追加 history | `save_run(record: dict[str, object], data_dir: Path) -> None` |
| `inference/app.py` | Flask 页面、API、错误映射；本地启动 | `create_app(data_dir: Path | None = None, server_url: str | None = None) -> Flask` |
| `inference/templates/index.html` | 输入框、回答、指标占位和状态文字 | DOM IDs：`prompt`、`submit`、`status`、`response`、`prompt-tokens`、`output-tokens`、`latency`、`tps`、`run-id` |
| `inference/static/app.js` | `fetch('/api/infer')` 并更新页面 | 使用上表 DOM IDs，使用 `textContent` |
| `inference/README.md` | 精确安装/运行/验证/故障说明与指标来源 | 文档，不承诺未实测结果 |
| `inference/example_output.json` | schema 示例，显式标注 `example` | B/C 字段说明的辅助材料，不是实测数据 |
| `tests/test_llama_client.py`、`tests/test_store.py`、`tests/test_app.py` | 纯本地自动测试 | `python -m unittest discover -s tests -v` |

真实记录的顶层键固定为 `schema_version`, `run_id`, `timestamp_utc`, `model_id`, `prompt`, `response`, `prompt_tokens`, `output_tokens`, `latency_seconds`, `generation_tokens_per_second`, `status`。成功时 `status="success"`，`run_id` 是 UUID4 字符串。另存 `server_usage`、`server_timings` 和 `server_raw_response` 三个原始子对象，供核对和导出演示证据；本地记录会包含 Prompt，提交公开仓库前要检查内容。`generation_tokens_per_second` 可为 `null`，`prompt_tokens` 必须是非负整数，`output_tokens` 必须是正整数，latency 必须大于零。可选 `backend` 只可标为人工配置值，不可假称自动检测。

### Task 1: llama-server 客户端和规范化指标

**Files:**
- Create: `inference/__init__.py`
- Create: `inference/llama_client.py`
- Test: `tests/test_llama_client.py`

**Interfaces:**
- Consumes: 本机 llama-server 的 `GET /v1/models`、`POST /v1/chat/completions`；`urllib.request`。
- Produces: 上表固定的 `infer(...)` 与 `InferenceError`。只返回成功记录；失败抛异常，不返回伪成功数据。

- [ ] **Step 1: 写失败测试。** 用 `unittest.mock.patch('urllib.request.urlopen', ...)` 或线程内本地假 HTTP server 模拟 `GET /v1/models` 和 `POST /v1/chat/completions`。成功响应的 `model.id="demo-model"`, `message.content="Hello"`, `usage.prompt_tokens=7`, `usage.completion_tokens=5`, `timings.predicted_per_second=20.0`。断言规范化记录的对应值、`schema_version="1.0"`、`latency_seconds>0`、`run_id` 可解析为 UUID4，发给上游的 JSON 含 `max_tokens:128`、`temperature:0`、`stream:false`。第二条测试传中文、引号和换行，断言上游收到完整同值字符串。
- [ ] **Step 2: 运行测试确认失败。** `python -m unittest discover -s tests -p test_llama_client.py -v`；预期因为模块/函数未实现而失败。
- [ ] **Step 3: 实现 `InferenceError(kind: str, message: str)` 和 `infer(prompt: str, server_url: str, timeout_seconds: float = 120.0) -> dict[str, object]`。** 先查 `/v1/models` 的第一个 ID，再发非流式 chat 请求；只有 POST 部分计入端到端 latency。`timestamp_utc` 为完成请求的 UTC 时间。解析 `choices[0].message.content`、`usage`、可选 `timings`，保留 `server_usage`、`server_timings`、`server_raw_response` 原值。HTTP 连接/超时 `kind="unavailable"`，非 2xx `kind="upstream_error"`，数据缺失或类型错误 `kind="invalid_response"`。
- [ ] **Step 4: 增加失败模式测试。** 分别覆盖服务拒绝连接、503 Loading、空 `choices`、缺 `usage`、`completion_tokens="five"`、空 response、缺 `predicted_per_second`。最后一种应成功但 TPS 为 `None`；其余应抛对应 `InferenceError`。请求超时的测试不要真等 120 秒，用 mock 立即抛 `TimeoutError`。
- [ ] **Step 5: 运行 `python -m unittest discover -s tests -p test_llama_client.py -v`，确认全部 PASS。** 如发现服务返回字段与文档不同，只在真实响应验证后改解析规则和测试。
- [ ] **Step 6: 检查改动并提交。** `git add inference/__init__.py inference/llama_client.py tests/test_llama_client.py`；`git commit -m "feat: collect local inference response and metrics"`。

### Task 2: 安全保存同次请求记录

**Files:**
- Create: `inference/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: Task 1 返回的成功记录。
- Produces: `save_run(record: dict[str, object], data_dir: Path) -> None`；`data_dir/latest.json` 与 `data_dir/history.jsonl`。

- [ ] **Step 1: 写失败测试。** 用 `tempfile.TemporaryDirectory()`；连续调用两次 `save_run`，断言 `latest.json` 等于第二条完整记录、`history.jsonl` 恰好两行且每行 `json.loads` 成功、`run_id` 分别相同；中文 `ensure_ascii=False` 后可读。添加测试：模拟写临时文件失败，旧 `latest.json` 仍是有效 JSON；不要模拟或删除用户目录。
- [ ] **Step 2: 运行 `python -m unittest discover -s tests -p test_store.py -v` 确认失败。**
- [ ] **Step 3: 实现 `save_run(...)`。** `mkdir(parents=True, exist_ok=True)`；在 `data_dir` 内生成唯一临时文件，`json.dump(..., ensure_ascii=False)` 并 flush/close 后 `os.replace` 更新 latest；history 每次追加一行 UTF-8 JSON 和换行。若保存失败，向调用者抛异常，网页不得宣称记录已保存。
- [ ] **Step 4: 运行 `python -m unittest discover -s tests -p test_store.py -v` 确认 PASS。**
- [ ] **Step 5: `git add inference/store.py tests/test_store.py`；`git commit -m "feat: persist inference runs"`。**

### Task 3: 本地 Web API

**Files:**
- Create: `inference/requirements.txt`
- Create: `inference/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: Task 1 `infer(...)`、Task 2 `save_run(...)`。
- Produces: `create_app(...)`、`GET /`、`POST /api/infer`；Flask 只监听 `127.0.0.1:7860`。

- [ ] **Step 1: 写失败测试。** 在测试中 mock `inference.app.infer` 和 `inference.app.save_run`，用 Flask `test_client()` POST `{ "prompt": "Hi" }`，断言 HTTP 200、返回 JSON 的 `response`/`run_id` 与 mock 记录相同，保存函数恰调用一次。`"  "`、缺 Prompt、非字符串、超过 4000 字符分别返回 400，且推理函数从未调用。上游 `InferenceError("unavailable", ...)` 返回 503；`invalid_response` 返回 502，且不保存。存储失败返回 500，不把请求报告为成功。`GET /` 返回 200 与 HTML。
- [ ] **Step 2: 在虚拟环境安装依赖并运行测试确认失败。** `python -m venv .venv`；PowerShell 中运行 `& .\.venv\Scripts\python.exe -m pip install -r inference\requirements.txt`；再运行 `& .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_app.py -v`。先创建 `requirements.txt` 写 `Flask>=3.1,<3.2`，记录实际安装版本。
- [ ] **Step 3: 实现 `create_app(data_dir: Path | None = None, server_url: str | None = None) -> Flask`。** 默认 `data_dir=仓库根目录/inference/runs`，默认服务 URL 为 `http://127.0.0.1:8080`，用环境变量 `LLAMA_SERVER_URL` 覆盖；不要从浏览器请求接受任意服务器 URL。POST 验证 Prompt 后调用 `infer`、`save_run`，返回同一记录。`GET /` 渲染 `index.html`。`python -m inference.app` 时启动 `host="127.0.0.1", port=7860, debug=False`。
- [ ] **Step 4: 运行 `& .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_app.py -v`，确认 PASS。**
- [ ] **Step 5: `git add inference/requirements.txt inference/app.py tests/test_app.py`；`git commit -m "feat: expose local inference web API"`。**

### Task 4: 极简网页与同次结果展示

**Files:**
- Create: `inference/templates/index.html`
- Create: `inference/static/app.js`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: Task 3 `POST /api/infer` 返回的规范化记录。
- Produces: 用户在 `http://127.0.0.1:7860` 输入 Prompt 后看到回答、token 数、延迟、TPS 和 `run_id`。

- [ ] **Step 1: 扩展页面测试。** `GET /` 的 HTML 必须含固定 DOM IDs 和 `app.js` 引用。手动浏览器验收脚本写在测试注释或 README：成功时指标可见；请求中按钮禁用且状态是“正在生成”；失败时错误可见且旧结果不冒充新结果；TPS=`null` 时显示“暂不可用”。
- [ ] **Step 2: 运行 `& .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_app.py -v`，确认新测试失败。**
- [ ] **Step 3: 实现页面。** 一页布局：标题、简短本地运行说明、多行 Prompt、提交按钮、状态文字、回答框、四个指标、`run_id`。不做 CPU/RAM 图表、模型切换或图片上传。JS 使用 `fetch('/api/infer', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prompt})})`，渲染回答只用 `textContent`，拒绝空白输入；成功/错误/加载状态互斥。数值展示控制小数位但 JSON 原值保留。
- [ ] **Step 4: 运行全部自动测试。** `& .\.venv\Scripts\python.exe -m unittest discover -s tests -v`；预期 Task 1–4 测试全 PASS。再启动 Flask，浏览器检查页面在 100% 缩放下无裁切、输入框和指标可读；无模型时错误状态正常。
- [ ] **Step 5: `git add inference/templates/index.html inference/static/app.js tests/test_app.py`；`git commit -m "feat: add local inference demo page"`。**

### Task 5: 真实模型验证、文档和交付证据

**Files:**
- Create: `.gitignore`
- Create: `inference/README.md`
- Create: `inference/example_output.json`
- Create: `inference/evidence/environment.md`
- Create only after actual run: `inference/evidence/demo_run.json`、`inference/evidence/demo_run_raw.json`、`inference/evidence/screenshot.png`

**Interfaces:**
- Consumes: Tasks 1–4 的可运行网页和 JSON。
- Produces: 另一位组员可以复现的说明，以及 A 可交给 B/C/D 的同次真实运行证据。

- [ ] **Step 1: 写 `.gitignore`。** 至少含 `.venv/`, `local_assets/`, `inference/runs/`, `*.gguf`, `__pycache__/`, `*.pyc`, `*.zip`；确认已跟踪文件没有模型权重或运行时包。`inference/evidence/` 中只放选定的少量可公开证据。
- [ ] **Step 2: 从官方 release 下载 `b12242` 的 CPU 包到被忽略的 `local_assets/runtime/`，从同一 Hugging Face 模型仓库只下载 Q4_K_M GGUF 到 `local_assets/models/`。** README 写官方 URL、release/revision、SHA-256、实际大小。不要在计划里填测量值；实施后由本机命令得出。PowerShell 解压和 `Get-FileHash`，然后运行 `llama-server.exe --version` 和 `--help` 确认路径/参数。
- [ ] **Step 3: 启动 `llama-server` 于 `127.0.0.1:8080`。** 初始命令：`& .\local_assets\runtime\llama-server.exe -m .\local_assets\models\Qwen3.5-0.8B-Q4_K_M.gguf --host 127.0.0.1 --port 8080 --ctx-size 2048 --n-gpu-layers 0`。若 release 解压后在子目录，调整路径并把**真实有效命令**写 README。另一个 PowerShell 窗口运行 `Invoke-RestMethod http://127.0.0.1:8080/health`；若模型一直在 thinking 或 response 为空，检查 `--reasoning off` 及原始响应，记录最终参数。
- [ ] **Step 4: 启动 Flask 并在网页完成三条真实 Prompt。** `& .\.venv\Scripts\python.exe -m inference.app`，打开 `http://127.0.0.1:7860`。用英文、中文和含引号/换行 Prompt 各一次；页面显示非空回答和同次指标。对选中的一条演示，保留 `latest.json` 副本、其中的 `server_raw_response` 子对象副本与屏幕截图；页面、JSON 和证据文件都以同一个本地 `run_id` 标识。
- [ ] **Step 5: 核对指标。** `prompt_tokens` 与 `output_tokens` 等于上游 `usage`；`generation_tokens_per_second` 等于 `timings.predicted_per_second` 或为 null；`latency_seconds>0`；没有把模型文件大小写成运行时 RAM/显存。记录服务版本、Python 版本、OS/CPU/GPU、磁盘占用以及启动命令。
- [ ] **Step 6: 写 README 与示例。** 精确说明下载、校验、虚拟环境、启动两个服务、网页地址、JSON 文件位置、各字段口径、服务未启动/503/端口占用的解决方法，以及 CPU 基线与可选 GPU/mmproj 的区别。`example_output.json` 应带 `run_id="example-only"` 且在 README 明确“示例非实测”。
- [ ] **Step 7: 最终验证。** 重新运行 `& .\.venv\Scripts\python.exe -m unittest discover -s tests -v`；停止并重新启动两个服务，按 README 从头跑一次新 Prompt；检查 `git status --short` 与 `git ls-files`，确认没有 GGUF、ZIP、虚拟环境或私有路径进入 Git。没有真实模型成功运行时，不创建 `demo_run.json`/截图并明确报告阻塞。
- [ ] **Step 8: `git add .gitignore inference/README.md inference/example_output.json inference/evidence/`；`git commit -m "docs: document local inference demo and evidence"`。** 推送或创建 PR 按当前会话授权和仓库协作方式执行；不要把未实测结果写成完成。

### Optional Task 6: Intel Arc GPU 和图片输入

这项**不得阻塞 Tasks 1–5**。用户明确把它们作为加分项。

- [ ] GPU：下载同一 release `b12242` 的 Windows x64 Vulkan 包到 `local_assets/runtime-vulkan/`，运行 `--list-devices` 或查看启动日志，确认实际列出 Intel Arc；`--n-gpu-layers 99` 请求 offload，记录实际卸载层数。与 CPU 使用同一模型/Prompt/上下文/输出上限，分别跑至少两轮，记录 TPS、端到端延迟和稳定性。失败时回到 CPU 并在 README 记下错误，不报告未证实的加速。
- [ ] 图片：从与 Q4_K_M 相同仓库下载 `Qwen3.5-0.8B-mmproj-F16.gguf`，用 `--mmproj` 启动；先通过真实 API 图片请求验证回答，再考虑给网页加上传控件。图片输入要限制本地图片大小、使用非私人测试图并标注 `input_modality="image+text"`。没有成功响应就标记未完成。

## 自查和 Luna 执行提示词

**计划自查：**必需范围由 Tasks 1–5 覆盖；接口统一是 `infer → save_run → /api/infer → 页面`；测试覆盖 Review Focus 五项；模型与 GPU/mmproj 都留在 Git 之外。对用户可见的成功断言以真实模型运行证据为准，mock 测试只能证明代码路径。

Luna 更适合一次处理一个边界清楚、可测试的 Task。第一次把下面整段交给 Luna，在已打开该仓库的 Codex 聊天中执行。检查它报告的文件和测试输出后，再用后面的继续提示词逐项推进；不要仅凭 Luna 的完成声明跳过验收。

```text
你是成员 A 的实施者。仓库是 https://github.com/RainaQiu/local-llm-telemetry-dashboard 。先读取 docs/superpowers/specs/2026-11-10-a-sprint2-design-cn.md 和 docs/superpowers/plans/2026-11-10-a-local-inference-luna.md，再检查当前仓库状态和 AGENTS.md。这一轮**只执行 Task 1**；先写失败测试、运行确认失败、写最少代码、运行确认通过，完成后停下并报告。只做 A 的 Sprint 2 本地推理；不要做训练、B 的 Dashboard 或 C 的 Agent。不要提前下载大模型、不要开始 Task 2，也不要把可选 GPU/mmproj 混入 Task 1。

Task 1 的关键验收：规范化记录里的 token/TPS 来自同一次模拟 llama-server 响应，端到端延迟来自客户端计时，异常响应不能变成伪成功。mock 测试通过不等于真实模型已运行。不要编造模型输出、速度、截图或 SHA-256。遇到路径/版本与计划不同时，核对证据再调整；需要改变 JSON 字段或超出 A 范围时说明。完成后报告改动文件、失败测试的输出、通过测试的输出、Git 提交/PR 链接和 Task 2 是否具备前置条件。
```

后续每次在同一个仓库聊天中发：

```text
继续执行 docs/superpowers/plans/2026-11-10-a-local-inference-luna.md 的 Task N（把 N 改成 2、3、4、5）。先核对前一 Task 的代码、接口和测试都存在，再只做本 Task 的步骤与验收。不要提前执行下一 Task；完成后给出本 Task 的命令、完整测试结果、文件改动和未解决问题。Task 5 必须实测本地模型与网页，不能拿 mock 测试代替真实运行。
```

