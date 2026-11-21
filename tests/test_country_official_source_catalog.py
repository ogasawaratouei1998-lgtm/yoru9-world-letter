"""UNESCO feed inventory maps sources to the correct countries without approval."""
from pathlib import Path
import unittest

from country_unesco_source_catalog import build_inventory, collect_sites

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = b"""<?xml version="1.0" encoding="utf-8"?>
<query><row><id_number>668</id_number><site>Angkor</site><iso_code>kh</iso_code></row>
<row><id_number>1377</id_number><site>Wadi Rum Protected Area</site><iso_code>jo</iso_code></row>
<row><id_number>999</id_number><site>Shared World Site</site><iso_code>jo;kh</iso_code></row>
<row><id_number>0</id_number><site>Unknown Site</site><iso_code></iso_code></row>
</query>
"""


class OfficialUNESCOSourceIndexTests(unittest.TestCase):
    def test_iso_matching_is_exact_and_supports_cross_border_sites(self):
        groups = collect_sites(EXAMPLE)
        self.assertEqual(len(groups["KH"]), 2)
        self.assertEqual(len(groups["JO"]), 2)
        self.assertNotIn("NO", groups)
        self.assertEqual(groups["KH"][0]["sourceUrl"], "https://whc.unesco.org/en/list/668/")

    def test_covers_every_pending_country_without_making_up_heritage_sites(self):
        doc = build_inventory(ROOT, EXAMPLE)
        self.assertEqual(doc["catalogCount"], 196)
        self.assertEqual(doc["pendingCount"], 171)
        self.assertTrue(doc["countries"]["KH"]["sourceFound"])
        self.assertTrue(doc["countries"]["JO"]["sourceFound"])
        self.assertFalse(doc["countries"]["NO"]["sourceFound"])
        for entry in doc["countries"].values():
            self.assertEqual(entry["editorialStatus"], "pending")
            self.assertFalse(entry["portraitApproved"])
            self.assertFalse(entry["photographApproved"])


if __name__ == "__main__":
    unittest.main()
