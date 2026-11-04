import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from archive_scope import production_archive


class ClosureTests(unittest.TestCase):
    def data(self):
        paths = ['src/A.sol', 'lib/D.sol', 'script/Deploy.s.sol', 'src/test/Mock.sol']
        sources = {p: {'ast': {'id': i, 'nodes': []}} for i, p in enumerate(paths)}
        sources['src/A.sol']['ast']['nodes'] = [{'nodeType': 'ImportDirective', 'sourceUnit': 1}]
        return {'working_dir': '/repo', 'compilation_units': {'unit': {'source_units': sources,
                 'filenames': [{'absolute': '/repo/' + p, 'relative': p} for p in paths]}},
                'source_content': {'/repo/' + p: p for p in paths}}

    def test_closure_keeps_required_dependency_not_unreachable_scripts(self):
        data = self.data()
        selected, report = production_archive(data, ['src'])
        self.assertEqual(set(selected['source_content']), {'/repo/src/A.sol', '/repo/lib/D.sol'})
        self.assertEqual(len(data['source_content']), 4)
        self.assertEqual(len(report['excluded_unreachable_sources']), 2)

    def test_missing_import_is_not_silently_dropped(self):
        data = self.data()
        data['compilation_units']['unit']['source_units']['src/A.sol']['ast']['nodes'][0]['sourceUnit'] = 999
        with self.assertRaises(ValueError):
            production_archive(data, ['src'])

    def test_empty_scope_rejected(self):
        with self.assertRaises(ValueError):
            production_archive(self.data(), ['missing'])
