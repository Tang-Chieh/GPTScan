import importlib.util
from pathlib import Path
from types import SimpleNamespace as S
import unittest

spec = importlib.util.spec_from_file_location("build_bridge", Path(__file__).resolve().parents[1] / "scripts/reusable_build_bridge.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BoundaryTests(unittest.TestCase):
    def test_setup_dependency_additions_allowed(self):
        before = S(scope_fingerprint="same", retained_files=("src/A.sol",))
        after = S(scope_fingerprint="same", retained_files=("src/A.sol", "node_modules/pkg/B.sol", "lib/pkg/C.sol"))
        module.audit_dependency_boundary(before, after)

    def test_project_changes_and_policy_changes_rejected(self):
        before = S(scope_fingerprint="same", retained_files=("src/A.sol",))
        for after in (S(scope_fingerprint="same", retained_files=()),
                      S(scope_fingerprint="same", retained_files=("src/A.sol", "src/New.sol")),
                      S(scope_fingerprint="different", retained_files=("src/A.sol",))):
            with self.assertRaises(ValueError):
                module.audit_dependency_boundary(before, after)
