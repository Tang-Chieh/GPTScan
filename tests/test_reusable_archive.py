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
    def test_brownie_dependency_is_context_not_report_target(self):
        archive, manifest, build = fixture()
        unit = archive['compilation_units']['u']
        file = {'absolute': '/work/home/.brownie/packages/vendor/pkg/contracts/Dep.sol',
                'relative': '../home/.brownie/packages/vendor/pkg/contracts/Dep.sol',
                'used': '../home/.brownie/packages/vendor/pkg/contracts/Dep.sol', 'short': 'Dep.sol'}
        unit['filenames'].append(file)
        source = copy.deepcopy(unit['source_units']['contracts/A.sol'])
        source['contracts']['A']['filenames'] = copy.deepcopy(file)
        unit['source_units'][file['relative']] = source
        archive['source_content'][file['absolute']] = 'library Dep {}'
        with tempfile.TemporaryDirectory() as folder:
            _, scope = materialize_archive(archive, manifest, build, Path(folder) / 'snapshot')
            self.assertEqual(len(scope['compiled_sources']), 2)
            self.assertEqual(len(scope['target_files']), 1)
    def test_truffle_project_uri_maps_to_exact_compiled_source(self):
        archive, manifest, build = fixture()
        archive['compilation_units']['u']['source_units']['contracts/A.sol']['ast']['absolutePath'] = 'project:/contracts/A.sol'
        with tempfile.TemporaryDirectory() as folder:
            normalized, scope = materialize_archive(archive, manifest, build, Path(folder) / 'snapshot')
            ast = normalized['compilation_units']['u']['source_units']['contracts/A.sol']['ast']
            self.assertEqual(ast['absolutePath'], scope['target_files'][0])
    def test_case_distinct_sources_do_not_overwrite_on_macos(self):
        archive, manifest, build = fixture()
        unit = archive['compilation_units']['u']
        other = copy.deepcopy(unit['filenames'][0])
        other['absolute'] = '/work/repo/project/contracts/a.sol'
        for key in ('relative', 'used', 'short'):
            other[key] = 'contracts/a.sol'
        unit['filenames'].append(other)
        source = copy.deepcopy(unit['source_units']['contracts/A.sol'])
        source['contracts']['A']['filenames'] = copy.deepcopy(other)
        unit['source_units']['contracts/a.sol'] = source
        archive['source_content'][other['absolute']] = 'contract Other {}'
        with tempfile.TemporaryDirectory() as folder:
            _, scope = materialize_archive(archive, manifest, build, Path(folder) / 'snapshot')
            self.assertEqual(len(validate_scope(scope, scope['project_root'])), 2)
            self.assertEqual(set(scope['original_relative_paths'].values()), {'project/contracts/A.sol', 'project/contracts/a.sol'})
            self.assertEqual(len({Path(n).read_text() for n in scope['target_files']}), 2)
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
