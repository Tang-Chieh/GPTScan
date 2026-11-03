from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from docker_runtime import image_id

DIGEST = "sha256:" + "a" * 64


class ImageTests(unittest.TestCase):
    def test_tag_resolution_pins_same_local_image_id(self):
        with patch("docker_runtime.subprocess.check_output", side_effect=[DIGEST + "\n", DIGEST + "\n"]) as call:
            self.assertEqual(image_id("example:tag"), DIGEST)
            self.assertIn(DIGEST, call.call_args.args[0])

    def test_missing_or_ambiguous_local_image_rejected(self):
        for result in ("", DIGEST + "\nsha256:" + "b" * 64):
            with patch("docker_runtime.subprocess.check_output", return_value=result):
                with self.assertRaises(ValueError):
                    image_id("example:tag")
