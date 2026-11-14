# Part A: local inference

Hi all,

I finished the local model and inference work we planned for Sprint 2. I used `llama.cpp` to run a small Qwen model on my laptop, built a simple page for entering prompts, and saved the answer and timing data from each run.

## What works

The model is Qwen3.5 0.8B in a 4-bit GGUF file. `llama-server` runs it locally; a small Flask app sends it prompts and shows the response. Each run records input/output tokens, request latency, generation speed, and a run ID. The latest result is saved in `inference/runs/latest.json`.

To call it from code, send `{"prompt":"Your question here"}` to `POST http://127.0.0.1:7860/api/infer`. The response includes `response`, `prompt_tokens`, `output_tokens`, `latency_seconds`, and `generation_tokens_per_second`. The [setup steps](inference/README.md) and a [real response](inference/evidence/demo_run.json) are in this repo. Model files and binaries are downloaded separately; they are not in Git.

## Results from my laptop

These runs were on my Windows laptop with an Intel Core Ultra 7 155H, 32 GB RAM, and Intel Arc integrated graphics. The CPU and Vulkan tests used the same Qwen model and prompt. Each row below is one actual request, in the order it ran.

### First test (13 November)

| Order | Where it ran | Input / output tokens | Request latency | Generation speed |
| --- | --- | ---: | ---: | ---: |
| 1 | CPU | 24 / 40 | 1.57 s | 27.13 tokens/s |
| 2 | Intel Arc (Vulkan) | 24 / 38 | 13.25 s | 36.64 tokens/s |
| 3 | CPU | 24 / 40 | 1.66 s | 26.35 tokens/s |
| 4 | Intel Arc (Vulkan) | 24 / 38 | 1.54 s | 57.91 tokens/s |

### Second test (14 November)

| Order | Where it ran | Input / output tokens | Request latency | Generation speed |
| --- | --- | ---: | ---: | ---: |
| 1 | CPU | 24 / 40 | 0.83 s | 54.07 tokens/s |
| 2 | Intel Arc (Vulkan) | 24 / 38 | 0.90 s | 63.28 tokens/s |
| 3 | CPU | 24 / 40 | 0.77 s | 54.40 tokens/s |
| 4 | Intel Arc (Vulkan) | 24 / 38 | 0.99 s | 62.74 tokens/s |

The first Vulkan request took much longer to finish than the others; we did not measure why. The Vulkan startup log showed all 25 model layers offloaded to Intel Arc. See the [test notes](inference/evidence/task6-hardware.md) and [raw run records](inference/evidence/task6_comparison_runs.json).

I also sent one synthetic image through the server API: 91 input tokens, 101 output tokens, 2.83 s request latency, and 60.19 tokens/s. The [image result](inference/evidence/image_run.json) is saved. The Flask page only accepts text, and the image run is a different workload from the tables.

"CPU" in the tables means the model ran on the CPU. I did **not** record CPU utilization (%) or RAM use during these A runs, so I do not have measured percentages to report.

## How this fits with Local LLM Lab

Jason's desktop app is our main demo. It uses PyTorch for inference and training; my prototype uses `llama.cpp` and a quantized model. His current app runs on CPU on my Intel Arc laptop, while my Vulkan run used the GPU. We can show this as a short hardware experiment without merging the codebases.

I can walk through the setup and results, or share the JSON output with whoever is working on the dashboard or integration. I reran the project's tests on 14 November: 20 passed.

Raina
