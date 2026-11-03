#!/usr/bin/env python3
"""Build via the existing Docker runner, verify archive, load Falcon without rebuild."""
import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from reusable_archive import materialize_archive, reusable_runner, safe_relative, sha256, verify_archive
from run_dataset import execute, git_value, repo_id, save
from docker_runtime import image_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reusable-root", type=Path, required=True, help="Trusted Reusable Dataset checkout")
    parser.add_argument("--repo-id", type=repo_id, required=True)
    parser.add_argument("--repo-path", type=Path)
    parser.add_argument("--build-json", type=Path)
    parser.add_argument("--archive", type=Path, help="Reuse an existing archive with its verified sidecar")
    parser.add_argument("--image", default="pmdetector-reusable:per-repo-final")
    parser.add_argument("--build-cache", type=Path, default=ROOT / ".local/reusable-builds")
    parser.add_argument("--docker-cache-volume", default="pmdetector-reusable-cache")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--build-timeout-minutes", type=float, default=30)
    parser.add_argument("--run-analysis", action="store_true", help="Otherwise check archive/Falcon/CallGraph without model requests")
    parser.add_argument("--timeout-minutes", type=float, default=30, help="Separate GPTScan analysis time budget")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--gateway-url", default="http://127.0.0.1:4000/v1")
    parser.add_argument("--model", default="openai-codex/gpt-5.6-luna")
    args = parser.parse_args()
    if min(args.build_timeout_minutes, args.timeout_minutes) <= 0:
        parser.error("Timeouts must be positive")
    if args.run_analysis and (not args.token_file or not args.token_file.is_file()):
        parser.error("--run-analysis requires --token-file")
    reusable = args.reusable_root.resolve()
    build_path = (args.build_json or reusable / "dataset/repos" / args.repo_id / "build.json").resolve()
    build = json.loads(build_path.read_text())
    if build.get("repo_id") != args.repo_id:
        parser.error("build.json repo_id differs from requested repository")
    source_relative = safe_relative(build["source"]["repo_path"])
    source = (args.repo_path or reusable.joinpath(*source_relative.parts)).resolve()
    if not source.is_dir() or git_value(source, "rev-parse", "HEAD") != build["source"]["ref"]:
        parser.error("Source repository missing or HEAD differs from build.json")
    out = args.output_dir.resolve()
    if out == source or source in out.parents:
        parser.error("Output must be outside original source")
    out.mkdir(parents=True, exist_ok=False)
    save(out / "build.json", build)
    manifest = {"repo_id": args.repo_id, "status": "running", "stage": "build",
                "detector_commit": git_value(ROOT, "rev-parse", "HEAD"),
                "detector_dirty": bool(git_value(ROOT, "status", "--porcelain")),
                "reusable_commit": git_value(reusable, "rev-parse", "HEAD"),
                "runner_sha256": sha256(reusable / "scripts/docker_repo_runner.py"),
                "scope_policy_sha256": sha256(reusable / "src/build_scope.py"),
                "build_json_sha256": sha256(build_path), "model": args.model,
                "run_analysis": args.run_analysis, "original_source": str(source),
                "source_commit": build["source"]["ref"], "build_timeout_minutes": args.build_timeout_minutes,
                "analysis_timeout_minutes": args.timeout_minutes, "credential_values_saved": False}
    save(out / "adapter_manifest.json", manifest)
    try:
        runner = reusable_runner(reusable)
        archive_relative = safe_relative(build["analysis_input"]["path"])
        if args.archive:
            archive = args.archive.resolve()
            manifest["build_reused"] = True
        else:
            cached = args.build_cache.resolve() / args.repo_id
            cached.mkdir(parents=True, exist_ok=True)
            with (cached / ".adapter.lock").open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                save(cached / "build.json", build)
                container = "gptscan-build-" + uuid.uuid4().hex[:12]
                selected_image = image_id(args.image)
                command = ["docker", "run", "--rm", "--name", container, "--platform", "linux/amd64",
                           "--mount", f"type=bind,source={reusable},target=/reusable,readonly",
                           "--mount", f"type=bind,source={ROOT / 'scripts/reusable_build_bridge.py'},target=/bridge.py,readonly",
                           "--mount", f"type=bind,source={source},target=/workspace/{source_relative},readonly",
                           "--mount", f"type=bind,source={cached},target=/workspace/dataset/repos/{args.repo_id}",
                           "--mount", f"type=volume,source={args.docker_cache_volume},target=/cache",
                           "--env", "PYTHONPATH=/reusable:/opt/pmdetector", "--entrypoint", "python", selected_image,
                           "/bridge.py", "/reusable/scripts/docker_repo_runner.py", "--workspace-root", "/workspace",
                           "--build-json", f"/workspace/dataset/repos/{args.repo_id}/build.json"]
                manifest["build_command"] = command
                manifest["image_reference"] = args.image
                manifest["image_id"] = selected_image
                manifest["build_bridge_sha256"] = sha256(ROOT / "scripts/reusable_build_bridge.py")
                save(out / "adapter_manifest.json", manifest)
                code, timed_out = execute(command, ROOT, os.environ.copy(), out / "build.log",
                                          args.build_timeout_minutes * 60)
                if timed_out:
                    subprocess.run(["docker", "rm", "-f", container], capture_output=True)
                    raise TimeoutError("Reusable Docker build exceeded its time budget")
                result = json.loads((cached / "build_result.json").read_text()) if (cached / "build_result.json").exists() else {}
                save(out / "build_result.json", result)
                if code != 0 or result.get("status") != "success":
                    raise RuntimeError(f"Reusable build failed: {result.get('failure', {})}; see build.log")
            archive = cached.joinpath(*archive_relative.parts)
            manifest["build_reused"] = result.get("cache_decisions", {}).get("archive", {}).get("status") == "hit"
        sidecar = verify_archive(runner, build, archive)
        manifest.update(stage="archive", archive=str(archive), archive_sha256=sha256(archive),
                        archive_manifest_sha256=sha256(runner.archive_manifest_path(archive)))
        normalized, scope = materialize_archive(json.loads(archive.read_text()), sidecar, build, out / "source")
        # Original production files must match the archived bytes, including on cache hits.
        for name, digest in scope["source_files_sha256"].items():
            relative = Path(name).relative_to(out / "source")
            original = source / relative
            if original.is_file() and sha256(original) != digest:
                raise ValueError(f"Original source differs from archive: {relative}")
        save(out / "input_export_archive.json", normalized)
        save(out / "scope.json", scope)
        scope["archive_sha256"] = sha256(out / "input_export_archive.json")
        save(out / "scope.json", scope)
        manifest.update(stage="falcon", compiled_sources=len(scope["compiled_sources"]),
                        target_files=len(scope["target_files"]),
                        normalized_archive_sha256=scope["archive_sha256"])
        save(out / "adapter_manifest.json", manifest)
        work = out / "work"
        work.mkdir()
        for name in ("rules", "jars", "whitelist.json", "modifier_whitelist.json"):
            (work / name).symlink_to(ROOT / "src" / name)
        env = os.environ.copy()
        for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL"):
            env.pop(key, None)
        env["GPTSCAN_SCOPE_FILE"] = str(out / "scope.json")
        env["VIRTUAL_ENV"] = sys.prefix
        env["GPTSCAN_EVENTS"] = str(out / "model_events.jsonl")
        command = [sys.executable, str(ROOT / "scripts/check_archive.py"),
                   "--archive", str(out / "input_export_archive.json"), "--scope", str(out / "scope.json"),
                   "--output", str(out / "archive_check.json")]
        code, timed_out = execute(command, work, env, out / "archive_check.log", 300)
        if code or timed_out:
            raise RuntimeError("Falcon/CallGraph preflight failed; see archive_check.log")
        manifest.update(stage="ready", archive_check=json.loads((out / "archive_check.json").read_text()))
        if not args.run_analysis:
            manifest["status"] = "ready_for_analysis"
            save(out / "adapter_manifest.json", manifest)
            print(f"READY {args.repo_id}: archive -> Falcon -> CallGraph; no model calls")
            return 0
        manifest.update(stage="analysis")
        save(out / "adapter_manifest.json", manifest)
        command = [sys.executable, str(ROOT / "src/main.py"), "-s", scope["project_root"],
                   "-o", str(out / "output.json"), "--strict", "--repo-id", args.repo_id,
                   "--repo-root", str(out / "source"), "--prediction-output", str(out / "prediction_case.json"),
                   "--archive", str(out / "input_export_archive.json"), "--scope-file", str(out / "scope.json"),
                   "--profile", "price", "--model", args.model, "--gateway-url", args.gateway_url,
                   "--gateway-token-file", str(args.token_file.resolve())]
        manifest["analysis_command"] = command
        save(out / "adapter_manifest.json", manifest)
        code, timed_out = execute(command, work, env, out / "execution.log", args.timeout_minutes * 60)
        events = [json.loads(line) for line in (out / "model_events.jsonl").read_text().splitlines()] if (out / "model_events.jsonl").exists() else []
        manifest.update(completed_model_requests=sum(e["status"] == "completed" for e in events),
                        analysis_error_events=sum(e.get("error") == "analysis_error" for e in events))
        if code or timed_out or any(e["status"] == "failed" for e in events):
            if (out / "prediction_case.json").exists():
                (out / "prediction_case.json").rename(out / "partial_prediction_case.json")
            manifest["status"] = "timed_out" if timed_out else "failed"
            raise RuntimeError("GPTScan analysis incomplete; see execution.log")
        prediction = json.loads((out / "prediction_case.json").read_text())
        manifest.update(status="completed", stage="complete", prediction_count=len(prediction["predictions"]))
        save(out / "adapter_manifest.json", manifest)
        print(f"COMPLETED {args.repo_id}: {manifest['prediction_count']} predictions")
        return 0
    except Exception as error:
        if manifest["status"] != "timed_out":
            manifest["status"] = "failed"
        manifest["failure"] = {"stage": manifest["stage"], "type": type(error).__name__, "message": str(error)}
        save(out / "adapter_manifest.json", manifest)
        print(f"FAILED {args.repo_id} at {manifest['stage']}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
