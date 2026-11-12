# Environment and Real-Run Evidence

Captured on 2026-11-11. The records below came from live requests through the browser UI to the local `llama-server`; they are not fixture or mock outputs. The normalized record, preserved server response, and screenshot for the selected English request share the same `run_id`.

## Machine and software

- Windows registry values: `ProductName=Windows 10 Education`, `EditionID=Education`, `DisplayVersion=25H2`, `CurrentBuild=26200`, `UBR=9711`. The CIM caption separately reported `Microsoft Windows 11 Education`; the system surfaces disagree on the product label, so both raw values are recorded.
- System model: Lenovo `21LD`; CPU: Intel Core Ultra 7 155H, 16 cores / 22 logical processors; visible memory: 33,150,328 KiB (about 31.61 GiB).
- GPU reported by Windows: Intel Arc Graphics, driver `32.0.101.8243`. This run used the CPU-only runtime with `--n-gpu-layers 0`; no GPU offload was measured.
- Python `3.11.9`; Flask `3.1.3`.
- llama.cpp release: [`b12242`](https://github.com/ggml-org/llama.cpp/releases/tag/b12242), `llama-server` version `0.9.0-dev (build 12242, commit 3b4d6ab3f)`, built with Clang `20.1.8` for Windows x86_64.
- Runtime archive: `llama-b12242-bin-win-cpu-x64.zip`, 24,931,401 bytes; SHA-256 `4723cd1f1b10169b6ca681f787ea37238e449b1c56538b4b90c71a82fad949a0`.
- Model: [`Qwen3.5-0.8B-Q4_K_M.gguf`](https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF/blob/1870603ac8ab59c7ddb9d94cccf3b297e379538f/Qwen3.5-0.8B-Q4_K_M.gguf), from revision `1870603ac8ab59c7ddb9d94cccf3b297e379538f`, 590,880,672 bytes; SHA-256 `be5b3cb8c2f3ebd791349c9c775ea38950f23a2b9e792ca2f0411597dd172988`.
- At measurement, ignored `local_assets/` occupied 680,179,779 bytes (648.67 MiB), including the model, runtime archive, extracted runtime, and local logs. Model size is not RAM or VRAM usage.

## Reproduction command

Run from the repository root. This is the verified CPU command; `--reasoning off` is needed so the selected response content is returned within the app's 128-token output limit.

```powershell
$env:LLAMA_ARG_CORS_ORIGINS = "localhost"
& .\local_assets\runtime\cpu-b12242\llama-server.exe `
  -m .\local_assets\models\Qwen3.5-0.8B-Q4_K_M.gguf `
  --host 127.0.0.1 `
  --port 8080 `
  --ctx-size 2048 `
  --n-gpu-layers 0 `
  --reasoning off
```

In another PowerShell window:

```powershell
$env:LLAMA_SERVER_URL = "http://127.0.0.1:8080"
& .\.venv\Scripts\python.exe -m inference.app
```

The final restart returned `{"status":"ok"}` from `http://127.0.0.1:8080/health`, exposed the pinned model ID at `/v1/models`, and returned HTTP 200 from the Flask page at `http://127.0.0.1:7860/`. A CORS preflight for `http://localhost:7860` returned `Access-Control-Allow-Origin: http://localhost:7860`.

## Three live browser requests

The UI was marked `en-US`. For each request, the browser's displayed run ID matched `latest.json`; normalized token counts and TPS matched the raw response's `usage` and `timings`; client latency was positive. The quoted/multiline prompt retained its embedded quotes and newline.

| Input | `run_id` | Prompt / output tokens | Client latency | Server generation TPS |
|---|---|---:|---:|---:|
| English | `5d535edd-096a-4227-a9b9-8e9327f143d7` | 24 / 40 | 1.5066202000016347 s | 27.346639693998114 |
| Chinese | `c757ef33-d5da-4721-a75e-6de0c29751aa` | 20 / 47 | 1.227215199964121 s | 39.94171982099163 |
| Quoted and multiline | `31efb908-f34d-4fb6-9289-814199b4f5b3` | 32 / 33 | 0.9192063999944367 s | 38.23369870411658 |

Exact prompts sent in the browser UI:

1. English: `In one sentence, what does a local language model do?`
2. Chinese: `用一句话解释本地语言模型是什么。`
3. Quoted and multiline (the line break shown here was part of the prompt):

```text
Explain the phrase "local model" in one short sentence.
Include the word "offline".
```

Responses returned by this model:

1. **English:** “A local language model processes input data within a specific local environment to generate output, typically by leveraging its internal knowledge base and training data to perform tasks like translation, summarization, or logical reasoning.”
2. **Chinese:** “本地语言模型是指训练数据完全来自本地设备（如手机、电脑或服务器）的深度学习模型，其核心优势在于无需依赖云端算力即可实现实时推理，但同时也面临数据隐私和算力资源受限的挑战。”
3. **Quoted and multiline:** “A local model is a neural network trained on data from a single device or a specific geographic area, running entirely in **offline** mode without requiring internet connectivity.”

These are raw model outputs, not validated definitions. In particular, the Chinese and third answers incorrectly imply that a local model is defined by where its training data came from. The 0.8B model can hallucinate; verify factual claims independently.

## Failure observed and handling

A real request before setting `--reasoning off` returned `finish_reason=length`, `usage.completion_tokens=128`, and an empty `message.content` (with a non-empty reasoning field). The API rejected it as an invalid response and did not record it as a successful inference. After restarting with `--reasoning off`, all three browser requests above returned non-empty content and successful records. The failed response is retained only under ignored `local_assets/logs/`.

## Evidence files and scope

- [`demo_run.json`](demo_run.json): normalized record for `5d535edd-096a-4227-a9b9-8e9327f143d7`.
- [`demo_run_raw.json`](demo_run_raw.json): raw upstream response for that same request.
- [`screenshot.png`](screenshot.png): browser capture showing that response, metrics, and the same run ID. The browser validation reported no JavaScript console errors or page errors.
- No GPU runtime or `mmproj` was downloaded; no GPU offload or image inference is claimed. The automated test suite uses simulated responses and is separate evidence from these real runs.
