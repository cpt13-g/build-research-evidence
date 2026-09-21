from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from common import ProtocolError  # noqa: E402
from validate_project import _validate_runtime_reference  # noqa: E402


class RuntimeReferenceValidationTests(unittest.TestCase):
    def test_rejects_reference_missing_from_published_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "docs" / "INTERNAL_PLAN.md"
            target.parent.mkdir()
            target.write_text("local only", encoding="utf-8")

            with self.assertRaisesRegex(ProtocolError, "absent from the published repository"):
                _validate_runtime_reference(root, "docs/INTERNAL_PLAN.md", set())

    def test_accepts_tracked_runtime_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "docs" / "PROTOCOLS.md"
            target.parent.mkdir()
            target.write_text("runtime protocol", encoding="utf-8")

            _validate_runtime_reference(root, "docs/PROTOCOLS.md", {"docs/PROTOCOLS.md"})


if __name__ == "__main__":
    unittest.main()
