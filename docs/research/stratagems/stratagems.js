const stratagems = [
[1,'瞞天過海','まんてんかかい','Deceive the heavens to cross the sea','Normality / Habit','正常性バイアス、慣れによる警戒低下','Status quo bias / habituation','日常業務に紛れた情報漏洩、いつものUIに紛れた誘導','あまりにも日常的なものは疑われにくい。反復と慣れを利用する計略。'],
[2,'囲魏救趙','いぎきゅうちょう','Besiege Wei to rescue Zhao','Attention / Indirect Pressure','注意分散、間接圧力への反応','Limited attention / opportunity cost','競合の本丸ではなく弱点市場を攻める、交渉で別論点を突く','正面から助けるのではなく、相手の別の重要地点を突いて行動を変えさせる。'],
[3,'借刀殺人','しゃくとうさつじん','Kill with a borrowed knife','Social / Responsibility','責任分散、代理行動、他者利用','Diffusion of responsibility / agency problem','代理店・インフルエンサー・第三者レビューを使う','自分の手を汚さず、他者の力・権威・怒りを利用する。'],
[4,'以逸待労','いいつたいろう','Wait at ease for the exhausted enemy','Fatigue / Timing','疲労による判断力低下、焦り','Decision fatigue / ego depletion','長期交渉、相手が疲れたタイミングで条件提示','余裕を保ち、相手の疲労や焦りが判断を鈍らせるのを待つ。'],
[5,'趁火打劫','ちんかだこう','Loot a burning house','Loss / Crisis','危機時の損失回避、焦燥判断','Loss aversion / scarcity under stress','市場急落時の買収、炎上中の競合から顧客獲得','相手が混乱や損失に直面している時に、その判断の歪みを利用する。'],
[6,'声東撃西','せいとうげきせい','Make noise in the east, attack in the west','Attention','注意誘導、一点集中による盲点化','Attentional bias / misdirection','広告・政治・SNSで本命から視線を逸らす','目立つ情報で注意を誘導し、本命を見えにくくする。'],
[7,'無中生有','むちゅうしょうゆう','Create something from nothing','Reality Construction','真実性錯覚、存在の錯覚、反復効果','Illusory truth effect / availability heuristic','ステマ、噂、ブランド人気の演出','実体が薄いものでも、反復・演出・噂によって存在感が生まれる。'],
[8,'暗渡陳倉','あんとちんそう','Secretly cross at Chencang','Expectation','予想固定、見えている経路への過信','Confirmation bias / inattentional blindness','表向きのロードマップと裏の開発、競合の盲点攻略','見えている動きで相手の予測を固定し、別経路で本命を進める。'],
[9,'隔岸観火','かくがんかんか','Watch the fire from across the river','Social / Inaction','傍観者効果、介入コスト回避','Bystander effect / strategic delay','競合同士の消耗を待つ、炎上を静観する','他者の混乱に介入せず、消耗や変化を待つ。'],
[10,'笑裏蔵刀','しょうりぞうとう','Hide a knife behind a smile','Trust / Impression','ハロー効果、好意による警戒低下','Halo effect / affect heuristic','営業トーク、政治的微笑、親切を装った誘導','好意的な外見や態度で警戒を下げ、裏の意図を隠す。'],
[11,'李代桃僵','りだいとうきょう','Sacrifice the plum tree to preserve the peach tree','Trade-off','代替損失の受容、損切り判断','Sunk cost control / substitution','小さな部門を切って本体を守る、炎上時の責任者交代','重要なものを守るために、別のものを犠牲にする。'],
[12,'順手牽羊','じゅんしゅけんよう','Take the opportunity to steal a goat','Opportunity','小さな損失の軽視、注意外の損失','Mental accounting / salience bias','追加手数料、サブスクの小額課金、細かな権限取得','目立たない小さな機会を拾い、相手が軽視する損失を利用する。'],
[13,'打草驚蛇','だそうきょうだ','Beat the grass to startle the snake','Detection','反応からの推定、警戒反応の観察','Signaling / information elicitation','小さな質問で本音を見る、セキュリティ監査','小さな刺激を与え、隠れた相手や本音の反応を見る。'],
[14,'借屍還魂','しゃくしかんこん','Borrow a corpse to revive the soul','Authority / Legacy','権威バイアス、過去資産への信頼','Authority bias / nostalgia effect','古いブランドの復活、権威ある名義を借りる','既にある名義・権威・過去資産を利用して新しい意味を宿す。'],
[15,'調虎離山','ちょうこりざん','Lure the tiger away from the mountain','Context','環境依存の強さ、ホーム優位','Context effect / home advantage','相手の得意領域から引き離す、プラットフォーム変更','相手を得意な場所・条件から引き離し、能力を弱める。'],
[16,'欲擒故縦','よくきんこしょう','To capture, first let go','Reactance','自由を与えられると警戒が下がる、心理的リアクタンス','Reactance theory / commitment','営業で押さずに選ばせる、無料トライアル','追い詰めず、あえて自由を与えることで相手の自発的接近を誘う。'],
[17,'抛磚引玉','ほうせんいんぎょく','Throw a brick to attract jade','Reciprocity / Bait','返報性、アンカリング','Reciprocity / anchoring','無料資料、安価な入口商品、釣り投稿','小さなものを差し出し、より大きな反応や価値を引き出す。'],
[18,'擒賊擒王','きんぞくきんおう','Capture the leader to capture the bandits','Hierarchy','中心人物への依存、権威集中','Network centrality / authority bias','キーマン攻略、インフルエンサー獲得','集団全体ではなく、中心人物・権威・キーノードを狙う。'],
[19,'釜底抽薪','ふていちゅうしん','Remove the firewood from under the pot','Root Cause','表面現象への注意偏り','Root cause intervention / systems thinking','競合の資金源・供給網・流通を断つ','表面の火ではなく、火を支える燃料を取り除く。'],
[20,'渾水摸魚','こんすいぼぎょ','Fish in troubled waters','Chaos','混乱時の注意低下、認知負荷','Cognitive load / ambiguity exploitation','制度変更時の便乗、炎上中の情報操作','混乱している環境では判断精度が落ちる。その隙を利用する。'],
[21,'金蝉脱殻','きんせんだっかく','Shed the shell like a golden cicada','Appearance','外形維持による継続錯覚','Continuity bias / framing','看板だけ残して中身を変える、ブランド移行','外見や看板を残しながら、中身だけを入れ替える。'],
[22,'関門捉賊','かんもんそくぞく','Shut the door to catch the thief','Constraint','逃げ道を失うと選択肢が狭まる','Choice architecture / constraint strategy','契約条項、囲い込み、解約導線の制限','出口を塞ぎ、相手の選択肢を限定する。'],
[23,'遠交近攻','えんこうきんこう','Befriend distant states while attacking nearby ones','Distance / Alliance','近接脅威の過大評価、遠方リスクの過小評価','Psychological distance / coalition strategy','遠い業界と提携し、近い競合を攻める','遠方と組み、近くの脅威を処理する。心理的距離を利用する計略。'],
[24,'仮道伐虢','かどうばっかく','Borrow a path to attack Guo','Access','協力要請への油断、目的の誤認','Foot-in-the-door / trust exploitation','API連携から市場侵入、提携を入口にする','通行や協力を名目にアクセス権を得て、本来の目的を達成する。'],
[25,'偸梁換柱','とうりょうかんちゅう','Replace the beams and pillars','Substitution','構造変化への気づきにくさ','Change blindness / substitution effect','規約改定、UI変更で主導権を移す','柱や梁のような重要構造を、気づかれないうちに入れ替える。'],
[26,'指桑罵槐','しそうばかい','Point at the mulberry, curse the locust','Indirect Signaling','間接批判の読み取り、社会的圧力','Signaling / social norm enforcement','名指しせず牽制、組織内メッセージ','直接言わず、別対象を叱ることで本命に圧力をかける。'],
[27,'仮痴不癲','かちふてん','Feign foolishness without going mad','Impression','第一印象効果、ステレオタイプ、能力過小評価','Stereotyping / first impression effect','弱そうに見せて油断させる、初心者を装う','愚者のふりをして、相手の見下しや油断を引き出す。'],
[28,'上屋抽梯','じょうおくちゅうてい','Remove the ladder after the enemy climbs up','Commitment','コミット後の撤退困難、損切り不能','Sunk cost fallacy / escalation of commitment','導入後に条件変更、撤退コストを上げる','相手を一度乗せた後、退路を断って選択を固定する。'],
[29,'樹上開花','じゅじょうかいか','Make flowers bloom on a tree','Signal Amplification','見せかけの規模、装飾による過大評価','Signaling / halo effect','実態以上に大きく見せるPR、展示会演出','実体以上に華やかに見せ、相手の評価を増幅させる。'],
[30,'反客為主','はんかくいしゅ','Turn from guest into host','Control','既成事実化、主導権移転への鈍感さ','Endowment effect / default effect','外部委託先が主導権を握る、プラットフォーム依存','客の立場から入り込み、いつの間にか主導権を握る。'],
[31,'美人計','びじんけい','Use beauty as a trap','Desire','魅力バイアス、感情による判断歪み','Affect heuristic / attractiveness bias','広告モデル、恋愛詐欺、感情訴求','魅力や欲望によって判断力を鈍らせる。'],
[32,'空城計','くうじょうけい','Empty fort strategy','Uncertainty','情報不足時の物語補完、過剰推論','Ambiguity aversion / predictive inference','沈黙による深読み、OSSの堂々公開、投資家の推測','情報の空白を作り、相手自身に物語を補完させる。'],
[33,'反間計','はんかんけい','Use enemy spies against them','Trust / Doubt','疑心暗鬼、信頼ネットワークの破壊','Trust erosion / information asymmetry','内部不信、リーク情報、競合撹乱','情報と疑念を使い、相手組織の信頼構造を壊す。'],
[34,'苦肉計','くにくけい','Inflict injury on oneself to win trust','Credibility','犠牲を払う者は本気だと見なす','Costly signaling / credibility heuristic','身銭を切るPR、謝罪演出、内部告発の信頼性','自分に痛みを与えることで、本気度や信用を演出する。'],
[35,'連環計','れんかんけい','Chain stratagems together','System','複数要因の連鎖を見落とす','Complexity neglect / systems trap','複数施策の組み合わせ、依存関係で縛る','単独ではなく、複数の仕掛けを連鎖させて逃げにくくする。'],
[36,'走為上','そういじょう','If all else fails, retreat','Exit','撤退の恥、損切り回避','Sunk cost fallacy / loss aversion','撤退判断、ピボット、プロジェクト停止','逃げることを敗北ではなく、合理的な選択肢として扱う。']
].map(([id,name,reading,english,category,bias,behavioral,example,summary])=>({id,name,reading,english,category,bias,behavioral,example,summary}));

