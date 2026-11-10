import io
import json
import unittest
import uuid
from urllib.error import HTTPError
from unittest.mock import patch

from inference.llama_client import InferenceError, infer


class FakeHTTPResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.status = 200

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class LlamaClientTests(unittest.TestCase):
    server_url = "http://127.0.0.1:8080"

    def models_response(self):
        return FakeHTTPResponse({"data": [{"id": "demo-model"}]})

    def completion_response(self, **overrides):
        payload = {
            "choices": [{"message": {"role": "assistant", "content": "Hello"}}],
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": 5,
                "total_tokens": 12,
            },
            "timings": {
                "prompt_ms": 10.0,
                "predicted_ms": 250.0,
                "predicted_per_second": 20.0,
            },
        }
        payload.update(overrides)
        return payload

    def run_with_responses(self, *responses, prompt="Hi"):
        with patch("urllib.request.urlopen", side_effect=responses):
            return infer(prompt, self.server_url)

    def assert_inference_error(self, expected_kind, *responses):
        with patch("urllib.request.urlopen", side_effect=responses):
            with self.assertRaises(InferenceError) as raised:
                infer("Hi", self.server_url)
        self.assertEqual(raised.exception.kind, expected_kind)

    def test_normalizes_metrics_and_measures_only_chat_request(self):
        raw_response = self.completion_response()
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=[
                    self.models_response(),
                    FakeHTTPResponse(raw_response),
                ],
            ) as urlopen,
            patch(
                "inference.llama_client.time.perf_counter",
                side_effect=[10.0, 12.5],
            ),
        ):
            record = infer("Hi", self.server_url)

        self.assertEqual(record["schema_version"], "1.0")
        self.assertEqual(record["model_id"], "demo-model")
        self.assertEqual(record["prompt"], "Hi")
        self.assertEqual(record["response"], "Hello")
        self.assertEqual(record["prompt_tokens"], 7)
        self.assertEqual(record["output_tokens"], 5)
        self.assertEqual(record["generation_tokens_per_second"], 20.0)
        self.assertEqual(record["latency_seconds"], 2.5)
        self.assertGreater(record["latency_seconds"], 0)
        self.assertEqual(record["server_usage"], raw_response["usage"])
        self.assertEqual(record["server_timings"], raw_response["timings"])
        self.assertEqual(record["server_raw_response"], raw_response)
        self.assertEqual(record["status"], "success")
        self.assertEqual(uuid.UUID(record["run_id"]).version, 4)

        self.assertEqual(urlopen.call_count, 2)
        models_request = urlopen.call_args_list[0].args[0]
        self.assertEqual(models_request.full_url, f"{self.server_url}/v1/models")
        self.assertEqual(models_request.get_method(), "GET")
        chat_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(
            chat_request.full_url,
            f"{self.server_url}/v1/chat/completions",
        )
        self.assertEqual(chat_request.get_method(), "POST")
        request_payload = json.loads(chat_request.data.decode("utf-8"))
        self.assertEqual(request_payload["model"], "demo-model")
        self.assertEqual(request_payload["messages"], [{"role": "user", "content": "Hi"}])
        self.assertEqual(request_payload["max_tokens"], 128)
        self.assertEqual(request_payload["temperature"], 0)
        self.assertIs(request_payload["stream"], False)
        self.assertEqual(urlopen.call_args_list[0].kwargs["timeout"], 120.0)
        self.assertEqual(urlopen.call_args_list[1].kwargs["timeout"], 120.0)

    def test_preserves_unicode_quotes_and_newlines_in_prompt(self):
        prompt = '请用中文回答："你好"\n第二行包含引号 \' 和反斜线 \\。'
        with patch(
            "urllib.request.urlopen",
            side_effect=[
                self.models_response(),
                FakeHTTPResponse(self.completion_response()),
            ],
        ) as urlopen:
            infer(prompt, self.server_url)

        chat_request = urlopen.call_args_list[1].args[0]
        request_payload = json.loads(chat_request.data.decode("utf-8"))
        self.assertEqual(request_payload["messages"][0]["content"], prompt)

    def test_connection_refused_is_unavailable(self):
        self.assert_inference_error(
            "unavailable",
            ConnectionRefusedError("connection refused"),
        )

    def test_request_timeout_is_unavailable(self):
        self.assert_inference_error(
            "unavailable",
            self.models_response(),
            TimeoutError("request timed out"),
        )

    def test_http_503_is_an_upstream_error(self):
        error = HTTPError(
            f"{self.server_url}/v1/chat/completions",
            503,
            "Service Unavailable",
            None,
            io.BytesIO(b"Loading"),
        )
        self.assert_inference_error("upstream_error", self.models_response(), error)

    def test_empty_choices_is_invalid_response(self):
        self.assert_inference_error(
            "invalid_response",
            self.models_response(),
            FakeHTTPResponse(self.completion_response(choices=[])),
        )

    def test_missing_usage_is_invalid_response(self):
        response = self.completion_response()
        response.pop("usage")
        self.assert_inference_error(
            "invalid_response",
            self.models_response(),
            FakeHTTPResponse(response),
        )

    def test_non_integer_completion_tokens_is_invalid_response(self):
        response = self.completion_response()
        response["usage"]["completion_tokens"] = "five"
        self.assert_inference_error(
            "invalid_response",
            self.models_response(),
            FakeHTTPResponse(response),
        )

    def test_empty_response_is_invalid_response(self):
        response = self.completion_response()
        response["choices"][0]["message"]["content"] = " \n"
        self.assert_inference_error(
            "invalid_response",
            self.models_response(),
            FakeHTTPResponse(response),
        )

    def test_missing_generation_speed_is_null_and_keeps_raw_response(self):
        response = self.completion_response()
        response.pop("timings")
        record = self.run_with_responses(
            self.models_response(),
            FakeHTTPResponse(response),
        )

        self.assertIsNone(record["generation_tokens_per_second"])
        self.assertIsNone(record["server_timings"])
        self.assertEqual(record["server_raw_response"], response)


    def test_zero_measured_latency_does_not_return_success(self):
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=[
                    self.models_response(),
                    FakeHTTPResponse(self.completion_response()),
                ],
            ),
            patch(
                "inference.llama_client.time.perf_counter",
                side_effect=[10.0, 10.0],
            ),
        ):
            with self.assertRaises(InferenceError) as raised:
                infer("Hi", self.server_url)

        self.assertEqual(raised.exception.kind, "unavailable")

if __name__ == "__main__":
    unittest.main()
