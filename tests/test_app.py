import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inference.app import create_app
from inference.llama_client import InferenceError


class InferenceAppTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary_directory.name) / "runs"
        self.server_url = "http://127.0.0.1:8080"
        self.app = create_app(
            data_dir=self.data_dir,
            server_url=self.server_url,
        )
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_post_returns_and_saves_the_same_inference_record(self):
        record = {
            "schema_version": "1.0",
            "run_id": "run-001",
            "prompt": "Hi",
            "response": "Hello",
            "status": "success",
        }

        with (
            patch("inference.app.infer", return_value=record) as infer_mock,
            patch("inference.app.save_run") as save_mock,
        ):
            response = self.client.post(
                "/api/infer",
                json={"prompt": "  Hi  ", "server_url": "http://untrusted.invalid"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), record)
        infer_mock.assert_called_once_with("Hi", self.server_url)
        save_mock.assert_called_once_with(record, self.data_dir)

    def test_invalid_prompts_return_400_without_inference_or_storage(self):
        invalid_payloads = [
            {"prompt": "  "},
            {},
            {"prompt": 7},
            {"prompt": "x" * 4001},
        ]

        with (
            patch("inference.app.infer") as infer_mock,
            patch("inference.app.save_run") as save_mock,
        ):
            for payload in invalid_payloads:
                with self.subTest(payload=payload if len(str(payload)) < 100 else "too long"):
                    response = self.client.post("/api/infer", json=payload)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("error", response.get_json())

        infer_mock.assert_not_called()
        save_mock.assert_not_called()

    def test_inference_errors_return_gateway_status_and_are_not_saved(self):
        cases = [
            ("unavailable", 503),
            ("invalid_response", 502),
            ("upstream_error", 502),
        ]

        for kind, expected_status in cases:
            with self.subTest(kind=kind):
                with (
                    patch(
                        "inference.app.infer",
                        side_effect=InferenceError(kind, "upstream failed"),
                    ),
                    patch("inference.app.save_run") as save_mock,
                ):
                    response = self.client.post(
                        "/api/infer", json={"prompt": "Hi"}
                    )

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.get_json()["kind"], kind)
                save_mock.assert_not_called()

    def test_storage_failure_returns_500_without_a_success_record(self):
        record = {"run_id": "run-002", "response": "Hello", "status": "success"}
        with (
            patch("inference.app.infer", return_value=record),
            patch("inference.app.save_run", side_effect=OSError("disk full")),
        ):
            response = self.client.post("/api/infer", json={"prompt": "Hi"})

        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())
        self.assertNotIn("status", response.get_json())

    def test_root_returns_html(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/html")
        self.assertIn("<!doctype html>", response.get_data(as_text=True).lower())


if __name__ == "__main__":
    unittest.main()
