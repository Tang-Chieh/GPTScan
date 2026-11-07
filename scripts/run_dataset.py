#!/usr/bin/env python3
"""Run an existing repo through GPTScan; never clone, patch or flatten its source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def repo_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise argparse.ArgumentTypeError("repo-id must be a plain directory name")
    return value


def source_inventory(root):
    ignored = {".git", "node_modules", ".venv", "artifacts", "cache", "out"}
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name not in ignored
                         and not (Path(directory) / name).is_symlink())
        for filename in sorted(files):
            path = Path(directory) / filename
            if path.suffix == ".sol":
                path.resolve().relative_to(root)  # no external symlinks
                result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def git_value(root, *args):
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def save(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def execute(command, work, env, log, timeout):
    with log.open("w") as stream:
        proc = subprocess.Popen(command, cwd=work, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return proc.wait(timeout=timeout), False
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            return proc.returncode, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", required=True, type=repo_id)
    parser.add_argument("--repos-root", type=Path)
    parser.add_argument("--repo-path", type=Path)
    parser.add_argument("--project-subdir", default=".", help="Framework project root inside the repo")
    parser.add_argument("--build-json", type=Path, help="Reuse dataset build.json working_directory (never executes setup commands)")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=("price", "general"), default="price")
    parser.add_argument("--model", default="openai-codex/gpt-5.6-luna")
    parser.add_argument("--gateway-url", default="http://127.0.0.1:4000/v1")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--solc-version", help="Installed solc-select version (does not auto-install)")
    parser.add_argument("--timeout-minutes", type=float, default=30)
    parser.add_argument("--prepare-only", action="store_true", help="Inventory and commands only; no model call")
    args = parser.parse_args()
    if (args.repo_path is None) == (args.repos_root is None):
        parser.error("Supply exactly one of --repo-path and --repos-root")
    if args.timeout_minutes <= 0:
        parser.error("timeout-minutes must be positive")
    source = (args.repo_path or args.repos_root / args.repo_id).resolve()
    build = json.loads(args.build_json.read_text()) if args.build_json else None
    subdir = (build.get("source", {}).get("working_directory", args.project_subdir)
              if build is not None else args.project_subdir)
    project = (source / subdir).resolve()
    project.relative_to(source)
    if not source.is_dir() or not project.is_dir():
        parser.error("Repository or project subdirectory not found")
    out = args.output_dir.resolve()
    # Generated files must not affect source discovery or the input fingerprint.
    if out == source or source in out.parents:
        parser.error("Output directory must be outside the input repository")
    sys.path.insert(0, str(ROOT / "src"))
    from model_transport import gateway_url
    gateway_url(args.gateway_url)
    if not args.prepare_only and (not args.token_file or not args.token_file.is_file()):
        parser.error("A local gateway --token-file is required")
    inventory = source_inventory(source)
    if not inventory:
        parser.error("Repository has no Solidity sources")
    out.mkdir(parents=True, exist_ok=False)  # never overwrite an old experiment
    work = out / "work"
    work.mkdir()
    # Upstream uses fixed relative resource and temporary paths. Each run gets its
    # own cwd, so callgraph.json/dataflow.json never clobber another repo's run.
    for name in ("rules", "jars", "whitelist.json", "modifier_whitelist.json"):
        (work / name).symlink_to(ROOT / "src" / name)
    command = [sys.executable, str(ROOT / "src/main.py"), "-s", str(project),
               "-o", str(out / "prediction_case.json"), "--strict", "--repo-id", args.repo_id,
               "--repo-root", str(source),
               "--provider", "codex-gateway", "--profile", args.profile, "--model", args.model,
               "--gateway-url", args.gateway_url]
    if args.token_file:
        command += ["--gateway-token-file", str(args.token_file.resolve())]
    manifest = {"status": "prepared", "repo_id": args.repo_id,
                "repo_commit": git_value(source, "rev-parse", "HEAD"),
                "repo_dirty": bool(git_value(source, "status", "--porcelain")),
                "detector_commit": git_value(ROOT, "rev-parse", "HEAD"),
                "detector_dirty": bool(git_value(ROOT, "status", "--porcelain")),
                "source_root": str(source), "project_root": str(project),
                "solc_version": args.solc_version,
                "build_json_sha256": hashlib.sha256(args.build_json.read_bytes()).hexdigest() if args.build_json else None,
                "model": args.model, "profile": args.profile,
                "timeout_minutes": args.timeout_minutes, "source_files_sha256": inventory,
                "command": command, "credential_values_saved": False}
    save(out / "run_manifest.json", manifest)
    if args.prepare_only:
        print(f"Prepared {args.repo_id}: {len(inventory)} Solidity files; no inference")
        return 0
    env = dict(os.environ)
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "GPTSCAN_GATEWAY_TOKEN_FILE"):
        env.pop(name, None)
    env["GPTSCAN_EVENTS"] = str(out / "model_events.jsonl")
    env["PYTHONUNBUFFERED"] = "1"
    if sys.prefix != sys.base_prefix:
        env["VIRTUAL_ENV"] = sys.prefix
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    if args.solc_version:
        env["SOLC_VERSION"] = args.solc_version
    manifest["status"] = "running"
    save(out / "run_manifest.json", manifest)
    start = time.monotonic()
    try:
        code, timed_out = execute(command, work, env, out / "execution.log", args.timeout_minutes * 60)
    except OSError:
        manifest.update(status="failed", error="could_not_start_scanner")
        save(out / "run_manifest.json", manifest)
        raise
    events_path = out / "model_events.jsonl"
    events = [json.loads(line) for line in events_path.read_text().splitlines()] if events_path.exists() else []
    failed = any(event["status"] == "failed" for event in events)
    success = code == 0 and not timed_out and (out / "prediction_case.json").is_file()
    if not success and (out / "prediction_case.json").exists():
        (out / "prediction_case.json").rename(out / "partial_prediction_case.json")
    partial = failed or any(e.get('error') == 'analysis_error' for e in events)
    manifest.update(status=("completed_with_errors" if partial else "completed") if success else "timed_out" if timed_out else "failed",
                    processing_completed=success, analysis_complete=success and not partial,
                    returncode=code, elapsed_seconds=round(time.monotonic() - start, 3),
                    model_requests_completed=sum(e["status"] == "completed" for e in events),
                    model_requests_failed=sum(e["status"] == "failed" for e in events))
    save(out / "run_manifest.json", manifest)
    print(json.dumps({key: manifest[key] for key in ("repo_id", "status", "elapsed_seconds")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
