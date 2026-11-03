"""Preflight requires complete Falcon IR and scoped CallGraph; no LLM calls."""
import argparse
import json
import logging
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reusable_archive import load_falcon, sha256, validate_scope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scope = json.loads(args.scope.read_text())
    if sha256(args.archive) != scope["archive_sha256"]:
        raise ValueError("Normalized archive hash differs from scope manifest")
    validate_scope(scope, scope["project_root"])
    errors = []
    class ErrorTracker(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.ERROR:
                errors.append(record.getMessage())
    logging.getLogger().addHandler(ErrorTracker())
    instance = load_falcon(args.archive)
    if errors:
        raise RuntimeError("Falcon logged IR/parsing errors: " + "; ".join(errors))
    from antlr4helper.callgraph import CallGraph
    os.environ["GPTSCAN_SCOPE_FILE"] = str(args.scope.resolve())
    graph = CallGraph(scope["project_root"])
    for filename, data in graph.files.items():
        for contract in data["subcontracts"]:
            matches = [item for item in instance.contracts if item.name == contract["name"]
                       and Path(item.source_mapping.filename.absolute).resolve() == Path(filename).resolve()]
            if len(matches) != 1:
                raise ValueError(f"Parser target is not uniquely compiled: {filename}:{contract['name']}")
    result = {"status": "passed", "compiler_invoked": False, "model_requests": 0,
              "falcon_contracts": len(instance.contracts), "ir_errors": len(errors),
              "parser_files": len(graph.files),
              "parser_functions": sum(len(c["functions"]) for d in graph.files.values() for c in d["subcontracts"]),
              "archive_sha256": sha256(args.archive)}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
