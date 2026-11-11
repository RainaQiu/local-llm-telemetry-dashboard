"use strict";

const form = document.querySelector("#inference-form");
const promptInput = document.querySelector("#prompt");
const submitButton = document.querySelector("#submit");
const statusMessage = document.querySelector("#status");
const responseOutput = document.querySelector("#response");
const promptTokensOutput = document.querySelector("#prompt-tokens");
const outputTokensOutput = document.querySelector("#output-tokens");
const latencyOutput = document.querySelector("#latency");
const tpsOutput = document.querySelector("#tps");
const runIdOutput = document.querySelector("#run-id");

function setStatus(message, state) {
  statusMessage.textContent = message;
  statusMessage.dataset.state = state;
}

function clearResult() {
  responseOutput.textContent = "等待一次推理后显示回答。";
  promptTokensOutput.textContent = "—";
  outputTokensOutput.textContent = "—";
  latencyOutput.textContent = "—";
  tpsOutput.textContent = "—";
  runIdOutput.textContent = "—";
}

function isValidRecord(record) {
  return (
    record !== null &&
    typeof record === "object" &&
    typeof record.response === "string" &&
    record.response.trim().length > 0 &&
    Number.isInteger(record.prompt_tokens) &&
    record.prompt_tokens >= 0 &&
    Number.isInteger(record.output_tokens) &&
    record.output_tokens > 0 &&
    typeof record.latency_seconds === "number" &&
    Number.isFinite(record.latency_seconds) &&
    record.latency_seconds > 0 &&
    (record.generation_tokens_per_second === null ||
      (typeof record.generation_tokens_per_second === "number" &&
        Number.isFinite(record.generation_tokens_per_second) &&
        record.generation_tokens_per_second >= 0)) &&
    typeof record.run_id === "string" &&
    record.run_id.trim().length > 0
  );
}

function renderRecord(record) {
  responseOutput.textContent = record.response;
  promptTokensOutput.textContent = String(record.prompt_tokens);
  outputTokensOutput.textContent = String(record.output_tokens);
  latencyOutput.textContent = `${record.latency_seconds.toFixed(2)} 秒`;
  tpsOutput.textContent =
    record.generation_tokens_per_second === null
      ? "暂不可用"
      : `${record.generation_tokens_per_second.toFixed(2)} tokens/s`;
  runIdOutput.textContent = record.run_id;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) {
    clearResult();
    setStatus("请输入 Prompt 后再生成。", "error");
    promptInput.focus();
    return;
  }

  clearResult();
  submitButton.disabled = true;
  setStatus("正在生成", "loading");

  try {
    const response = await fetch("/api/infer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    let record;
    try {
      record = await response.json();
    } catch {
      throw new Error("服务返回了无法读取的响应。请检查本地推理服务。");
    }

    if (!response.ok) {
      throw new Error(
        typeof record.error === "string"
          ? record.error
          : "本次推理失败，请检查本地推理服务。",
      );
    }
    if (!isValidRecord(record)) {
      throw new Error("服务返回的数据不完整，本次结果未显示。请重试。");
    }

    renderRecord(record);
    setStatus("生成完成", "success");
  } catch (error) {
    clearResult();
    const message =
      error instanceof Error && error.message
        ? error.message
        : "请求失败，请检查本地推理服务。";
    setStatus(message, "error");
  } finally {
    submitButton.disabled = false;
  }
});
