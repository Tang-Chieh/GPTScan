"""Run the trusted reusable runner with a dependency-only scope audit correction.

The upstream production boundary must not mistake freshly installed dependency
Solidity files for new project sources. No project source boundary or exclusion
policy change is allowed. The external checkout itself is never edited.
"""
import importlib.util
from pathlib import Path
import sys


def audit_dependency_boundary(before, after):
    if before.scope_fingerprint != after.scope_fingerprint:
        raise ValueError("Scope policy changed during setup")
    def project_sources(scope):
        return {name for name in scope.retained_files
                if Path(name).parts[0] not in {"node_modules", "lib"}}
    if project_sources(before) != project_sources(after):
        raise ValueError("Project Solidity source boundary changed during setup")


def main():
    runner_path = Path(sys.argv.pop(1)).resolve()
    sys.path.insert(0, str(runner_path.parents[1]))
    spec = importlib.util.spec_from_file_location("gptscan_docker_reusable_runner", runner_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.audit_scope_boundary = audit_dependency_boundary
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
