from pathlib import Path
import unittest
from api.verify_python_runtime import verify_runtime

class PythonRuntimeTests(unittest.TestCase):
    def test_pinned_runtime_is_accepted(self):
        pin = Path(__file__).resolve().parents[2] / ".python-version"
        version = tuple(map(int, pin.read_text().strip().split(".")))
        self.assertEqual(verify_runtime(version), pin.read_text().strip())

    def test_render_default_drift_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "runtime drift"):
            verify_runtime((3, 14, 3))
