"""Verified reusable-dataset archive -> portable source snapshot + Falcon input.

Only archive metadata paths are rebased. Source text, bytecode, AST IDs and src
offsets are preserved; no compiler or package manager is invoked by the loader.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_relative(value):
    path = PurePosixPath(value)
    if not isinstance(value, str) or not value or "\\" in value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe relative path: {value!r}")
    return path


def reusable_runner(root):
    """Load the user's trusted checkout, not a second copy of its build rules."""
    root = Path(root).resolve()
    sys.path.insert(0, str(root))
    name = "gptscan_reusable_build_runner"
    spec = importlib.util.spec_from_file_location(name, root / "scripts/docker_repo_runner.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_archive(runner, build, archive):
    archive = Path(archive).resolve()
    relative = safe_relative(build["analysis_input"]["path"])
    parent = archive
    for _ in relative.parts:
        parent = parent.parent
    if parent.joinpath(*relative.parts) != archive:
        raise ValueError("Archive location does not match build.json analysis_input.path")
    node = runner.selected_node_version(build, None)
    if node is None and (parent / "build_result.json").is_file():
        effective = json.loads((parent / "build_result.json").read_text()).get("toolchain", {}).get("node", "")
        if effective.startswith("v"):
            node = effective[1:]
    result = runner.validate_archive(build, parent, node_version=node, allow_unresolved_entrypoint=True)
    if not result.valid:
        raise ValueError(f"Reusable archive verification failed ({result.reason}): {result.message}")
    sidecar = runner.archive_manifest_path(archive)
    return json.loads(sidecar.read_text())


def materialize_archive(data, manifest, build, repository):
    """Extract an archive-owned snapshot. Reject escaping paths and missing ASTs."""
    if data.get("crytic_version") != "0.0.2" or not data.get("compilation_units"):
        raise ValueError("Expected a single Crytic Compile 0.0.2 archive with compilation units")
    if not isinstance(data.get("source_content"), dict) or not data["source_content"]:
        raise ValueError("Archive has no embedded source content")
    repository = Path(repository).resolve()
    if repository.exists():
        raise ValueError("Archive snapshot destination already exists")
    working = safe_relative(build["source"].get("working_directory", "."))
    old_project = PurePosixPath(manifest["archive_source_root"])
    if not old_project.is_absolute() or ".." in old_project.parts:
        raise ValueError("Archive source root must be an absolute normalized path")
    old_repo = old_project
    for part in reversed(working.parts):
        if old_repo.name != part:
            raise ValueError("Archive source root disagrees with build working_directory")
        old_repo = old_repo.parent
    project = repository.joinpath(*working.parts)
    replacements = {}
    texts = {}
    for name, content in data["source_content"].items():
        if not isinstance(name, str) or not isinstance(content, str):
            raise ValueError("Invalid embedded source")
        original = PurePosixPath(name)
        if not original.is_absolute() or ".." in original.parts:
            raise ValueError(f"Source path is not absolute and normalized: {name}")
        relative = original.relative_to(old_repo)
        safe_relative(str(relative))
        destination = repository.joinpath(*relative.parts)
        replacements[name] = str(destination)
        texts[destination] = content

    rebased = copy.deepcopy(data)
    rebased["working_dir"] = str(project)
    rebased["source_content"] = {replacements[name]: content for name, content in data["source_content"].items()}
    compiled = set()
    dependencies = set()

    def filename(value):
        absolute = value["absolute"]
        if absolute not in replacements:
            raise ValueError(f"Compiled source has no embedded text: {absolute}")
        for key in ("absolute", "relative", "used", "short"):
            if value.get(key) in replacements:
                value[key] = replacements[value[key]]

    def ast_paths(value):
        if isinstance(value, dict):
            if value.get("absolutePath") in replacements:
                value["absolutePath"] = replacements[value["absolutePath"]]
            for item in value.values():
                ast_paths(item)
        elif isinstance(value, list):
            for item in value:
                ast_paths(item)

    for unit in rebased["compilation_units"].values():
        for item in unit["filenames"]:
            filename(item)
        sources = {}
        for key, source in unit["source_units"].items():
            if not source.get("ast"):
                raise ValueError(f"Missing AST: {key}")
            matches = [item["absolute"] for item in unit["filenames"]
                       if key in item.values() or replacements.get(key) in item.values()]
            # A short name can be ambiguous; relative and absolute keys must resolve uniquely.
            if len(set(matches)) != 1:
                raise ValueError(f"Cannot uniquely resolve compiled source: {key}")
            absolute = matches[0]
            compiled.add(absolute)
            for contract in source.get("contracts", {}).values():
                if contract.get("is_dependency"):
                    dependencies.add(absolute)
                filename(contract["filenames"])
            ast_paths(source["ast"])
            sources[replacements.get(key, key)] = source
        unit["source_units"] = sources
    targets = []
    excluded_targets = {}
    dependency_directories = {"node_modules", "lib", "external", "openzeppelin", "uniswap", "pancakeswap", "legacy"}
    for name in sorted(compiled):
        relative = Path(name).relative_to(project)
        if name not in dependencies and not dependency_directories.intersection(part.casefold() for part in relative.parts[:-1]):
            targets.append(name)
        else:
            excluded_targets[name] = "dependency/vendor context retained for Falcon, not a report target"
    if not targets:
        raise ValueError("Archive has no compiled production targets")
    # Verification is performed before any files are written. This directory is new,
    # so no preexisting symlink can redirect extraction outside the snapshot.
    repository.mkdir(parents=True)
    for path, content in texts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
    return rebased, {"schema_version": "1.0.0", "repository_root": str(repository),
                     "project_root": str(project), "target_files": targets,
                     "compiled_sources": sorted(compiled),
                     "dependency_sources": sorted(dependencies),
                     "excluded_analysis_files": excluded_targets,
                     "target_policy": {"version": "gptscan-production-v1",
                                       "dependency_directories": sorted(dependency_directories)},
                     "source_files_sha256": {str(path): hashlib.sha256(text.encode()).hexdigest()
                                              for path, text in texts.items()},
                     "analysis_scope": manifest["analysis_scope"]}


def validate_scope(scope, project):
    root = Path(project).resolve()
    if root != Path(scope["project_root"]).resolve():
        raise ValueError("Scope project root does not match scanner source")
    targets = []
    if not scope.get("target_files"):
        raise ValueError("Scope has no target files")
    for name in scope["target_files"]:
        path = Path(name).resolve()
        path.relative_to(root)
        if str(path) not in scope["compiled_sources"]:
            raise ValueError("Analysis target was not compiled")
        if sha256(path) != scope["source_files_sha256"].get(str(path)):
            raise ValueError("Analysis source differs from compiled archive content")
        targets.append(path)
    return targets


def load_falcon(archive):
    """Explicit Archive platform: cannot fall back to invoking a compiler."""
    from crytic_compile import CryticCompile
    from crytic_compile.platform.archive import Archive
    from falcon import Falcon
    from falcon_compat import install
    install()
    compiled = CryticCompile(Archive(str(Path(archive).resolve())))
    return Falcon(compiled, disallow_partial=True)
