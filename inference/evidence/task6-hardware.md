# Task 6: Optional GPU and Image Inference

This evidence covers the optional GPU and image experiments after Tasks 1–5. It records actual local llama-server responses; mock tests are not used as model execution evidence. The run timestamps are preserved in the JSON records and were produced on 2026-11-13 UTC.

## Environment and artifacts

- Platform: Windows x64.
- Runtime: official llama.cpp b12242 Windows x64 CPU and Vulkan builds; llama-server reported 0.9.0-dev (build 12242, commit 3b4d6ab3f).
- Model: notschmee/Qwen3.5-0.8B-GGUF, revision 1870603ac8ab59c7ddb9d94cccf3b297e379538f, Q4_K_M file. CPU and Vulkan used the same model file.
- Device reported by llama-cli --list-devices: Vulkan0: Intel(R) Arc(TM) Graphics (18452 MiB, 17684 MiB free). This is reported available memory; it is not evidence of dedicated VRAM.
- Vulkan server startup log: 23 repeating layers were requested for offload and the runtime reported offloaded 25/25 layers to GPU. It also disabled Flash Attention over K/V rows because that operation was unsupported by this Vulkan device/runtime path.

| Local artifact | Size | SHA-256 |
| --- | ---: | --- |
| local_assets/runtime-vulkan/llama-b12242-bin-win-vulkan-x64.zip | 37,891,857 bytes | dd22ce13006727691186aa755559a8bd7c8491dc4e8b3a91a316b6e37ef96192 |
| local_assets/models/Qwen3.5-0.8B-mmproj-F16.gguf | 207,346,400 bytes | c85d84e89a6b1f9a006d02e7fa86282bd4a1dc1812cde949a5cc7031c68776bf |
| inference/evidence/sample_image.png | 972 bytes | 639cb4f9cc17d4cedc1c68101f00124d4cdd4b1bfa8b981e1054edad711a8830 |

The two downloaded optional artifacts remain under ignored local_assets/ and are not committed.

## CPU and Vulkan text runs

Both servers used the same prompt, model, context size 2048, max_tokens=128, temperature=0, non-streaming mode, and --reasoning off. CPU used --n-gpu-layers 0; Vulkan used --n-gpu-layers 99. The sequence alternated CPU, Vulkan, CPU, Vulkan.

| Backend | Run ID | Prompt/output tokens | Server generation TPS | Client end-to-end latency |
| --- | --- | ---: | ---: | ---: |
| CPU | 3098b44b-7a32-48e6-8054-0dd49dc80362 | 24 / 40 | 27.1257 | 1.5720 s |
| Vulkan | 50becbf7-454a-4802-bf54-e4b2fa7b970b | 24 / 38 | 36.6397 | 13.2472 s |
| CPU | d1fbc391-8761-4f03-992c-f61608c9196c | 24 / 40 | 26.3525 | 1.6621 s |
| Vulkan | 2ebedf40-5805-4b9c-a926-05d56e46e1b3 | 24 / 38 | 57.9119 | 1.5431 s |

The first Vulkan request had substantially higher end-to-end latency than the CPU request; the second was slightly lower. Server generation TPS and client end-to-end latency are different measurements. Two alternating requests are useful as a smoke comparison, not a general performance claim or a stable benchmark. Vulkan generation TPS was higher in these two observed requests, but this small sample does not establish consistent speedup.

## Image API run

- Synthetic, non-private 256×256 PNG: white background, red square on the left, blue circle on the right.
- The Vulkan server was started with the same Q4_K_M model plus --mmproj local_assets/models/Qwen3.5-0.8B-mmproj-F16.gguf; health check returned HTTP 200.
- A direct OpenAI-compatible POST /v1/chat/completions request containing the image data URL and a text prompt returned HTTP 200.
- Run ID: b61027aa-43c3-48f5-8cfe-0faf1c980a68.
- Prompt: What two colored shapes are shown, and where is each one?
- Observed response identified a red square on the left and a blue circle on the right. The exact response, raw server response, usage, and timings are in [image_run.json](image_run.json) and [image_run_raw.json](image_run_raw.json).
- Prompt/output tokens: 91 / 101. Client end-to-end latency: 2.8250 s. Server generation TPS: 60.1913.
- The normalized experiment record includes input_modality: image+text and the synthetic image SHA-256. This is evidence metadata only; the app's standard JSON schema and text-only UI were not changed.

Image TPS is not comparable to text TPS because prompt processing includes image input. The successful API call demonstrates this pinned runtime/model/projector combination accepted the tested image request; it does not establish broad image quality or application UI support.
