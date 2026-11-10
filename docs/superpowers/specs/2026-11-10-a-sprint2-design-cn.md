# Sprint 2 成员 A 模型与推理执行计划

> 2026-11-10 修订。本文只规划 Sprint 2 中 A 负责的本地模型、网页交互和推理指标。命令与数值样例均需在实际运行后核验，不能作为已经完成的证据。现有资料没有写明准确截止时间，因此使用“第 1 天/第 2 天”安排。

## 1. 我作为 A 要交什么

我先让用户在**本机网页**输入 Prompt，看到 Qwen3.5-0.8B 的回答；后台由 `llama.cpp` 的 `llama-server` 加载量化 GGUF 并推理。我再从服务端响应提取输入/输出 token 数和生成速度，补充客户端测到的总延迟，给 B/C 一份稳定的 JSON。Sprint 2 的目标是能演示、能解释、能复现这个闭环：

```text
浏览器输入 Prompt → A 的本地 Flask 网页 → 本机 llama-server → Qwen3.5-0.8B GGUF
                  ← 同次 Response + usage/timings ←
                           ↓
                    A 的真实推理记录 JSON → B 的 Dashboard / C 的后续集成
```

`llama-server` 自带的 Web UI 先用于验证模型能在浏览器对话。为了让网页上的回答和指标确定来自**同一次请求**，A 再做一个极简的本地网页：Python Flask 只提供网页和 `/api/infer`，由后端调用 `llama-server` 的 `/v1/chat/completions`，把该响应的回答与指标一起返回网页并保存 JSON。这是 A 的推理演示页，只有输入框、回答和几项数值；B 以后负责真正的监测 Dashboard。我不把 B 的监控图表或 C 的 Agent 当作 A 的 Sprint 2 完成条件。

## 2. 已确认的机器条件和 GPU 判断

