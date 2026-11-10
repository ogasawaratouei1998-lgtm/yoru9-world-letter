"""Check that the public reader and offline worker have valid JavaScript."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReaderFrontendTest(unittest.TestCase):
    def test_reader_ids_and_offline_honesty(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for token in ('id="editionTag"', 'id="storyHeading"', 'id="dateGuide"',
                      'id="offlineNotice"', 'serviceWorker.register',
                      "edition.editionType==='special'", "'前回の配信号"):
            with self.subTest(token=token):
                self.assertIn(token, page)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for JS syntax checks")
    def test_reader_and_worker_javascript_syntax(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", page, flags=re.S)
        self.assertGreaterEqual(len(scripts), 2)
        sources = [("reader.js", scripts[-1]),
                   ("service-worker.js", (ROOT / "service-worker.js").read_text(encoding="utf-8"))]
        for name, source in sources:
            with self.subTest(source=name), tempfile.TemporaryDirectory() as directory:
                temp = Path(directory) / name
                temp.write_text(source, encoding="utf-8")
                result = subprocess.run(["node", "--check", str(temp)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
