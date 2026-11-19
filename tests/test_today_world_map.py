"""Regression checks: current-issue-only pastel world map and complete monthly retirement."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"index.html").read_text(encoding="utf-8")


class TodayWorldMapTest(unittest.TestCase):
    def test_only_current_issue_map_is_shown_no_monthly_shelf(self):
        for token in ('id="todayMapSection"','id="todayMapTitle"',
                      'id="todayMapDate"','id="todayMapPins"',
                      'id="todayMapLegend"','id="todayMapNote"',
                      'assets/world-today-illustrated.svg',
                      'function currentIssueCountries()',
                      'function renderTodayMap()',
                      'renderTodayMap();',
                      'loadCountryCatalog().then(()=>renderTodayMap());'):
            self.assertIn(token,HTML,token)
        for retired in ('monthRetrospective','monthCards','monthDetails',
                        'loadMonthRetrospective()','loadMonthlyVerified()',
                        'loadPublishedMonthDates()','visibleMonthStories',
                        'data-month-travel','この1か月の世界の「まさか」',
                        'id="coverWorldMap"','id="mapExtras"',
                        'id="archiveExtras"'):
            self.assertNotIn(retired,HTML,retired)
        self.assertFalse((ROOT/".github/workflows/monthly-editorial.yml").exists())
        self.assertIn('actuallyToday?',HTML)
        self.assertIn("edition.editionDate===localDate(new Date())",HTML)
        self.assertIn("ニュースの発生現場",HTML)

    def test_pastel_map_uses_real_natural_earth_land_outline(self):
        asset=ROOT/"assets/world-today-illustrated.svg"
        root=ET.parse(asset).getroot()
        self.assertTrue(root.tag.endswith("svg"))
        self.assertEqual(root.attrib.get("viewBox"),"0 0 960 480")
        paths=root.findall(".//{http://www.w3.org/2000/svg}path")
        self.assertGreater(len(paths),50)
        text=asset.read_text(encoding="utf-8")
        for color in ("#CBEFF0","#FFE8B9","#FF9D8F"):
            self.assertIn(color,text)
        self.assertIn("Natural Earth",text)
        build=(ROOT/"build_site.py").read_text(encoding="utf-8")
        worker=(ROOT/"service-worker.js").read_text(encoding="utf-8")
        self.assertIn("'assets/world-today-illustrated.svg'",build)
        self.assertIn("'assets/world-today-illustrated.svg'",worker)
        self.assertNotIn("'data/retrospective/2026-11-17.json'",build)
        self.assertNotIn("data/monthly/index.json",worker)

    def test_current_issue_country_centroids_ground_pin_placements(self):
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        catalog=json.loads((ROOT/"country-catalog.json").read_text(encoding="utf-8"))
        assert len(issue["stories"])>=1
        for story in issue["stories"]:
            name=story["country"].lower()
            matched=[x for x in catalog if x["name"].lower()==name
                     or x["code"].lower()==name
                     or name in [a.lower() for a in x["aliases"]]]
            self.assertEqual(len(matched),1,story["country"])
            x=matched[0]
            self.assertTrue(-180<=x["lon"]<=180)
            self.assertTrue(-90<=x["lat"]<=90)
            px=(x["lon"]+180)/360*100
            py=(90-x["lat"])/180*100
            self.assertTrue(0<=px<=100 and 0<=py<=100)

    @unittest.skipUnless(shutil.which("node"),"Node.js required")
    def test_runtime_pins_come_only_from_current_issue_no_extra_countries(self):
        # Extract the actual production country/mapping code, not a duplicate.
        start=HTML.index("function countryRecord(name){")
        end=HTML.index("function setReleaseStatus(message){",start)
        code=HTML[start:end]
        catalog=json.loads((ROOT/"country-catalog.json").read_text(encoding="utf-8"))
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        # Separately isolate only pure functions, without browser-dependent catalog loading.
        pure=code.split("async function loadCountryCatalog()")[0]
        maplogic="function currentIssueCountries(){"+code.split("function currentIssueCountries(){")[1].split("function renderTodayMap(){")[0]
        script=("const countryCatalog="+json.dumps(catalog,ensure_ascii=False)+";\n"+
                "const edition="+json.dumps(issue,ensure_ascii=False)+";\n"+
                pure+maplogic+
                "\nconst results=currentIssueCountries();"+
                "if(results.length!==3)throw Error('expected 3 unique countries, got '+results.length);"+
                "for(const c of results){"+
                "if(!c.point||c.indices.length!==1||c.point.x<0||c.point.x>100||c.point.y<0||c.point.y>100)"+
                "throw Error('invalid current country pin '+c.name);"+
                "}"+
                "if(!results.some(c=>c.name==='アルゼンチン')||"+
                "!results.some(c=>c.name==='フランス')||"+
                "!results.some(c=>c.name==='アメリカ合衆国'))"+
                "throw Error('country centroids missing');")
        r=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)


if __name__=="__main__":
    unittest.main()