这台电脑是 Windows 11 x64，CPU 为 **Intel Core Ultra 7 155H**，物理内存约 **32 GB**。Windows 检测到 `Intel(R) Arc(TM) Graphics`，设备 ID `0x7D55`，驱动版本 `32.0.101.8243`，状态为 OK。Intel 的 155H [产品规格](https://www.intel.com/content/www/us/en/products/sku/236847/intel-core-ultra-7-processor-155h-24m-cache-up-to-4-80-ghz/specifications.html)也列出 Arc 集成 GPU 和 8 个 Xe 核心。因此答案是：**你有 GPU，而且它是集成显卡，不是独立显卡。**

Windows 报出的约 2 GB `AdapterRAM` 不应简单解释为“显卡只有 2 GB 固定显存”；集成 GPU 会使用共享系统内存。它是否能在某个 `llama.cpp` 版本上稳定、快速地运行这个模型，仍需实测。`llama.cpp` 官方 [SYCL 文档](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md)明确列出 Meteor Lake 内置 Arc GPU，官方 [Releases](https://github.com/ggml-org/llama.cpp/releases)也提供 Windows x64 Vulkan/SYCL 包。我的执行顺序是：**先用 CPU 包得到可靠基线，再用 Vulkan 或 SYCL 包试 GPU offload**；不把 GPU 测试当作文本原型的前置条件，也不预先承诺 GPU 一定更快。

## 3. 模型与运行时选择

### 3.1 首选模型

选择 **Qwen3.5-0.8B Q4 GGUF**，先做文本推理，再决定是否加图片。Qwen 的 [原始 0.8B 模型卡](https://huggingface.co/Qwen/Qwen3.5-0.8B)将其列为支持图像和文本的模型。为保证文本权重和视觉 projector 匹配，建议从**同一个 GGUF 仓库**取两份文件：

| 用途 | 文件 | 页面标示大小 | Sprint 2 优先级 |
|---|---|---:|---|
| 文本推理 | [`notschmee/Qwen3.5-0.8B-GGUF` 的 `Qwen3.5-0.8B-Q4_K_M.gguf`](https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF/tree/main) | 约 0.56–0.59 GB | 必做，只下载这一个文件即可开始 |
| 图片输入 | 同一仓库的 `Qwen3.5-0.8B-mmproj-F16.gguf` | 约 0.20 GB | 文本和指标完成后再下载与测试 |

两份文件合计不到 1 GB；加上运行时和临时缓存仍需实际记录总磁盘占用，不能仅凭权重大小代表整个项目占用。该 GGUF 仓库由社区上传，**原始模型是 Qwen 发布的，量化文件并非 Qwen 官方上传**。下载前核对模型卡、文件名、仓库 revision 和文件 SHA-256；不将不同模型版本的 `mmproj` 随意混用。另一条更接近 llama.cpp 官方维护的[文本备选仓库](https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/tree/main)有 `Qwen3.5-0.8B-Q4_0.gguf`（约 563 MB），但当前文件列表没有可直接配套的 `mmproj`，因此若想演示图片，首选同仓库成对文件。

模型小不等于回答一定可靠。验收重点是本地部署和指标测量；用 3–5 道简单问题检验回答是否适合现场演示，不把模型生成的技术命令未经核对直接写入教程。若 0.8B 在本机质量或速度不符合演示需要，再比较更大模型；只有在基础闭环稳定后才做，且记录额外磁盘、内存与时间成本。

### 3.2 llama.cpp 运行时

从 [llama.cpp 官方 Releases](https://github.com/ggml-org/llama.cpp/releases)选定一个**具体 release**的 Windows x64 CPU 包，解压在用户有权限的目录，例如 `runtime/cpu/`；记录 release 编号、下载链接、SHA-256。先用该包的 `--help` 验证可执行文件名与参数。后续 GPU 对照实验再下载**同一 release**的 Windows x64 Vulkan 包；SYCL 也受官方支持，但可能带来更多运行时依赖，只有 Vulkan 路径不顺且时间允许时再试。CPU 与 GPU 不混用不同 release 来比较速度。

推荐先由 A 本地保存模型文件，而不是让运行时自动拉取整个仓库。每一步都能解释：GGUF 是模型权重，Q4 是量化格式，`llama-server` 负责加载与推理，Web UI/API 负责交互，B 的监测模块负责 CPU/RAM 及可视化。

## 4. Sprint 2 的详细实施顺序

### 第 1 天上午：环境、下载、首次文本推理

- [ ] 团队仓库为 [RainaQiu/local-llm-telemetry-dashboard](https://github.com/RainaQiu/local-llm-telemetry-dashboard)，当前只有初始 README。确认 Sprint 2 展示时间和 A 的工作分支；项目资料文件夹不是代码仓库。
- [ ] 记录 Windows、CPU、GPU、驱动、RAM、空闲磁盘；以 `Get-CimInstance Win32_VideoController` 和 `Get-ComputerInfo` 的输出作环境证据。模型/运行时文件不要提交进 Git。
- [ ] 下载选定 CPU release 并解压；执行 `llama-server.exe --version` 与 `--help`。若可执行文件名称变了，以该 release 的实际文件为准，更新运行说明。
- [ ] 只下载 `Qwen3.5-0.8B-Q4_K_M.gguf`，核对文件大小、记录 SHA-256、revision。先不下载 projector、其他量化版本和整个 Hugging Face 仓库。
- [ ] 在本机启动 `llama-server`，绑定 `127.0.0.1`，限制上下文初始为 2048，CPU 模式 `--n-gpu-layers 0`。调用 `/health`，直到返回 ready；不要把尚在加载的 503 当作模型故障。
- [ ] 打开服务自带的 Web UI，输入一条短英文问题，再输入一条短中文问题；两次都应有非空回答。保存服务日志和一张能看出本地网页地址的截图。
- [ ] 若回答一直在“思考”、输出很长或网页显示为空，先检查原始响应是否把文字放在 `reasoning_content`，再按所选 release 的 `--help` 测试 `--reasoning off` 和较小的输出上限；记录实际生效的设置，不直接换模型。

**启动命令草案**，需要按选定 release 的 `--help` 实测：

```powershell
Get-FileHash .\models\Qwen3.5-0.8B-Q4_K_M.gguf -Algorithm SHA256
.\runtime\cpu\llama-server.exe --version
.\runtime\cpu\llama-server.exe -m .\models\Qwen3.5-0.8B-Q4_K_M.gguf --host 127.0.0.1 --port 8080 --ctx-size 2048 --n-gpu-layers 0
```

**第一个验收点：**浏览器 `http://127.0.0.1:8080` 可以与本地模型对话；关闭服务后网页不能继续生成，重启服务可恢复；服务日志显示选定 GGUF 已加载。此时不必有自定义网页或 Dashboard。

### 第 1 天下午：获取真实指标并冻结接口

- [ ] 查询 `/v1/models` 获取服务实际使用的 model ID，向 `/v1/chat/completions` 发一次非流式请求；保存**原始 JSON**。响应中的 `choices[0].message.content` 是回答，`usage.prompt_tokens`/`usage.completion_tokens` 分别是输入/输出 token 数；`timings` 中的 `prompt_ms`、`predicted_ms`、`predicted_per_second` 等字段按该 release 实际返回情况读取。字段示意见 [llama.cpp Server 文档](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)。
- [ ] 用客户端单调时钟测量“发出 HTTP 请求 → 收到完整响应”的 `latency_seconds`。把它标为端到端延迟。`timings.predicted_per_second` 是模型生成速度；若缺失则写 `null`，不要用总延迟硬算成同名指标。`time to first token` 只有开启流式输出并计时首个 token 才能测，本 Sprint 可留空。
- [ ] 写一个很小的请求/记录模块（`inference/llama_client.py`），接收 Prompt、服务器地址，完成 JSON 请求、响应解析和计时；不需要自己实现模型加载。另用 `inference/app.py` 提供本地网页与 `/api/infer`，把同一次请求的回答和指标返回浏览器并保存。
- [ ] 定义 `schema_version: "1.0"` 的记录格式并给 B/C 一份**标为示例**的 JSON；与 B/C 约好真实记录的位置。Sprint 2 的最终演示使用 A 的极简网页，不能把内置 Web UI 的 A 次回答和脚本的 B 次指标拼成一条证据。
- [ ] 与 B 确定 `run_id`、开始/结束时间及 CPU/RAM 曲线如何关联；C 只需知道本地服务地址与记录格式。B/C 的模块可在 A 数据之外并行推进。

**最小 JSON 合同（以下值纯属格式示意）：**

```json
{
  "schema_version": "1.0",
  "run_id": "example-001",
  "timestamp_utc": "2026-11-10T15:30:00Z",
  "model_id": "Qwen3.5-0.8B-Q4_K_M",
  "backend": "cpu",
  "prompt": "Explain a local LLM in one sentence.",
  "response": "Example answer, not a measured run.",
  "prompt_tokens": 12,
  "output_tokens": 18,
  "latency_seconds": 2.4,
  "generation_tokens_per_second": 12.5,
  "status": "success"
}
```

`prompt_tokens`、`output_tokens` 和生成 TPS 必须对应服务端返回字段；`latency_seconds` 对应客户端测量。若字段缺失或请求失败，记录错误与 `null`，不凭经验填数字。结果应有唯一 `run_id`；可写 `runs/latest.json` 供 B/C 读取，并追加 `runs/history.jsonl` 供演示或调试。更新 `latest.json` 时先写临时文件再替换，避免下游读到半个 JSON。

**第二个验收点：**在 A 的极简网页输入新的 Prompt，页面能显示非空 Response 和指标，同时生成同一个 `run_id` 的 JSON；打开原始服务端响应能核对 token 与速度，查看客户端日志能核对总延迟。

### 第 2 天上午：网页演示、异常测试、GPU 可行性

- [ ] 检验三条真实 Prompt：英文、中文、含引号/换行的输入；再次运行同一 Prompt 做稳定性检查。限制最大输出 token，使现场演示可控；记录是否为冷启动或热机推理。
- [ ] 检验服务未启动、模型路径错误、空 Prompt、API 返回缺少计数字段四种情况。程序应给清楚的错误并退出失败，不能生成 `status=success` 的假记录。
- [ ] 如有时间，从同一 release 下载 Vulkan 包；先运行 `--list-devices` 或查看启动日志确认它**实际识别 Intel Arc**，再试 `--n-gpu-layers` offload。记录日志中的设备名、卸载层数、是否成功生成文字、峰值内存和同一组 Prompt 的速度。若不识别、崩溃或速度无优势，回到 CPU 基线；不要为了 GPU 加速推迟交付。
- [ ] 对比 CPU/GPU 时保持同一模型、Prompt、上下文和输出上限；分别记录冷启动与热机轮次。只有至少两轮可重复结果后，才能说明“这台机器上 GPU 是否更快”。

**第三个验收点：**文本网页演示稳定，指标记录真实，异常情况不会造假；GPU 结果可记录为“成功”“失败及原因”或“未测试”，三种状态都不影响 Sprint 2 的最小交付。

### 第 2 天下午：可选图片输入，再做交接

- [ ] 只有前三个验收点通过且仍有时间，才下载与模型同仓库的 `Qwen3.5-0.8B-mmproj-F16.gguf`。记录总下载量和模型文件 hash。`llama-server` 的 `--mmproj` 是官方支持的 projector 参数，见 [Server 文档](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)与[多模态说明](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)。
- [ ] 以 `-m <Q4 GGUF> --mmproj <F16 GGUF>` 启动。先用一张非私人、内容容易核查的小图片做 API 测试，再看当前 Web UI 是否支持上传图片。若 UI 不支持，可用本地极简页面或请求脚本演示；不要仅因两个文件成功加载就宣称多模态已跑通。
- [ ] 图片演示需有原图、提问、回答、原始响应，以及记录中 `input_modality: "image+text"`。图片输入的 token/延迟应单独标注，不与文本请求直接比速度。失败则保持文本演示；多模态写“未完成/可选”，不占用必交成果的时间。
- [ ] 给 B/C 一个真实 `latest.json`、字段解释与错误示例；给 D 一页以内的 A 进展摘要：本机环境、模型与运行时版本、下载体积、网页地址、一个同次请求的回答和指标、运行截图、尚未完成项。

**第四个验收点：**组员依照 README 在 A 的电脑上能重启服务并重放演示；至少一位组员看过命令和 JSON，确认字段能被后续模块读取。跨平台步骤可在 Sprint 3 按实际需要补充，Sprint 2 不把 Windows/Mac 双平台验证设为 A 的阻塞项。

## 5. A 需要提交的具体文件

团队仓库已建立，目前没有既有代码规范；建议按以下结构实现。

```text
inference/
  README.md                # 人能照做的下载、启动、网页访问、指标解释
  app.py                   # Flask 页面与 /api/infer；保存同次请求 JSON
  llama_client.py          # 调用 llama-server，测量、解析并返回记录
  templates/index.html     # 极简输入框、回答和指标
  static/app.js            # 提交 Prompt，显示 loading/error/success
  requirements.txt         # Flask 版本范围
  example_output.json      # 明确标为示例，不冒充测量
  evidence/
    environment.md         # 本机硬件、驱动、运行时和模型版本
    demo_run.json          # 一次真实运行的记录
    demo_run_raw.json      # 同一次请求的原始服务端响应（可脱敏）
    screenshot.png         # 网页或本地结果页截图
```

模型 GGUF、projector、运行时压缩包和大日志不进 Git；README 给出官方来源及版本/校验值。`llama_client.py` 优先使用 Python 标准库发 HTTP 请求；Flask 是本地网页唯一必需的 Python 依赖。README 不只列命令，还应解释模型文件、量化、推理服务、网页/API、A 的指标和 B 的监测如何接起来。

## 6. 交付判定与演示脚本

| 必须证明 | 判定方法 |
|---|---|
| 真正本地运行 | 服务监听 `127.0.0.1`，本机有 GGUF，网页能在没有云模型 API 的情况下生成新回答。 |
| 网页可用 | 浏览器能输入新的 Prompt 并看到对应 Response；如果使用内置 UI 与记录程序，证据清楚标明各自请求。 |
| 指标可信 | 输入/输出 token 和生成 TPS 能追溯到同一原始响应；总延迟有明确客户端计时口径。 |
| 体积合理 | 记录 GGUF、projector（若有）、运行时和缓存的实际占用；不把全部仓库下载下来。 |
| 可交接 | B/C 能读取真实 JSON，知道字段、单位和 `null`/失败语义；D 能拿它做 TP2 演示材料。 |

**90 秒演示：**（1）打开 `127.0.0.1` 网页并输入现场新问题；（2）展示新回答；（3）打开同次请求的 JSON，指给大家看 input/output tokens、latency、TPS；（4）显示模型 GGUF 文件和运行时日志，说明模型确实在本机；（5）如果图片功能已验证，追加 20–30 秒图片问答。演示时只说**实测到的**速度和占用，不把文件大小当作实际 RAM/显存使用量。

## 7. 顺序与时间预算

| 阶段 | 估计专注时间 | 最迟产出 |
|---|---:|---|
| 下载、版本固定与文本首次运行 | 2–4 小时 | 可在网页生成回答 |
| 解析 API、计时、JSON 合同 | 2–3 小时 | 同次请求的真实记录 |
| 异常测试、README、证据 | 2–3 小时 | 可交接的 Sprint 2 原型 |
| GPU offload 对照 | 1–2 小时，可跳过 | 有证据的加速结论或失败记录 |
| mmproj 图片输入 | 1–3 小时，可跳过 | 已验证的图片演示或明确未完成 |

先保证前三行；可选项只用剩余时间。若下载、DLL、端口或 GPU 后端出现问题，记录错误、恢复 CPU 路径并继续推进网页和指标。A 的学习重点是弄懂模型权重如何被加载、量化如何影响大小、CPU/GPU 后端如何选择、token 和延迟如何测量，以及这些指标如何交给 B/C。

## 8. 技术资料

- [Qwen 原始 Qwen3.5-0.8B 模型卡](https://huggingface.co/Qwen/Qwen3.5-0.8B)；[成对 Q4_K_M 与 mmproj 文件](https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF/tree/main)；[llama.cpp 官方 Q4_0 文本备选](https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF/tree/main)。
- [llama.cpp Releases](https://github.com/ggml-org/llama.cpp/releases)；[Server API 与指标](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)；[多模态加载说明](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)；[Intel SYCL 后端](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md)。
- [Intel Core Ultra 7 155H 产品规格](https://www.intel.com/content/www/us/en/products/sku/236847/intel-core-ultra-7-processor-155h-24m-cache-up-to-4-80-ghz/specifications.html)。

