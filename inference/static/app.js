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
  responseOutput.textContent = "Your response will appear here after an inference run.";
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
  latencyOutput.textContent = `${record.latency_seconds.toFixed(2)} s`;
  tpsOutput.textContent =
    record.generation_tokens_per_second === null
      ? "Not available"
      : `${record.generation_tokens_per_second.toFixed(2)} tokens/s`;
  runIdOutput.textContent = record.run_id;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) {
    clearResult();
    setStatus("Enter a prompt before generating.", "error");
    promptInput.focus();
    return;
  }

  clearResult();
  submitButton.disabled = true;
  setStatus("Generating...", "loading");

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
      throw new Error("The server returned an unreadable response. Check that the local inference service is running.");
    }

    if (!response.ok) {
      throw new Error(
        typeof record.error === "string"
          ? record.error
          : "Inference failed. Check that the local inference service is running.",
      );
    }
    if (!isValidRecord(record)) {
      throw new Error("The server returned an incomplete result. No result was shown. Please try again.");
    }

    renderRecord(record);
    setStatus("Generation complete", "success");
  } catch (error) {
    clearResult();
    const message =
      error instanceof Error && error.message
        ? error.message
        : "Request failed. Check that the local inference service is running.";
    setStatus(message, "error");
  } finally {
    submitButton.disabled = false;
  }
});
