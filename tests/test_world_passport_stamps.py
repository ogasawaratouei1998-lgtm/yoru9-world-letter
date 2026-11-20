"""Regression: the stamp book is removed; optional country quizzes remain usable."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CountryQuizWithoutStampBookTest(unittest.TestCase):
    def test_stamp_collection_removed_and_photo_quiz_remains_accessible(self):
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        quiz=(ROOT/"world-passport.js").read_text(encoding="utf-8")
        for obsolete in ("todayPassportBoard","todayPassportStamps","todayPassportCount",
                         "todayPassportMeter","todayQuizStampReward","todayPassportLifetime",
                         "WORLD PASSPORT ·","スタンプ帳","スタンプ獲得"):
            with self.subTest(item=obsolete):
                self.assertNotIn(obsolete,page)
        for obsolete in ("localStorage","worldPassportStamps","persistWorldPassport",
                         "todayPassportBoard","todayQuizStampReward"):
            with self.subTest(script=obsolete):
                self.assertNotIn(obsolete,quiz)
        self.assertIn('id="todayMapLegend"',page)
        self.assertIn("#todayMapLegend{display:flex;",page)
        self.assertIn("button.addEventListener('click',()=>startWorldPassport(item))",page)
        self.assertIn("question.focus({preventScroll:true})",quiz)
        self.assertIn("function revealWorldPassportAnswerPhoto(question)",quiz)
        self.assertIn("function finishWorldPassport()",quiz)
        self.assertIn("next.textContent=run.step<run.questions.length-1?'次の問題へ →':'閉じる'",quiz)
        self.assertIn("const WORLD_PASSPORT_QUIZZES=Object.freeze({",quiz)

    @unittest.skipUnless(shutil.which("node"),"Node.js required")
    def test_two_round_quiz_opens_advances_and_closes_without_persistence(self):
        quiz=(ROOT/"world-passport.js").read_text(encoding="utf-8")
        mock=r"""
const nodes={};
function element(){
 return {dataset:{},style:{},hidden:false,textContent:'',children:[],open:false,
  handlers:{},attributes:{},disabled:false,
  setAttribute(k,v){this.attributes[k]=v},
  removeAttribute(k){delete this.attributes[k]},
  addEventListener(type,fn){this.handlers[type]=fn},
  querySelectorAll(selector){return selector==='button'?this.children:[]},
  append(...items){this.children.push(...items)},
  replaceChildren(){this.children=[]},
  scrollIntoView(){},focus(){},close(){this.open=false}
 };
}
const $=id=>(nodes[id]??=element());
const document={
 getElementById:$,createElement:()=>element(),
 querySelectorAll(selector){return selector==='#todayMapLegend .today-map-country'?[]:[]}
};
const localStorage=new Proxy({}, {get(){throw new Error('Removed stamp storage must not be touched')}});
const hideTodayCountryIntro=()=>{};
const countryRecord=()=>({region:'ヨーロッパ'});
const loadTravelStops=async()=>({});
const requestAnimationFrame=callback=>callback();
$('todayCountryQuiz').hidden=true;
function check(ok,num){if(!ok)throw new Error('quiz assertion '+num)}
"""
        checker=r"""
const item={code:'IT',name:'イタリア',indices:[0]};
check(WORLD_PASSPORT_QUIZZES.IT.length===2,1);
startWorldPassport(item);
check(!$('todayCountryQuiz').hidden,2);
check(worldPassportActive.step===0,3);
check($('todayQuizChoices').children.length===3,4);
const first=worldPassportActive.questions[0].answer;
answerWorldPassport(first);
check($('todayQuizNext').textContent==='次の問題へ →',5);
check($('todayQuizResult').hidden===false,6);
finishWorldPassport();
check(worldPassportActive.step===1,7);
check($('todayQuizResult').hidden===true,8);
const second=worldPassportActive.questions[1].answer;
answerWorldPassport(second);
check($('todayQuizNext').textContent==='閉じる',9);
finishWorldPassport();
check(worldPassportActive===null&&$('todayCountryQuiz').hidden,10);
startWorldPassport(item);
check(worldPassportActive.step===0,11);
closeWorldPassport();
check(worldPassportActive===null,12);
"""
        run=subprocess.run(["node","-e",mock+quiz+checker],text=True,capture_output=True)
        self.assertEqual(run.returncode,0,run.stderr)


if __name__=="__main__":
    unittest.main()
