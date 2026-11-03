"""Real compiler + Java + pipeline, deterministic fake model. No subscription usage."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]


class Gateway(BaseHTTPRequestHandler):
    mode = "positive"

    def log_message(self, *args):
        pass

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert data["model"] == "openai-codex/gpt-5.6-luna"
        assert "price/oracle manipulation" in data["instructions"]
        prompt = data["input"][-1]["content"]
        if self.mode == "malformed":
            answer = "not a valid answer"
        elif '"1": Does it' in prompt:
            keys = re.findall(r'"(\d+)": Does it', prompt)
            answer = json.dumps({key: "no" if self.mode == "negative" or (self.mode == "rejected" and key != "1")
                                 else "yes" for key in keys})
        elif "VariableA" in prompt:
            answer = json.dumps({"VariableA": {"price": "pool spot price"},
                                 "VariableB": {"valuation": "not monetary" if self.mode == "rejected" else "collateral valuation"}})
        else:
            answer = "yes"
        body = json.dumps({"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": answer}]}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    with tempfile.TemporaryDirectory() as folder:
        temporary = Path(folder)
        token = temporary / "bearer"
        token.write_text("fake-local-test-bearer")
        server = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for mode in ("positive", "negative", "malformed", "rejected"):
                Gateway.mode = mode
                out = temporary / mode
                source = ROOT / "tests/fixtures/price-repo"
                if mode == "rejected":
                    source = temporary / "rule-rejection-source"
                    source.mkdir()
                    (source / "Oracle.sol").write_text((ROOT / "tests/fixtures/price-repo/Oracle.sol").read_text().replace(
                        "function borrow(", "function getLiquidity("))
                command = [sys.executable, str(ROOT / "scripts/run_dataset.py"),
                           "--repo-id", "synthetic-price", "--repo-path", str(source),
                           "--output-dir", str(out), "--token-file", str(token), "--solc-version", "0.8.19",
                           "--gateway-url", f"http://127.0.0.1:{server.server_port}/v1", "--timeout-minutes", "2"]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=150)
                status = json.loads((out / "run_manifest.json").read_text())["status"]
                if mode == "malformed":
                    assert proc.returncode != 0 and status == "failed", proc.stdout + proc.stderr
                    assert not (out / "prediction_case.json").exists()
                else:
                    assert proc.returncode == 0 and status == "completed", (out / "execution.log").read_text()
                    prediction = json.loads((out / "prediction_case.json").read_text())
                    assert len(prediction["predictions"]) == (1 if mode == "positive" else 0)
                    metadata = json.loads((out / "output.json.metadata.json").read_text())
                    assert metadata["compile_succeeded"] and metadata["analysis_errors"] == 0
                    if mode == "rejected":
                        assert "Candidate rejected by rule" in (out / "execution.log").read_text()
                print(f"Full runtime regression passed: {mode}")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    main()
