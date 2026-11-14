# Part A: local inference

Hi all,

I finished the local model and inference work we planned for Sprint 2. I used `llama.cpp` to run a small Qwen model on my laptop, built a simple page for entering prompts, and saved the answer and timing data from each run.

## What works

The model is Qwen3.5 0.8B in a 4-bit GGUF file. `llama-server` runs it locally; a small Flask app sends it prompts and shows the response. Each successful run records the input and output token counts, request latency, generation speed, and a run ID. The latest result is also saved in `inference/runs/latest.json`, so another part of the project can read it.

If you want to call it from code, send `{"prompt":"Your question here"}` to `POST http://127.0.0.1:7860/api/infer`. The response has `response`, `prompt_tokens`, `output_tokens`, `latency_seconds`, and `generation_tokens_per_second`, along with the raw `llama-server` data. A [real example](inference/evidence/demo_run.json) and the [setup steps](inference/README.md) are in this repo. Model files and binaries are downloaded separately, so they are not in Git.

## What I found on my laptop

My Intel Arc graphics worked with the Vulkan build of `llama.cpp`; its log showed all 25 layers offloaded. I also ran the same model and prompt on CPU and Vulkan twice. In the repeat test, Vulkan generated about 63 tokens/s and CPU about 54 tokens/s, but the whole request took about 0.94 s on Vulkan versus 0.80 s on CPU. These are small test runs, so I would present them as observations rather than a general speed claim. I also tested one image prompt with Qwen's projector through the server API; the Flask page itself only accepts text. The [run details](inference/evidence/task6-hardware.md) and [image result](inference/evidence/image_run.json) are here.

## How this fits with Local LLM Lab

Jason's desktop app is our main demo. It uses PyTorch for inference and training; my prototype uses `llama.cpp` and a quantized model. On my Intel Arc laptop, his current app runs on CPU, while this route can use the GPU. We can include that as a short hardware experiment in the team report or presentation. We do not need to merge the two codebases for the demo.

I can walk through the inference setup and results, or share the JSON output with whoever is working on the dashboard or integration. I reran the project's tests on 14 November: 20 passed.

Raina
