"""Real compile once, then verified compiler-free Falcon/IR and scoped parser.

No Docker or model credentials required. Real reusable Docker tests are recorded
separately; this fixture makes archive portability and type-code regressions CI-testable.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["VIRTUAL_ENV"] = sys.prefix
os.environ["SOLC_VERSION"] = "0.8.19"
os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")
from crytic_compile import CryticCompile
from crytic_compile.platform.archive import generate_archive_export
from reusable_archive import load_falcon, materialize_archive, sha256


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        original = root / "original"
        original.mkdir()
        shutil.copyfile(ROOT / "tests/fixtures/price-repo/Oracle.sol", original / "Oracle.sol")
        (original / "CodeFactory.sol").write_text('''pragma solidity ^0.8.19;
import "./Oracle.sol";
contract CodeFactory {
    function creation() public pure returns (bytes memory) { return type(Oracle).creationCode; }
    function runtime() public pure returns (bytes memory) { return type(Oracle).runtimeCode; }
    function name() public pure returns (string memory) { return type(Oracle).name; }
}
''')
        compiled = CryticCompile(str(original / "CodeFactory.sol"))
        archive, _ = generate_archive_export(compiled)
        manifest = {"archive_source_root": str(original), "analysis_scope": {"policy_version": "production-v1"}}
        rebased, scope = materialize_archive(archive, manifest, {"source": {"working_directory": "."}}, root / "snapshot")
        archive_path = root / "input_export_archive.json"
        archive_path.write_text(json.dumps(rebased))
        scope["archive_sha256"] = sha256(archive_path)
        scope_path = root / "scope.json"
        scope_path.write_text(json.dumps(scope))
        # Any attempt to compile or spawn another tool during Falcon loading fails.
        with patch("subprocess.Popen", side_effect=AssertionError("Archive loader must not compile")):
            instance = load_falcon(archive_path)
        factory = next(c for c in instance.contracts if c.name == "CodeFactory")
        oracle = next(c for c in instance.contracts if c.name == "Oracle")
        unit = next(u for name, u in instance.crytic_compile.compilation_units.items()).source_units[oracle.source_mapping.filename]
        for name, expected in (("creation", unit.bytecode_init("Oracle")),
                               ("runtime", unit.bytecode_runtime("Oracle"))):
            fn = next(f for f in factory.functions if f.name == name)
            values = [str(getattr(getattr(ir, "rvalue", None), "value", "")) for n in fn.nodes for ir in n.irs]
            assert expected and expected in values, (name, values)
        # A nested test file physically present must not leak into parser targets.
        leak = root / "snapshot/src/test/deep/Leak.sol"
        leak.parent.mkdir(parents=True)
        leak.write_text("pragma solidity ^0.8.19; contract Leak {}")
        work = root / "work"
        work.mkdir()
        for name in ("whitelist.json", "modifier_whitelist.json", "jars"):
            (work / name).symlink_to(ROOT / "src" / name)
        env = {**os.environ, "GPTSCAN_SCOPE_FILE": str(scope_path)}
        result = subprocess.run([sys.executable, str(ROOT / "scripts/check_archive.py"),
                                 "--archive", str(archive_path), "--scope", str(scope_path),
                                 "--output", str(root / "check.json")], cwd=work, env=env,
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        check = json.loads((root / "check.json").read_text())
        assert check["ir_errors"] == 0 and check["parser_files"] == len(scope["target_files"])
        print("Archive runtime passed: no recompile; exact creation/runtime bytecode; nested tests excluded")


if __name__ == "__main__":
    main()