const cards=document.getElementById('cards');
const search=document.getElementById('search');
const category=document.getElementById('category');
const categoryCards=document.getElementById('categoryCards');
const categoryCount=document.getElementById('categoryCount');
const categories=[...new Set(stratagems.map(s=>s.category))].sort();
categoryCount.textContent=categories.length;
for(const c of categories){const opt=document.createElement('option');opt.value=c;opt.textContent=c;category.appendChild(opt)}
function renderCategoryCards(){categoryCards.innerHTML='';categories.forEach(c=>{const count=stratagems.filter(s=>s.category===c).length;const div=document.createElement('div');div.className='category-card';div.innerHTML=`<strong>${c}</strong><span>${count} stratagem${count>1?'s':''} mapped</span>`;div.addEventListener('click',()=>{category.value=c;render();document.getElementById('atlas').scrollIntoView({behavior:'smooth'});});categoryCards.appendChild(div);});}
function render(){const q=search.value.toLowerCase().trim();const cat=category.value;const filtered=stratagems.filter(s=>cat==='all'||s.category===cat).filter(s=>Object.values(s).join(' ').toLowerCase().includes(q));cards.innerHTML='';filtered.forEach(s=>{const card=document.createElement('article');card.className='stratagem-card';card.innerHTML=`<div class="card-top"><span class="number">#${String(s.id).padStart(2,'0')}</span><span class="badge">${s.category}</span></div><h3>${s.name}</h3><p class="reading">${s.reading}</p><p class="english">${s.english}</p><p class="summary">${s.summary}</p><div class="meta"><p><b>Bias:</b> ${s.bias}</p><p><b>Behavioral reading:</b> ${s.behavioral}</p><p><b>Modern example:</b> ${s.example}</p></div>`;cards.appendChild(card);});if(!filtered.length)cards.innerHTML='<article class="stratagem-card"><h3>No results</h3><p class="summary">別のキーワードで検索してください。</p></article>';}
search.addEventListener('input',render);category.addEventListener('change',render);renderCategoryCards();render();
