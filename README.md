# Local LLM Telemetry Dashboard

A local-first inference telemetry demo powered by `llama.cpp` `llama-server`. It displays the response and metrics for the same request.

## What It Includes

- A Flask web app and JSON API bound to `127.0.0.1`.
- A prompt page that displays the response, prompt and output token counts, end-to-end latency, generation speed, and `run_id`.
- Local run records written to `inference/runs/latest.json` and `inference/runs/history.jsonl`.

The current implementation focuses on local inference. It does not include model training, a system resource dashboard, or an agent workflow.

## Requirements

- Python 3.11 or newer.
- A separately installed `llama-server` with a loaded model. It must expose the OpenAI-compatible `/v1/models` and `/v1/chat/completions` endpoints.

This repository does not include `llama.cpp` binaries or model weights. Start your own local `llama-server` before submitting a prompt. The app defaults to `http://127.0.0.1:8080`; set `LLAMA_SERVER_URL` to use another local endpoint.

## Run the App

Run these commands from the repository root.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r inference\requirements.txt
$env:LLAMA_SERVER_URL = "http://127.0.0.1:8080"
.\.venv\Scripts\python.exe -m inference.app
```

### macOS or Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r inference/requirements.txt
LLAMA_SERVER_URL="http://127.0.0.1:8080" .venv/bin/python -m inference.app
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860). The web app binds to loopback and is intended for local use.

## Metrics and Records

Prompt and completion token counts come from the `usage` object in the same `llama-server` completion response as the displayed answer. Generation speed comes from `timings.predicted_per_second`; when the server omits that value, the API stores `null` and the page shows "Not available." End-to-end latency is measured by the Python client around the chat completion request. It is not calculated from token counts.

Successful records contain the normalized metrics and the original server usage, timing, and response objects. The prompt and response are saved locally in the run files, so review their contents before sharing them.

The API accepts `POST /api/infer` with a JSON body such as:

```json
{
  "prompt": "Explain local language models in one sentence."
}
```

Prompts must contain 1-4,000 characters after trimming. If `llama-server` is unavailable or returns an invalid response, the page shows an error and does not present a successful run.

## Run Tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests use simulated HTTP responses and do not require model weights or a running `llama-server`. A passing test suite does not mean that real model inference has been run.

For the pinned Windows runtime, model checksums, launch commands, and verified run evidence, see the [local inference guide](inference/README.md).
