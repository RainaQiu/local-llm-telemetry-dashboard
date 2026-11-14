# Member A handoff — local model and inference (Sprint 2)

**Owner:** Raina Qiu · **Repository:** `RainaQiu/local-llm-telemetry-dashboard` · **Branch:** `codex/a-sprint2-task1`
**Status:** Member A's Sprint 2 scope is complete. This is a working inference prototype and a set of measured experiments, not a claim that the team's full application is complete.

## What A delivered

| Agreed Sprint 2 A criterion | Delivered evidence |
| --- | --- |
| Run a small pretrained LLM on an ordinary laptop | Qwen3.5-0.8B Q4_K_M GGUF runs through a pinned llama.cpp `llama-server` build on this Windows laptop. See [setup and artifact checksums](inference/README.md) and [environment record](inference/evidence/environment.md). |
| Accept a prompt and generate a response | The Flask page and `POST /api/infer` call the local server. A successful real request is in [demo_run.json](inference/evidence/demo_run.json), with a [screenshot](inference/evidence/screenshot.png). |
| Record response, token count, latency, and optional tokens/s | The same successful request returns the response, prompt/output tokens, client request latency, generation tokens/s, timestamp, and run ID. Its raw upstream response and timings are retained in the record. |
| Provide reproducible steps and a real result | [Local inference guide](inference/README.md) includes pinned versions, SHA-256 hashes, setup/launch commands, metric definitions, and troubleshooting. `inference/evidence/` contains real run records. |

The local web page is an A-module demonstration; the full CPU/RAM dashboard, agent, and fine-tuning are outside the agreed A scope. Jason's Local LLM Lab provides those broader product workflows independently.

## Interface for teammates

The app binds to `127.0.0.1:7860` and calls `llama-server` at `127.0.0.1:8080` by default. Submit a JSON request:

```http
POST http://127.0.0.1:7860/api/infer
Content-Type: application/json

{"prompt":"In one sentence, what does a local language model do?"}
```

The successful JSON response includes these stable top-level fields:

```json
{
  "schema_version": "1.0",
  "run_id": "5d535edd-096a-4227-a9b9-8e9327f143d7",
  "timestamp_utc": "2026-11-12T00:06:40.889983Z",
  "model_id": "local_assets/models/Qwen3.5-0.8B-Q4_K_M.gguf",
  "prompt": "In one sentence, what does a local language model do?",
  "response": "A local language model processes input data within a specific local environment to generate output, typically by leveraging its internal knowledge base and training data to perform tasks like translation, summarization, or logical reasoning.",
  "prompt_tokens": 24,
  "output_tokens": 40,
  "latency_seconds": 1.5066202000016347,
  "generation_tokens_per_second": 27.346639693998114,
  "status": "success"
}
```

This is an excerpt of the measured [full response](inference/evidence/demo_run.json), which also contains `server_usage`, `server_timings`, and `server_raw_response`. `generation_tokens_per_second` is `null` if the upstream server provides no timing. `latency_seconds` measures the client's chat-completion request; it is distinct from server generation speed. The endpoint accepts a trimmed prompt of 1–4,000 characters. Invalid input returns HTTP 400; an unavailable server returns 503; invalid/upstream responses return 502; a record-write failure returns 500. Input/upstream failures are not saved; a record-write failure does not return a success response.

Every successful request is written to the Git-ignored `inference/runs/latest.json` and appended to `inference/runs/history.jsonl`. These files include prompts and responses; review them before sharing. Teammates can consume the HTTP response directly or read `latest.json` for a local demo. The `run_id` links the UI result, normalized record, and raw server response.

## Run it locally

The [guide](inference/README.md) is the source of truth for first-time downloads and SHA-256 checks. After the pinned model and CPU runtime are present in Git-ignored `local_assets/`:

1. Start the CPU `llama-server` on `127.0.0.1:8080` with the Qwen GGUF, `--ctx-size 2048`, `--n-gpu-layers 0`, and `--reasoning off`; wait for `/health` to return `{"status":"ok"}`. The exact command is in the guide.
2. From the repository root, run `.\.venv\Scripts\python.exe -m inference.app` on Windows after installing `inference/requirements.txt` into the venv. The page is at `http://127.0.0.1:7860`.
3. Submit an English prompt through the page or `POST /api/infer`. Inspect the returned JSON and the local `inference/runs/` records.
4. Run tests with `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. On 2026-11-14 this environment's Python 3.11.9 ran **20 tests, all passing**. The tests mock model responses; the evidence files above document real model execution separately.

The runtime binaries, model, and projector are intentionally excluded from Git. A fresh clone must follow the download/verification instructions before attempting inference. The app is local-only and neither service should be exposed on a public network for this demo.

## Additional A experiments available to the team

- **Intel Arc/Vulkan:** The same Qwen GGUF ran with llama.cpp's Vulkan build; its startup log reported **25/25 layers offloaded** to Intel Arc. This laptop does have a GPU, even though Local LLM Lab's current PyTorch path uses CPU on it. The reported 18,452 MiB Vulkan memory must not be called dedicated VRAM.
- **Controlled CPU/Vulkan comparison:** Two short sessions kept the model and prompt fixed. In the repeat session, mean server generation speed was 54.24 tok/s on CPU and 63.01 tok/s on Vulkan, while mean client latency was 0.80 s on CPU and 0.94 s on Vulkan. There were only two requests per backend in that session; this is a reproducibility/smoke comparison, not a stable speedup claim. See [hardware evidence](inference/evidence/task6-hardware.md) and [raw comparison records](inference/evidence/task6_comparison_runs.json).
- **Image input:** Qwen plus the pinned `mmproj` accepted a synthetic image and answered the tested shape/location prompt through llama-server's API. This was **API-only**; the Flask page remains text-only. See [image record](inference/evidence/image_run.json).

These experiments add hardware-compatibility and measurement evidence to Jason's desktop demo. They use a different model format and runtime from Local LLM Lab, so their speed figures must not be directly compared with its SmolLM2/PyTorch figures. A future optional llama.cpp backend would require a deliberate interface design with Jason; it is not needed to count A's Sprint 2 delivery.

## Suggested team use

Use Local LLM Lab for the main guided product demonstration. Credit this work as **Member A: model selection, local inference, telemetry contract, reproducibility, and Intel Arc/Vulkan investigation** in the progress update and final presentation. I can provide the JSON interface and run records to whoever owns dashboard/integration, and explain the CPU/Vulkan findings. No code merge is required for that handoff.
