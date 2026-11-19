/* The World Passport: a tiny factual quiz, NOT a news article or travel postcard.
 * Trivia is sourced from the public country guides or country-catalog.json.
 * The AI one-liners are clearly marked as original fictional humor. */
'use strict';
const WORLD_PASSPORT_QUIZZES=Object.freeze({
 AR:[
  {question:'イグアスの滝を包む風景は？',options:['熱帯の森','氷の洞窟','砂漠の砂丘'],answer:0,
   photoKey:'ar-iguazu-postcard',photoLabel:'正解の風景｜イグアスの滝と熱帯の森',
   fact:'アルゼンチン北東部のイグアスの滝は、熱帯の森に囲まれています。',
   quip:'水の勢いがすごすぎて、森まで拍手しているように見える。'},
  {question:'アルゼンチンのマテ茶に似合うのは？',options:['車の給油','語らいのひととき','壁のペンキ塗り'],answer:1,
   photoKey:'ar-mate-quiz-image',photoLabel:'正解の文化｜マテ茶の器とボンビージャ',
   fact:'マテ茶はアルゼンチンの日常や人との語らいの中で親しまれています。',
   quip:'どれだけ話が弾んでも、オチまでは淹れてくれない。'}
 ],
 FR:[
  {question:'モン・サン＝ミシェルの景色を変えるのは？',options:['火山の噴火','オーロラ','潮の満ち引き'],answer:2,
   photoKey:'fr-mont-low-tide-quiz-image',photoLabel:'正解の景色｜潮の満ち引きの影響を受ける干潟',
   fact:'ノルマンディーのモン・サン＝ミシェルは、潮の満ち引きで周囲の景色が変わります。',
   quip:'景色の模様替え係は海。毎日、無給で大仕事。'},
  {question:'フランス南部の海岸が面するのは？',options:['地中海','カリブ海','北極海'],answer:0,
   photoKey:'fr-mediterranean-quiz-image',photoLabel:'正解の海｜南フランス・ニースの地中海',
   fact:'フランスは大西洋と地中海の両方に面しています。',
   quip:'北極海でバカンスを始めたら、水着より防寒着が主役。'}
 ],
 US:[
  {question:'サンフランシスコの海峡に架かる橋は？',options:['ロンドン橋','ゴールデンゲートブリッジ','ブルックリン橋'],answer:1,
   photoKey:'us-golden-gate-postcard',photoLabel:'正解の橋｜ゴールデンゲートブリッジ',
   fact:'ゴールデンゲートブリッジは、サンフランシスコの海峡を渡る橋です。',
   quip:'名前はゴールデン、見た目はオレンジ。名乗った瞬間からツッコミ待ち。'},
  {question:'ヨセミテ国立公園の巨大な岩壁で知られる岩石は？',options:['サンゴ','石炭','花崗岩'],answer:2,
   photoKey:'us-yosemite-color-quiz-image',photoLabel:'正解の地形｜ヨセミテの岩壁と谷',
   fact:'ヨセミテには花崗岩の大きな岩壁や谷が広がっています。',
   quip:'地球のプロフィール写真、岩肌の圧が強い。'}
 ]
});
let worldPassportEdition='',worldPassportStamps={},worldPassportActive=null;
let worldPassportLastAwarded='',worldPassportLifetime={};
const WORLD_PASSPORT_LIFETIME_KEY='yoru9-world-passport-lifetime-v1';
function loadWorldPassportLifetime(){
 worldPassportLifetime={};
 try{
  const saved=JSON.parse(localStorage.getItem(WORLD_PASSPORT_LIFETIME_KEY)||'{}');
  if(!saved||typeof saved!=='object'||Array.isArray(saved))return;
  for(const [code,result] of Object.entries(saved)){
   if(/^[A-Z]{2}$/.test(code)&&result&&Number.isInteger(result.score)&&
      Number.isInteger(result.total)&&result.total>=1&&result.total<=2&&
      result.score>=0&&result.score<=result.total){
    worldPassportLifetime[code]={score:result.score,total:result.total};
   }
  }
 }catch(_){}
}
function persistWorldPassportLifetime(){
 try{localStorage.setItem(WORLD_PASSPORT_LIFETIME_KEY,JSON.stringify(worldPassportLifetime))}catch(_){}
}
function rememberWorldPassportCountry(code,score,total){
 const old=worldPassportLifetime[code];
 if(!old||score/total>old.score/old.total||
    (score/total===old.score/old.total&&score>old.score)){
  worldPassportLifetime[code]={score,total};
 }
 persistWorldPassportLifetime();
}
function passportKey(){return 'yoru9-world-passport-v1:'+String(edition.editionDate||'demo')}
function loadWorldPassport(){
 const key=passportKey();
 if(key===worldPassportEdition)return;
 worldPassportEdition=key;worldPassportActive=null;worldPassportStamps={};worldPassportLastAwarded='';
 loadWorldPassportLifetime();
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
function updateWorldPassportBoard(){
 const countries=currentIssueCountries();
 const earned=countries.filter(item=>!!worldPassportStamps[item.code]).length;
 const total=countries.length;
 const board=$('todayPassportBoard');
 board.dataset.complete=String(total>0&&earned===total);
 $('todayPassportCount').textContent=earned+' / '+total;
 const meter=$('todayPassportMeter');
 meter.setAttribute('aria-valuemax',String(total));
 meter.setAttribute('aria-valuenow',String(earned));
 $('todayPassportMeterFill').style.width=(total?Math.round(earned/total*100):0)+'%';
 $('todayPassportMessage').textContent=!total
  ?'掲載国が決まったらスタンプが登場します。'
  :earned===total
   ?'世界パスポート完成！ 全'+total+'か国をめぐりました。'
   :earned===0
    ?'まだ0枚。好きな国のスタンプを押しに行こう！'
    :'スタンプ'+earned+'枚獲得！ あと'+(total-earned)+'か国で完成。';
 $('todayPassportLifetime').textContent='通算訪問国：'+Object.keys(worldPassportLifetime).length+'か国（この端末に保存）';
 const album=$('todayPassportStamps');album.replaceChildren();
 countries.forEach(item=>{
  const result=worldPassportStamps[item.code],completed=!!result;
  const stamp=document.createElement('button');
  stamp.type='button';stamp.className='today-passport-stamp';
  stamp.dataset.countryCode=item.code;
  stamp.dataset.earned=String(completed);
  stamp.dataset.ever=String(!completed&&!!worldPassportLifetime[item.code]);
  stamp.dataset.fresh=String(completed&&worldPassportLastAwarded===item.code);
  stamp.setAttribute('aria-controls','todayCountryQuiz');
  stamp.setAttribute('aria-label',item.name+(completed
   ?'のスタンプ獲得済み。タップで再挑戦'
   :'のスタンプ未獲得。タップでクイズに挑戦'));
  const seal=document.createElement('span');
  seal.className='today-passport-stamp-seal';
  seal.setAttribute('aria-hidden','true');
  seal.textContent=completed?'★':'＋';
  const country=document.createElement('span');
  country.className='today-passport-stamp-country';country.textContent=item.name;
  const status=document.createElement('span');
  status.className='today-passport-stamp-status';
  status.textContent=completed
   ?'獲得済 · '+result.score+'/'+result.total+'問正解'
   :worldPassportLifetime[item.code]?'前の号で訪問済 · 今号に挑戦':'まだ空欄 · 挑戦する';
  stamp.append(seal,country,status);
  stamp.addEventListener('click',()=>startWorldPassport(item));
  album.append(stamp);
 });
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
 updateWorldPassportBoard();
}
function closeWorldPassport(){
 resetWorldPassportPhoto();
 $('todayCountryQuiz').hidden=true;worldPassportActive=null;updateWorldPassportButtons();
}
function startWorldPassport(item){
 loadWorldPassport();
 hideTodayCountryIntro();
 worldPassportActive={item,questions:passportQuizQuestions(item),step:0,score:0,streak:0,answered:false};
 $('todayCountryQuiz').hidden=false;
 renderWorldPassportRound();updateWorldPassportButtons();
 $('todayCountryQuiz').scrollIntoView({block:'nearest'});
}
let passportPhotoTicket=0;
function resetWorldPassportPhoto(){
 passportPhotoTicket++;
 const picture=$('todayQuizPhotoImage');
 picture.onload=null;picture.onerror=null;
 picture.removeAttribute('src');
 $('todayQuizPhotoFigure').hidden=true;
 $('todayQuizPhotoNotice').hidden=true;
 $('todayQuizPhotoNotice').textContent='';
 const dialog=$('todayQuizPhotoDialog');
 if(dialog.open)dialog.close();
}
function showWorldPassportPhotoNotice(message){
 $('todayQuizPhotoFigure').hidden=true;
 $('todayQuizPhotoNotice').textContent=message;
 $('todayQuizPhotoNotice').hidden=false;
}
/* Reuse the release-bundled Wikimedia manifest so captions, authors and license
   links are always tied to the exact image. Never substitute unrelated photos. */
async function revealWorldPassportAnswerPhoto(question){
 const ticket=passportPhotoTicket;
 if(!question.photoKey){
  // Not every country has a vetted answer photograph yet.
  showWorldPassportPhotoNotice('この問題の正解に合う写真は準備中です。解説をお楽しみください。');
  return;
 }
 const run=worldPassportActive,step=run?.step;
 let stop;
 try{
  const manifest=await loadTravelStops();
  stop=manifest?.[question.photoKey];
 }catch(_){stop=null;}
 if(ticket!==passportPhotoTicket||worldPassportActive!==run||
    !run?.answered||run.step!==step)return;
 if(!stop||!/^assets\/travel\/[a-z0-9-]+\.jpg$/.test(stop.photoAsset||'')||
    !String(stop.photo||'').startsWith('https://thumb.wikimedia.org/wikipedia/commons/thumb/')||
    !String(stop.photoPage||'').startsWith('https://commons.wikimedia.org/wiki/File:')||
    !String(stop.licenseUrl||'').startsWith('https://creativecommons.org/')||
    !stop.author||!stop.license||!stop.photoCaption){
  showWorldPassportPhotoNotice('正解写真の出典を確認できませんでした。写真なしで解説を表示します。');
  return;
 }
 const picture=$('todayQuizPhotoImage');
 const label=question.photoLabel||'正解に関する実写真';
 picture.alt=label+'。'+stop.photoCaption;
 $('todayQuizPhotoCaption').textContent=label+'｜'+stop.photoCaption;
 const source=$('todayQuizPhotoSource'),license=$('todayQuizPhotoLicense');
 source.textContent=stop.author;source.href=stop.photoPage;
 license.textContent=stop.license;license.href=stop.licenseUrl;
 let triedFallback=false;
 picture.onload=()=>{
  if(ticket!==passportPhotoTicket||worldPassportActive!==run)return;
  $('todayQuizPhotoNotice').hidden=true;
  $('todayQuizPhotoFigure').hidden=false;
 };
 picture.onerror=()=>{
  if(ticket!==passportPhotoTicket||worldPassportActive!==run)return;
  if(!triedFallback){
   triedFallback=true;picture.src=stop.photo;return;
  }
  showWorldPassportPhotoNotice('正解写真を読み込めませんでした。解説はそのまま読めます。');
 };
 picture.src='./'+stop.photoAsset;
}
function openWorldPassportPhoto(){
 const original=$('todayQuizPhotoImage');
 if($('todayQuizPhotoFigure').hidden||!original.complete||!original.naturalWidth)return;
 const dialog=$('todayQuizPhotoDialog');
 $('todayQuizPhotoLarge').src=original.currentSrc||original.src;
 $('todayQuizPhotoLarge').alt=original.alt;
 $('todayQuizPhotoDialogCaption').textContent=$('todayQuizPhotoCaption').textContent;
 if(typeof dialog.showModal==='function'&&!dialog.open)dialog.showModal();
}
document.getElementById('todayQuizPhotoZoom').addEventListener('click',openWorldPassportPhoto);
document.getElementById('todayQuizPhotoDialogClose').addEventListener('click',()=>{
 const dialog=document.getElementById('todayQuizPhotoDialog');
 if(dialog.open)dialog.close();
});
document.getElementById('todayQuizPhotoDialog').addEventListener('click',event=>{
 if(event.target===event.currentTarget)event.currentTarget.close();
});
function renderWorldPassportRound(){
 const run=worldPassportActive;if(!run)return;
 const q=run.questions[run.step];
 run.answered=false;
 resetWorldPassportPhoto();
 $('todayQuizTitle').textContent=run.item.name+'の「へぇ！」チャレンジ';
 $('todayQuizProgress').textContent='第'+(run.step+1)+'問 / '+run.questions.length+'問 · 景色と文化の3択';
 const stepMeter=$('todayQuizSteps');stepMeter.replaceChildren();
 run.questions.forEach((_,i)=>{
  const dot=document.createElement('span');dot.className='today-quiz-step';
  dot.dataset.step=i<run.step?'done':i===run.step?'current':'waiting';
  dot.setAttribute('aria-label','第'+(i+1)+'問 '+(i<run.step?'回答済み':i===run.step?'回答中':'これから'));
  stepMeter.append(dot);
 });
 $('todayQuizStampReward').hidden=true;
 $('todayQuizStampReward').dataset.new='false';
 $('todayQuizNextCountry').hidden=true;
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
 if(correct){run.score++;run.streak++}else run.streak=0;
 const currentStep=$('todayQuizSteps').children[run.step];
 if(currentStep)currentStep.dataset.step='done';
 $('todayQuizChoices').querySelectorAll('button').forEach((button,index)=>{
  button.disabled=true;
  if(index===question.answer)button.dataset.correct='true';
  if(index===picked&&!correct)button.dataset.pickedWrong='true';
 });
 $('todayQuizVerdict').textContent=correct
  ?'正解！ '+(run.streak>1?run.streak+'問連続正解！':'スタンプに一歩近づいた！')
  :'惜しい！ 正解は「'+question.options[question.answer]+'」。次で挽回しよう！';
 $('todayQuizExplanation').textContent=question.fact;
 $('todayQuizJoke').textContent='AIツッコミ（創作の冗談）：'+question.quip;
 $('todayQuizResult').hidden=false;
 revealWorldPassportAnswerPhoto(question);
 $('todayQuizNext').hidden=false;
 const finished=run.step===run.questions.length-1;
 if(finished){
  const code=run.item.code,previous=worldPassportStamps[code];
  const firstStamp=!previous;
  const newBest=!previous||run.score>previous.score;
  // A stamp represents visiting/completing the country challenge; the score
  // and personal best remain truthful and are never weakened by a replay.
  if(newBest)worldPassportStamps[code]={score:run.score,total:run.questions.length};
  if(firstStamp)worldPassportLastAwarded=code;
  rememberWorldPassportCountry(code,run.score,run.questions.length);
  persistWorldPassport();updateWorldPassportButtons();
  const reward=$('todayQuizStampReward');
  reward.hidden=false;
  reward.dataset.new=String(firstStamp);
  $('todayQuizRewardSeal').textContent='★';
  $('todayQuizRewardTitle').textContent=firstStamp
   ?'スタンプ獲得！ '+run.item.name
   :newBest?'自己ベスト更新！ '+run.item.name:'スタンプ確認！ '+run.item.name;
  $('todayQuizRewardText').textContent=run.score===run.questions.length
   ?'全問正解！ '+run.score+'/'+run.questions.length+'問。今日の世界をよく知りました。'
   :'今回'+run.score+'/'+run.questions.length+'問正解。クイズ完走の記念スタンプです。';
  const remaining=currentIssueCountries().filter(item=>!worldPassportStamps[item.code]);
  $('todayQuizNextCountry').hidden=remaining.length===0;
  if(remaining.length){
   $('todayQuizNextCountry').textContent='次は'+remaining[0].name+'へ →';
  }
 }
 $('todayQuizNext').textContent=finished?'もう一度挑戦する ↻':'次の問題へ →';
}
function nextWorldPassportRound(){
 const run=worldPassportActive;
 if(!run||!run.answered)return;
 if(run.step===run.questions.length-1){run.step=0;run.score=0;run.streak=0}
 else run.step++;
 renderWorldPassportRound();
}
document.getElementById('todayQuizClose').addEventListener('click',closeWorldPassport);
document.getElementById('todayQuizNext').addEventListener('click',nextWorldPassportRound);
document.getElementById('todayQuizNextCountry').addEventListener('click',()=>{
 if(!worldPassportActive?.answered)return;
 const remaining=currentIssueCountries().filter(item=>!worldPassportStamps[item.code]);
 if(remaining.length)startWorldPassport(remaining[0]);
});
