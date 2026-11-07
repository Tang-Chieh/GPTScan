"""Seven selected rules must equal upstream semantically except output.impact."""
import hashlib
import json
from pathlib import Path
import unittest

import yaml


class UpstreamRulePreservationTests(unittest.TestCase):
    def test_only_impact_differs_from_upstream(self):
        # Canonical YAML hashes from upstream 29a174773bd526c32ab7d6a8c78a63870330ccc7.
        baseline = {
            'Flashloan_Price.yml': 'd2c5d78a3d9257721730f7a3a5e11437f8bd2ab8bdc8a5dbad48175dc53eab8a',
            'FirstDeposit.yml': 'b8055fcbb1aadf108676ed7b0cf427d0b36805de382e6d52400eceac1877315e',
            'Flashloan_Buy.yml': 'e1276c96e5d382754361630daeb9a8eb029b29eafed384dee3ad81625cd54b25',
            'Flashloan_Vote.yml': 'b47bdc745995ec0f693ba2e26150c30e70a690baea7f8488f60735ea10a0993c',
            'FrontRun.yml': 'f0757d722fff762200eeb2da01b45820d9c6c2722234eea08111393c869ac497',
            'WrongOrder_Checkpoint.yml': '68d2adbe9abe7f20eab8871fb84b7a700e1a3220a9cf24d302c802564437303c',
            'WrongOrder_Interest.yml': '1e9e5c25769d8757b6231b9863eb62e9fc508b2b96bf86ec06866e5659dcdac4',
        }
        root = Path(__file__).resolve().parents[1] / 'src/rules'
        for name, expected in baseline.items():
            with self.subTest(rule=name):
                rule = yaml.safe_load((root / name).read_text())
                self.assertTrue(rule['output'].pop('impact').strip())
                actual = hashlib.sha256(json.dumps(rule, sort_keys=True).encode()).hexdigest()
                self.assertEqual(actual, expected)
