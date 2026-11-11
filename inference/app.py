"""Local Flask API that joins inference and record storage."""

import os
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

from inference.llama_client import InferenceError, infer
from inference.store import save_run


def create_app(
    data_dir: Path | None = None,
    server_url: str | None = None,
) -> Flask:
    """Create the local inference app with injectable paths for tests."""

    inference_dir = Path(__file__).resolve().parent
    resolved_data_dir = (
        Path(data_dir) if data_dir is not None else inference_dir / "runs"
    )
    resolved_server_url = (
        server_url
        if server_url is not None
        else os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080")
    )

    app = Flask(__name__)
    app.config["INFERENCE_DATA_DIR"] = resolved_data_dir
    app.config["LLAMA_SERVER_URL"] = resolved_server_url

    @app.get("/")
    def index() -> Response | str:
        template_path = inference_dir / "templates" / "index.html"
        if template_path.is_file():
            return render_template("index.html")
        return Response(
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<title>Local inference</title></head><body><main>"
            "<h1>Local inference API</h1>"
            "<p>Submit prompts to the local inference endpoint.</p>"
            "</main></body></html>",
            mimetype="text/html",
        )

    @app.post("/api/infer")
    def api_infer() -> tuple[Response, int] | Response:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Request body must be a JSON object."), 400

        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            return jsonify(error="prompt must be a string."), 400
        prompt = prompt.strip()
        if not prompt or len(prompt) > 4000:
            return (
                jsonify(error="prompt must contain 1 to 4000 characters."),
                400,
            )

        try:
            record = infer(prompt, app.config["LLAMA_SERVER_URL"])
        except InferenceError as exc:
            status_code = 503 if exc.kind == "unavailable" else 502
            return jsonify(error=str(exc), kind=exc.kind), status_code

        try:
            save_run(record, app.config["INFERENCE_DATA_DIR"])
        except Exception:
            return jsonify(error="Unable to save the inference record."), 500

        return jsonify(record)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=7860, debug=False)
