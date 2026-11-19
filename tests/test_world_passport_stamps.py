"""Regression: World Passport visible stamp album and score state."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class WorldPassportStampsTest(unittest.TestCase):
    def test_passport_always_visible_with_accessible_completion_progress(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        game=(ROOT/"world-passport.js").read_text(encoding="utf-8")
        for marker in (
            'id="todayPassportBoard"', 'id="todayPassportCount"',
            'id="todayPassportMeter" role="progressbar"',
            'id="todayPassportMeterFill"', 'id="todayPassportStamps"',
            'id="todayQuizSteps"', 'id="todayQuizStampReward"',
            'id="todayQuizRewardSeal"', 'id="todayQuizNextCountry"'
        ):
            self.assertIn(marker,page)
        for marker in (
            "function updateWorldPassportBoard()", "stamp.dataset.earned=String(completed)",
            "stamp.addEventListener('click',()=>startWorldPassport(item))",
            "worldPassportStamps[code]={score:run.score,total:run.questions.length}",
            "persistWorldPassport();updateWorldPassportButtons()",
            "firstStamp=!previous", "todayQuizStampReward",
            "todayQuizNextCountry", "run.streak++"
        ):
            self.assertIn(marker,game)
        self.assertIn("@media(prefers-reduced-motion:reduce)",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required")
    def test_first_stamp_completion_replay_and_reload(self):
        game=(ROOT/"world-passport.js").read_text(encoding="utf-8")
        mock=r"""
const listeners=new Map(),store=new Map();
function element(){
 return {dataset:{},style:{},hidden:false,textContent:'',children:[],
  open:false,handlers:{},attributes:{},
  setAttribute(k,v){this.attributes[k]=v},
  removeAttribute(k){delete this.attributes[k]},
  addEventListener(type,fn){this.handlers[type]=fn},
  querySelectorAll(selector){return selector==='button'?this.children:[]},
  append(...items){this.children.push(...items)},
  replaceChildren(){this.children=[]},
  scrollIntoView(){},close(){this.open=false},
  remove(){},getAttribute(k){return this.attributes[k]}
 };
}
const nodes={};
const $=id=>(nodes[id]??=element());
const document={
 getElementById:$,createElement:()=>element(),
 querySelectorAll(selector){return selector==='#todayMapLegend .today-map-country'?[]:[]}
};
const localStorage={
 getItem(k){return store.get(k)||null},
 setItem(k,v){store.set(k,v)}
};
const edition={editionDate:'2026-11-20'};
const countries=[{code:'AR',name:'アルゼンチン',indices:[0]},
 {code:'JP',name:'日本',indices:[1]}];
function currentIssueCountries(){return countries}
function countryRecord(code){return {region:code==='JP'?'アジア':'南アメリカ'}}
function hideTodayCountryIntro(){}
async function loadTravelStops(){return {}}
"""
        check=r"""
loadWorldPassport();updateWorldPassportBoard();
if($('todayPassportCount').textContent!=='0 / 2')process.exit(11);
if($('todayPassportStamps').children.length!==2)process.exit(12);
if($('todayPassportStamps').children[0].dataset.earned!=='false')process.exit(13);
startWorldPassport(countries[0]);
if(worldPassportActive.questions.length!==2)process.exit(14);
answerWorldPassport(worldPassportActive.questions[0].answer);
if(!$('todayQuizStampReward').hidden)process.exit(15);
nextWorldPassportRound();
answerWorldPassport(worldPassportActive.questions[1].answer);
if(!$('todayQuizStampReward').dataset.new==='true')process.exit(16);
if(!worldPassportStamps.AR||worldPassportStamps.AR.score!==2)process.exit(17);
if($('todayPassportCount').textContent!=='1 / 2')process.exit(18);
if($('todayPassportMeter').attributes['aria-valuenow']!=='1')process.exit(19);
if($('todayPassportStamps').children[0].dataset.earned!=='true')process.exit(20);
if($('todayQuizNextCountry').hidden)process.exit(21);
nextWorldPassportRound();
answerWorldPassport(2);
nextWorldPassportRound();
answerWorldPassport(1);
if(worldPassportStamps.AR.score!==2)process.exit(22);
const newCountryButton=$('todayQuizNextCountry');
newCountryButton.handlers.click();
if(worldPassportActive.item.code!=='JP')process.exit(23);
answerWorldPassport(worldPassportActive.questions[0].answer);
if($('todayPassportCount').textContent!=='2 / 2')process.exit(24);
if($('todayPassportBoard').dataset.complete!=='true')process.exit(25);
if(!$('todayPassportMessage').textContent.includes('世界パスポート完成'))process.exit(26);
if(!$('todayQuizNextCountry').hidden)process.exit(27);
worldPassportEdition='';worldPassportStamps={};
loadWorldPassport();updateWorldPassportBoard();
if($('todayPassportCount').textContent!=='2 / 2')process.exit(28);
if(worldPassportStamps.AR.score!==2)process.exit(29);
"""
        run=subprocess.run(['node','-e',mock+'\n'+game+'\n'+check],
                           capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr or run.stdout)


if __name__=="__main__":
    unittest.main()
