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
 ],
 GB:[
  {question:'ロンドンのタワーブリッジが架かる川は？',options:['セーヌ川','テムズ川','ドナウ川'],answer:1,
   photoKey:'uk-towerbridge-postcard',photoLabel:'正解の橋｜ロンドンのタワーブリッジとテムズ川',
   fact:'タワーブリッジはロンドンのテムズ川に架かる橋です。',
   quip:'名前はタワー、流れるのはテムズ。川にも自己紹介の出番を。'},
  {question:'エディンバラ城があるのはイギリスのどの地域？',options:['ウェールズ','イングランド','スコットランド'],answer:2,
   photoKey:'uk-country-postcard',photoLabel:'正解の城｜スコットランドのエディンバラ城',
   fact:'エディンバラはスコットランドの首都で、エディンバラ城は街の象徴です。',
   quip:'高台の城が街を見守る。写真の撮影枚数までは数えきれない。'}
 ],
 ES:[
  {question:'サグラダ・ファミリアがあるスペインの都市は？',options:['マドリード','バルセロナ','セビリア'],answer:1,
   photoKey:'spain-barcelona-postcard',photoLabel:'正解の建築｜バルセロナのサグラダ・ファミリア',
   fact:'サグラダ・ファミリアはバルセロナにあるガウディゆかりの聖堂です。',
   quip:'街の名刺代わりが世界級の建築。自己紹介のスケールが大きい。'},
  {question:'スペインの「タパス」とは、一般に何のこと？',options:['小皿料理','伝統的な船','夜行列車'],answer:0,
   fact:'タパスとはスペインのバルなどで親しまれる小皿料理やおつまみです。',
   quip:'料理は小皿でも、会話は特大サイズになりがち。'}
 ],
 JP:[
  {question:'富士山がまたがる2つの県は？',options:['長野県と岐阜県','京都府と滋賀県','山梨県と静岡県'],answer:2,
   photoKey:'japan-fuji-postcard',photoLabel:'正解の山｜山梨県・静岡県にまたがる富士山',
   fact:'富士山は山梨県と静岡県にまたがる日本で最も高い山です。',
   quip:'存在感が大きすぎて二つの県にまたがってしまった。'},
  {question:'東京・浅草の浅草寺があるのはどこ？',options:['京都府','東京都','奈良県'],answer:1,
   photoKey:'japan-country-postcard',photoLabel:'正解の寺院｜東京・浅草寺',
   fact:'浅草寺は東京都台東区浅草にあり、雷門などで知られています。',
   quip:'雷門は人気者。記念写真の行列まで名物になりそう。'}
 ],
 NZ:[
  {question:'ミルフォード・サウンドがあるのは？',options:['北島','南島','チャタム諸島'],answer:1,
   photoKey:'nz-milford-sound-postcard',photoLabel:'正解の景色｜南島のミルフォード・サウンド',
   fact:'ミルフォード・サウンドはニュージーランド南島のフィヨルドランド国立公園にあります。',
   quip:'山と海の共演が大迫力。観客は静かに見上げるしかない。'},
  {question:'ニュージーランドの先住民族として知られるのは？',options:['サーミ','イヌイット','マオリ'],answer:2,
   fact:'マオリはニュージーランドの先住民族で、言葉や芸術などの文化を受け継いでいます。',
   quip:'文化の積み重ねは、世界地図のピンだけでは収まりません。'}
 ]

});
let worldPassportEdition='',worldPassportStamps={},worldPassportProgress={},worldPassportActive=null;
let worldPassportLastAwarded='',worldPassportLifetime={},worldPassportJustCompleted=false;
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
function passportProgressKey(){return passportKey()+':unanswered-next-v1'}
function persistWorldPassportProgress(){
 try{localStorage.setItem(passportProgressKey(),JSON.stringify(worldPassportProgress))}catch(_){}
}
function recordWorldPassportNextQuestion(run){
 // Keep the next question ready when the revealed answer is closed.
 if(run.step>=run.questions.length-1)return;
 worldPassportProgress[run.item.code]={step:run.step+1,score:run.score,streak:run.streak};
 persistWorldPassportProgress();
}
function loadWorldPassport(){
 const key=passportKey();
 if(key===worldPassportEdition)return;
 worldPassportEdition=key;worldPassportActive=null;worldPassportStamps={};worldPassportProgress={};worldPassportLastAwarded='';worldPassportJustCompleted=false;
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
 // An answered question can be closed without throwing away the unfinished
 // country's earned score, even after a reload on the same daily edition.
 try{
  const saved=JSON.parse(localStorage.getItem(passportProgressKey())||'{}');
  if(saved&&typeof saved==='object'&&!Array.isArray(saved)){
   for(const [code,result] of Object.entries(saved)){
    const max=Array.isArray(WORLD_PASSPORT_QUIZZES[code])?WORLD_PASSPORT_QUIZZES[code].length:1;
    if(/^[A-Z]{2}$/.test(code)&&!worldPassportStamps[code]&&
       Number.isInteger(result?.step)&&result.step>=1&&result.step<max&&
       Number.isInteger(result.score)&&result.score>=0&&result.score<=result.step&&
       Number.isInteger(result.streak)&&result.streak>=0&&result.streak<=result.score){
     worldPassportProgress[code]={step:result.step,score:result.score,streak:result.streak};
    }
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
function worldPassportGrade(score,total){
 return score===total?'gold':score>0?'silver':'bronze';
}
function worldPassportGradeLabel(score,total){
 return score===total?'ゴールド':score>0?'シルバー':'チャレンジ';
}
function updateWorldPassportBoard(){
 const countries=currentIssueCountries();
 const earned=countries.filter(item=>!!worldPassportStamps[item.code]).length;
 const total=countries.length;
 const board=$('todayPassportBoard');
 board.dataset.complete=String(total>0&&earned===total);
 board.dataset.celebrate=String(worldPassportJustCompleted&&total>0&&earned===total);
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
  const partial=!completed&&worldPassportProgress[item.code];
  const stamp=document.createElement('button');
  stamp.type='button';stamp.className='today-passport-stamp';
  stamp.dataset.countryCode=item.code;
  stamp.dataset.earned=String(completed);
  stamp.dataset.grade=completed?worldPassportGrade(result.score,result.total):'none';
  stamp.dataset.ever=String(!completed&&!!worldPassportLifetime[item.code]);
  stamp.dataset.fresh=String(completed&&worldPassportLastAwarded===item.code);
  stamp.setAttribute('aria-controls','todayCountryQuiz');
  stamp.setAttribute('aria-label',item.name+(completed
   ?'のスタンプ獲得済み。タップで再挑戦'
   :partial?'の続きのクイズを再開':'のスタンプ未獲得。タップでクイズに挑戦'));
  const seal=document.createElement('span');
  seal.className='today-passport-stamp-seal';
  seal.setAttribute('aria-hidden','true');
  seal.textContent=completed?'★':'＋';
  const country=document.createElement('span');
  country.className='today-passport-stamp-country';country.textContent=item.name;
  const status=document.createElement('span');
  status.className='today-passport-stamp-status';
  status.textContent=completed
   ?'★ '+worldPassportGradeLabel(result.score,result.total)+' · '+result.score+'/'+result.total+'問正解'
   :partial?'第'+(partial.step+1)+'問から再開':worldPassportLifetime[item.code]?'前の号で訪問済 · 今号に挑戦':'まだ空欄 · 挑戦する';
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
function focusWorldPassportQuestion(run){
 // The answer explanation/photo may be much taller than the next question.
 // After replacing it, reset the viewport: otherwise iOS scroll anchoring can
 // leave the visitor at the following "今日のひと言" footer.
 const reposition=()=>{
  if(worldPassportActive!==run||$('todayCountryQuiz').hidden)return;
  const question=$('todayQuizQuestion');
  if(typeof question.focus==='function')question.focus({preventScroll:true});
  $('todayCountryQuiz').scrollIntoView({block:'start',behavior:'auto'});
 };
 // Let the browser finish laying out the newly shortened quiz first.
 if(typeof requestAnimationFrame==='function')requestAnimationFrame(reposition);
 else reposition();
}
function startWorldPassport(item){
 loadWorldPassport();
 hideTodayCountryIntro();
 const questions=passportQuizQuestions(item);
 const saved=!worldPassportStamps[item.code]&&worldPassportProgress[item.code];
 const resume=saved&&saved.step<questions.length?saved:null;
 worldPassportActive={item,questions,step:resume?resume.step:0,
  score:resume?resume.score:0,streak:resume?resume.streak:0,answered:false};
 $('todayCountryQuiz').hidden=false;
 renderWorldPassportRound();updateWorldPassportButtons();
 focusWorldPassportQuestion(worldPassportActive);
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
/* Each correctly selected answer earns a separate burst, before any country stamp.
   Decorations are aria-hidden, use no sound, and never intercept pointer events. */
function celebrateWorldPassportCorrect(button,streak){
 if(!button)return;
 button.dataset.popped='true';
 const burst=document.createElement('span');
 burst.className='quiz-answer-sparks';
 burst.dataset.active='true';
 burst.setAttribute('aria-hidden','true');
 const shapes=['✦','★','✧','✦','◆','★','✧','✦','★','✧'];
 for(const shape of shapes){
  const particle=document.createElement('span');
  particle.textContent=shape;
  burst.append(particle);
 }
 button.append(burst);
 const flash=$('todayQuizCorrectFlash');
 flash.hidden=false;
 $('todayQuizCorrectFlashLabel').textContent=streak>1
  ?streak+'連続正解！':'正解！ キラッとひらめいた！';
}
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
 $('todayQuizStampReward').dataset.perfect='false';
 $('todayQuizCorrectFlash').hidden=true;
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
 if(correct)celebrateWorldPassportCorrect($('todayQuizChoices').querySelectorAll('button')[picked],run.streak);
 $('todayQuizVerdict').textContent=correct
  ?'正解！ '+(run.streak>1?run.streak+'問連続正解！':'スタンプに一歩近づいた！')
  :'惜しい！ 正解は「'+question.options[question.answer]+'」。答えを確認したら閉じられます。';
 $('todayQuizExplanation').textContent=question.fact;
 $('todayQuizJoke').textContent='AIツッコミ（創作の冗談）：'+question.quip;
 $('todayQuizResult').hidden=false;
 revealWorldPassportAnswerPhoto(question);
 $('todayQuizNext').hidden=false;
 const finished=run.step===run.questions.length-1;
 if(!finished){recordWorldPassportNextQuestion(run);updateWorldPassportButtons()}
 if(finished){
  const code=run.item.code,previous=worldPassportStamps[code];
  if(worldPassportProgress[code]){delete worldPassportProgress[code];persistWorldPassportProgress()}
  const firstStamp=!previous;
  const newBest=!previous||run.score>previous.score;
  // A stamp represents visiting/completing the country challenge; the score
  // and personal best remain truthful and are never weakened by a replay.
  const missingBefore=currentIssueCountries().filter(item=>!worldPassportStamps[item.code]);
  if(newBest)worldPassportStamps[code]={score:run.score,total:run.questions.length};
  if(firstStamp)worldPassportLastAwarded=code;
  worldPassportJustCompleted=firstStamp&&missingBefore.length===1&&missingBefore[0].code===code;
  rememberWorldPassportCountry(code,run.score,run.questions.length);
  persistWorldPassport();updateWorldPassportButtons();
  const reward=$('todayQuizStampReward');
  reward.hidden=false;
  reward.dataset.new=String(firstStamp);
  reward.dataset.grade=worldPassportGrade(run.score,run.questions.length);
  reward.dataset.perfect=String(run.score===run.questions.length);
  $('todayQuizRewardSeal').textContent='★';
  $('todayQuizRewardTitle').textContent=firstStamp
   ?worldPassportGradeLabel(run.score,run.questions.length)+'スタンプ獲得！ '+run.item.name
   :newBest?'自己ベスト更新！ '+run.item.name:'スタンプ確認！ '+run.item.name;
  $('todayQuizRewardText').textContent=run.score===run.questions.length
   ?'全問正解！ '+run.score+'/'+run.questions.length+'問。今日の世界をよく知りました。'
   :'今回'+run.score+'/'+run.questions.length+'問正解。クイズ完走の記念スタンプです。';
 }
 // The answer is already shown; this button only closes the quiz.
 $('todayQuizNext').textContent='閉じる';
}
function finishWorldPassport(){
 closeWorldPassport();
 const showAlbum=()=>{
  const heading=$('todayPassportHeading');
  if(typeof heading.focus==='function')heading.focus({preventScroll:true});
  $('todayPassportBoard').scrollIntoView({block:'start',behavior:'auto'});
 };
 if(typeof requestAnimationFrame==='function')requestAnimationFrame(showAlbum);
 else showAlbum();
}
document.getElementById('todayQuizClose').addEventListener('click',closeWorldPassport);
document.getElementById('todayQuizNext').addEventListener('click',finishWorldPassport);
