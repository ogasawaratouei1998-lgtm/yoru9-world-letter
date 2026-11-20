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
            'id="todayQuizRewardSeal"', 'id="todayQuizNextCountry"',
            'id="todayPassportLifetime"', 'class="passport-sparkles"',
            'id="todayQuizCorrectFlash"', 'id="todayQuizCorrectFlashLabel"'
        ):
            self.assertIn(marker,page)
        for marker in (
            "function updateWorldPassportBoard()", "stamp.dataset.earned=String(completed)",
            "stamp.addEventListener('click',()=>startWorldPassport(item))",
            "worldPassportStamps[code]={score:run.score,total:run.questions.length}",
            "persistWorldPassport();updateWorldPassportButtons()",
            "firstStamp=!previous", "todayQuizStampReward",
            "todayQuizNextCountry", "run.streak++",
            "WORLD_PASSPORT_LIFETIME_KEY", "rememberWorldPassportCountry(",
            "worldPassportGrade(", "stamp.dataset.ever=String(",
            "function celebrateWorldPassportCorrect(",
            "if(correct)celebrateWorldPassportCorrect(",
            "worldPassportJustCompleted=firstStamp"
        ):
            self.assertIn(marker,game)
        self.assertIn("@media(prefers-reduced-motion:reduce)",page)

    def test_quiz_next_button_repositions_before_footer_and_avoids_focus_jump(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        game=(ROOT/"world-passport.js").read_text(encoding="utf-8")
        self.assertIn('id="todayQuizQuestion" tabindex="-1"',page)
        self.assertIn("scroll-margin-top:calc(var(--safe-top) + 82px)",page)
        self.assertIn("function focusWorldPassportQuestion(run)",game)
        self.assertIn("question.focus({preventScroll:true})",game)
        self.assertIn("scrollIntoView({block:'start',behavior:'auto'})",game)
        self.assertIn("requestAnimationFrame(reposition)",game)
        self.assertIn("worldPassportActive!==run",game)
        next_part=game[game.index("function nextWorldPassportRound(){"):
                       game.index("document.getElementById('todayQuizClose')")]
        self.assertIn("renderWorldPassportRound();",next_part)
        self.assertIn("focusWorldPassportQuestion(run);",next_part)
        self.assertLess(next_part.index("renderWorldPassportRound();"),
                        next_part.index("focusWorldPassportQuestion(run);"))
        self.assertNotIn("'closing'",next_part)

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
  scrollIntoView(options){this.scrollCalls=(this.scrollCalls||0)+1;this.lastScrollOptions=options},
  focus(options){this.focusCalls=(this.focusCalls||0)+1;this.lastFocusOptions=options},
  close(){this.open=false},
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
if($('todayCountryQuiz').scrollCalls!==1||$('todayCountryQuiz').lastScrollOptions?.block!=='start')process.exit(52);
if($('todayQuizQuestion').focusCalls!==1||$('todayQuizQuestion').lastFocusOptions?.preventScroll!==true)process.exit(53);
answerWorldPassport(worldPassportActive.questions[0].answer);
if(!$('todayQuizStampReward').hidden)process.exit(15);
const firstCorrect=$('todayQuizChoices').children[worldPassportActive.questions[0].answer];
if(firstCorrect.dataset.popped!=='true')process.exit(40);
if(firstCorrect.children[0]?.className!=='quiz-answer-sparks')process.exit(41);
if(firstCorrect.children[0]?.children.length!==10)process.exit(42);
if($('todayQuizCorrectFlash').hidden)process.exit(43);
if(!$('todayQuizCorrectFlashLabel').textContent.includes('正解'))process.exit(44);
nextWorldPassportRound();
if(worldPassportActive.step!==1)process.exit(54);
if($('todayCountryQuiz').scrollCalls!==2||$('todayCountryQuiz').lastScrollOptions?.block!=='start')process.exit(55);
if($('todayQuizQuestion').focusCalls!==2)process.exit(56);
if(!$('todayQuizResult').hidden)process.exit(57);
if(!$('todayQuizCorrectFlash').hidden)process.exit(45);
answerWorldPassport(worldPassportActive.questions[1].answer);
if(!$('todayQuizCorrectFlashLabel').textContent.includes('連続正解'))process.exit(46);
if($('todayQuizStampReward').dataset.new!=='true')process.exit(16);
if($('todayQuizStampReward').dataset.perfect!=='true')process.exit(47);
if(!worldPassportStamps.AR||worldPassportStamps.AR.score!==2)process.exit(17);
if($('todayPassportCount').textContent!=='1 / 2')process.exit(18);
if($('todayPassportMeter').attributes['aria-valuenow']!=='1')process.exit(19);
if($('todayPassportStamps').children[0].dataset.earned!=='true')process.exit(20);
if($('todayQuizNextCountry').hidden)process.exit(21);
nextWorldPassportRound();
if(worldPassportActive.step!==0||$('todayCountryQuiz').scrollCalls!==3)process.exit(58);
answerWorldPassport(2);
if(!$('todayQuizVerdict').textContent.includes('惜しい！'))process.exit(59);
if(!$('todayQuizCorrectFlash').hidden)process.exit(48);
if($('todayQuizChoices').children[2].dataset.popped==='true')process.exit(49);
nextWorldPassportRound();
if(worldPassportActive.step!==1||$('todayCountryQuiz').scrollCalls!==4)process.exit(60);
if(!$('todayQuizResult').hidden)process.exit(61);
answerWorldPassport(1);
if(worldPassportStamps.AR.score!==2)process.exit(22);
const newCountryButton=$('todayQuizNextCountry');
newCountryButton.handlers.click();
if(worldPassportActive.item.code!=='JP')process.exit(23);
if($('todayCountryQuiz').scrollCalls!==5)process.exit(62);
if($('closing').scrollCalls)process.exit(63);
for(let i=0;i<worldPassportActive.questions.length;i++){
 answerWorldPassport(worldPassportActive.questions[i].answer);
 if(i<worldPassportActive.questions.length-1)nextWorldPassportRound();
}
if($('todayPassportCount').textContent!=='2 / 2')process.exit(24);
if($('todayPassportBoard').dataset.complete!=='true')process.exit(25);
if($('todayPassportBoard').dataset.celebrate!=='true')process.exit(50);
if(!$('todayPassportMessage').textContent.includes('世界パスポート完成'))process.exit(26);
if(!$('todayQuizNextCountry').hidden)process.exit(27);
worldPassportEdition='';worldPassportStamps={};
loadWorldPassport();updateWorldPassportBoard();
if($('todayPassportCount').textContent!=='2 / 2')process.exit(28);
if(worldPassportStamps.AR.score!==2)process.exit(29);
if($('todayPassportLifetime').textContent!=='通算訪問国：2か国（この端末に保存）')process.exit(30);
if($('todayPassportStamps').children[0].dataset.grade!=='gold')process.exit(31);
edition.editionDate='2026-11-21';
loadWorldPassport();updateWorldPassportBoard();
if($('todayPassportCount').textContent!=='0 / 2')process.exit(32);
if($('todayPassportLifetime').textContent!=='通算訪問国：2か国（この端末に保存）')process.exit(33);
if($('todayPassportStamps').children[0].dataset.ever!=='true')process.exit(34);
if($('todayPassportStamps').children[0].dataset.earned!=='false')process.exit(35);
if($('todayPassportBoard').dataset.celebrate!=='false')process.exit(51);
"""
        run=subprocess.run(['node','-e',mock+'\n'+game+'\n'+check],
                           capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr or run.stdout)


if __name__=="__main__":
    unittest.main()
