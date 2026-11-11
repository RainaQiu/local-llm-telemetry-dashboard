# Local Inference Setup

This guide runs the Flask demo with a local `llama.cpp` server and the Qwen3.5-0.8B Q4_K_M GGUF model. The runtime and model stay under the ignored `local_assets/` directory; neither is committed to Git.

## Requirements

- Windows x64 and Python 3.11 or newer.
- A network connection for the one-time downloads below.
- About 650 MiB for the model, runtime archive, and extracted CPU runtime, plus Python environment and runtime cache space.

The selected GGUF is a community quantization of Qwen3.5-0.8B from [`notschmee/Qwen3.5-0.8B-GGUF`](https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF). The llama.cpp CPU runtime is the `b12242` pre-release from the [official releases page](https://github.com/ggml-org/llama.cpp/releases/tag/b12242). These are the exact artifacts exercised for the real run recorded in [`evidence/environment.md`](evidence/environment.md).

## Download and Verify the Required Files

Run these PowerShell commands from the repository root. They download only the CPU runtime archive and the single Q4_K_M model file. They do not download the full Hugging Face repository, a GPU runtime, or an mmproj file.

```powershell
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path local_assets\runtime,local_assets\models | Out-Null

curl.exe --fail --location --retry 3 --retry-all-errors `
  --output local_assets\runtime\llama-b12242-bin-win-cpu-x64.zip `
  https://github.com/ggml-org/llama.cpp/releases/download/b12242/llama-b12242-bin-win-cpu-x64.zip
if ($LASTEXITCODE -ne 0) { throw "The llama.cpp runtime download failed." }

$runtimeSha256 = (Get-FileHash local_assets\runtime\llama-b12242-bin-win-cpu-x64.zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($runtimeSha256 -ne "4723cd1f1b10169b6ca681f787ea37238e449b1c56538b4b90c71a82fad949a0") {
  throw "The runtime SHA-256 does not match the official release digest."
}

Expand-Archive `
  -LiteralPath local_assets\runtime\llama-b12242-bin-win-cpu-x64.zip `
  -DestinationPath local_assets\runtime\cpu-b12242

$modelUrl = "https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF/resolve/1870603ac8ab59c7ddb9d94cccf3b297e379538f/Qwen3.5-0.8B-Q4_K_M.gguf?download=true"
curl.exe --fail --location --retry 3 --retry-all-errors `
  --output local_assets\models\Qwen3.5-0.8B-Q4_K_M.gguf `
  $modelUrl
if ($LASTEXITCODE -ne 0) { throw "The model download failed." }

$modelSha256 = (Get-FileHash local_assets\models\Qwen3.5-0.8B-Q4_K_M.gguf -Algorithm SHA256).Hash.ToLowerInvariant()
if ($modelSha256 -ne "be5b3cb8c2f3ebd791349c9c775ea38950f23a2b9e792ca2f0411597dd172988") {
  throw "The model SHA-256 does not match the pinned Hugging Face revision."
}

Get-Item local_assets\runtime\llama-b12242-bin-win-cpu-x64.zip,local_assets\models\Qwen3.5-0.8B-Q4_K_M.gguf |
  Select-Object FullName,Length
```

Verified artifact metadata:

| Artifact | Pinned source | Bytes | SHA-256 |
|---|---|---:|---|
| `llama-b12242-bin-win-cpu-x64.zip` | [llama.cpp b12242 release](https://github.com/ggml-org/llama.cpp/releases/tag/b12242) | 24,931,401 | `4723cd1f1b10169b6ca681f787ea37238e449b1c56538b4b90c71a82fad949a0` |
| `Qwen3.5-0.8B-Q4_K_M.gguf` | [Hugging Face file](https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF/blob/1870603ac8ab59c7ddb9d94cccf3b297e379538f/Qwen3.5-0.8B-Q4_K_M.gguf) at revision `1870603ac8ab59c7ddb9d94cccf3b297e379538f` | 590,880,672 | `be5b3cb8c2f3ebd791349c9c775ea38950f23a2b9e792ca2f0411597dd172988` |

The release reports `llama-server` version `0.9.0-dev (build 12242, commit 3b4d6ab3f)` on this machine. The CPU archive extracted to `local_assets/runtime/cpu-b12242/`; verify the path with `Test-Path` after extraction.

## Create the Python Environment

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r inference\requirements.txt
```

The verified environment used Python 3.11.9 and Flask 3.1.3.

## Start Both Local Services

In the first PowerShell window, set CORS to localhost and start the CPU server:

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

The `--reasoning off` option is required for this model/runtime combination with this app's 128-token response limit. Without it, the tested build used the entire completion allowance in `reasoning_content`, left `message.content` empty, and the app correctly returned HTTP 502 rather than recording a false success. `LLAMA_ARG_CORS_ORIGINS=localhost` uses the release's documented localhost-only CORS setting; the app calls llama-server from Flask, so browser code does not need direct access to port 8080.

Wait for the model to load, then check health from another window:

```powershell
curl.exe --noproxy "*" http://127.0.0.1:8080/health
```

The verified ready response is `{"status":"ok"}`. Do not submit prompts while the model is still loading.

In a second PowerShell window, run the Flask app:

```powershell
# Optional override; this is the app's default.
$env:LLAMA_SERVER_URL = "http://127.0.0.1:8080"
& .\.venv\Scripts\python.exe -m inference.app
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860). Both services bind to loopback. Do not change their host to `0.0.0.0` for this local demo.

## Run Tests

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The automated tests use simulated HTTP responses and do not prove real model execution. The real prompts, run IDs, metrics, and screenshot are recorded under `inference/evidence/`.

## Records and Metric Definitions

Successful records are written to `inference/runs/latest.json` and appended to `inference/runs/history.jsonl`. Both paths are Git-ignored because records contain prompts and responses.

- `prompt_tokens` and `output_tokens` come from `usage.prompt_tokens` and `usage.completion_tokens` in the same upstream completion response as the displayed answer.
- `generation_tokens_per_second` comes from that response's `timings.predicted_per_second`; it is `null` if the server omits the field. The UI then displays “Not available.”
- `latency_seconds` is measured by the Python client around the chat-completion HTTP request using a monotonic clock. It is not calculated by dividing tokens by time.
- `run_id` joins the browser result, normalized JSON record, and `server_raw_response`.

[`example_output.json`](example_output.json) is a schema placeholder with `run_id: "example-only"` and `status: "example"`. It contains no measured tokens, latency, TPS, prompt, or model response. Use [`evidence/demo_run.json`](evidence/demo_run.json) for the real, measured record.

## Troubleshooting

- **Health check is unavailable:** wait for the model load to finish and confirm the GGUF path. The app maps an unavailable llama-server to HTTP 503 and does not save a success record.
- **Port 8080 is occupied:** identify and stop the process that owns the port before starting `llama-server`; do not terminate an unknown process.
- **Port 7860 is occupied:** identify and stop the process that owns the port before starting Flask.
- **HTTP 502 with an empty completion:** confirm `--reasoning off` is present. The default reasoning output from the tested build can consume the 128-token budget without producing `message.content`.
- **The browser page is unavailable:** confirm the Flask process is running at `127.0.0.1:7860` and check its terminal for errors.

## Scope and Limitations

This is the CPU-only local inference baseline. A GPU comparison would require a separate Vulkan runtime and explicit offload validation. Image input would require a compatible `mmproj` file and API/UI support. Neither optional artifact or feature is downloaded or included here. Training, a resource dashboard, and an agent workflow are also out of scope. The 0.8B model can produce inaccurate answers; treat output as a demo and verify factual claims independently. The exact tested prompts and real outputs are in [`evidence/environment.md`](evidence/environment.md) and [`evidence/demo_run.json`](evidence/demo_run.json).
