"""Negative tests using the actual external reusable runner, no Docker/model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reusable_archive import reusable_runner, verify_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reusable-root", type=Path, required=True)
    parser.add_argument("--build-json", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runner = reusable_runner(args.reusable_root)
    build = json.loads(args.build_json.read_text())
    archive_manifest = json.loads(runner.archive_manifest_path(args.archive).read_text())
    results = []
    for mode in ("valid", "sha_mismatch", "source_commit_mismatch", "excluded_source_injection"):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / build["analysis_input"]["path"]
            target.parent.mkdir(parents=True)
            shutil.copyfile(args.archive, target)
            shutil.copyfile(args.archive.parent.parent / "build_result.json", root / "build_result.json")
            manifest = dict(archive_manifest)
            if mode == "sha_mismatch":
                target.write_text(target.read_text() + "\n")
            elif mode == "source_commit_mismatch":
                manifest["source_commit"] = "0" * 40
            elif mode == "excluded_source_injection":
                data = json.loads(target.read_text())
                data["source_content"][manifest["archive_source_root"] + "/test/Leak.sol"] = "contract Leak {}"
                target.write_text(json.dumps(data))
                # Keep the hash valid: the independent scope check must reject it.
                manifest["archive_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            runner.archive_manifest_path(target).write_text(json.dumps(manifest))
            try:
                verify_archive(runner, build, target)
                accepted = True
                reason = "verified"
            except ValueError as error:
                accepted = False
                reason = str(error)
            assert accepted == (mode == "valid"), (mode, reason)
            results.append({"case": mode, "passed": True, "accepted": accepted, "reason": reason})
    args.output.write_text(json.dumps({"status": "passed", "checks": results}, indent=2) + "\n")
    print("Actual reusable provenance checks passed: valid, hash, source commit, excluded-source injection")


if __name__ == "__main__":
    main()
