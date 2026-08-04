"""Local CLI integration tests that never contact an external provider."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from orca_vision_helper import cli


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))


def test_keyless_custom_add_check_analyze_full_path(tmp_path, capsys):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            assert self.path == "/v1/models"
            body = json.dumps({"data": [{"id": "vision-model"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # noqa: N802
            assert self.path == "/v1/chat/completions"
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            body = json.dumps({
                "choices": [{
                    "message": {"content": '{"summary":"local ok","issues":[]}'},
                    "finish_reason": "stop",
                }]
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A002
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        rc = cli.main([
            "provider", "add", "--type", "custom", "--id", "local-gateway",
            "--base-url", base_url, "--model", "vision-model", "--set-default",
        ])
        assert rc == 0
        capsys.readouterr()

        rc = cli.main(["provider", "list"])
        listed = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert listed["providers"][0]["key_required"] is False
        assert listed["providers"][0]["has_key"] is False

        rc = cli.main(["check"])
        checked = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert checked["ok"] is True
        assert checked["endpoint"]["model_available"] is True

        from PIL import Image

        image = tmp_path / "shot.png"
        Image.new("RGB", (16, 16), "white").save(image)
        rc = cli.main(["analyze", str(image), "--json"])
        analyzed = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert analyzed["status"] == "ok"
        assert analyzed["report"]["summary"] == "local ok"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
