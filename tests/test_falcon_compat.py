import sys
from pathlib import Path
from types import SimpleNamespace as S
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from falcon_compat import contract_bytecode, is_bytecode_member


class Filename:
    def __init__(self, absolute):
        self.absolute = absolute


class BytecodeTests(unittest.TestCase):
    def test_unhashable_non_bytecode_member_delegates(self):
        self.assertFalse(is_bytecode_member(S(value="name")))
        self.assertTrue(is_bytecode_member("creationCode"))
        self.assertTrue(is_bytecode_member("runtimeCode"))
    def contract(self, path):
        return S(name="SameName", source_mapping=S(filename=Filename(path)))

    def unit(self, init, runtime):
        return S(contracts_names={"SameName"}, bytecode_init=lambda name: init,
                 bytecode_runtime=lambda name: runtime)

    def test_duplicate_names_resolved_by_file(self):
        cc = S(source_units={Filename("/repo/A.sol"): self.unit("aa", "ab"),
                             Filename("/repo/B.sol"): self.unit("ba", "bb")})
        self.assertEqual(contract_bytecode(cc, self.contract("/repo/B.sol")), "ba")
        self.assertEqual(contract_bytecode(cc, self.contract("/repo/B.sol"), True), "bb")

    def test_missing_or_ambiguous_source_rejected(self):
        for cc in (S(source_units={}), S(source_units={
                Filename("/repo/B.sol"): self.unit("aa", "ab"),
                Filename("/repo/B.sol"): self.unit("ba", "bb")})):
            with self.assertRaises(ValueError):
                contract_bytecode(cc, self.contract("/repo/B.sol"))


if __name__ == "__main__":
    unittest.main()
