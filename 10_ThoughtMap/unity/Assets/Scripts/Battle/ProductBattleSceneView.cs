using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public class ProductBattleSceneView : MonoBehaviour
{
    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private string deckFileName = "deck.json";
    [SerializeField] private string battlePrepSceneName = "BattlePrepScene";
    [SerializeField] private bool loadOnStart = true;

    [Header("Scene References")]
    [SerializeField] private Transform playerBoardRoot;
    [SerializeField] private Transform enemyBoardRoot;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private ProductBattleLogPanelView battleLogPanel;

    [Header("Battle Presentation Timing")]
    [SerializeField, Min(0f)] private float turnDelay = 0.4f;
    [SerializeField, Min(0f)] private float targetDelay = 0.2f;
    [SerializeField, Min(0f)] private float attackDelay = 0.3f;
    [SerializeField, Min(0f)] private float damageDelay = 0.2f;
    [SerializeField, Min(0f)] private float hpUpdateDuration = 0.4f;
    [SerializeField, Min(0f)] private float resultDisplayDuration = 1f;

    [Header("Battle Result MVP Score")]
    [SerializeField] private BattleResultScoreSettings battleResultScoreSettings = new BattleResultScoreSettings();

    [Header("Sprites")]
    [SerializeField] private Sprite defaultCardArt;
    [SerializeField] private Sprite defaultAttributeIcon;
    [SerializeField] private Sprite[] cardArtPool;
    [SerializeField] private AttributeSpriteMap[] attributeSprites;
    [SerializeField] private AttributeSpriteMap[] cardTemplateSprites;

    [Header("Board Layout")]
    [SerializeField] private float cardScale = 0.52f;
    [SerializeField] private float horizontalCellSpacing = 205f;
    [SerializeField] private float verticalCellSpacing = 68f;
    [SerializeField] private bool showDebugUi;

    private readonly Dictionary<string, BattlePresentationUnitData> presentationUnits = new Dictionary<string, BattlePresentationUnitData>();
    private Coroutine battleRoutine;
    private BattleResultView resultPanel;
    private RewardView rewardView;
    private RewardData pendingReward;
    private BattleResultData completedResultData;
    private readonly PlayerProgressRepository progressRepository = new PlayerProgressRepository();
    private ThoughtMapPersonalRepository personalRepository;
    private BattleSceneHudView battleHud;
    private KnowledgeNetworkView knowledgeNetwork;
    private BattleEffectSequenceController effectSequence;
    private IReadOnlyDictionary<string, BattleUnitView> battleUnits;
    private BattleWorldPopupView worldPopup;
    private IBattleStatusReadModel statusReadModel;
    public BattlePhase1Result LastBattleResult { get; private set; }

    [ContextMenu("Load Deck Preview")]
    public void LoadDeckPreview()
    {
        List<ThoughtMapBattleCardData> cards = LoadCards();
        ThoughtMapBattleDeckConfig config = LoadDeckConfig();
        if (cards.Count == 0)
        {
            WriteStatus("No cards loaded. Place cards.csv in StreamingAssets or assign Cards Csv Asset.");
            return;
        }

        ClearChildren(playerBoardRoot);
        ClearChildren(enemyBoardRoot);
        presentationUnits.Clear();

        List<ThoughtMapBattleCardData> playerCards = ResolveCards(cards, config != null ? config.deployedCardIds : null);
        if (playerCards.Count != 5 ||
            config == null ||
            config.gridPositions == null || config.gridPositions.Count != 5 ||
            config.preparedUnits == null || config.preparedUnits.Count != 5)
        {
            WriteStatus("Battle Prep data is incomplete. Save exactly 5 deployed cards in Battle Prep before battle.");
            return;
        }

        CampaignStageData campaignStage = CampaignManager.Instance.CurrentStage;
        EnemyDeckData enemyDeck = campaignStage == null ? null : EnemyDeckLoader.Load(campaignStage.enemyDeckId);
        List<ThoughtMapBattleCardData> enemyCards = ResolveCards(cards, enemyDeck == null ? null : enemyDeck.cardIds);
        if (enemyCards.Count != 5)
        {
            WriteStatus("Enemy team data is incomplete. Check campaign.json and enemy_decks.json; exactly 5 valid card IDs are required.");
            return;
        }

        Dictionary<string, List<GeneratedSkillDto>> assignedSkills = ResolveAssignedSkills(config);
        List<ThoughtMapGridPosition> playerPositions = ResolvePlayerPositions(config);
        List<ThoughtMapGridPosition> enemyPositions = Enumerable.Range(0, 5)
            .Select(index => new ThoughtMapGridPosition(index, 4))
            .ToList();
        List<ThoughtMapGridPosition> enemyVisualPositions = ResolveEnemyVisualPositions(enemyDeck, enemyCards);
        BuildPresentationData(playerCards, "P", false, config, assignedSkills);
        BuildPresentationData(enemyCards, "E", true, null, assignedSkills);
        SpawnBattleCharacters(playerPositions, enemyVisualPositions);
        if (battleUnits != null && battleUnits.TryGetValue("P1", out BattleUnitView firstPlayer)) SelectBattleUnit(firstPlayer);
        if (battleUnits != null && battleUnits.TryGetValue("E1", out BattleUnitView firstEnemy)) battleHud?.SelectUnit(firstEnemy);

        if (battleLogPanel != null)
        {
            battleLogPanel.Clear();
            battleLogPanel.gameObject.SetActive(false);
        }
        BattleController controller = new BattleController(scoreSettings: battleResultScoreSettings);
        statusReadModel = controller;
        battleHud?.SetStatusSource(statusReadModel);
        InitializeStatusViews();
        if (battleRoutine != null)
        {
            StopCoroutine(battleRoutine);
        }
        battleRoutine = StartCoroutine(controller.RunCoroutine(
            playerCards,
            enemyCards,
            playerPositions,
            enemyPositions,
            PresentBattleEvent,
            HandleBattleLogEvent,
            HandleBattleCompleted,
            config.preparedUnits,
            assignedSkills));
    }

    private void Start()
    {
        personalRepository = GetComponent<ThoughtMapPersonalRepository>() ?? gameObject.AddComponent<ThoughtMapPersonalRepository>();
        EnsureBattleHud();
        TMP_Text legacyTitle = GetComponentsInChildren<TMP_Text>(true).FirstOrDefault(text => text.gameObject.name == "TitleText");
        if (legacyTitle != null) legacyTitle.gameObject.SetActive(false);
        ConfigureActionStatusPosition();
        ConfigureBattleCamera();
        if (loadOnStart)
        {
            LoadDeckPreview();
        }
    }

    private List<ThoughtMapBattleCardData> LoadCards()
    {
        try
        {
            if (cardsCsvAsset != null)
            {
                return ThoughtMapCardsCsvLoader.LoadFromText(cardsCsvAsset.text);
            }
            return ThoughtMapCardsCsvLoader.LoadFromStreamingAssets(streamingAssetsCsvPath);
        }
        catch (System.Exception exc)
        {
            WriteStatus("Could not load cards.csv: " + exc.Message);
            return new List<ThoughtMapBattleCardData>();
        }
    }

    private ThoughtMapBattleDeckConfig LoadDeckConfig()
    {
        string path = Path.Combine(Application.persistentDataPath, deckFileName);
        if (!File.Exists(path))
        {
            WriteStatus("deck.json not found. Save Battle Prep before opening BattleScene.");
            return null;
        }

        try
        {
            return JsonUtility.FromJson<ThoughtMapBattleDeckConfig>(File.ReadAllText(path));
        }
        catch (System.Exception exc)
        {
            WriteStatus("Could not read deck.json: " + exc.Message);
            return null;
        }
    }

    private List<ThoughtMapBattleCardData> ResolveCards(List<ThoughtMapBattleCardData> cards, List<string> ids)
    {
        List<ThoughtMapBattleCardData> resolved = new List<ThoughtMapBattleCardData>();
        if (ids == null)
        {
            return resolved;
        }

        foreach (string id in ids)
        {
            ThoughtMapBattleCardData card = cards.FirstOrDefault(candidate => GetCardId(candidate) == id);
            if (card != null)
            {
                resolved.Add(card);
            }
        }
        return resolved;
    }

    private void BuildPresentationData(List<ThoughtMapBattleCardData> cards,string prefix,bool enemySide,ThoughtMapBattleDeckConfig config,Dictionary<string,List<GeneratedSkillDto>> assignedSkills)
    {
        for(int i=0;i<cards.Count;i++){ThoughtMapBattleCardData card=cards[i];string cardId=GetCardId(card);ThoughtMapBattlePreparedUnitData prepared=config?.preparedUnits?.FirstOrDefault(x=>x!=null&&x.cardId==cardId);assignedSkills.TryGetValue(cardId,out List<GeneratedSkillDto> skills);string unitId=prefix+(i+1);presentationUnits[unitId]=new BattlePresentationUnitData(unitId,card,ResolveCardArt(card,i),enemySide,prepared,skills);}
    }

    private void SpawnBattleCharacters(
        IReadOnlyList<ThoughtMapGridPosition> playerPositions,
        IReadOnlyList<ThoughtMapGridPosition> enemyPositions)
    {
        GameObject stageRoot = GameObject.Find("BattleFieldRoot");
        if (stageRoot == null) return;
        BattleCharacterStageView stageView = stageRoot.GetComponent<BattleCharacterStageView>();
        if (stageView == null) stageView = stageRoot.AddComponent<BattleCharacterStageView>();
        stageView.Spawn(playerPositions, enemyPositions, presentationUnits);
        battleUnits = stageView.Units;
        knowledgeNetwork = stageRoot.GetComponent<KnowledgeNetworkView>();
        if (knowledgeNetwork == null) knowledgeNetwork = stageRoot.AddComponent<KnowledgeNetworkView>();
        knowledgeNetwork.Initialize(stageView.Units);
        effectSequence = stageRoot.GetComponent<BattleEffectSequenceController>() ?? stageRoot.AddComponent<BattleEffectSequenceController>();
        effectSequence.Initialize(stageView.Units);
    }

    private void InitializeStatusViews()
    {
        if (battleUnits == null) return;
        TMP_FontAsset font = ThoughtMapTmpFontResolver.Resolve(statusText == null ? null : statusText.font);
        foreach (BattleUnitView unit in battleUnits.Values)
        {
            if (unit?.StatusRoot == null) continue;
            BattleUnitStatusView view = unit.StatusRoot.GetComponent<BattleUnitStatusView>() ?? unit.StatusRoot.gameObject.AddComponent<BattleUnitStatusView>();
            view.Initialize(font);
            view.Refresh(System.Array.Empty<BattleStatusDisplayModel>(), false);
        }
    }

    private void RefreshStatusView(ThoughtMapBattleUnit unit)
    {
        if (unit == null || battleUnits == null || !battleUnits.TryGetValue(unit.battleId, out BattleUnitView battleUnit)) return;
        BattleUnitStatusView statusView = battleUnit.StatusRoot == null ? null : battleUnit.StatusRoot.GetComponent<BattleUnitStatusView>();
        statusView?.Refresh(BattleStatusPresenter.Build(unit, statusReadModel), !unit.IsAlive);
        battleHud?.RefreshStatus(unit, battleUnit);
    }

    private void SelectBattleUnit(BattleUnitView view)
    {
        battleHud?.SelectUnit(view);
        if (battleUnits == null) return;
        foreach (KeyValuePair<string, BattleUnitView> pair in battleUnits)
            pair.Value?.SetCardSelected(view != null && pair.Key == view.UnitId);
    }

    private void SetTargetCard(string unitId, bool targeted)
    {
        if (battleUnits != null && battleUnits.TryGetValue(unitId, out BattleUnitView unit))
            unit.SetCardTargeted(targeted);
    }

    private void ClearCardTargets()
    {
        battleHud?.HideTarget();
        if (battleUnits == null) return;
        foreach (BattleUnitView unit in battleUnits.Values) unit?.SetCardTargeted(false);
    }

    private void HandleBattleLogEvent(BattlePhase1Event battleEvent)
    {
        if (battleEvent == null)
        {
            return;
        }
        if (!string.IsNullOrWhiteSpace(battleEvent.logLine))
        {
            battleLogPanel?.AppendLine(battleEvent.logLine);
            battleHud?.AppendLog(battleEvent.logLine);
        }
        if (battleEvent.phase == BattlePresentationPhase.StatusChanged) RefreshStatusView(battleEvent.target);
    }

    private IEnumerator PresentBattleEvent(BattlePhase1Event battleEvent)
    {
        if (battleEvent == null)
        {
            yield break;
        }

        BattleUnitView attackerView=null,targetView=null;
        if(battleUnits!=null){if(battleEvent.attacker!=null)battleUnits.TryGetValue(battleEvent.attacker.battleId,out attackerView);if(battleEvent.target!=null)battleUnits.TryGetValue(battleEvent.target.battleId,out targetView);}
        switch (battleEvent.phase)
        {
            case BattlePresentationPhase.TurnStarted:
                battleHud?.SetTurn(battleEvent.turn);
                yield return ShowStatusFade($"Turn {battleEvent.turn}", turnDelay, false);
                break;
            case BattlePresentationPhase.TargetSelected:
                battleHud?.SetPhase(battleEvent.attacker == null ? "Player" : battleEvent.attacker.team);
                battleHud?.UpdateUnit(battleEvent.attacker, attackerView);
                battleHud?.UpdateUnit(battleEvent.target, targetView);
                SetTargetCard(battleEvent.target == null ? string.Empty : battleEvent.target.battleId, true);
                yield return Wait(targetDelay);
                break;
            case BattlePresentationPhase.AttackStarted:
                SetActionStatus($"{battleEvent.attacker.battleId} attacks {battleEvent.target.battleId}");
                if (effectSequence != null && attackerView != null && targetView != null)
                    yield return effectSequence.Play(CreateEffectContext(BattleEffectType.Attack, battleEvent, attackerView, targetView));
                else
                    yield return Wait(attackDelay);
                break;
            case BattlePresentationPhase.SkillActivated:
                if (battleEvent.attacker != null)
                {
                    knowledgeNetwork?.PlaySelfEnhance(
                        battleEvent.attacker.battleId,
                        24,
                        battleEvent.attacker.card == null ? string.Empty : battleEvent.attacker.card.primaryAttribute);
                    if(attackerView!=null)worldPopup?.Show(attackerView.PresentationAnchor,$"Skill\n{battleEvent.skillName}\nActivated",new Color(1f,.82f,.2f),1.2f);
                }
                break;
            case BattlePresentationPhase.SkillEffectApplied:
                if (targetView != null)
                {
                    Color color = battleEvent.skillEffectType switch
                    {
                        BattleSkillEffectType.Heal => new Color(.25f, 1f, .42f),
                        BattleSkillEffectType.Shield => new Color(.35f, .8f, 1f),
                        BattleSkillEffectType.AttackBuff => new Color(1f, .82f, .2f),
                        BattleSkillEffectType.Stun => new Color(.72f, .5f, 1f),
                        _ => new Color(1f, .25f, .4f),
                    };
                    string label = battleEvent.skillEffectType == BattleSkillEffectType.Heal
                        ? $"+{battleEvent.damage}"
                        : battleEvent.skillEffectType.ToString();
                    worldPopup?.Show(targetView.PresentationAnchor, label, color, .75f);
                    BattleEffectType visualType = ToVisualEffect(battleEvent.skillEffectType);
                    if (effectSequence != null)
                        yield return effectSequence.Play(CreateEffectContext(visualType, battleEvent, attackerView, targetView));
                    else
                    {
                        targetView.SetCardSelected(true);
                        yield return Wait(.16f);
                        targetView.SetCardSelected(false);
                    }
                }
                RefreshStatusView(battleEvent.target);
                break;
            case BattlePresentationPhase.DamageApplied:
                SetActionStatus($"{battleEvent.damage} Damage");
                if(targetView!=null)worldPopup?.Show(targetView.PresentationAnchor,$"-{battleEvent.damage}",new Color(1f,.25f,.18f),1f);
                yield return Wait(damageDelay);
                break;
            case BattlePresentationPhase.HpUpdated:
                targetView?.PresentationData?.ApplyRuntime(battleEvent.target);
                yield return Wait(hpUpdateDuration);
                battleHud?.UpdateUnit(battleEvent.target, targetView);
                RefreshStatusView(battleEvent.target);
                break;
            case BattlePresentationPhase.ActionFinished:
                ClearCardTargets();
                if (battleEvent.target != null && !battleEvent.target.IsAlive)
                {
                    targetView?.SetCardSelected(false);
                    if (effectSequence != null && targetView != null)
                        yield return effectSequence.Play(CreateEffectContext(BattleEffectType.Defeat, battleEvent, attackerView, targetView));
                    else
                        targetView?.SetCardDead(true);
                }
                HideActionStatus();
                break;
            case BattlePresentationPhase.BattleFinished:
                ClearCardTargets();
                yield return ShowStatusFade(
                    $"{(battleEvent.playerWon ? "Victory" : "Defeat")}\nTurn {battleEvent.turn}",
                    resultDisplayDuration,
                    true);
                break;
        }
    }

    private static BattleEffectType ToVisualEffect(BattleSkillEffectType type) => type switch
    {
        BattleSkillEffectType.Heal => BattleEffectType.Heal,
        BattleSkillEffectType.Shield => BattleEffectType.Shield,
        BattleSkillEffectType.AttackBuff => BattleEffectType.Buff,
        BattleSkillEffectType.DamageOverTime => BattleEffectType.Dot,
        BattleSkillEffectType.DefenseDebuff or BattleSkillEffectType.Stun or BattleSkillEffectType.Taunt => BattleEffectType.Debuff,
        _ => BattleEffectType.Attack,
    };

    private static BattleEffectContext CreateEffectContext(
        BattleEffectType type,
        BattlePhase1Event battleEvent,
        BattleUnitView source,
        BattleUnitView target)
    {
        bool critical = battleEvent != null && battleEvent.target != null &&
                        battleEvent.damage >= Mathf.Max(30, Mathf.RoundToInt(battleEvent.target.maxHp * .28f));
        Color team = battleEvent != null && battleEvent.attacker != null &&
                     string.Equals(battleEvent.attacker.team, "Enemy", System.StringComparison.OrdinalIgnoreCase)
            ? new Color(1f, .14f, .08f)
            : new Color(.08f, .58f, 1f);
        return new BattleEffectContext
        {
            effectType = type,
            sourceUnit = source,
            targetUnit = target,
            amount = battleEvent == null ? 0 : battleEvent.damage,
            teamColor = team,
            attributeColor = Color.clear,
            isCritical = critical,
            isDefeat = type == BattleEffectType.Defeat
        };
    }

    private void EnsureBattleHud()
    {
        Configure3DStageVisibility();
        battleHud = GetComponentInChildren<BattleSceneHudView>(true);
        if (battleHud == null)
        {
            GameObject hudObject = new GameObject("BattleSceneHUD", typeof(RectTransform), typeof(BattleSceneHudView));
            hudObject.transform.SetParent(transform, false);
            battleHud = hudObject.GetComponent<BattleSceneHudView>();
            battleHud.Build(statusText == null ? null : statusText.font, playerBoardRoot, enemyBoardRoot);
        }
        worldPopup = GetComponent<BattleWorldPopupView>() ?? gameObject.AddComponent<BattleWorldPopupView>();
        worldPopup.Initialize(statusText);
    }

    private void Configure3DStageVisibility()
    {
        Image rootBackground = GetComponent<Image>();
        if (rootBackground != null)
        {
            Color color = rootBackground.color;
            color.a = 0f;
            rootBackground.color = color;
        }

        foreach (Image image in GetComponentsInChildren<Image>(true))
        {
            if (image.gameObject.name != "BattleField") continue;
            Color color = image.color;
            color.a = 0f;
            image.color = color;
            image.raycastTarget = false;
        }
    }

    private void ConfigureActionStatusPosition()
    {
        RectTransform rect = statusText == null ? null : statusText.rectTransform;
        if (rect == null) return;
        rect.anchorMin = new Vector2(0.35f, 0.82f); rect.anchorMax = new Vector2(0.65f, 0.90f);
        rect.offsetMin = rect.offsetMax = Vector2.zero;
        rect.SetAsLastSibling();
    }

    private void ConfigureBattleCamera()
    {
        Camera camera = Camera.main;
        if (camera == null) return;
        camera.transform.position = new Vector3(0f, 12f, -18f);
        camera.transform.rotation = Quaternion.Euler(32f, 0f, 0f);
        camera.orthographic = true;
        camera.orthographicSize = 7.8f;
        camera.fieldOfView = 50f;
    }

    private void HandleBattleCompleted(BattlePhase1Result result)
    {
        LastBattleResult = result;
        battleRoutine = null;
        if (statusText != null)
        {
            Color color = statusText.color;
            color.a = 1f;
            statusText.color = color;
        }
        WriteStatus(result.finished
            ? $"Battle Finished: {(result.playerWon ? "Win" : "Lose")} / Turn {result.turn}"
            : "Battle could not finish.");
        if (result.finished)
        {
            ShowBattleResult(result);
        }
    }

    private void ShowBattleResult(BattlePhase1Result result)
    {
        if (resultPanel == null)
        {
            GameObject resultObject = new GameObject(
                "BattleResultOverlay",
                typeof(RectTransform),
                typeof(UnityEngine.UI.Image),
                typeof(BattleResultView));
            resultObject.transform.SetParent(transform, false);
            resultPanel = resultObject.GetComponent<BattleResultView>();
        }
        resultPanel.gameObject.SetActive(true);
        try
        {
            BattleResultData data = result.battleResultData;
            if (data == null)
            {
                Debug.LogError("[BattleResult] BattleController did not produce BattleResultData.", this);
                return;
            }
            completedResultData = data;
            pendingReward = new RewardGenerator().Generate(data);
            SaveBattleHistory(data, pendingReward);
            resultPanel.Show(
                data,
                statusText == null ? null : statusText.font,
                ShowRewards,
                RetryBattle);
        }
        catch (System.Exception exc)
        {
            Debug.LogError("[BattleResult] Result display or JSON save failed: " + exc, this);
        }
    }

    private void ShowRewards()
    {
        if (completedResultData == null)
        {
            Debug.LogError("[Reward] BattleResultData is missing.", this);
            return;
        }
        if (pendingReward == null)
        {
            pendingReward = new RewardGenerator().Generate(completedResultData);
        }
        if (rewardView == null)
        {
            GameObject rewardObject = new GameObject(
                "BattleRewardOverlay",
                typeof(RectTransform),
                typeof(UnityEngine.UI.Image),
                typeof(RewardView));
            rewardObject.transform.SetParent(transform, false);
            rewardView = rewardObject.GetComponent<RewardView>();
        }
        rewardView.gameObject.SetActive(true);
        rewardView.Show(
            pendingReward,
            progressRepository.Load(),
            statusText == null ? null : statusText.font,
            ClaimRewardsAndReturn);
    }

    private void ClaimRewardsAndReturn()
    {
        if (pendingReward == null)
        {
            Debug.LogError("[Reward] No pending reward to claim.", this);
            return;
        }
        try
        {
            PlayerProgressData progress = progressRepository.ClaimAndSave(pendingReward);
            if (personalRepository != null && !string.IsNullOrWhiteSpace(ThoughtMapPersonalSession.Email))
            {
                StartCoroutine(personalRepository.SaveProgress(ThoughtMapPersonalSession.Email, progress, null));
                if (pendingReward.hasGeneratedSkill && !string.IsNullOrWhiteSpace(pendingReward.generatedSkillId))
                {
                    GeneratedSkillDto skill = GeneratedSkillLibrary.LoadFromStreamingAssets(GeneratedSkillLibrary.DefaultRelativePath)
                        .FirstOrDefault(item => item.skill_id == pendingReward.generatedSkillId);
                    if (skill != null)
                    {
                        StartCoroutine(personalRepository.SaveGeneratedSkill(
                            ThoughtMapPersonalSession.Email,
                            completedResultData == null ? "" : completedResultData.mvpCardId,
                            skill,
                            null));
                    }
                }
            }
            CampaignManager.Instance.CompleteCurrentStage(completedResultData != null && completedResultData.victory);
        }
        catch (System.Exception exc)
        {
            Debug.LogError("[Reward] Could not save player progress: " + exc, this);
            return;
        }
        ReturnToBattlePrep();
    }

    private void SaveBattleHistory(BattleResultData data, RewardData reward)
    {
        if (personalRepository == null || data == null) return;
        PersonalDeckLibrary decks = personalRepository.LoadDeckCache();
        BattleHistoryRecord record = new BattleHistoryRecord
        {
            battleId = System.Guid.NewGuid().ToString("N"),
            date = System.DateTime.UtcNow.ToString("o"),
            deckId = decks.lastUsedDeckId ?? "",
            stageId = CampaignManager.Instance.CurrentStage == null ? "" : CampaignManager.Instance.CurrentStage.stageId,
            victory = data.victory,
            turn = data.turnCount,
            mvp = data.mvpCardId,
            damage = data.statistics == null ? 0 : data.statistics.totalDamage,
            reward = reward,
            battleLog = data.battleLog == null ? new List<string>() : new List<string>(data.battleLog),
            cardIds = data.playerResults == null ? new List<string>() : data.playerResults.Select(item => item.cardId).Where(id => !string.IsNullOrWhiteSpace(id)).ToList(),
            skillIds = new List<string>()
        };
        StartCoroutine(personalRepository.SaveBattleHistory(ThoughtMapPersonalSession.Email, record, null));
    }

    private void ReturnToBattlePrep()
    {
        LoadSceneIfAvailable(battlePrepSceneName, "Battle Prep");
    }

    private void RetryBattle()
    {
        LoadSceneIfAvailable(SceneManager.GetActiveScene().name, "Battle Scene");
    }

    private void LoadSceneIfAvailable(string sceneName, string label)
    {
        if (string.IsNullOrWhiteSpace(sceneName))
        {
            Debug.LogError($"[BattleResult] {label} scene name is empty.", this);
            return;
        }
        if (!Application.CanStreamedLevelBeLoaded(sceneName))
        {
            Debug.LogError(
                $"[BattleResult] Cannot load {label} '{sceneName}'. Add and enable it in the active Unity 6 Build Profile Scene List.",
                this);
            return;
        }
        SceneManager.LoadScene(sceneName);
    }

    private void SetActionStatus(string value)
    {
        if (statusText == null)
        {
            return;
        }
        statusText.text = value;
        Color color = statusText.color;
        color.a = 1f;
        statusText.color = color;
    }

    private void HideActionStatus()
    {
        if (statusText == null)
        {
            return;
        }
        Color color = statusText.color;
        color.a = 0f;
        statusText.color = color;
    }

    private IEnumerator ShowStatusFade(string value, float duration, bool large)
    {
        if (statusText == null)
        {
            yield return Wait(duration);
            yield break;
        }

        float originalSize = statusText.fontSize;
        Color originalColor = statusText.color;
        statusText.text = value;
        statusText.fontSize = large ? originalSize * 1.6f : originalSize;
        float fadeDuration = Mathf.Min(0.2f, duration * 0.25f);
        float holdDuration = Mathf.Max(0f, duration - fadeDuration * 2f);
        yield return FadeStatus(0f, 1f, fadeDuration);
        yield return Wait(holdDuration);
        yield return FadeStatus(1f, 0f, fadeDuration);
        statusText.fontSize = originalSize;
        originalColor.a = 0f;
        statusText.color = originalColor;
    }

    private IEnumerator FadeStatus(float from, float to, float duration)
    {
        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            Color color = statusText.color;
            color.a = Mathf.Lerp(from, to, duration <= 0f ? 1f : Mathf.Clamp01(elapsed / duration));
            statusText.color = color;
            yield return null;
        }
        Color finalColor = statusText.color;
        finalColor.a = to;
        statusText.color = finalColor;
    }

    private static IEnumerator Wait(float seconds)
    {
        if (seconds > 0f)
        {
            yield return new WaitForSeconds(seconds);
        }
    }

    private Dictionary<string, List<GeneratedSkillDto>> ResolveAssignedSkills(ThoughtMapBattleDeckConfig config)
    {
        Dictionary<string, GeneratedSkillDto> library = GeneratedSkillLibrary.ToDictionary(
            GeneratedSkillLibrary.LoadFromStreamingAssets(GeneratedSkillLibrary.DefaultRelativePath)
        );
        Dictionary<string, List<GeneratedSkillDto>> result = new Dictionary<string, List<GeneratedSkillDto>>();
        if (config == null || config.assignedSkills == null)
        {
            return result;
        }
        foreach (CardAssignedSkillData assignment in config.assignedSkills)
        {
            if (assignment == null || string.IsNullOrWhiteSpace(assignment.cardId))
            {
                continue;
            }
            result[assignment.cardId] = assignment.skillIds == null
                ? new List<GeneratedSkillDto>()
                : assignment.skillIds
                    .Where(id => library.ContainsKey(id))
                    .Select(id => library[id])
                    .ToList();
        }
        return result;
    }

    private List<ThoughtMapGridPosition> ResolvePlayerPositions(ThoughtMapBattleDeckConfig config)
    {
        List<ThoughtMapGridPosition> positions = new List<ThoughtMapGridPosition>();
        if (config != null && config.gridPositions != null)
        {
            foreach (ThoughtMapBattleDeckPosition position in config.gridPositions.Take(5))
            {
                positions.Add(new ThoughtMapGridPosition(position.x, position.y));
            }
        }
        while (positions.Count < 5)
        {
            positions.Add(new ThoughtMapGridPosition(positions.Count, 0));
        }
        return positions;
    }

    private List<ThoughtMapGridPosition> ResolveEnemyVisualPositions(
        EnemyDeckData deck,
        IReadOnlyList<ThoughtMapBattleCardData> enemyCards)
    {
        List<ThoughtMapGridPosition> positions = new List<ThoughtMapGridPosition>();
        for (int i = 0; i < enemyCards.Count; i++)
        {
            string cardId = GetCardId(enemyCards[i]);
            ThoughtMapBattleDeckPosition saved = deck == null || deck.visualPositions == null
                ? null
                : deck.visualPositions.FirstOrDefault(position => position != null && position.cardId == cardId);
            positions.Add(saved == null
                ? new ThoughtMapGridPosition(i, 1)
                : new ThoughtMapGridPosition(saved.x, saved.y));
        }
        return positions;
    }

    private Sprite ResolveCardArt(ThoughtMapBattleCardData card, int index)
    {
        string key = ResolveDominantAttribute(card);
        Sprite template = ResolveMappedSprite(cardTemplateSprites, key);
        if (template != null)
        {
            return template;
        }
        if (cardArtPool != null && cardArtPool.Length > 0 && cardArtPool.Any(sprite => sprite != null))
        {
            Sprite[] available = cardArtPool.Where(sprite => sprite != null).ToArray();
            return available[Mathf.Abs(index) % available.Length];
        }
        return defaultCardArt;
    }

    private Sprite ResolveAttributeIcon(ThoughtMapBattleCardData card)
    {
        string key = ResolveDominantAttribute(card);
        return ResolveMappedSprite(attributeSprites, key) ?? defaultAttributeIcon;
    }

    private Sprite ResolveMappedSprite(AttributeSpriteMap[] maps, string attribute)
    {
        string key = NormalizeAttributeKey(attribute);
        if (maps != null)
        {
            foreach (AttributeSpriteMap map in maps)
            {
                if (map != null && map.sprite != null && NormalizeAttributeKey(map.attribute) == key)
                {
                    return map.sprite;
                }
            }
        }
        return null;
    }

    private string ResolveDominantAttribute(ThoughtMapBattleCardData card)
    {
        if (card == null || card.parameterScores == null || card.parameterScores.Count == 0)
        {
            return card == null ? string.Empty : card.primaryAttribute;
        }
        return card.parameterScores.OrderByDescending(pair => pair.Value).First().Key;
    }

    private string NormalizeAttributeKey(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return string.Empty;
        }
        string key = value.Trim().ToLowerInvariant();
        switch (key)
        {
            case "economics": return "economy";
            case "moral": return "morality";
            case "ideal": return "ideology";
            default: return key;
        }
    }

    private string GetCardId(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return "";
        }
        return !string.IsNullOrWhiteSpace(card.cardId) ? card.cardId : card.docId;
    }

    private void WriteStatus(string value)
    {
        if (statusText != null)
        {
            statusText.text = value;
        }
        Debug.Log("[ProductBattleScene] " + value, this);
    }

    private void ClearChildren(Transform root)
    {
        if (root == null)
        {
            return;
        }
        for (int i = root.childCount - 1; i >= 0; i--)
        {
            Destroy(root.GetChild(i).gameObject);
        }
    }
}
