/* The World Passport: a tiny factual quiz, NOT a news article or travel postcard.
 * Trivia is sourced from the public country guides or country-catalog.json.
 * The AI one-liners are clearly marked as original fictional humor. */
'use strict';
const WORLD_PASSPORT_QUIZZES=Object.freeze({
 AR:[
  {question:'イグアスの滝を包む風景は？',options:['熱帯の森','氷の洞窟','砂漠の砂丘'],answer:0,
   fact:'アルゼンチン北東部のイグアスの滝は、熱帯の森に囲まれています。',
   quip:'水の勢いがすごすぎて、森まで拍手しているように見える。'},
  {question:'アルゼンチンのマテ茶に似合うのは？',options:['車の給油','語らいのひととき','壁のペンキ塗り'],answer:1,
   fact:'マテ茶はアルゼンチンの日常や人との語らいの中で親しまれています。',
   quip:'どれだけ話が弾んでも、オチまでは淹れてくれない。'}
 ],
 FR:[
  {question:'モン・サン＝ミシェルの景色を変えるのは？',options:['火山の噴火','オーロラ','潮の満ち引き'],answer:2,
   fact:'ノルマンディーのモン・サン＝ミシェルは、潮の満ち引きで周囲の景色が変わります。',
   quip:'景色の模様替え係は海。毎日、無給で大仕事。'},
  {question:'フランス南部の海岸が面するのは？',options:['地中海','カリブ海','北極海'],answer:0,
   fact:'フランスは大西洋と地中海の両方に面しています。',
   quip:'北極海でバカンスを始めたら、水着より防寒着が主役。'}
 ],
 US:[
  {question:'サンフランシスコの海峡に架かる橋は？',options:['ロンドン橋','ゴールデンゲートブリッジ','ブルックリン橋'],answer:1,
   fact:'ゴールデンゲートブリッジは、サンフランシスコの海峡を渡る橋です。',
   quip:'名前はゴールデン、見た目はオレンジ。名乗った瞬間からツッコミ待ち。'},
  {question:'ヨセミテ国立公園の巨大な岩壁で知られる岩石は？',options:['サンゴ','石炭','花崗岩'],answer:2,
   fact:'ヨセミテには花崗岩の大きな岩壁や谷が広がっています。',
   quip:'地球のプロフィール写真、岩肌の圧が強い。'}
 ]
});
let worldPassportEdition='',worldPassportStamps={},worldPassportActive=null;
function passportKey(){return 'yoru9-world-passport-v1:'+String(edition.editionDate||'demo')}
function loadWorldPassport(){
 const key=passportKey();
 if(key===worldPassportEdition)return;
 worldPassportEdition=key;worldPassportActive=null;worldPassportStamps={};
 try{
  const saved=JSON.parse(localStorage.getItem(key)||'{}');
  if(saved&&typeof saved==='object'&&!Array.isArray(saved)){
   for(const [code,result] of Object.entries(saved)){
    if(/^[A-Z]{2}$/.test(code)&&Number.isInteger(result?.score)&&
       Number.isInteger(result?.total)&&result.total>=1&&result.total<=2&&
       result.score>=0&&result.score<=result.total)worldPassportStamps[code]=result;
   }
  }
 }catch(_){}
}
function persistWorldPassport(){
 try{localStorage.setItem(passportKey(),JSON.stringify(worldPassportStamps))}catch(_){}
}
function passportQuizQuestions(item){
 if(WORLD_PASSPORT_QUIZZES[item.code])return WORLD_PASSPORT_QUIZZES[item.code];
 const region=countryRecord(item.code)?.region;
 if(region){
  const choices=[region,...['アジア','ヨーロッパ','アフリカ','北アメリカ','南アメリカ','オセアニア']
   .filter(value=>value!==region)].slice(0,3);
  const first=choices.shift();choices.splice(item.code.charCodeAt(0)%3,0,first);
  return [{question:item.name+'が位置する地域は？',options:choices,
   answer:choices.indexOf(region),
   fact:'公開の国・地域一覧では、'+item.name+'は「'+region+'」に分類されています。',
   quip:'地球儀では指一本の距離でも、航空券だとそうはいかない。'}];
 }
 const number=item.indices.length;
 return [{question:'今号の「'+item.name+'」のニュースは何本？',
  options:[number+'本',(number+1)+'本',(number+2)+'本'],answer:0,
  fact:'この公開号に載っている記事を数えると'+number+'本です。',
  quip:'ちゃんと数えた。指折り数えるのも世界旅行の第一歩。'}];
}
function passportProgressText(){
 const countries=currentIssueCountries();
 const count=countries.filter(item=>worldPassportStamps[item.code]).length;
 return countries.length>0&&count===countries.length
  ?'世界パスポート完成！ '+count+'か国のスタンプを集めました。'
  :'世界パスポート：'+count+' / '+countries.length+'か国のスタンプ';
}
function updateWorldPassportButtons(){
 document.querySelectorAll('#todayMapLegend .today-map-country').forEach(button=>{
  const code=button.dataset.countryCode;
  const completed=!!worldPassportStamps[code];
  button.dataset.quizDone=String(completed);
  button.textContent=button.dataset.countryLabel+(completed?' ✓':' ？');
  button.setAttribute('aria-expanded',String(worldPassportActive?.item.code===code));
  button.setAttribute('aria-label',button.dataset.countryName+
   (completed?'の世界クイズにもう一度挑戦':'の世界クイズに挑戦'));
 });
 $('todayQuizPassport').textContent=passportProgressText();
}
function closeWorldPassport(){
 $('todayCountryQuiz').hidden=true;worldPassportActive=null;updateWorldPassportButtons();
}
function startWorldPassport(item){
 loadWorldPassport();
 hideTodayCountryIntro();
 worldPassportActive={item,questions:passportQuizQuestions(item),step:0,score:0,answered:false};
 $('todayCountryQuiz').hidden=false;
 renderWorldPassportRound();updateWorldPassportButtons();
 $('todayCountryQuiz').scrollIntoView({block:'nearest'});
}
function renderWorldPassportRound(){
 const run=worldPassportActive;if(!run)return;
 const q=run.questions[run.step];
 run.answered=false;
 $('todayQuizTitle').textContent=run.item.name+'の「へぇ！」チャレンジ';
 $('todayQuizProgress').textContent='第'+(run.step+1)+'問 / '+run.questions.length+'問 · 景色と文化の3択';
 $('todayQuizQuestion').textContent=q.question;
 $('todayQuizResult').hidden=true;$('todayQuizNext').hidden=true;
 const options=$('todayQuizChoices');options.replaceChildren();
 q.options.forEach((answer,i)=>{
  const button=document.createElement('button');
  button.type='button';button.textContent=String(i+1)+' · '+answer;
  button.addEventListener('click',()=>answerWorldPassport(i));
  options.append(button);
 });
}
function answerWorldPassport(picked){
 const run=worldPassportActive;
 if(!run||run.answered)return;
 const question=run.questions[run.step];
 if(!question||picked<0||picked>=question.options.length)return;
 run.answered=true;const correct=picked===question.answer;
 if(correct)run.score++;
 $('todayQuizChoices').querySelectorAll('button').forEach((button,index)=>{
  button.disabled=true;
  if(index===question.answer)button.dataset.correct='true';
  if(index===picked&&!correct)button.dataset.pickedWrong='true';
 });
 $('todayQuizVerdict').textContent=correct?'正解！ 世界の「へぇ！」を発見。':'惜しい！ 正解は「'+question.options[question.answer]+'」。';
 $('todayQuizExplanation').textContent=question.fact;
 $('todayQuizJoke').textContent='AIツッコミ（創作の冗談）：'+question.quip;
 $('todayQuizResult').hidden=false;
 $('todayQuizNext').hidden=false;
 const finished=run.step===run.questions.length-1;
 if(finished){
  worldPassportStamps[run.item.code]={score:run.score,total:run.questions.length};
  persistWorldPassport();updateWorldPassportButtons();
 }
 $('todayQuizNext').textContent=finished
  ?'スタンプ獲得！ '+run.score+' / '+run.questions.length+'問正解 · もう一度挑戦'
  :'次の問題へ';
}
function nextWorldPassportRound(){
 const run=worldPassportActive;
 if(!run||!run.answered)return;
 if(run.step===run.questions.length-1){run.step=0;run.score=0}
 else run.step++;
 renderWorldPassportRound();
}
$('todayQuizClose').addEventListener('click',closeWorldPassport);
$('todayQuizNext').addEventListener('click',nextWorldPassportRound);
