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
        (original / 'Errors.sol').write_text('pragma solidity ^0.8.19; error Bad(uint256 value);')
        (original / "CodeFactory.sol").write_text('''pragma solidity ^0.8.19;
import "./Oracle.sol";
import "./Errors.sol" as Errors;
type Amount is uint256;
using AmountLib for Amount global;
using {plus as +} for Amount global;
function plus(Amount a, Amount b) pure returns(Amount) { return Amount.wrap(Amount.unwrap(a) + Amount.unwrap(b)); }
library AmountLib { function unwrap(Amount value) internal pure returns(uint256) { return Amount.unwrap(value); } }
library Events { event Seen(uint256 value); }
contract CodeFactory {
    function creation() public pure returns (bytes memory) { return type(Oracle).creationCode; }
    function runtime() public pure returns (bytes memory) { return type(Oracle).runtimeCode; }
    function name() public pure returns (string memory) { return type(Oracle).name; }
    function aliasValue(Amount value) public pure returns(uint256) { return value.unwrap(); }
    function operatorValue(Amount a, Amount b) public pure returns(Amount) { return a+b; }
    function asmLookup(uint256 x) public pure returns(uint256 y) { assembly { function hash(v) -> r { r:=add(v,1) } function inner(v) -> r { r:=hash(v) } y:=inner(x) } }
    function trigger(uint256 value) public { if(value == 0) revert Errors.Bad(value); emit Events.Seen(value); }
    function tupleSlot(uint256 x) public pure returns(uint256) { (uint256 a, ) = x > 0 ? (x, 1) : (2, 3); return a; }
    function choose(uint256 x) public pure returns(uint256) { uint256 a=x; a+=1; a+=2; return a; }
    function choose(address x) public pure returns(uint256) { uint256 a=uint160(x); a+=3; a+=4; return a; }
    function route(uint256 x) public pure returns(uint256) { x=choose(x); x+=1; x+=2; return x; }
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
        from falcon.solc_parsing.yul.evm_functions import format_function_descriptor
        from falcon.core.declarations.solidity_variables import SolidityFunction
        assert len(SolidityFunction(format_function_descriptor('tload')).return_type) == 1
        assert SolidityFunction(format_function_descriptor('tstore')).return_type == []
        assert SolidityFunction(format_function_descriptor('mcopy')).return_type == []
        import importlib
        yul = importlib.import_module('falcon.solc_parsing.yul.parse_yul')
        assert yul.parsers['YulVariableDeclaration'](None, None, {}) is None
        assert yul.parsers['YulLiteral'](None, None, {'kind': 'string', 'hexValue': 'ff00'}).value.encode('latin1') == b'\xff\x00'
        oracle = next(c for c in instance.contracts if c.name == "Oracle")
        from falcon.ir.operations.event_call import EventCall
        from falcon.ir.operations.solidity_call import SolidityCall
        trigger = next(f for f in factory.functions if f.name == 'trigger')
        assert any(isinstance(ir, EventCall) for n in trigger.nodes for ir in n.irs)
        assert any(isinstance(ir, SolidityCall) and 'revert' in str(ir.function).lower() for n in trigger.nodes for ir in n.irs)
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
        probe = '''import sys
sys.path.insert(0, sys.argv[1])
from reusable_archive import load_falcon
load_falcon(sys.argv[2])
from antlr4helper.callgraph import CallGraph
graph = CallGraph(sys.argv[3])
file = next(f for f in graph.files if f.endswith('CodeFactory.sol'))
assert graph.get_function_detail(file, 'CodeFactory', 'choose(uint256)')
assert graph.get_function_detail(file, 'CodeFactory', 'choose(address)')
assert graph.get_callees(file, 'CodeFactory', 'route(uint256)') == [(file, 'CodeFactory', 'choose(uint256)')]
assert graph.get_callers('choose(address)', file, 'CodeFactory') == []
assert graph.get_callers('choose(uint256)', file, 'CodeFactory') == [(file, 'CodeFactory', 'route(uint256)')]
from types import SimpleNamespace
from static_check import run_static_check
import analysis_context
factory = next(c for c in analysis_context.falcon.contracts if c.name == 'CodeFactory')
assert run_static_check('find_data_dependency', ['x', 'a'], 'choose(uint256)',
                        SimpleNamespace(contracts=[factory, factory]), '', 'CodeFactory', file)
'''
        result = subprocess.run([sys.executable, '-c', probe, str(ROOT / 'src'), str(archive_path), scope['project_root']],
                                cwd=work, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        print("Archive runtime passed: no recompile; exact creation/runtime bytecode; nested tests excluded")


if __name__ == "__main__":
    main()
