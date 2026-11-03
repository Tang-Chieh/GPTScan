import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reusable_archive import materialize_archive, safe_relative, validate_scope


def fixture():
    filename = {"absolute": "/work/repo/project/contracts/A.sol", "relative": "contracts/A.sol",
                "used": "contracts/A.sol", "short": "contracts/A.sol"}
    text = 'contract A { string constant X = "/work/repo/project/contracts/A.sol"; }'
    archive = {"crytic_version": "0.0.2", "working_dir": "/work/repo/project", "type": 1,
               "source_content": {filename["absolute"]: text},
               "compilation_units": {"u": {"compiler": {}, "filenames": [filename],
                  "source_units": {"contracts/A.sol": {"ast": {"nodeType": "SourceUnit",
                     "absolutePath": filename["absolute"], "nodes": [{"nodeType": "Literal", "value": filename["absolute"]}]},
                     "contracts": {"A": {"filenames": copy.deepcopy(filename), "is_dependency": False,
                                          "bin": "abcd", "srcmap": "1:2:3"}}}}}}}
    manifest = {"archive_source_root": "/work/repo/project", "analysis_scope": {"policy_version": "production-v1"}}
    return archive, manifest, {"source": {"working_directory": "project"}}


class ArchiveTests(unittest.TestCase):
    def test_rebase_preserves_code_literal_bytecode_and_srcmap(self):
        archive, manifest, build = fixture()
        before = copy.deepcopy(archive)
        with tempfile.TemporaryDirectory() as folder:
            rebased, scope = materialize_archive(archive, manifest, build, Path(folder) / "snapshot")
            root = scope["project_root"]
            self.assertEqual(len(validate_scope(scope, root)), 1)
            source = rebased["compilation_units"]["u"]["source_units"]["contracts/A.sol"]
            self.assertEqual(source["ast"]["nodes"][0]["value"], "/work/repo/project/contracts/A.sol")
            self.assertEqual(source["contracts"]["A"]["bin"], "abcd")
            self.assertEqual(source["contracts"]["A"]["srcmap"], "1:2:3")
            self.assertEqual(archive, before)
            self.assertEqual(Path(scope["target_files"][0]).read_text(), next(iter(archive["source_content"].values())))
            Path(scope["target_files"][0]).write_text("changed")
            with self.assertRaises(ValueError):
                validate_scope(scope, root)

    def test_escaping_missing_ast_and_missing_source_rejected(self):
        for mode in ("traversal", "outside", "ast", "source"):
            archive, manifest, build = fixture()
            if mode == "traversal":
                archive["source_content"]["/work/repo/project/../../escape.sol"] = "bad"
            elif mode == "outside":
                archive["source_content"]["/etc/escape.sol"] = "bad"
            elif mode == "ast":
                archive["compilation_units"]["u"]["source_units"]["contracts/A.sol"]["ast"] = {}
            else:
                archive["source_content"] = {"/work/repo/project/other.sol": "contract B{}"}
            with tempfile.TemporaryDirectory() as folder:
                destination = Path(folder) / "snapshot"
                with self.assertRaises(ValueError):
                    materialize_archive(archive, manifest, build, destination)
                self.assertFalse(destination.exists())

    def test_target_must_have_been_compiled(self):
        with tempfile.TemporaryDirectory() as folder:
            archive, manifest, build = fixture()
            _, scope = materialize_archive(archive, manifest, build, Path(folder) / "snapshot")
            scope["compiled_sources"] = []
            with self.assertRaises(ValueError):
                validate_scope(scope, scope["project_root"])


if __name__ == "__main__":
    unittest.main()
