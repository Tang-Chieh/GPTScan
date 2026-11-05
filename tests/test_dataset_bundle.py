import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def run_bundle(self, mode):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = root / 'bundle'
            (bundle / 'repo').mkdir(parents=True)
            raw = b'{"crytic_version":"0.0.2"}'
            compressed = gzip.compress(raw, mtime=0)
            build = json.dumps({'repo_id': 'repo', 'analysis_input': {'path': 'analysis_artifacts/repo.json'}}).encode()
            if mode == 'traversal':
                build = json.dumps({'analysis_input': {'path': '../escape.json'}}).encode()
            sha = lambda value: hashlib.sha256(value).hexdigest()
            record = {'repo_id': 'repo', 'archive': 'repo/archive.json.gz', 'build_json': 'repo/build.json',
                      'legacy': True, 'target_roots': ['contracts'], 'archive_sha256': sha(raw),
                      'gzip_sha256': sha(compressed), 'archive_bytes': len(raw), 'build_json_sha256': sha(build)}
            if mode == 'checksum':
                record['gzip_sha256'] = '0' * 64
            if mode == 'size':
                record['archive_bytes'] = 2 ** 40
            (bundle / 'repo/archive.json.gz').write_bytes(compressed)
            (bundle / 'repo/build.json').write_bytes(build)
            (bundle / 'manifest.json').write_text(json.dumps({'repos': [record]}))
            out = root / 'unpacked'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/unpack_dataset_inputs.py'),
                                     '--bundle', str(bundle), '--output-dir', str(out)], capture_output=True)
            if mode == 'valid':
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((out / 'repo/analysis_artifacts/repo.json').read_bytes(), raw)
                plan = json.loads((out / 'archive_plan.json').read_text())
                self.assertEqual(plan[0]['repo_id'], 'repo')
                self.assertEqual(plan[0]['target_roots'], ['contracts'])
                self.assertEqual(Path(plan[0]['build_json']).read_bytes(), build)
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((out / 'escape.json').exists())

    def test_valid_archive_is_restored_byte_for_byte(self):
        self.run_bundle('valid')

    def test_checksum_mismatch_rejected(self):
        self.run_bundle('checksum')

    def test_path_traversal_rejected(self):
        self.run_bundle('traversal')

    def test_unbounded_decompression_rejected(self):
        self.run_bundle('size')
