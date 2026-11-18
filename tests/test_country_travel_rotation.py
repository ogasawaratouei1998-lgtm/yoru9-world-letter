"""Long-run variety for verified country selection and licensed travel photos."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from collections import Counter

from auto_editorial import recent_country_cooldown_counts, select_diverse_verified_stories

ROOT=Path(__file__).resolve().parents[1]


class CountryRotationTest(unittest.TestCase):
    def test_previous_nights_receive_strong_cooldown_from_real_archive(self):
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/"data"/"archive"
            archive.mkdir(parents=True)
            for day,countries in (
                ("2026-11-18",("アメリカ","フランス")),
                ("2026-11-17",("アメリカ",)),
                ("2026-11-16",("日本",)),
                ("2026-11-15",("ドイツ",))):
                (archive/(day+".json")).write_text(json.dumps({
                    "status":"published","editionDate":day,
                    "stories":[{"country":c} for c in countries]
                },ensure_ascii=False),encoding="utf-8")
            old=os.getcwd()
            try:
                os.chdir(td)
                recency=recent_country_cooldown_counts(date(2026,11,19))
            finally:
                os.chdir(old)
        self.assertEqual(recency["US"],13)  # yesterday 9, day before 4
        self.assertEqual(recency["FR"],9)
        self.assertEqual(recency["JP"],2)
        self.assertEqual(recency["DE"],0)  # four days old

    def test_same_quality_verified_news_rotate_away_from_recent_country(self):
        pool=[{"id":id,"country":country,"category":"work","title":"verified event"}
              for id,country in [
                  ("us","アメリカ"),("fr","フランス"),
                  ("jp","日本"),("ar","アルゼンチン")
              ]]
        picks=select_diverse_verified_stories(
            pool,Counter(),Counter(),recent_country_cooldown=Counter({"US":9}),
            selection_seed="2026-11-19")
        self.assertEqual({p["id"] for p in picks},{"fr","jp","ar"})
        self.assertEqual(picks,select_diverse_verified_stories(
            pool,Counter(),Counter(),recent_country_cooldown=Counter({"US":9}),
            selection_seed="2026-11-19"))
        # If only three verified incidents exist, publish those three rather
        # than fabricate news in novel countries to satisfy a rotation quota.
        self.assertEqual(len(select_diverse_verified_stories(
            pool[:3],Counter(),Counter(),
            recent_country_cooldown=Counter({"US":100}))),3)


@unittest.skipUnless(shutil.which("node"),"Node.js required for photo rotation regression")
class TravelPhotoRotationTest(unittest.TestCase):
    def test_photos_rotate_across_six_reload_sessions_without_repeating(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        start=page.index("const travelSelections=new Map();")
        end=page.index("function travelPostcardHtml(",start)
        logic=page[start:end]
        manifest=json.loads((ROOT/"travel-stops.json").read_text(encoding="utf-8"))
        # Actual current six-photo US catalog, not synthetic random sample.
        us={k:v for k,v in manifest.items() if v.get("country")=="アメリカ合衆国"}
        self.assertGreaterEqual(len({v["photoAsset"] for v in us.values()}),6)
        script=(
            "const vm=require('vm');\n"
            "const data=Object.create(null);\n"
            "const storage={getItem:k=>data[k]??null,setItem:(k,v)=>{data[k]=v}};\n"
            "const logic="+json.dumps(logic,ensure_ascii=False)+";\n"
            "const stops="+json.dumps(us,ensure_ascii=False)+";\n"
            "function visit(country,storyId){\n"
            " const sandbox={localStorage:storage,Math,console};\n"
            " return vm.runInNewContext('function countryKeys(){return [];} ' +"
            " 'function countryLabel(x){return x;} '+logic+"
            " '\\nconst stops='+JSON.stringify(stops)+';'+"
            " 'chooseTravelPhoto('+JSON.stringify({id:storyId,country:country})+',stops)?.photoAsset',sandbox);\n"
            "}\n"
            "const chosen=Array.from({length:6},(_,i)=>visit('アメリカ','story-'+i));\n"
            "if(chosen.some(x=>!x)||new Set(chosen).size!==6)"
            " throw Error('US artwork repeated before exhausting all six: '+chosen);\n"
            "if(chosen[0]==='assets/travel/grand-canyon.jpg')"
            " throw Error('Old archive cover unexpectedly chosen first: '+chosen[0]);\n"
            "const seventh=visit('アメリカ','seventh');\n"
            "if(seventh!==chosen[0])throw Error('Least-recently-seen rotation failed');\n"
            "const japan=visit('日本','japan');\n"
            "if(japan!==undefined)throw Error('Cross-country photo was substituted');\n"
            "if(!data['yoru9-travel-photo-rotation-v1'])"
            " throw Error('No cross-reload history stored');\n"
        )
        run=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_privacy_mode_without_storage_still_keeps_own_country(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        logic=page[page.index("const travelSelections=new Map();"):
                   page.index("function travelPostcardHtml(")]
        raw={"fr":{"country":"フランス","place":"港","region":"フランス",
                   "latitude":45.0,"longitude":6.0,
                   "photo":"https://thumb.wikimedia.org/wikipedia/commons/thumb/x/photo.jpg",
                   "photoAsset":"assets/travel/fr.jpg",
                   "photoPage":"https://commons.wikimedia.org/wiki/File:France.jpg",
                   "licenseUrl":"https://creativecommons.org/licenses/by/4.0/"}}
        script=("function countryKeys(){return [];} function countryLabel(x){return x;}\n"+
            logic+"\nconst stops="+json.dumps(raw,ensure_ascii=False)+";"+
            "if(chooseTravelPhoto({id:'x',country:'フランス'},stops)?.country!=='フランス')process.exit(2);"+
            "if(chooseTravelPhoto({id:'y',country:'アメリカ'},stops)!==null)process.exit(3);")
        run=subprocess.run(["node","-e",script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)


if __name__=="__main__":
    unittest.main()
