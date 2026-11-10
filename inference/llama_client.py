"""Client for a local llama-server OpenAI-compatible API."""

import json
import math
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError


class InferenceError(Exception):
    """A request or response error from the local inference service."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def _request_bytes(
    request: urllib.request.Request, timeout_seconds: float
) -> bytes:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if isinstance(status, int) and not 200 <= status < 300:
                raise InferenceError(
                    "upstream_error", f"llama-server returned HTTP {status}."
                )
            return response.read()
    except HTTPError as exc:
        raise InferenceError(
            "upstream_error", f"llama-server returned HTTP {exc.code}."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise InferenceError(
            "unavailable", "llama-server is unavailable or the request timed out."
        ) from exc


def _decode_json(body: bytes) -> dict[str, object]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InferenceError(
            "invalid_response", "llama-server returned invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise InferenceError(
            "invalid_response", "llama-server returned a JSON value instead of an object."
        )
    return payload


def _make_request(
    url: str, method: str, body: bytes | None = None
) -> urllib.request.Request:
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(url, data=body, headers=headers, method=method)


def _invalid_response(message: str) -> None:
    raise InferenceError("invalid_response", message)


def _require_token_count(value: object, name: str, *, positive: bool) -> int:
    minimum = 1 if positive else 0
    if type(value) is not int or value < minimum:
        expectation = "a positive integer" if positive else "a non-negative integer"
        _invalid_response(f"llama-server usage.{name} must be {expectation}.")
    return value


def _generation_speed(timings: object) -> float | int | None:
    if timings is None:
        return None
    if not isinstance(timings, dict):
        _invalid_response("llama-server timings must be an object when present.")

    value = timings.get("predicted_per_second")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid_response(
            "llama-server timings.predicted_per_second must be a number or null."
        )
    try:
        is_finite = math.isfinite(value)
    except OverflowError:
        is_finite = False
    if not is_finite or value < 0:
        _invalid_response(
            "llama-server timings.predicted_per_second must be a finite non-negative number."
        )
    return value


def infer(
    prompt: str,
    server_url: str,
    timeout_seconds: float = 120.0,
) -> dict[str, object]:
    """Run one non-streaming completion and return its normalized metrics."""

    base_url = server_url.rstrip("/")
    models_request = _make_request(f"{base_url}/v1/models", "GET")
    models_response = _decode_json(
        _request_bytes(models_request, timeout_seconds)
    )
    models = models_response.get("data")
    if not isinstance(models, list) or not models:
        _invalid_response("llama-server /v1/models did not return any models.")
    first_model = models[0]
    if not isinstance(first_model, dict):
        _invalid_response("llama-server /v1/models returned an invalid model entry.")
    model_id = first_model.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        _invalid_response("llama-server /v1/models returned a model without an ID.")

    chat_payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
        "temperature": 0,
        "stream": False,
    }
    chat_body = json.dumps(
        chat_payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    chat_request = _make_request(
        f"{base_url}/v1/chat/completions", "POST", chat_body
    )

    started_at = time.perf_counter()
    response_body = _request_bytes(chat_request, timeout_seconds)
    latency_seconds = time.perf_counter() - started_at
    if latency_seconds <= 0:
        raise InferenceError(
            "unavailable", "Client could not measure a positive request latency."
        )
    server_response = _decode_json(response_body)

    choices = server_response.get("choices")
    if not isinstance(choices, list) or not choices:
        _invalid_response("llama-server returned no completion choices.")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        _invalid_response("llama-server returned an invalid completion choice.")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        _invalid_response("llama-server completion did not include a message.")
    response_text = message.get("content")
    if not isinstance(response_text, str) or not response_text.strip():
        _invalid_response("llama-server completion response was empty.")

    usage = server_response.get("usage")
    if not isinstance(usage, dict):
        _invalid_response("llama-server completion did not include usage metrics.")
    prompt_tokens = _require_token_count(
        usage.get("prompt_tokens"), "prompt_tokens", positive=False
    )
    output_tokens = _require_token_count(
        usage.get("completion_tokens"), "completion_tokens", positive=True
    )

    timings = server_response.get("timings")
    generation_tokens_per_second = _generation_speed(timings)

    timestamp_utc = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    return {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "timestamp_utc": timestamp_utc,
        "model_id": model_id,
        "prompt": prompt,
        "response": response_text,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "latency_seconds": latency_seconds,
        "generation_tokens_per_second": generation_tokens_per_second,
        "status": "success",
        "server_usage": usage,
        "server_timings": timings,
        "server_raw_response": server_response,
    }
