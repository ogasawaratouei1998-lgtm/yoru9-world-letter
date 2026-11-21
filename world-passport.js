/* The Country Quiz: a factual, optional 3-choice journey through the countries
 * in the approved news issue. No stamp book, scoring archive, collection state,
 * per-country rewards or user progress storage. Quiz photos retain their
 * licensed sources and are disclosed only after answering. */
'use strict';
const WORLD_PASSPORT_QUIZZES=Object.freeze({
 IT:[
  {question:'ピサの斜塔が建っているのは、イタリアのどの都市？',
   options:['ピサ','ローマ','ミラノ'],answer:0,
   photoKey:'italy-pisa-tower-postcard',photoLabel:'正解の建築｜ピサの斜塔',
   fact:'ピサの斜塔は、トスカーナ州ピサにある大聖堂の鐘楼です。',
   quip:'斜めに立っても、長年しっかり観光の主役。'},
  {question:'ヴェネツィアの街を象徴する大きな水路は？',
   options:['ライン川','大運河','テムズ川'],answer:1,
   photoKey:'italy-venice-grand-canal-postcard',photoLabel:'正解の水景｜ヴェネツィアの大運河',
   fact:'ヴェネツィアの大運河は歴史的な建物に沿って流れ、街の水上交通を支えています。',
   quip:'道路を探すより、舟を探したほうが早い日もある。'}
 ],
 DE:[
  {question:'ライン川沿いで、二つの大きな塔の大聖堂が知られる都市は？',
   options:['ベルリン','ミュンヘン','ケルン'],answer:2,
   photoKey:'germany-cologne-cathedral-postcard',photoLabel:'正解の建築｜ケルン大聖堂',
   fact:'ケルン大聖堂はライン川沿いの都市ケルンにあるゴシック様式の大聖堂です。',
   quip:'塔が高すぎて、街のランドマークが自己主張を忘れない。'},
  {question:'ノイシュヴァンシュタイン城があるドイツの州は？',
   options:['バイエルン州','ブランデンブルク州','ヘッセン州'],answer:0,
   photoKey:'germany-neuschwanstein-castle-postcard',photoLabel:'正解の城｜ノイシュヴァンシュタイン城',
   fact:'ノイシュヴァンシュタイン城は、ドイツ南部バイエルン州にある19世紀の城です。',
   quip:'絵本のような城だけれど、背景は本物のアルプス山麓。'}
 ],
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
 BR:[
  {question:'写真に写るサンパウロの有名な大通りは？',options:['アヴェニーダ・パウリスタ','シャンゼリゼ通り','フィフス・アベニュー'],answer:0,photoKey:'brazil-paulista-quiz-image',photoLabel:'正解の通り｜サンパウロ・アヴェニーダ・パウリスタ',fact:'アヴェニーダ・パウリスタはサンパウロの文化施設が集まる通りで、MASPなどが並びます。',quip:'通りを歩けば美術館が次々登場。散歩が文化祭になりそう。'},
  {question:'ブラジル側から撮影したこの滝は何という？',options:['エンジェルフォール','イグアスの滝','ヴィクトリアの滝'],answer:1,photoKey:'brazil-iguacu-panorama-quiz-image',photoLabel:'正解の滝｜ブラジル側から見たイグアスの滝',fact:'イグアスの滝はブラジルとアルゼンチンにまたがり、ブラジル側のイグアス国立公園は1986年にUNESCO世界遺産へ登録されました。',quip:'国境より目立つのは水しぶき。滝の迫力に地図が負ける。'},
 ],
 ES:[
  {question:'サグラダ・ファミリアが建つ都市は？',options:['マドリード','バルセロナ','セビリア'],answer:1,photoKey:'spain-sagrada-nativity-quiz-image',photoLabel:'正解の建築｜バルセロナのサグラダ・ファミリア・生誕のファサード',fact:'サグラダ・ファミリアの「生誕のファサード」と地下聖堂は、ガウディ作品群としてUNESCO世界遺産に登録されています。',quip:'塔だけじゃない。外壁の細工まで観光案内の主役級。'},
  {question:'写真のアルハンブラ宮殿がある都市は？',options:['グラナダ','バルセロナ','バレンシア'],answer:0,photoKey:'spain-alhambra-quiz-image',photoLabel:'正解の宮殿｜アンダルシアのグラナダ・アルハンブラ宮殿',fact:'アルハンブラ宮殿はグラナダにあり、ヘネラリフェとアルバイシン地区とともに世界遺産に登録されています。',quip:'城壁の奥まで歴史ぎっしり。地図の答えはグラナダ。'},
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
 KR:[
  {question:'石段と石塔で知られる、慶州の世界遺産の寺は？',options:['仏国寺','景福宮','海印寺'],answer:0,photoKey:'korea-bulguksa-quiz-image',photoLabel:'正解の寺院｜慶州・仏国寺',fact:'仏国寺は新羅時代の仏教建築を伝える寺で、石窟庵とともにUNESCO世界遺産に登録されています。',quip:'階段の先まで文化財。登る前から歴史が濃い。'},
  {question:'済州島の城山日出峰を形づくったのは何？',options:['サンゴ礁','人工の盛り土','火山の噴出'],answer:2,photoKey:'korea-seongsan-quiz-image',photoLabel:'正解の地形｜済州島・城山日出峰',fact:'城山日出峰は火山活動で生まれた凝灰丘で、済州島の火山地形の一部として世界自然遺産に登録されています。',quip:'海のそばの巨大な山。正体は火山の作品。'},
 ],
 NZ:[
  {question:'ピオピオタヒ／ミルフォード・サウンドがある島は？',options:['北島','南島','チャタム諸島'],answer:1,photoKey:'nz-milford-fiord-quiz-image',photoLabel:'正解の景色｜南島のミルフォード・サウンド',fact:'ミルフォード・サウンドはニュージーランド南島、フィヨルドランド国立公園の北西部にあるフィヨルドです。',quip:'山が水面まで迫ってくる。地図の答えは南島。'},
  {question:'ニュージーランドで最も高い山は？',options:['ルアペフ山','タラナキ山','アオラキ／マウント・クック'],answer:2,photoKey:'nz-aoraki-quiz-image',photoLabel:'正解の山｜南島・アオラキ／マウント・クック',fact:'アオラキ／マウント・クックはニュージーランドの最高峰で、同名の国立公園に位置します。',quip:'最高峰の答えは、山の名前からして存在感たっぷり。'},
 ],

});

let worldPassportActive=null;
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

function updateWorldPassportButtons(){
 document.querySelectorAll('#todayMapLegend .today-map-country').forEach(button=>{
  button.textContent=button.dataset.countryLabel+' · クイズ';
  button.setAttribute('aria-expanded',String(worldPassportActive?.item.code===button.dataset.countryCode));
  button.setAttribute('aria-label',button.dataset.countryName+'の3択クイズに挑戦');
 });
}
function closeWorldPassport(){
 resetWorldPassportPhoto();
 $('todayCountryQuiz').hidden=true;
 worldPassportActive=null;
 updateWorldPassportButtons();
}
function focusWorldPassportQuestion(run){
 const reposition=()=>{
  if(worldPassportActive!==run||$('todayCountryQuiz').hidden)return;
  const question=$('todayQuizQuestion');
  if(typeof question.focus==='function')question.focus({preventScroll:true});
  $('todayCountryQuiz').scrollIntoView({block:'start',behavior:'auto'});
 };
 if(typeof requestAnimationFrame==='function')requestAnimationFrame(reposition);
 else reposition();
}
function startWorldPassport(item){
 hideTodayCountryIntro();
 const questions=passportQuizQuestions(item);
 worldPassportActive={item,questions,step:0,streak:0,answered:false};
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
 $('todayQuizTitle').textContent=run.item.name+'の「へぇ！」クイズ';
 $('todayQuizProgress').textContent='第'+(run.step+1)+'問 / '+run.questions.length+'問 · 景色と文化の3択';
 const steps=$('todayQuizSteps');steps.replaceChildren();
 run.questions.forEach((_,i)=>{
  const bar=document.createElement('span');bar.className='today-quiz-step';
  bar.dataset.step=i<run.step?'done':i===run.step?'current':'waiting';
  bar.setAttribute('aria-label','第'+(i+1)+'問');
  steps.append(bar);
 });
 $('todayQuizCorrectFlash').hidden=true;
 $('todayQuizResult').hidden=true;
 $('todayQuizNext').hidden=true;
 $('todayQuizQuestion').textContent=q.question;
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
 run.answered=true;
 const correct=picked===question.answer;
 if(correct)run.streak++;else run.streak=0;
 const mark=$('todayQuizSteps').children[run.step];
 if(mark)mark.dataset.step='done';
 $('todayQuizChoices').querySelectorAll('button').forEach((button,index)=>{
  button.disabled=true;
  if(index===question.answer)button.dataset.correct='true';
  if(index===picked&&!correct)button.dataset.pickedWrong='true';
 });
 if(correct)celebrateWorldPassportCorrect($('todayQuizChoices').querySelectorAll('button')[picked],run.streak);
 $('todayQuizVerdict').textContent=correct
  ?'正解！ '+(run.streak>1?run.streak+'問連続正解！':'その通り！')
  :'惜しい！ 正解は「'+question.options[question.answer]+'」。';
 $('todayQuizExplanation').textContent=question.fact;
 $('todayQuizJoke').textContent='AIツッコミ（創作の冗談）：'+question.quip;
 $('todayQuizResult').hidden=false;
 revealWorldPassportAnswerPhoto(question);
 const next=$('todayQuizNext');
 next.textContent=run.step<run.questions.length-1?'次の問題へ →':'閉じる';
 next.hidden=false;
}
function finishWorldPassport(){
 const run=worldPassportActive;
 if(!run||!run.answered)return;
 if(run.step<run.questions.length-1){
  run.step++;
  renderWorldPassportRound();
  focusWorldPassportQuestion(run);
 }else{
  closeWorldPassport();
  const legend=$('todayMapLegend');
  if(legend&&typeof legend.scrollIntoView==='function')
   legend.scrollIntoView({block:'nearest',behavior:'auto'});
 }
}
document.getElementById('todayQuizClose').addEventListener('click',closeWorldPassport);
document.getElementById('todayQuizNext').addEventListener('click',finishWorldPassport);
