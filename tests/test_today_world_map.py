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
        from country_codes import country_codes
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        catalog=json.loads((ROOT/"country-catalog.json").read_text(encoding="utf-8"))
        by_code={entry["code"]:entry for entry in catalog}
        self.assertTrue(1<=len(issue["stories"])<=5)
        for story in issue["stories"]:
            # A factual story may be cross-border; unknown geographies are
            # listed without a fabricated pin rather than blocking releases.
            for code in country_codes(story["country"]):
                with self.subTest(country=story["country"],code=code):
                    self.assertIn(code,by_code)
                    item=by_code[code]
                    self.assertTrue(-180<=item["lon"]<=180)
                    self.assertTrue(-90<=item["lat"]<=90)
                    px=(item["lon"]+180)/360*100
                    py=(90-item["lat"])/180*100
                    self.assertTrue(0<=px<=100 and 0<=py<=100)

    @unittest.skipUnless(shutil.which("node"),"Node.js required")
    def test_runtime_pins_come_only_from_current_issue_no_extra_countries(self):
        # Run production mapping functions against the ACTUAL published issue.
        # This regression must survive future 1, 2, 3, 4 and 5-story nights.
        start=HTML.index("function countryRecord(name){")
        end=HTML.index("function setReleaseStatus(message){",start)
        code=HTML[start:end]
        catalog=json.loads((ROOT/"country-catalog.json").read_text(encoding="utf-8"))
        issue=json.loads((ROOT/"data/current.json").read_text(encoding="utf-8"))
        pure=code.split("async function loadCountryCatalog()")[0]
        maplogic="function currentIssueCountries(){"+code.split(
            "function currentIssueCountries(){")[1].split(
            "function renderTodayMap(){")[0]
        script=("const countryCatalog="+json.dumps(catalog,ensure_ascii=False)+";\\n"+
                "let edition="+json.dumps(issue,ensure_ascii=False)+";\\n"+
                pure+maplogic+
                """
function verify(label){
 const expected=new Map();
 edition.stories.forEach((story,index)=>{
  const codes=countryKeys(story.country);
  const keys=codes.length?codes:['unmapped:'+String(story.country||'国名未登録')];
  for(const code of keys){
   if(!expected.has(code))expected.set(code,[]);
   expected.get(code).push(index);
  }
 });
 const actual=currentIssueCountries();
 if(actual.length!==expected.size)
   throw Error(label+': wrong unique country count '+actual.length+' vs '+expected.size);
 for(const row of actual){
  const indices=expected.get(row.code);
  if(!indices||JSON.stringify(indices)!==JSON.stringify(row.indices))
   throw Error(label+': wrong country/story association '+row.code);
  if(row.point){
   if(row.point.x<0||row.point.x>100||row.point.y<0||row.point.y>100)
    throw Error(label+': invalid centroid '+row.code);
  }else if(!row.code.startsWith('unmapped:')){
   throw Error(label+': missing centroid '+row.code);
  }
 }
}
verify('current published edition');
for(let n=1;n<=5;n++){
 edition.stories=countryCatalog.slice(0,n).map((c,i)=>({id:'synthetic-'+i,country:c.name}));
 verify('synthetic '+n);
}
edition.stories=[
 {id:'a',country:'アメリカ'},{id:'b',country:'アメリカ'},
 {id:'c',country:'イギリス・アメリカ'},
 {id:'d',country:'未登録の国'}
];
verify('same-country deduplication, cross-border and unknown location');
if(currentIssueCountries().length!==3)throw Error('deduplication failed');
""")
        r=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)


if __name__=="__main__":
    unittest.main()
