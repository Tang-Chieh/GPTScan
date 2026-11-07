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
    bad_json_sent = False

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
            if self.mode == "retry_json" and not Gateway.bad_json_sent:
                Gateway.bad_json_sent = True
                answer = '{"VariableA":{"price":"bad"quote"}}'
            else:
                answer = json.dumps({"VariableA": {"price": "pool spot price"},
                                     "VariableB": {"valuation": "not monetary" if self.mode == "rejected" else "LP token value"}})
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
            for mode in ("positive", "negative", "malformed", "rejected", "retry_json"):
                Gateway.mode = mode
                Gateway.bad_json_sent = False
                out = temporary / mode
                # Exercise the retained upstream LP rule, not the removed OraclePrice rule.
                source = temporary / (mode + "-source")
                source.mkdir()
                (source / "Oracle.sol").write_text((ROOT / "tests/fixtures/price-repo/Oracle.sol").read_text().replace(
                    "function borrow(", "function getLiquidity("))
                command = [sys.executable, str(ROOT / "scripts/run_dataset.py"),
                           "--repo-id", "synthetic-price", "--repo-path", str(source),
                           "--output-dir", str(out), "--token-file", str(token), "--solc-version", "0.8.19",
                           "--gateway-url", f"http://127.0.0.1:{server.server_port}/v1", "--timeout-minutes", "2"]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=150)
                status = json.loads((out / "run_manifest.json").read_text())["status"]
                expected_errors = mode in {'malformed', 'rejected', 'retry_json'}
                assert proc.returncode == 0 and status == ('completed_with_errors' if expected_errors else 'completed'), (out / "execution.log").read_text()
                prediction = json.loads((out / "prediction_case.json").read_text())
                assert not (out / "output.json").exists(), "Native intermediate output must not be required"
                assert "results" not in prediction and prediction["repo_id"] == "synthetic-price"
                assert len(prediction["predictions"]) == (1 if mode == "positive" else 0)
                metadata = json.loads((out / "prediction_case.json.metadata.json").read_text())
                assert metadata["output_format"] == "PredictionCase"
                assert metadata["compile_succeeded"]
                assert (metadata["analysis_errors"] > 0) == expected_errors
                if os.environ.get("GPTSCAN_BENCHMARK_CONTRACT"):
                    subprocess.run([sys.executable, str(ROOT / "scripts/validate_prediction.py"),
                                    "--contract-file", os.environ["GPTSCAN_BENCHMARK_CONTRACT"],
                                    "--prediction", str(out / "prediction_case.json")], check=True)
                if mode == "positive":
                    # Exercise the CLI's -o directly, optional native debugging and legacy alias.
                    env = os.environ.copy()
                    env['SOLC_VERSION'] = '0.8.19'
                    env['VIRTUAL_ENV'] = sys.prefix
                    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env.get('PATH', '')
                    direct = subprocess.run([
                        sys.executable, str(ROOT / 'src/main.py'), '-s', str(source),
                        '-o', str(out / 'direct.json'), '--repo-id', 'synthetic-price',
                        '--repo-root', str(source), '--strict',
                        '--native-output', str(out / 'native-debug.json'),
                        '--prediction-output', str(out / 'alias.json'),
                        '--gateway-token-file', str(token),
                        '--gateway-url', f'http://127.0.0.1:{server.server_port}/v1'],
                        cwd=out / 'work', env=env, capture_output=True, text=True, timeout=150)
                    assert direct.returncode == 0, direct.stdout + direct.stderr
                    primary = json.loads((out / 'direct.json').read_text())
                    assert primary == json.loads((out / 'alias.json').read_text())
                    assert primary['predictions'] and 'results' not in primary
                    assert json.loads((out / 'native-debug.json').read_text())['results']
                if mode == "rejected":
                    assert 'validate_description' in (out / "execution.log").read_text()
                if mode == "retry_json":
                    events = [json.loads(line) for line in (out / "model_events.jsonl").read_text().splitlines()]
                    assert sum(event["status"] == "format_retry" for event in events) == 0
                print(f"Full runtime regression passed: {mode}")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    main()
