"""Deterministic PredictionCase export; never consults benchmark ground truth."""
import hashlib
import json
import os
import tempfile
from pathlib import Path


def write_json_atomic(path, value):
    """Publish a complete JSON document, never a partially written Judge input."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_prediction_output(raw, output, repo_id, repo_root, model, detector_version, alias=None):
    """Build canonical output in memory; no native JSON intermediary is required."""
    prediction = export_prediction_case(raw, repo_id, repo_root, model, detector_version)
    write_json_atomic(output, prediction)
    if alias and Path(alias).resolve() != Path(output).resolve():
        write_json_atomic(alias, prediction)
    return prediction


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing non-empty {name}")
    return value


def export_prediction_case(raw, repo_id, repo_root, model, detector_version):
    root = Path(repo_root).resolve()
    findings = []
    scope_file = os.environ.get('GPTSCAN_SCOPE_FILE')
    logical_paths = json.loads(Path(scope_file).read_text()).get('original_relative_paths', {}) if scope_file else {}
    for result in raw["results"]:
        locations = []
        for item in result["affectedFiles"]:
            relative = Path(item["filePath"]).resolve().relative_to(root).as_posix()
            relative = logical_paths.get(str(Path(item['filePath']).resolve()), relative)
            start, end = item["range"]["start"]["line"], item["range"]["end"]["line"]
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                raise ValueError("Invalid inclusive line range")
            locations.append({"file": relative,
                              "contract": nonempty(item.get("contract"), "contract"),
                              "function": nonempty(item.get("function"), "function"),
                              "start_line": start, "end_line": end})
        if not locations:
            raise ValueError("Finding has no source location")
        identity = json.dumps([repo_id, result["code"], locations], sort_keys=True)
        findings.append({
            "finding_id": "GPTSCAN-" + hashlib.sha256(identity.encode()).hexdigest()[:16],
            "title": nonempty(result.get("title"), "title"),
            "description": nonempty(result.get("description"), "description"),
            "impact": nonempty(result.get("impact"), "impact"),
            "mitigation": nonempty(result.get("recommendation"), "recommendation"),
            "vulnerable_code": locations, "severity": result["severity"],
            "report_basis": "rule-template; not an LLM-generated exploit proof",
            "rule_id": result["code"],
        })
    return {"repo_id": nonempty(repo_id, "repo_id"),
            "detector_metadata": {"detector_version": nonempty(detector_version, "detector_version"),
                                  "llm_model": nonempty(model, "model")},
            "predictions": findings}
