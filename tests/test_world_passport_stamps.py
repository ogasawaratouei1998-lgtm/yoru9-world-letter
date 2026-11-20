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
            'id="todayQuizRewardSeal"', 'id="todayQuizNext"',
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
            "nextWorldPassportRound", "finishWorldPassport", "run.streak++",
            "WORLD_PASSPORT_LIFETIME_KEY", "rememberWorldPassportCountry(",
            "worldPassportGrade(", "stamp.dataset.ever=String(",
            "function celebrateWorldPassportCorrect(",
            "if(correct)celebrateWorldPassportCorrect(",
            "worldPassportJustCompleted=firstStamp"
        ):
            self.assertIn(marker,game)
        self.assertIn("@media(prefers-reduced-motion:reduce)",page)
        self.assertIn('id="todayPassportHeading" tabindex="-1"',page)
        self.assertNotIn("todayQuizNextCountry",page)
        self.assertNotIn("todayQuizNextCountry",game)
        self.assertNotIn("もう一度挑戦する",game)
        self.assertIn("スタンプ帳へ戻る",game)

    def test_answer_close_button_returns_to_stamps_and_preserves_partial_progress(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        game=(ROOT/"world-passport.js").read_text(encoding="utf-8")
        self.assertIn('id="todayQuizQuestion" tabindex="-1"',page)
        self.assertIn('id="todayQuizNext" type="button" hidden>閉じる</button>',page)
        self.assertNotIn("次の問題へ →",game)
        self.assertNotIn("nextWorldPassportRound",game)
        self.assertNotIn("もう一度挑戦する",game)
        self.assertIn("recordWorldPassportNextQuestion(run)",game)
        self.assertIn("passportProgressKey()",game)
        self.assertIn("function finishWorldPassport()",game)
        self.assertIn("scrollIntoView({block:'start',behavior:'auto'})",game)
        self.assertIn("question.focus({preventScroll:true})",game)
        self.assertIn("worldPassportActive!==run",game)
        self.assertIn("document.getElementById('todayQuizNext').addEventListener('click',finishWorldPassport)",game)
        self.assertIn("const saved=worldPassportProgress[item.code];",game)
        self.assertIn("step:resume?resume.step:0",game)
        self.assertIn("todayPassportBoard",game)
        self.assertIn("scroll-margin-top:calc(var(--safe-top) + 82px)",page)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required")
    def test_close_after_answer_then_resume_stamps_and_reload(self):
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
function check(ok,n){if(!ok)process.exit(n)}
function closeAnswered(){
 const fn=$('todayQuizNext').handlers.click;
 check(!!fn,70);fn();
 check(worldPassportActive===null&&$('todayCountryQuiz').hidden,71);
 check($('todayPassportBoard').lastScrollOptions?.block==='start',72);
 check(!$('closing').scrollCalls,73);
}
function openStamp(i){
 const fn=$('todayPassportStamps').children[i].handlers.click;
 check(!!fn,74);fn();
 check(!$('todayCountryQuiz').hidden,75);
}
loadWorldPassport();updateWorldPassportBoard();
check($('todayPassportCount').textContent==='0 / 2',11);
check($('todayPassportStamps').children.length===2,12);
openStamp(0);
check(worldPassportActive.questions.length===2&&worldPassportActive.step===0,14);
check($('todayCountryQuiz').scrollCalls===1,52);
check($('todayQuizQuestion').focusCalls===1,53);
answerWorldPassport(worldPassportActive.questions[0].answer);
check($('todayQuizStampReward').hidden,15);
const firstCorrect=$('todayQuizChoices').children[worldPassportActive.questions[0].answer];
check(firstCorrect.dataset.popped==='true',40);
check(firstCorrect.children[0]?.className==='quiz-answer-sparks',41);
check(firstCorrect.children[0]?.children.length===10,42);
check(!$('todayQuizCorrectFlash').hidden,43);
check($('todayQuizNext').textContent==='閉じる',44);
check(worldPassportActive.step===0,76);
check(worldPassportProgress.AR?.step===1&&worldPassportProgress.AR?.score===1,77);
check($('todayPassportCount').textContent==='0 / 2',78);
check($('todayPassportStamps').children[0].children[2].textContent==='第2問から再開',79);
closeAnswered();
check($('todayPassportBoard').scrollCalls===1,80);
// Even across browser refresh, tapping AR resumes the SECOND question.
worldPassportEdition='';worldPassportStamps={};worldPassportProgress={};
loadWorldPassport();updateWorldPassportBoard();
check(worldPassportProgress.AR?.step===1&&worldPassportProgress.AR?.score===1,81);
openStamp(0);
check(worldPassportActive.item.code==='AR'&&worldPassportActive.step===1,82);
check(worldPassportActive.score===1,83);
check($('todayQuizResult').hidden&&$('todayQuizNext').hidden,84);
check($('todayCountryQuiz').scrollCalls===2,85);
answerWorldPassport(worldPassportActive.questions[1].answer);
check($('todayQuizStampReward').dataset.new==='true',86);
check($('todayQuizStampReward').dataset.perfect==='true',87);
check(worldPassportStamps.AR?.score===2,88);
check(!worldPassportProgress.AR,89);
check($('todayPassportCount').textContent==='1 / 2',90);
check($('todayQuizNext').textContent==='閉じる',91);
closeAnswered();
check($('todayPassportBoard').scrollCalls===2,92);
openStamp(1);
check(worldPassportActive.item.code==='JP'&&worldPassportActive.step===0,93);
const firstJP=worldPassportActive.questions[0],wrong=(firstJP.answer+1)%3;
answerWorldPassport(wrong);
check($('todayQuizVerdict').textContent.includes('惜しい！'),94);
check($('todayQuizVerdict').textContent.includes(firstJP.options[firstJP.answer]),95);
check($('todayQuizChoices').children[firstJP.answer].dataset.correct==='true',96);
check($('todayQuizChoices').children[wrong].dataset.pickedWrong==='true',97);
check($('todayQuizCorrectFlash').hidden,98);
check($('todayQuizNext').textContent==='閉じる',99);
check(worldPassportProgress.JP?.step===1&&worldPassportProgress.JP.score===0,100);
closeAnswered();
openStamp(1);
check(worldPassportActive.item.code==='JP'&&worldPassportActive.step===1,101);
check(worldPassportActive.score===0,102);
const lastJP=worldPassportActive.questions[1],wrongAgain=(lastJP.answer+1)%3;
answerWorldPassport(wrongAgain);
check($('todayQuizVerdict').textContent.includes(lastJP.options[lastJP.answer]),103);
check(worldPassportStamps.JP?.score===0,104);
check($('todayPassportStamps').children[1].dataset.grade==='bronze',105);
check($('todayPassportCount').textContent==='2 / 2',106);
check($('todayPassportBoard').dataset.complete==='true',107);
check($('todayPassportBoard').dataset.celebrate==='true',108);
check($('todayPassportMessage').textContent.includes('世界パスポート完成'),109);
check(!worldPassportProgress.JP,110);
check($('todayQuizNext').textContent==='閉じる',111);
closeAnswered();
check($('todayPassportBoard').scrollCalls===4,112);
check($('todayPassportHeading').focusCalls===4,113);
check($('todayPassportHeading').lastFocusOptions?.preventScroll===true,114);
// Closing never starts another country's quiz or replays the first question.
check(worldPassportActive===null,115);
worldPassportEdition='';worldPassportStamps={};worldPassportProgress={};
loadWorldPassport();updateWorldPassportBoard();
check($('todayPassportCount').textContent==='2 / 2',116);
check(worldPassportStamps.AR.score===2,117);
check(worldPassportStamps.JP.score===0,118);
check($('todayPassportLifetime').textContent==='通算訪問国：2か国（この端末に保存）',119);
check($('todayPassportStamps').children[0].dataset.grade==='gold',120);
edition.editionDate='2026-11-21';
loadWorldPassport();updateWorldPassportBoard();
check($('todayPassportCount').textContent==='0 / 2',121);
check(Object.keys(worldPassportProgress).length===0,122);
check($('todayPassportLifetime').textContent==='通算訪問国：2か国（この端末に保存）',123);
check($('todayPassportStamps').children[0].dataset.ever==='true',124);
check($('todayPassportStamps').children[0].dataset.earned==='false',125);
check($('todayPassportBoard').dataset.celebrate==='false',126);
"""
        run=subprocess.run(['node','-e',mock+'\n'+game+'\n'+check],
                           capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr or run.stdout)


if __name__=="__main__":
    unittest.main()
