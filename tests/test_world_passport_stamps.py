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
    def test_forward_only_quiz_with_correct_and_wrong_answers_and_reload(self):
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
function clickNext(){const fn=$('todayQuizNext').handlers.click;check(!!fn,70);fn();}
loadWorldPassport();updateWorldPassportBoard();
check($('todayPassportCount').textContent==='0 / 2',11);
check($('todayPassportStamps').children.length===2,12);
check($('todayPassportStamps').children[0].dataset.earned==='false',13);
startWorldPassport(countries[0]);
check(worldPassportActive.questions.length===2,14);
check($('todayCountryQuiz').scrollCalls===1&&$('todayCountryQuiz').lastScrollOptions?.block==='start',52);
check($('todayQuizQuestion').focusCalls===1&&$('todayQuizQuestion').lastFocusOptions?.preventScroll===true,53);
answerWorldPassport(worldPassportActive.questions[0].answer);
check($('todayQuizStampReward').hidden,15);
const firstCorrect=$('todayQuizChoices').children[worldPassportActive.questions[0].answer];
check(firstCorrect.dataset.popped==='true',40);
check(firstCorrect.children[0]?.className==='quiz-answer-sparks',41);
check(firstCorrect.children[0]?.children.length===10,42);
check(!$('todayQuizCorrectFlash').hidden,43);
check($('todayQuizCorrectFlashLabel').textContent.includes('正解'),44);
check($('todayQuizNext').textContent==='次の問題へ →',71);
clickNext();
check(worldPassportActive.step===1,54);
check($('todayCountryQuiz').scrollCalls===2&&$('todayCountryQuiz').lastScrollOptions?.block==='start',55);
check($('todayQuizQuestion').focusCalls===2,56);
check($('todayQuizResult').hidden,57);
check($('todayQuizCorrectFlash').hidden,45);
check($('todayQuizNext').hidden,72);
answerWorldPassport(worldPassportActive.questions[1].answer);
check($('todayQuizCorrectFlashLabel').textContent.includes('連続正解'),46);
check($('todayQuizStampReward').dataset.new==='true',16);
check($('todayQuizStampReward').dataset.perfect==='true',47);
check(!!worldPassportStamps.AR&&worldPassportStamps.AR.score===2,17);
check($('todayPassportCount').textContent==='1 / 2',18);
check($('todayPassportMeter').attributes['aria-valuenow']==='1',19);
check($('todayPassportStamps').children[0].dataset.earned==='true',20);
check($('todayQuizNext').textContent==='次は日本の問題へ →',21);
// Final answer must advance directly to the unvisited country, not restart AR.
clickNext();
check(worldPassportActive.item.code==='JP'&&worldPassportActive.step===0,23);
check($('todayCountryQuiz').scrollCalls===3,62);
check($('closing').scrollCalls===undefined,63);
const jpFirst=worldPassportActive.questions[0],wrong1=(jpFirst.answer+1)%3;
answerWorldPassport(wrong1);
check($('todayQuizVerdict').textContent.includes('惜しい！'),59);
check($('todayQuizVerdict').textContent.includes('正解は「'+jpFirst.options[jpFirst.answer]+'」'),73);
check($('todayQuizChoices').children[jpFirst.answer].dataset.correct==='true',74);
check($('todayQuizChoices').children[wrong1].dataset.pickedWrong==='true',75);
check($('todayQuizCorrectFlash').hidden,48);
check($('todayQuizChoices').children[wrong1].dataset.popped!=='true',49);
check($('todayQuizNext').textContent==='次の問題へ →',76);
// Even after a wrong answer, the same visible button must open question two.
clickNext();
check(worldPassportActive.item.code==='JP'&&worldPassportActive.step===1,60);
check($('todayCountryQuiz').scrollCalls===4,77);
check($('todayQuizResult').hidden,61);
check($('todayQuizNext').hidden,78);
const jpLast=worldPassportActive.questions[1],wrong2=(jpLast.answer+1)%3;
answerWorldPassport(wrong2);
check($('todayQuizVerdict').textContent.includes(jpLast.options[jpLast.answer]),79);
check(worldPassportStamps.JP?.score===0,80);
check($('todayPassportStamps').children[1].dataset.grade==='bronze',81);
check($('todayPassportCount').textContent==='2 / 2',24);
check($('todayPassportBoard').dataset.complete==='true',25);
check($('todayPassportBoard').dataset.celebrate==='true',50);
check($('todayPassportMessage').textContent.includes('世界パスポート完成'),26);
check($('todayQuizNext').textContent==='スタンプ帳へ戻る ✓',27);
// The last button must NOT replay question 1 or unexpectedly show the footer.
clickNext();
check(worldPassportActive===null&&$('todayCountryQuiz').hidden,82);
check($('todayPassportBoard').scrollCalls===1,83);
check($('todayPassportBoard').lastScrollOptions?.block==='start',84);
check($('todayPassportHeading').focusCalls===1,85);
check($('todayPassportHeading').lastFocusOptions?.preventScroll===true,86);
check($('closing').scrollCalls===undefined,87);
clickNext();check(worldPassportActive===null,88);
worldPassportEdition='';worldPassportStamps={};
loadWorldPassport();updateWorldPassportBoard();
check($('todayPassportCount').textContent==='2 / 2',28);
check(worldPassportStamps.AR.score===2,29);
check(worldPassportStamps.JP.score===0,89);
check($('todayPassportLifetime').textContent==='通算訪問国：2か国（この端末に保存）',30);
check($('todayPassportStamps').children[0].dataset.grade==='gold',31);
edition.editionDate='2026-11-21';
loadWorldPassport();updateWorldPassportBoard();
check($('todayPassportCount').textContent==='0 / 2',32);
check($('todayPassportLifetime').textContent==='通算訪問国：2か国（この端末に保存）',33);
check($('todayPassportStamps').children[0].dataset.ever==='true',34);
check($('todayPassportStamps').children[0].dataset.earned==='false',35);
check($('todayPassportBoard').dataset.celebrate==='false',51);
"""
        run=subprocess.run(['node','-e',mock+'\n'+game+'\n'+check],
                           capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr or run.stdout)


if __name__=="__main__":
    unittest.main()
