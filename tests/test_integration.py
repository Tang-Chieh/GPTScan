import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from model_transport import gateway_url, read_response, send
from prediction_export import export_prediction_case, write_prediction_output
from profiles import rule_paths
from answer_validation import is_yes, parse_choices

spec = importlib.util.spec_from_file_location("dataset_runner", ROOT / "scripts/run_dataset.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def raw(root):
    return {"results": [{"code": "oracle-price-manipulation", "severity": "HIGH",
                         "title": "Manipulable valuation", "description": "Price input affects valuation",
                         "impact": "Potential excessive borrowing", "recommendation": "Validate oracle input",
                         "affectedFiles": [{"filePath": str(root / "src/Pool.sol"),
                                            "contract": "Pool", "function": "borrow",
                                            "range": {"start": {"line": 3}, "end": {"line": 7}}}]}]}


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def test_prediction_contract_and_stable_ids(self):
        from pydantic import BaseModel, Field, StrictStr, StrictInt
        from typing import Annotated, Optional
        class Location(BaseModel):
            file: Annotated[StrictStr, Field(min_length=1)]
            contract: Annotated[StrictStr, Field(min_length=1)]
            function: Annotated[StrictStr, Field(min_length=1)]
            start_line: Optional[Annotated[StrictInt, Field(ge=1)]] = None
            end_line: Optional[Annotated[StrictInt, Field(ge=1)]] = None
        class Finding(BaseModel):
            finding_id: Annotated[StrictStr, Field(min_length=1)]
            title: Annotated[StrictStr, Field(min_length=1)]
            description: Annotated[StrictStr, Field(min_length=1)]
            impact: Annotated[StrictStr, Field(min_length=1)]
            mitigation: Annotated[StrictStr, Field(min_length=1)]
            vulnerable_code: list[Location]
        value = export_prediction_case(raw(self.root), "test", self.root, "model", "version")
        Finding.model_rebuild(_types_namespace={"Location": Location})
        Finding.model_validate(value["predictions"][0])
        self.assertEqual(value, export_prediction_case(raw(self.root), "test", self.root, "model", "version"))
        self.assertEqual(value["predictions"][0]["vulnerable_code"][0]["file"], "src/Pool.sol")

    def test_empty_case_valid(self):
        self.assertEqual(export_prediction_case({"results": []}, "test", self.root, "m", "v")["predictions"], [])

    def test_primary_output_is_judge_input_without_native_intermediate(self):
        output = self.root / 'output.json'
        value = write_prediction_output(raw(self.root), output, 'test', self.root, 'm', 'v2')
        self.assertEqual(json.loads(output.read_text()), value)
        self.assertEqual(value['repo_id'], 'test')
        self.assertNotIn('results', value)
        self.assertEqual({p.name for p in self.root.iterdir()}, {'output.json'})

    def test_compatibility_alias_contains_identical_prediction_case(self):
        output, alias = self.root / 'output.json', self.root / 'prediction_case.json'
        write_prediction_output({'results': []}, output, 'test', self.root, 'm', 'v2', alias=alias)
        self.assertEqual(output.read_bytes(), alias.read_bytes())
        self.assertEqual(json.loads(output.read_text())['predictions'], [])

    def test_invalid_content_does_not_publish_judge_output(self):
        output, alias = self.root / 'output.json', self.root / 'prediction_case.json'
        value = raw(self.root)
        value['results'][0]['recommendation'] = ''
        with self.assertRaises(ValueError):
            write_prediction_output(value, output, 'test', self.root, 'm', 'v2', alias=alias)
        self.assertFalse(output.exists())
        self.assertFalse(alias.exists())

    def test_missing_semantics_rejected(self):
        for key in ("impact", "recommendation", "title", "description"):
            value = raw(self.root)
            value["results"][0][key] = ""
            with self.assertRaises(ValueError):
                export_prediction_case(value, "test", self.root, "m", "v")

    def test_bad_locations_rejected(self):
        for key, value in (("contract", ""), ("function", ""), ("filePath", "/outside/File.sol")):
            data = raw(self.root)
            data["results"][0]["affectedFiles"][0][key] = value
            with self.assertRaises(ValueError):
                export_prediction_case(data, "test", self.root, "m", "v")
        data = raw(self.root)
        data["results"][0]["affectedFiles"][0]["range"]["end"]["line"] = 1
        with self.assertRaises(ValueError):
            export_prediction_case(data, "test", self.root, "m", "v")

    def test_identity_repo_and_rule_specific(self):
        a = export_prediction_case(raw(self.root), "a", self.root, "m", "v")
        b = export_prediction_case(raw(self.root), "b", self.root, "m", "v")
        self.assertNotEqual(a["predictions"][0]["finding_id"], b["predictions"][0]["finding_id"])


class TransportTests(unittest.TestCase):
    def test_answer_validation(self):
        self.assertTrue(is_yes("Yes"))
        self.assertFalse(is_yes("No."))
        self.assertEqual(parse_choices('{"1":"yes","2":"no"}', 2), {"1": "yes", "2": "no"})
        for answer in ('{}', '{"0":"yes"}', '{"1":"maybe"}', '```json\n{"1":"yes"}\n```'):
            with self.assertRaises(ValueError):
                parse_choices(answer, 1)
        with self.assertRaises(ValueError):
            is_yes("Unable to analyze")

    def test_loopback_only(self):
        self.assertEqual(gateway_url("http://127.0.0.1:4000/v1/"), "http://127.0.0.1:4000/v1")
        for url in ("https://example.com/v1", "http://127.0.0.1.evil/v1", "http://x@localhost/v1",
                    "http://localhost/v1?token=x", "http://localhost/wrong"):
            with self.assertRaises(ValueError):
                gateway_url(url)

    def response(self, text, content_type):
        stream = io.BytesIO(text.encode())
        stream.headers = {"Content-Type": content_type}
        return stream

    def completed(self):
        return {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "yes"}]}]}

    def test_json_response(self):
        self.assertEqual(read_response(self.response(json.dumps(self.completed()), "application/json")), "yes")

    def test_stream_requires_completion(self):
        event = {"type": "response.completed", "response": self.completed()}
        self.assertEqual(read_response(self.response("data: " + json.dumps(event) + "\n\n", "text/event-stream")), "yes")
        for event in ({"type": "response.output_text.delta", "delta": "yes"},
                      {"type": "response.failed"}, {"type": "response.incomplete"}):
            with self.assertRaises(ValueError):
                read_response(self.response("data: " + json.dumps(event) + "\n\n", "text/event-stream"))

    def test_no_implicit_api_key_fallback(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unused"}, clear=True):
            with self.assertRaisesRegex(ValueError, "GPTSCAN_GATEWAY_TOKEN_FILE"):
                send([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])

    def test_http_401_not_retried_or_logged_with_secret(self):
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as folder:
            token = Path(folder) / "bearer"
            token.write_text("local-test-bearer")
            error = HTTPError("http://localhost/v1", 401, "unauthorized", {}, None)
            with patch.dict(os.environ, {"GPTSCAN_PROVIDER": "codex-gateway", "GPTSCAN_GATEWAY_TOKEN_FILE": str(token)}, clear=True):
                with patch("model_transport.build_opener") as opener:
                    opener.return_value.open.side_effect = error
                    with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
                        send([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])
                    self.assertEqual(opener.return_value.open.call_count, 1)


class DatasetTests(unittest.TestCase):
    def test_profiles(self):
        import yaml
        price = rule_paths(ROOT / "src/rules", "price")
        self.assertEqual({p.name for p in price}, {
            "Flashloan_Price.yml", "FirstDeposit.yml", "Flashloan_Buy.yml",
            "Flashloan_Vote.yml", "FrontRun.yml", "WrongOrder_Checkpoint.yml",
            "WrongOrder_Interest.yml",
        })
        self.assertFalse((ROOT / "src/rules/OraclePrice.yml").exists())
        for path in price:
            rule = yaml.safe_load(path.read_text())
            self.assertTrue(rule["output"]["impact"])
            self.assertIn("static", rule)
        self.assertEqual(len(rule_paths(ROOT / "src/rules", "general")), 10)

    def test_prepare_does_not_modify_repo_or_need_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "repo" / "protocol"
            source.mkdir(parents=True)
            (source / "Pool.sol").write_text("pragma solidity ^0.8.0; contract Pool {}")
            command = [sys.executable, str(ROOT / "scripts/run_dataset.py"), "--repo-id", "example",
                       "--repo-path", str(source.parent), "--project-subdir", "protocol",
                       "--output-dir", str(root / "result"), "--prepare-only"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((root / "result/run_manifest.json").read_text())
            self.assertEqual(manifest["status"], "prepared")
            self.assertEqual(len(manifest["source_files_sha256"]), 1)
            self.assertFalse((root / "result/prediction_case.json").exists())
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)

    def test_build_json_used_only_for_project_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "repo/protocol"
            source.mkdir(parents=True)
            (source / "Pool.sol").write_text("contract Pool {}")
            build = root / "build.json"
            build.write_text(json.dumps({"source": {"working_directory": "protocol"},
                                         "setup": {"commands": [{"argv": ["DO_NOT_EXECUTE"]}]}}))
            command = [sys.executable, str(ROOT / "scripts/run_dataset.py"), "--repo-id", "example",
                       "--repo-path", str(source.parent), "--build-json", str(build),
                       "--output-dir", str(root / "result"), "--prepare-only"]
            proc = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            manifest = json.loads((root / "result/run_manifest.json").read_text())
            self.assertEqual(manifest["project_root"], str(source.resolve()))
            self.assertNotIn("DO_NOT_EXECUTE", manifest["command"])

    def test_path_traversal_and_source_symlink_rejected(self):
        with self.assertRaises(Exception):
            runner.repo_id("../bad")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "repo").mkdir()
            (root / "outside.sol").write_text("contract C {}")
            (root / "repo/link.sol").symlink_to(root / "outside.sol")
            with self.assertRaises(ValueError):
                runner.source_inventory(root / "repo")


if __name__ == "__main__":
    unittest.main()
