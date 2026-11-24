"""Keep all 196 countries independently reviewable in the GitHub Contents API."""
import json
import unittest
from pathlib import Path
from country_manifest_format import validate,format_manifest,LIMIT
ROOT=Path(__file__).resolve().parents[1]
class CountryManifestFormatTests(unittest.TestCase):
 def test_canonical_country_lines_and_api_size(self):
  path=ROOT/"country-content.json"
  doc=validate(path)
  self.assertEqual(len(doc["countries"]),196)
  self.assertLess(path.stat().st_size,LIMIT)
  self.assertEqual(format_manifest(doc),path.read_text(encoding="utf-8"))
 def test_noncanonical_file_is_rejected(self):
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"country-content.json"
   doc=json.loads((ROOT/"country-content.json").read_text(encoding="utf-8"))
   path.write_text(json.dumps(doc,indent=2,ensure_ascii=False),encoding="utf-8")
   with self.assertRaisesRegex(ValueError,"Not normalized"):
    validate(path)
if __name__=="__main__":unittest.main()
