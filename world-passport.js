/* The Country Quiz: a factual, optional 3-choice journey through the countries
 * in the approved news issue. No stamp book, scoring archive, collection state,
 * per-country rewards or user progress storage. Quiz photos retain their
 * licensed sources and are disclosed only after answering. */
'use strict';
const WORLD_PASSPORT_QUIZZES=Object.freeze({
 AR:[
  {question:'イグアスの滝を包む風景は？',options:['熱帯の森','氷の洞窟','砂漠の砂丘'],answer:0,photoKey:'ar-iguazu-postcard',photoLabel:'正解の風景｜イグアスの滝と熱帯の森',fact:'アルゼンチン北東部のイグアスの滝は、熱帯の森に囲まれています。',quip:'水の勢いがすごすぎて、森まで拍手しているように見える。'},
  {question:'アルゼンチンのマテ茶に似合うのは？',options:['車の給油','語らいのひととき','壁のペンキ塗り'],answer:1,photoKey:'ar-mate-quiz-image',photoLabel:'正解の文化｜マテ茶の器とボンビージャ',fact:'マテ茶はアルゼンチンの日常や人との語らいの中で親しまれています。',quip:'どれだけ話が弾んでも、オチまでは淹れてくれない。'},
 ],
 AG:[
  {question:'アンティグア島のベティーズ・ホープに残る風車は、かつて何に使われた？',options:['サトウキビを搾る作業','港に船を導く灯台','天体を観測する施設'],answer:0,photoKey:'antigua-bettys-hope-quiz-image',photoLabel:'正解の遺構｜ベティーズ・ホープの製糖風車',fact:'ベティーズ・ホープは砂糖プランテーションの跡地で、風車はサトウキビを搾る施設でした。そこでは奴隷にされた人々が労働を強いられた歴史も伝えられています。',quip:'丸い石塔は飾りじゃない。風の力まで製糖に動員していた。'},
  {question:'アンティグア島の自然の石橋『デビルズ・ブリッジ』を削り出したのは？',options:['船で運んだ石材','大西洋の波の浸食','火山から流れた溶岩'],answer:1,photoKey:'antigua-devils-bridge-quiz-image',photoLabel:'正解の自然景観｜アンティグア島・デビルズ・ブリッジ',fact:'デビルズ・ブリッジはアンティグア島東部にある石灰岩の自然のアーチ。大西洋の波が長い年月をかけて形をつくりました。',quip:'橋を設計したのは人間じゃなく、休みなく押し寄せる波。'},
 ],
 AU:[
  {question:'シドニー・オペラハウスが世界文化遺産に登録された年は？',options:['1973年','2007年','1981年'],answer:1,photoKey:'au-opera-house-postcard',photoLabel:'正解写真｜シドニー・オペラハウス',fact:'UNESCOの世界遺産一覧では、シドニー・オペラハウスの登録年は2007年とされています。',quip:'屋根は帆の形。でも舞台は海上ではなく、ちゃんと劇場の中。'},
  {question:'グレートバリアリーフが世界自然遺産に登録された年は？',options:['1981年','2007年','1999年'],answer:0,photoKey:'au-great-barrier-reef-postcard',photoLabel:'正解写真｜グレートバリアリーフ',fact:'UNESCOはグレートバリアリーフを1981年に世界自然遺産として登録しています。',quip:'青い海の中は大にぎわい。サンゴが街の主役になっている。'},
 ],
 AT:[
  {question:'シェーンブルン宮殿がある都市は？',options:['ウィーン','ザルツブルク','インスブルック'],answer:0,photoLabel:'正解写真｜シェーンブルン宮殿と庭園',fact:'シェーンブルン宮殿と庭園はウィーンにある世界文化遺産です。',quip:'宮殿の主役は建物だけじゃない。庭まで揃えて一つの舞台。',photoKey:'at-schoenbrunn-palace-postcard'},
  {question:'ザルツブルク旧市街の発展に深く関わったのは？',options:['大司教を中心とする宗教都市','海軍の造船都市','砂漠の交易都市'],answer:0,photoLabel:'正解写真｜ザルツブルク旧市街',fact:'UNESCOはザルツブルクの大司教領としての歴史的な都市景観を評価しています。',quip:'旧市街では道を曲がるたび、街が歴史の続きを語り出す。',photoKey:'at-salzburg-old-town-postcard'},
 ],
 BE:[
  {question:'グラン・プラスが示すブリュッセルの歴史的役割は？',options:['商業都市','砂漠の交易隊の宿営地','高山の観測基地'],answer:0,photoLabel:'正解写真｜ブリュッセルのグラン・プラス',fact:'UNESCOはグラン・プラスを商業都市として栄えたブリュッセルの象徴として説明しています。',quip:'商業都市の繁栄は広場に刻まれた。建物の装飾まで、宣伝上手。',photoKey:'be-grand-place-postcard'},
  {question:'ブルッヘの歴史都市景観に特徴的なのは？',options:['運河と歴史的街路','砂丘の連続','火山の溶岩流'],answer:0,photoLabel:'正解写真｜ブルッヘ歴史地区',fact:'UNESCOは中世以来の都市のかたちが残るブルッヘ歴史地区を評価しています。',quip:'運河は観光用の飾りじゃない。昔は荷物も暮らしも、この水路を使っていた。',photoKey:'be-bruges-belfry-postcard'},
 ],
 BG:[
  {question:'リラ修道院の周囲に広がる特徴的な環境は？',options:['山地','珊瑚礁','砂漠のオアシス'],answer:0,fact:'リラ修道院はブルガリアのリラ山地に位置する歴史的な修道院です。',photoLabel:'正解写真｜リラ修道院の回廊',quip:'山奥なのにこの存在感。隠れた修道院とはとても言えない。',photoKey:'bg-rila-monastery-postcard'},
  {question:'ボヤナ教会で評価されている重要な芸術は？',options:['中世の壁画','近代映画のセット','巨大な機械彫刻'],answer:0,fact:'UNESCOはボヤナ教会の中世の壁画を重要な文化的価値として紹介しています。',photoLabel:'正解写真｜ソフィア郊外のボヤナ教会',quip:'建物は小さくても、壁画の歴史は大作。見落とすには惜しい。',photoKey:'bg-boyana-church-postcard'},
 ],
 BA:[
  {question:'モスタルの古橋が現在伝える象徴的な意味は？',options:['氷河の観測','再建と和解・国際協力','新しい宇宙船の発射'],answer:1,fact:'UNESCOは再建された古橋を和解、国際協力、多様な共同体の共存の象徴と位置付けています。',photoLabel:'正解写真｜モスタル旧市街の古橋',quip:'橋の価値は石の量だけでは測れない。壊されたものを再びつなぐには、設計図だけでは足りなかった。',photoKey:'ba-mostar-night-postcard'},
  {question:'ヴィシェグラードの石橋が渡る川は？',options:['ナイル川','テムズ川','ドリナ川'],answer:2,fact:'UNESCOはメフメド・パシャ・ソコロヴィッチ橋がドリナ川に架かると説明しています。',photoLabel:'正解写真｜メフメド・パシャ・ソコロヴィッチ橋',quip:'十一のアーチが川を渡す。橋の美しさと土木の合理性が、同じ設計で成立している。',photoKey:'ba-visegrad-bridge-postcard'},
 ],
 BR:[
  {question:'写真に写るサンパウロの有名な大通りは？',options:['アヴェニーダ・パウリスタ','シャンゼリゼ通り','フィフス・アベニュー'],answer:0,photoKey:'brazil-paulista-quiz-image',photoLabel:'正解の通り｜サンパウロ・アヴェニーダ・パウリスタ',fact:'アヴェニーダ・パウリスタはサンパウロの文化施設が集まる通りで、MASPなどが並びます。',quip:'通りを歩けば美術館が次々登場。散歩が文化祭になりそう。'},
  {question:'ブラジル側から撮影したこの滝は何という？',options:['エンジェルフォール','イグアスの滝','ヴィクトリアの滝'],answer:1,photoKey:'brazil-iguacu-brazil-side-quiz-image',photoLabel:'正解の滝｜ブラジル側から見たイグアスの滝',fact:'イグアスの滝はブラジルとアルゼンチンにまたがり、ブラジル側のイグアス国立公園は1986年にUNESCO世界遺産へ登録されました。',quip:'国境より目立つのは水しぶき。滝の迫力に地図が負ける。'},
 ],
 CA:[
  {question:'ケベック旧市街の歴史地区が世界文化遺産に登録された年は？',options:['2007年','1985年','1950年'],answer:1,photoKey:'ca-old-quebec-postcard',photoLabel:'正解写真｜ケベック旧市街',fact:'ケベック旧市街の歴史地区は1985年に世界文化遺産へ登録されました。',quip:'城壁の街。いまは観光客のカメラがあちこちに陣取っている。'},
  {question:'カナダで最初の国立公園として知られる場所は？',options:['バンフ国立公園','ヨセミテ国立公園','フィヨルドランド国立公園'],answer:0,photoKey:'ca-banff-lake-louise-postcard',photoLabel:'正解写真｜バンフ国立公園',fact:'1885年に始まったバンフは、カナダで最初の国立公園として公園局に紹介されています。',quip:'カナダで最初の国立公園。絶景にも歴史にも先輩の貫禄。'},
 ],
 CH:[
  {question:'ベルン旧市街が世界文化遺産に登録された年は？',options:['1983年','2001年','2015年'],answer:0,photoLabel:'正解写真｜ベルン旧市街',fact:'UNESCO世界遺産センターによると、ベルン旧市街は1983年に登録されました。',quip:'時計を見上げる街でも、歴史の時間はずっと長い。',photoKey:'ch-bern-old-city-postcard'},
  {question:'ユングフラウ＝アレッチの世界自然遺産への初回登録年は？',options:['1983年','2001年','2020年'],answer:1,photoLabel:'正解写真｜アレッチ氷河',fact:'UNESCOによれば同地域は2001年に世界自然遺産に初登録され、2007年に拡張されました。',quip:'氷の流れはゆっくり。でも残した地形はとびきり大きい。',photoKey:'ch-aletsch-glacier-postcard'},
 ],
 CY:[
  {question:'ネア・パフォスの芸術遺産として知られるものは？',options:['モザイク','氷の彫刻','鋳鉄の高層塔'],answer:0,fact:'ネア・パフォスには古代のモザイクが残っています。',photoLabel:'正解写真｜パフォス・ディオニュソスの館',quip:'床に絵を描くために小石を並べた古代の職人。画素数を競うずっと前から、細部の表現にはこだわっていた。',photoKey:'cy-paphos-mosaic-postcard'},
  {question:'トロードス地方の教会群が特に伝える芸術は？',options:['近代の映画撮影','ビザンツ系の壁画','海底の彫刻'],answer:1,fact:'十件の教会・修道院の壁画がビザンツ美術などの変化を伝えます。',photoLabel:'正解写真｜トロードス地方・アシヌ教会',quip:'小さな教会だからこそ壁画に目が向く。建物の規模と芸術の価値は比例しない。',photoKey:'cy-asinou-fresco-postcard'},
 ],
 CZ:[
  {question:'プラハ歴史地区を流れる川は？',options:['ヴルタヴァ川','ナイル川','テムズ川'],answer:0,photoLabel:'正解写真｜プラハ歴史地区',fact:'プラハの歴史地区はヴルタヴァ川の両岸に広がっています。',quip:'橋を渡るだけで、プラハの歴史が川の両岸に広がる。',photoKey:'cz-charles-bridge-postcard'},
  {question:'チェスキー・クルムロフの旧市街を大きく囲む地形は？',options:['川の曲流','火山の噴火口','砂丘の列'],answer:0,photoLabel:'正解写真｜チェスキー・クルムロフ歴史地区',fact:'ヴルタヴァ川の曲流と城、旧市街が特徴的な景観をつくっています。',quip:'城下町を囲むのは城壁だけじゃない。川の曲がり方まで絵になる。',photoKey:'cz-cesky-krumlov-postcard'},
 ],
 DE:[
  {question:'ライン川沿いで、二つの大きな塔の大聖堂が知られる都市は？',options:['ベルリン','ミュンヘン','ケルン'],answer:2,photoKey:'germany-cologne-cathedral-postcard',photoLabel:'正解の建築｜ケルン大聖堂',fact:'ケルン大聖堂はライン川沿いの都市ケルンにあるゴシック様式の大聖堂です。',quip:'塔が高すぎて、街のランドマークが自己主張を忘れない。'},
  {question:'ノイシュヴァンシュタイン城があるドイツの州は？',options:['バイエルン州','ブランデンブルク州','ヘッセン州'],answer:0,photoKey:'germany-neuschwanstein-castle-postcard',photoLabel:'正解の城｜ノイシュヴァンシュタイン城',fact:'ノイシュヴァンシュタイン城は、ドイツ南部バイエルン州にある19世紀の城です。',quip:'絵本のような城だけれど、背景は本物のアルプス山麓。'},
 ],
 DK:[
  {question:'クロンボー城が見下ろす重要な海峡は？',options:['エーレスンド海峡','ジブラルタル海峡','マラッカ海峡'],answer:0,fact:'UNESCOはクロンボー城がエーレスンド海峡を押さえる位置に建つと説明しています。',photoLabel:'正解写真｜クロンボー城',quip:'海峡が狭ければ城の仕事は増える。最高の立地で、常に見張り番。',photoKey:'dk-kronborg-castle-postcard'},
  {question:'ロスキレ大聖堂の建築材料で特に重要なのは？',options:['レンガ','氷のブロック','珊瑚'],answer:0,fact:'UNESCOは北欧の大型宗教建築における早期のレンガ使用を高く評価しています。',photoLabel:'正解写真｜ロスキレ大聖堂',quip:'レンガが主役の大聖堂。積み重ねたのは建材だけでなく、王家の歴史。',photoKey:'dk-roskilde-cathedral-postcard'},
 ],
 EG:[
  {question:'ギザのピラミッド群を含むメンフィスの墓地遺跡の世界遺産登録年は？',options:['1979年','1985年','2001年'],answer:0,photoLabel:'正解写真｜ギザの大ピラミッド',fact:'UNESCOによると、メンフィスとその墓地遺跡は1979年に世界文化遺産へ登録されました。',quip:'古代の建築なのに、街の景色に今も堂々と割り込んでくる。',photoKey:'eg-giza-pyramid-postcard'},
  {question:'アブ・シンベルなどのヌビア遺跡群を救うため、国際的な保存活動を主導した機関は？',options:['UNESCO','欧州中央銀行','国際オリンピック委員会'],answer:0,photoLabel:'正解写真｜アブ・シンベル大神殿',fact:'UNESCOが1960年から1980年にかけて進めた国際保存活動により、神殿などが水没の危機から救われました。',quip:'古代の巨像を動かしたのは、現代の大きなチームワーク。',photoKey:'eg-abu-simbel-postcard'},
 ],
 ES:[
  {question:'サグラダ・ファミリアが建つ都市は？',options:['マドリード','バルセロナ','セビリア'],answer:1,photoKey:'spain-sagrada-nativity-quiz-image',photoLabel:'正解の建築｜バルセロナのサグラダ・ファミリア・生誕のファサード',fact:'サグラダ・ファミリアの「生誕のファサード」と地下聖堂は、ガウディ作品群としてUNESCO世界遺産に登録されています。',quip:'塔だけじゃない。外壁の細工まで観光案内の主役級。'},
  {question:'写真のアルハンブラ宮殿がある都市は？',options:['グラナダ','バルセロナ','バレンシア'],answer:0,photoKey:'spain-alhambra-quiz-image',photoLabel:'正解の宮殿｜アンダルシアのグラナダ・アルハンブラ宮殿',fact:'アルハンブラ宮殿はグラナダにあり、ヘネラリフェとアルバイシン地区とともに世界遺産に登録されています。',quip:'城壁の奥まで歴史ぎっしり。地図の答えはグラナダ。'},
 ],
 EE:[
  {question:'タリンが中世に発展した交易組織は？',options:['ハンザ同盟','国際連合','東インド会社'],answer:0,fact:'バルト海の交易を担ったハンザ同盟の重要な都市でした。',photoLabel:'正解写真｜タリン旧市街・市庁舎広場',quip:'商人の家まで立派なのが、交易都市の強さ。繁栄の証拠は帳簿だけでなく街並みにも残る。',photoKey:'ee-tallinn-square-postcard'},
  {question:'シュトルーヴェの測地弧は何を測るための遺産？',options:['海の塩分','地球の形と大きさ','鉱山の深さ'],answer:1,fact:'複数国の測量地点を結び、地球の形と大きさを精密に調べました。',photoLabel:'正解写真｜タルトゥ旧天文台',quip:'地球のサイズを測るのに衛星はなかった。測量点を国境越しに結ぶ発想が、現代の地図を支えている。',photoKey:'ee-tartu-observatory-postcard'},
 ],
 FI:[
  {question:'スオメンリンナが築かれた主な目的は？',options:['港の防衛','砂漠の灌漑','山岳農業'],answer:0,fact:'UNESCOはヘルシンキ港の入口に築かれた18世紀の海上要塞として紹介しています。',photoLabel:'正解写真｜スオメンリンナの海上要塞',quip:'海の上で城壁を築く。守備範囲は陸地だけでは足りなかった。',photoKey:'fi-suomenlinna-fortress-postcard'},
  {question:'ラウマ旧市街の伝統的な街並みを特徴づけるのは？',options:['木造家屋','大理石の高層塔','砂漠のテント'],answer:0,fact:'UNESCOは伝統的な木造建築が残る北欧の港町としてラウマを評価しています。',photoLabel:'正解写真｜木造のラウマ旧市街',quip:'古い木の家が並ぶ街。建て替えの速さより、残す技術で勝負した。',photoKey:'fi-old-rauma-postcard'},
 ],
 FR:[
  {question:'モン・サン＝ミシェルの景色を変えるのは？',options:['火山の噴火','オーロラ','潮の満ち引き'],answer:2,photoKey:'fr-mont-low-tide-quiz-image',photoLabel:'正解の景色｜潮の満ち引きの影響を受ける干潟',fact:'ノルマンディーのモン・サン＝ミシェルは、潮の満ち引きで周囲の景色が変わります。',quip:'景色の模様替え係は海。毎日、無給で大仕事。'},
  {question:'フランス南部の海岸が面するのは？',options:['地中海','カリブ海','北極海'],answer:0,photoKey:'fr-mediterranean-quiz-image',photoLabel:'正解の海｜南フランス・ニースの地中海',fact:'フランスは大西洋と地中海の両方に面しています。',quip:'北極海でバカンスを始めたら、水着より防寒着が主役。'},
 ],
 GB:[
  {question:'ロンドンのタワーブリッジが架かる川は？',options:['セーヌ川','テムズ川','ドナウ川'],answer:1,photoKey:'uk-towerbridge-postcard',photoLabel:'正解の橋｜ロンドンのタワーブリッジとテムズ川',fact:'タワーブリッジはロンドンのテムズ川に架かる橋です。',quip:'名前はタワー、流れるのはテムズ。川にも自己紹介の出番を。'},
  {question:'エディンバラ城があるのはイギリスのどの地域？',options:['ウェールズ','イングランド','スコットランド'],answer:2,photoKey:'uk-country-postcard',photoLabel:'正解の城｜スコットランドのエディンバラ城',fact:'エディンバラはスコットランドの首都で、エディンバラ城は街の象徴です。',quip:'高台の城が街を見守る。写真の撮影枚数までは数えきれない。'},
 ],
 GR:[
  {question:'アテネのアクロポリスが世界文化遺産に登録された年は？',options:['1987年','1995年','2007年'],answer:0,photoLabel:'正解写真｜アクロポリスのパルテノン神殿',fact:'UNESCOによるアテネのアクロポリスの登録年は1987年です。',quip:'何世紀も経ったのに、柱の存在感は現役です。',photoKey:'gr-parthenon-postcard'},
  {question:'古代ギリシャのデルフィで神託と深く関わった神は？',options:['アポロン','ポセイドン','ヘルメス'],answer:0,photoLabel:'正解写真｜デルフィのアポロン神殿跡',fact:'デルフィの聖域はアポロンの神託で知られ、UNESCO世界遺産にも登録されています。',quip:'山奥の相談所に世界中から人が集まる、古代の人気ぶり。',photoKey:'gr-delphi-apollo-postcard'},
 ],
 HR:[
  {question:'ドゥブロヴニクが発展した主な背景は？',options:['海上交易','砂漠の遊牧','氷河の採掘'],answer:0,photoLabel:'正解写真｜ドゥブロヴニク旧市街',fact:'UNESCOは歴史的な地中海の海洋勢力としてのドゥブロヴニクを説明しています。',quip:'城壁の外は海、内側は街。地形にまで防御の意志が見える。',photoKey:'hr-dubrovnik-old-city-postcard'},
  {question:'プリトヴィツェの湖と滝を生み出す主な働きは？',options:['石灰華の堆積','流氷の衝突','溶岩の噴出のみ'],answer:0,photoLabel:'正解写真｜プリトヴィツェ湖群国立公園',fact:'UNESCOは石灰華の堆積が天然の障壁や湖、滝を形成すると説明しています。',quip:'滝の設計者は水と石灰岩。しかも工事は現在進行形。',photoKey:'hr-plitvice-lakes-postcard'},
 ],
 HU:[
  {question:'ブダペストの景観の中心を流れる川は？',options:['ドナウ川','ナイル川','アマゾン川'],answer:0,fact:'UNESCOはドナウ川の両岸をブダペストの世界遺産の重要な一部としています。',photoLabel:'正解写真｜ドナウ川とブダ城',quip:'川一本でブダとペストを分けても、最後は橋で合体。都市の主役はずっとドナウ川。',photoKey:'hu-buda-castle-postcard'},
  {question:'ホッローケーが伝えるのは主にどのような生活？',options:['伝統的な農村生活','宇宙基地の暮らし','氷上都市の生活'],answer:0,fact:'UNESCOは農業の大変革以前の伝統的な農村生活が残る集落として評価しています。',photoLabel:'正解写真｜ホッローケーの古村落',quip:'世界遺産なのに現役の村。『保存のために誰も住めない』では意味がない。',photoKey:'hu-holloko-village-postcard'},
 ],
 ID:[
  {question:'ボロブドゥールで中心となる宗教的伝統は？',options:['キリスト教','古代ギリシャ神話','仏教'],answer:2,fact:'UNESCOはボロブドゥールを仏教寺院遺跡群として登録しています。',photoLabel:'正解写真｜ボロブドゥール寺院遺跡群',quip:'仏塔が七十二基。石の並びにまで祈りの意味を持たせる設計は、建築を単なる建物の枠からはみ出させた。',photoKey:'id-borobudur-stupa-postcard'},
  {question:'プランバナン寺院群の主要な宗教は？',options:['ヒンドゥー教','仏教','イスラム教'],answer:0,fact:'UNESCOはプランバナン寺院群をヒンドゥー教寺院として紹介しています。',photoLabel:'正解写真｜プランバナン寺院遺跡群',quip:'同じ島に異なる信仰の巨石建築。歴史は一つの宗教だけで説明できるほど単純ではない。',photoKey:'id-prambanan-postcard'},
 ],
 IN:[
  {question:'タージ・マハルの建設を命じたムガル帝国の皇帝は？',options:['シャー・ジャハーン','アクバル','アショーカ王'],answer:0,photoKey:'in-taj-mahal-postcard',photoLabel:'正解写真｜タージ・マハル',fact:'UNESCOは、シャー・ジャハーンが妻ムムターズ・マハルを追悼するために建設を命じたと説明しています。',quip:'大理石で伝えた追悼の思い。手紙では到底収まらない大きさ。'},
  {question:'クトゥブ・ミナールの高さはおよそ何メートル？',options:['24.5メートル','72.5メートル','150メートル'],answer:1,photoKey:'in-qutb-minar-postcard',photoLabel:'正解写真｜クトゥブ・ミナール',fact:'UNESCOによると、クトゥブ・ミナールの高さは72.5メートルです。',quip:'高さ72.5メートル。見上げる首にも歴史の授業が始まる。'},
 ],
 IE:[
  {question:'ブルー・ナ・ボーニャで知られる遺産は？',options:['近代の高層ビル','先史時代の巨石遺跡','海底の沈没船'],answer:1,fact:'UNESCOはこの地域を先史時代の巨石芸術の重要な集積地として紹介しています。',photoLabel:'正解写真｜ブルー・ナ・ボーニャの考古遺跡群・ニューグレンジ',quip:'文字がなくても石は語る。五千年先に残る説明書を作る技術、現代のアプリにも欲しい。',photoKey:'ie-newgrange-postcard'},
  {question:'スケリッグ・マイケルに残る主な遺構は？',options:['競馬場','巨大な造船所','修道院'],answer:2,fact:'UNESCOはスケリッグ・マイケルの修道院遺跡を文化遺産として評価しています。',photoLabel:'正解写真｜スケリッグ・マイケル',quip:'修道院の立地条件が厳しい。日常から離れるために、海まで越えるとは徹底している。',photoKey:'ie-skellig-michael-postcard'},
 ],
 IS:[
  {question:'シンクヴェトリルで930年に始まったものは？',options:['近代的な空港','野外議会','海底鉄道'],answer:1,fact:'UNESCOは930年にアルシングの野外集会が始まった場所として紹介しています。',photoLabel:'正解写真｜シンクヴェトリル国立公園・アルマンナギャウ',quip:'議事堂なしで法律を決めた。会議室の予約で揉める現代人には、耳の痛い話だ。',photoKey:'is-thingvellir-postcard'},
  {question:'ヴァトナヨークトルの景観をつくる主な組み合わせは？',options:['珊瑚礁と熱帯雨林','砂丘とマングローブ','氷河と火山'],answer:2,fact:'UNESCOは氷河と火山活動の相互作用を重要な価値として挙げています。',photoLabel:'正解写真｜ヴァトナヨークトル国立公園・ヨークルスアゥルロゥン氷河湖',quip:'氷の下で火山が活動中。冷蔵庫の下にコンロを置くようなものを、地球は本気でやっている。',photoKey:'is-jokulsarlon-postcard'},
 ],
 IT:[
  {question:'ピサの斜塔が建っているのは、イタリアのどの都市？',options:['ピサ','ローマ','ミラノ'],answer:0,photoKey:'italy-pisa-tower-postcard',photoLabel:'正解の建築｜ピサの斜塔',fact:'ピサの斜塔は、トスカーナ州ピサにある大聖堂の鐘楼です。',quip:'斜めに立っても、長年しっかり観光の主役。'},
  {question:'ヴェネツィアの街を象徴する大きな水路は？',options:['ライン川','大運河','テムズ川'],answer:1,photoKey:'italy-venice-grand-canal-postcard',photoLabel:'正解の水景｜ヴェネツィアの大運河',fact:'ヴェネツィアの大運河は歴史的な建物に沿って流れ、街の水上交通を支えています。',quip:'道路を探すより、舟を探したほうが早い日もある。'},
 ],
 JO:[
  {question:'ペトラの古代都市と深く結びつく人々は？',options:['マヤ人','ナバテア人','ヴァイキング'],answer:1,fact:'UNESCOはペトラをナバテア人の都市として紹介しています。',photoLabel:'正解写真｜ペトラ遺跡・エル・ハズネ',quip:'岩を削って建物を造るとは、資材調達の発想が逆だ。工事のやり直しが利かない分、設計図の責任は重い。',photoKey:'jo-petra-treasury-postcard'},
  {question:'ワディ・ラムが評価される二つの側面は？',options:['海洋と造船','氷河と製鉄','自然と文化'],answer:2,fact:'UNESCOはワディ・ラムを自然と文化の双方に価値がある遺産として扱っています。',photoLabel:'正解写真｜ワディ・ラム保護地域',quip:'砂漠に残る一万年以上の人の記録。電波がなくても、歴史はちゃんと保存されていた。',photoKey:'jo-wadi-rum-sunset-postcard'},
 ],
 JP:[
  {question:'富士山がまたがる2つの県は？',options:['長野県と岐阜県','京都府と滋賀県','山梨県と静岡県'],answer:2,photoKey:'japan-fuji-postcard',photoLabel:'正解の山｜山梨県・静岡県にまたがる富士山',fact:'富士山は山梨県と静岡県にまたがる日本で最も高い山です。',quip:'存在感が大きすぎて二つの県にまたがってしまった。'},
  {question:'東京・浅草の浅草寺があるのはどこ？',options:['京都府','東京都','奈良県'],answer:1,photoKey:'japan-country-postcard',photoLabel:'正解の寺院｜東京・浅草寺',fact:'浅草寺は東京都台東区浅草にあり、雷門などで知られています。',quip:'雷門は人気者。記念写真の行列まで名物になりそう。'},
 ],
 KH:[
  {question:'アンコールの寺院群と結びつく歴史的な王朝は？',options:['ローマ帝国','クメール王朝','アステカ帝国'],answer:1,fact:'UNESCOはアンコールをクメール王朝の主要な遺産として扱っています。',photoLabel:'正解写真｜アンコール遺跡群・アンコール・ワット',quip:'寺院だけでなく都市全体が巨大だった。地図を拡大するたび、当時の建築計画の規模にこちらの想像力が負ける。',photoKey:'kh-angkor-wat-postcard'},
  {question:'プレアヴィヒア寺院で特に重要な宗教的対象は？',options:['古代ローマの皇帝','北欧神話の神々','シヴァ神'],answer:2,fact:'UNESCOはプレアヴィヒア寺院をシヴァ神に捧げられた建築として説明しています。',photoLabel:'正解写真｜プレアヴィヒア寺院',quip:'山の形に合わせて寺院を設計した。平地に戻して効率化する、という発想ではこの傑作は生まれない。',photoKey:'kh-preah-vihear-postcard'},
 ],
 KR:[
  {question:'石段と石塔で知られる、慶州の世界遺産の寺は？',options:['仏国寺','景福宮','海印寺'],answer:0,photoKey:'korea-bulguksa-quiz-image',photoLabel:'正解の寺院｜慶州・仏国寺',fact:'仏国寺は新羅時代の仏教建築を伝える寺で、石窟庵とともにUNESCO世界遺産に登録されています。',quip:'階段の先まで文化財。登る前から歴史が濃い。'},
  {question:'済州島の城山日出峰を形づくったのは何？',options:['サンゴ礁','人工の盛り土','火山の噴出'],answer:2,photoKey:'korea-seongsan-quiz-image',photoLabel:'正解の地形｜済州島・城山日出峰',fact:'城山日出峰は火山活動で生まれた凝灰丘で、済州島の火山地形の一部として世界自然遺産に登録されています。',quip:'海のそばの巨大な山。正体は火山の作品。'},
 ],
 LK:[
  {question:'シーギリヤの古代都市で特徴的な地形は？',options:['広大な氷床','高くそびえる岩山','海底火山の火口'],answer:1,fact:'UNESCOは岩山の上と周囲に広がる古代都市の遺構を評価しています。',photoLabel:'正解写真｜古代都市シーギリヤ',quip:'王都の立地条件が、平地ではなく高さ180メートルの岩山。土地選びの段階から工事担当者には難題だったはずだ。',photoKey:'lk-sigiriya-postcard'},
  {question:'キャンディの重要な宗教的伝統は？',options:['古代ローマの多神教','北欧の神話信仰','仏教'],answer:2,fact:'UNESCOはキャンディを仏教における重要な巡礼地として紹介しています。',photoLabel:'正解写真｜聖地キャンディ・仏歯寺',quip:'王国はなくなっても、祈りの場は残った。歴史の中心人物がいつまでも王様とは限らない。',photoKey:'lk-kandy-tooth-postcard'},
 ],
 LT:[
  {question:'ヴィリニュスが歴史的に政治の中心となった国は？',options:['ローマ帝国','アステカ帝国','リトアニア大公国'],answer:2,fact:'ヴィリニュスは長くリトアニア大公国の政治の中心でした。',photoLabel:'正解写真｜ヴィリニュス歴史地区・聖アンナ教会',quip:'異なる時代の建築が同居する旧市街。街全体を一つの様式で統一しなかったことが、むしろ財産になった。',photoKey:'lt-vilnius-anne-postcard'},
  {question:'砂州を守るために続けられてきた取り組みは？',options:['砂の固定と植林','海底の採掘','氷河の人工造成'],answer:0,fact:'風で動く砂を抑えるため、長年にわたる植林などの取り組みが続いています。',photoLabel:'正解写真｜クルシュー砂州・パルニディス砂丘',quip:'風が砂を運び、人が植林で守る。砂丘の景色は、自然任せでは残らなかった。',photoKey:'lt-nida-parnidis-postcard'},
 ],
 LV:[
  {question:'リガの近代建築を特徴づける様式の一つは？',options:['古代エジプト様式','アール・ヌーヴォー','インカの石造建築'],answer:1,fact:'リガの近代的な住宅地区にはアール・ヌーヴォー建築が残ります。',photoLabel:'正解写真｜リガ歴史地区・アール・ヌーヴォー建築',quip:'建物の壁まで芸術作品。リガでは、街を歩くだけで展覧会の会場が次々に現れる。',photoKey:'lv-riga-artnouveau-postcard'},
  {question:'クルディーガの世界遺産登録年は？',options:['1980年','1994年','2023年'],answer:2,fact:'クルディーガ旧市街は2023年に世界遺産に登録されました。',photoLabel:'正解写真｜クルディーガ旧市街・アレクシュピーテ川の橋',quip:'世界遺産の価値は建築の高さでは決まらない。小さな橋や家々が歴史を伝える主役になる。',photoKey:'lv-kuldiga-bridge-postcard'},
 ],
 MA:[
  {question:'フェズのメディナが伝えるのはどんな都市文化？',options:['歴史的なイスラム都市文化','南極の研究基地','近代の宇宙都市'],answer:0,fact:'UNESCOはフェズ旧市街を歴史的なイスラム都市の重要な事例として登録しています。',photoLabel:'正解写真｜フェズ旧市街・皮革工房',quip:'旧市街には観光客だけでなく職人もいる。街の歴史を保存するとは、看板を残すだけの仕事ではない。',photoKey:'ma-fez-tannery-postcard'},
  {question:'アイト・ベン・ハドゥの建築で特徴的な素材は？',options:['氷のブロック','土を用いた建築','鋼鉄製のドーム'],answer:1,fact:'UNESCOはアイト・ベン・ハドゥを伝統的な土造りの集落建築として説明しています。',photoLabel:'正解写真｜アイト・ベン・ハドゥ',quip:'土の建築を守り続けるには手入れがいる。建物は完成した日から維持管理が始まる。',photoKey:'ma-ait-benhaddou-postcard'},
 ],
 MX:[
  {question:'テオティワカンの巨大な建築群を貫く大通りの名前は？',options:['死者の大通り','王の道','海沿いの大通り'],answer:0,photoLabel:'正解写真｜テオティワカンの遺跡',fact:'テオティワカンには太陽のピラミッドなどを結ぶ『死者の大通り』が広がっています。',quip:'都市計画のスケールが、徒歩の散歩道を超えている。',photoKey:'mx-teotihuacan-postcard'},
  {question:'チチェン・イッツァにある階段状のピラミッドは何と呼ばれる？',options:['エル・カスティージョ','コロッセオ','クトゥブ・ミナール'],answer:0,photoLabel:'正解写真｜チチェン・イッツァ',fact:'エル・カスティージョはチチェン・イッツァを代表する階段状の石造ピラミッドです。',quip:'古代の街の主役級。階段が一段ずつ存在感を出してきます。',photoKey:'mx-chichen-itza-postcard'},
 ],
 NL:[
  {question:'アムステルダムの17世紀運河地区が世界文化遺産に登録された年は？',options:['1997年','2010年','2020年'],answer:1,photoLabel:'正解写真｜アムステルダムの運河',fact:'UNESCOはアムステルダムの17世紀運河地区を2010年に世界文化遺産へ登録しました。',quip:'運河が街の道案内役。水まで都市計画の一員です。',photoKey:'nl-amsterdam-canals-postcard'},
  {question:'キンデルダイクの風車は、主にどのような目的で利用された？',options:['低地の排水','海での漁網の巻き上げ','天体観測'],answer:0,photoLabel:'正解写真｜キンデルダイクの風車',fact:'風車群と水路は、低い土地を排水し守るための水利システムとして整備されました。',quip:'風車は名所になる前から、土地を守る仕事人でした。',photoKey:'nl-kinderdijk-windmills-postcard'},
 ],
 NO:[
  {question:'ブリッゲンと深い関係を持つ交易組織は？',options:['ハンザ同盟','東インド会社のみ','マヤの都市国家'],answer:0,photoLabel:'正解写真｜ブリッゲンの木造商館群',fact:'UNESCOはブリッゲンをハンザ同盟の交易史と結び付けて説明しています。',quip:'交易の歴史は木造の壁にも刻まれる。色鮮やかな港の記憶。',photoKey:'no-bryggen-postcard'},
  {question:'フィヨルドの谷を形づくった主な作用は？',options:['氷河の侵食','砂漠の砂嵐','火山灰の堆積のみ'],answer:0,photoLabel:'正解写真｜西ノルウェーのフィヨルド',fact:'UNESCOは西ノルウェーのフィヨルドを氷河による地形の顕著な例としています。',quip:'地形の彫刻家は氷河。作品の大きさに、人間の尺度が追いつかない。',photoKey:'no-geirangerfjord-postcard'},
 ],
 NP:[
  {question:'カトマンズ盆地の世界遺産を構成する主な要素は？',options:['氷山上の灯台','宮殿広場や宗教建築','巨大な海底遺跡'],answer:1,fact:'UNESCOは三つの宮殿広場など七つの資産群を挙げています。',photoLabel:'正解写真｜カトマンズ盆地・パタン宮殿広場',quip:'街そのものが博物館。展示物をガラスケースに入れる発想が、ここではむしろ邪魔になる。',photoKey:'np-patan-durbar-postcard'},
  {question:'サガルマータ国立公園に含まれる著名な山は？',options:['富士山','キリマンジャロ','エベレスト'],answer:2,fact:'UNESCOはエベレストを中心とするヒマラヤの山岳景観を紹介しています。',photoLabel:'正解写真｜サガルマータ国立公園・カラパタールからの眺望',quip:'世界最高峰でも、雲には勝てない。肩書きがどれだけ高くても、天気の都合は聞いてもらえないらしい。',photoKey:'np-everest-postcard'},
 ],
 NZ:[
  {question:'ピオピオタヒ／ミルフォード・サウンドがある島は？',options:['北島','南島','チャタム諸島'],answer:1,photoKey:'nz-milford-fiord-quiz-image',photoLabel:'正解の景色｜南島のミルフォード・サウンド',fact:'ミルフォード・サウンドはニュージーランド南島、フィヨルドランド国立公園の北西部にあるフィヨルドです。',quip:'山が水面まで迫ってくる。地図の答えは南島。'},
  {question:'ニュージーランドで最も高い山は？',options:['ルアペフ山','タラナキ山','アオラキ／マウント・クック'],answer:2,photoKey:'nz-aoraki-quiz-image',photoLabel:'正解の山｜南島・アオラキ／マウント・クック',fact:'アオラキ／マウント・クックはニュージーランドの最高峰で、同名の国立公園に位置します。',quip:'最高峰の答えは、山の名前からして存在感たっぷり。'},
 ],
 PE:[
  {question:'マチュ・ピチュと深く結び付く文明は？',options:['インカ文明','古代ギリシャ','フェニキア文明'],answer:0,photoLabel:'正解写真｜マチュ・ピチュ',fact:'UNESCOはマチュ・ピチュをインカ文明の代表的な建築遺産として紹介しています。',quip:'山頂の絶景だけじゃない。石段にも都市を造った人の意志がある。',photoKey:'pe-machu-picchu-postcard'},
  {question:'クスコに重なる二つの歴史的な建築の流れは？',options:['インカ期とスペイン統治期','江戸時代と明治時代','古代ローマとヴァイキング'],answer:0,photoLabel:'正解写真｜クスコの市街',fact:'UNESCOはクスコのインカ期とスペイン統治期の都市遺産を評価しています。',quip:'壁の継ぎ目が、千年単位の都市のリレーを見せてくれる。',photoKey:'pe-cusco-historic-center-postcard'},
 ],
 PH:[
  {question:'コルディリェーラの棚田を長く維持してきた人々は？',options:['古代ローマ軍','イフガオの人々','ヴァイキング'],answer:1,fact:'UNESCOはイフガオの人々の長い農業文化が棚田景観を形づくったと説明しています。',photoLabel:'正解写真｜コルディリェーラの棚田群・バタッド',quip:'棚田の曲線は装飾ではなく、斜面と水を利用する農業の知恵。美しさは働く人の積み重ねから生まれた。',photoKey:'ph-batad-terraces-postcard'},
  {question:'ビガンの歴史的街並みが示す文化の交流先は？',options:['北極圏のみ','南極大陸のみ','中国とヨーロッパなど'],answer:2,fact:'UNESCOは中国やヨーロッパなどの影響が重なるビガンの都市景観を評価しています。',photoLabel:'正解写真｜ビガン歴史都市・クリソロゴ通り',quip:'文化の交流は地図上の矢印だけではない。窓や屋根にまで、交易の記憶が残っている。',photoKey:'ph-vigan-crisologo-postcard'},
 ],
 PL:[
  {question:'クラクフ歴史地区の構成要素の一つは？',options:['ヴァヴェルの丘','富士山の五合目','ヴェネツィアの運河'],answer:0,fact:'UNESCOは中世都市クラクフ、ヴァヴェルの丘、カジミエシュを含む地区を登録しています。',photoLabel:'正解写真｜クラクフ・ヴァヴェルの丘',quip:'城を見上げて歴史を感じたら、広場で商人の時代を感じる。クラクフは二段構え。',photoKey:'pl-wawel-castle-postcard'},
  {question:'ヴィエリチカとボフニャで長く採掘されたものは？',options:['岩塩','石炭のみ','金'],answer:0,fact:'UNESCOは岩塩の採掘技術と地下施設の歴史を重要な価値として紹介しています。',photoLabel:'正解写真｜ヴィエリチカの聖キンガ礼拝堂',quip:'塩を掘っていたら地下に礼拝堂まで造った。採掘現場の仕事が芸術になった。',photoKey:'pl-wieliczka-salt-chapel-postcard'},
 ],
 PT:[
  {question:'ジェロニモス修道院とベレンの塔が世界文化遺産に登録された年は？',options:['1983年','1995年','2015年'],answer:0,photoLabel:'正解写真｜ジェロニモス修道院',fact:'UNESCOはジェロニモス修道院とベレンの塔を1983年に世界文化遺産へ登録しています。',quip:'海へ出た時代の記憶が、石の柱までぎっしり残る。',photoKey:'pt-jeronimos-monastery-postcard'},
  {question:'シントラの文化的景観が世界文化遺産に登録された年は？',options:['1983年','1995年','2007年'],answer:1,photoLabel:'正解写真｜シントラのペーナ宮殿',fact:'UNESCOによるシントラの文化的景観の登録年は1995年です。',quip:'森の中に宮殿。景色の設計まで王宮級のこだわり。',photoKey:'pt-pena-palace-postcard'},
 ],
 SG:[
  {question:'シンガポール植物園が世界文化遺産に登録された年は？',options:['1997年','2015年','2025年'],answer:1,photoLabel:'正解写真｜シンガポール植物園',fact:'UNESCO世界遺産センターの登録情報によると、シンガポール植物園の登録年は2015年です。',quip:'高層ビルの街で、植物も世界遺産の主役です。',photoKey:'sg-botanic-gardens-postcard'},
  {question:'スーパーツリー・グローブに集まっている巨大な樹木型構造物は何本？',options:['3本','12本','40本'],answer:1,photoLabel:'正解写真｜ガーデンズ・バイ・ザ・ベイ',fact:'公式案内では、18本あるスーパーツリーのうち12本がスーパーツリー・グローブに集まっています。',quip:'スーパーツリーが12本。樹木界の未来都市です。',photoKey:'sg-gardens-bay-postcard'},
 ],
 SI:[
  {question:'シュコツィアン洞窟の形成に重要な地形は？',options:['カルスト地形','珊瑚礁','砂丘'],answer:0,fact:'UNESCOは石灰岩と水がつくるカルスト地形を洞窟群の重要な価値としています。',photoLabel:'正解写真｜シュコツィアン洞窟群',quip:'大峡谷が地下にある。地図の平面だけでは、地球の実力を読み違える。',photoKey:'si-skocjan-caves-postcard'},
  {question:'リュブリャナの世界遺産で重視された設計思想は？',options:['人を中心とした都市設計','巨大な要塞の新設','砂漠の道路建設'],answer:0,fact:'UNESCOは建築家プレチニクによる人間中心の都市デザインを評価しています。',photoLabel:'正解写真｜リュブリャナの三本橋',quip:'橋一本で足りると思うのは設計者の都合。歩く人のために三本に増やした。',photoKey:'si-triple-bridge-postcard'},
 ],
 SE:[
  {question:'ドロットニングホルムの世界遺産に含まれるのは？',options:['宮殿と庭園、劇場','巨大な鉱山','ローマの円形競技場'],answer:0,fact:'UNESCOは宮殿と庭園、歴史的な劇場などを含む王領地を評価しています。',photoLabel:'正解写真｜ドロットニングホルム宮殿',quip:'庭園の木の並びまで王家仕様。『ちょっと整えて』の規模が違う。',photoKey:'se-drottningholm-palace-postcard'},
  {question:'ターヌムの岩絵と特に結びつく時代は？',options:['青銅器時代','産業革命期のみ','宇宙開発時代'],answer:0,fact:'UNESCOはターヌムの岩絵群を北欧青銅器時代の重要な記録とみなしています。',photoLabel:'正解写真｜ターヌムの岩絵',quip:'青銅器時代のメッセージ、保存期間は数千年。クラウドより石が強かった。',photoKey:'se-tanum-rock-carvings-postcard'},
 ],
 TH:[
  {question:'アユタヤ歴史都市が世界文化遺産に登録された年は？',options:['1985年','1991年','2007年'],answer:1,photoLabel:'正解写真｜アユタヤのワット・マハータート',fact:'UNESCO世界遺産センターの登録情報では、アユタヤ歴史都市の登録年は1991年です。',quip:'木の根が歴史を包む。自然の展示方法には驚かされる。',photoKey:'th-ayutthaya-mahathat-postcard'},
  {question:'UNESCOのスコータイ歴史都市群を構成する主な歴史都市は全部でいくつ？',options:['1つ','3つ','6つ'],answer:1,photoLabel:'正解写真｜スコータイ歴史公園',fact:'UNESCO登録資産はスコータイ、シーサッチャナーライ、カムペーンペットの三つの歴史都市から構成されています。',quip:'都の歴史も一か所では終わらない。見どころが三都市分。',photoKey:'th-sukhothai-park-postcard'},
 ],
 TR:[
  {question:'アヤソフィアを含むイスタンブール歴史地区の世界遺産登録年は？',options:['1979年','1985年','2007年'],answer:1,photoLabel:'正解写真｜イスタンブールのアヤソフィア',fact:'UNESCOはイスタンブール歴史地区を1985年に世界文化遺産へ登録しました。',quip:'ドーム一つに幾つもの時代。建物の履歴書が長すぎる。',photoKey:'tr-hagia-sophia-postcard'},
  {question:'カッパドキアの塔のような奇岩ができた主な自然の働きは？',options:['火山性の地層が風雨で削られた','サンゴの成長','湖面の凍結だけ'],answer:0,photoLabel:'正解写真｜カッパドキアの奇岩',fact:'UNESCOは火山性の地形が浸食され、特異な谷や奇岩を生んだと解説しています。',quip:'地球の彫刻作品。しかも全部ちょっとずつ形が違う。',photoKey:'tr-cappadocia-rocks-postcard'},
 ],
 TZ:[
  {question:'ストーン・タウンの発展に重要だった役割は？',options:['北極探検基地','海上交易','高山の鉱山都市'],answer:1,fact:'UNESCOは東アフリカ沿岸の交易都市としての歴史を評価しています。',photoLabel:'正解写真｜ザンジバルのストーン・タウン',quip:'海を越えた交易の歴史が、曲がりくねった路地に残っている。最短経路だけでは、街の面白さは測れない。',photoKey:'tz-stone-town-postcard'},
  {question:'キリマンジャロの特徴としてUNESCOが挙げるのは？',options:['世界最大の珊瑚礁','海底火山の島','アフリカ最高峰'],answer:2,fact:'UNESCOはキリマンジャロをアフリカで最も高い山として説明しています。',photoLabel:'正解写真｜キリマンジャロ国立公園・モシ市街からの遠望',quip:'標高5895メートル。アフリカの最高峰は、ビルの高さ競争に参加せずに圧勝している。',photoKey:'tz-kilimanjaro-postcard'},
 ],
 US:[
  {question:'サンフランシスコの海峡に架かる橋は？',options:['ロンドン橋','ゴールデンゲートブリッジ','ブルックリン橋'],answer:1,photoKey:'us-golden-gate-postcard',photoLabel:'正解の橋｜ゴールデンゲートブリッジ',fact:'ゴールデンゲートブリッジは、サンフランシスコの海峡を渡る橋です。',quip:'名前はゴールデン、見た目はオレンジ。名乗った瞬間からツッコミ待ち。'},
  {question:'ヨセミテ国立公園の巨大な岩壁で知られる岩石は？',options:['サンゴ','石炭','花崗岩'],answer:2,photoKey:'us-yosemite-color-quiz-image',photoLabel:'正解の地形｜ヨセミテの岩壁と谷',fact:'ヨセミテには花崗岩の大きな岩壁や谷が広がっています。',quip:'地球のプロフィール写真、岩肌の圧が強い。'},
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
