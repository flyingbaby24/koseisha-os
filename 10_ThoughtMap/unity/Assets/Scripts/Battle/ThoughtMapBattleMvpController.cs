using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ThoughtMapBattleMvpController : MonoBehaviour
{
    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private bool useStreamingAssetsFallback = true;

    [Header("Deck Selection")]
    [SerializeField] private bool useDeckConfigFromPersistentData = true;
    [SerializeField] private string deckConfigFileName = "deck.json";
    [SerializeField] private int deckSize = 10;
    [SerializeField] private int deployedCount = 5;
    [SerializeField] private int playerDeckStartIndex = 0;
    [SerializeField] private int enemyDeckStartIndex = 10;
    [SerializeField] private bool mirrorPlayerDeckWhenEnemyMissing = true;
    [SerializeField] private List<int> playerDeployedDeckIndexes = new List<int> { 0, 1, 2, 3, 4 };
    [SerializeField] private List<int> enemyDeployedDeckIndexes = new List<int> { 0, 1, 2, 3, 4 };

    [Header("Grid Placement")]
    [SerializeField] private List<ThoughtMapGridPosition> playerPositions = new List<ThoughtMapGridPosition>
    {
        new ThoughtMapGridPosition(0, 0),
        new ThoughtMapGridPosition(1, 0),
        new ThoughtMapGridPosition(2, 0),
        new ThoughtMapGridPosition(3, 0),
        new ThoughtMapGridPosition(4, 0),
    };
    [SerializeField] private List<ThoughtMapGridPosition> enemyPositions = new List<ThoughtMapGridPosition>
    {
        new ThoughtMapGridPosition(0, 4),
        new ThoughtMapGridPosition(1, 4),
        new ThoughtMapGridPosition(2, 4),
        new ThoughtMapGridPosition(3, 4),
        new ThoughtMapGridPosition(4, 4),
    };

    [Header("Simulation")]
    [SerializeField] private int maxRounds = 20;
    [SerializeField] private bool runOnStart;

    [Header("Optional UI")]
    [SerializeField] private ThoughtMapBattleCardView cardViewPrefab;
    [SerializeField] private ThoughtMapBattleGridCellView gridCellViewPrefab;
    [SerializeField] private Transform gridRoot;
    [SerializeField] private Transform playerDeckRoot;
    [SerializeField] private Transform enemyDeckRoot;
    [SerializeField] private TMP_Text battleLogText;
    [SerializeField] private ScrollRect battleLogScrollRect;
    [SerializeField] private TMP_Text battleResultText;
    [SerializeField] private ThoughtMapBattleSummaryView battleSummaryView;
    [SerializeField] private TMP_Text turnText;
    [SerializeField] private TMP_Text warningText;

    private readonly List<ThoughtMapBattleGridCellView> gridCells = new List<ThoughtMapBattleGridCellView>();
    private List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();
    private List<ThoughtMapBattleCardData> playerDeckCards = new List<ThoughtMapBattleCardData>();
    private List<ThoughtMapBattleCardData> enemyDeckCards = new List<ThoughtMapBattleCardData>();
    private List<ThoughtMapBattleCardData> enemyDeployedCards = new List<ThoughtMapBattleCardData>();
    private readonly Dictionary<int, ThoughtMapBattleCardData> playerPlacement = new Dictionary<int, ThoughtMapBattleCardData>();
    private readonly List<ThoughtMapBattleCardView> playerCardViews = new List<ThoughtMapBattleCardView>();
    private readonly Dictionary<string, ThoughtMapBattleGridCellView> activeUnitCells = new Dictionary<string, ThoughtMapBattleGridCellView>();
    private int selectedPlayerDeckIndex = -1;
    private bool battleLocked;
    private bool prepared;
    private Coroutine battleAnimationRoutine;

    private void Start()
    {
        if (runOnStart)
        {
            RunBattle();
        }
    }

    [ContextMenu("Run Source of Thought Battle MVP")]
    public void Run()
    {
        RunBattle();
    }

    public void RunBattle()
    {
        if (!prepared)
        {
            PrepareBattle();
        }

        if (loadedCards.Count == 0)
        {
            WriteWarning("No cards loaded. Assign a cards.csv TextAsset or place cards.csv in StreamingAssets.");
            WriteLog("Battle did not start because cards.csv was not loaded.");
            return;
        }

        List<ThoughtMapBattleUnit> playerUnits = BuildPlayerUnitsFromPlacement();
        if (playerUnits.Count == 0)
        {
            WriteWarning("Place at least one Player card on the grid before starting battle.");
            return;
        }

        battleLocked = true;
        selectedPlayerDeckIndex = -1;
        SetPlacementInteractivity(false);
        List<ThoughtMapBattleUnit> enemyUnits = BuildUnits(enemyDeployedCards, "Enemy", enemyPositions);
        RenderGrid(playerUnits, enemyUnits);

        ThoughtMapBattleSimulator simulator = new ThoughtMapBattleSimulator();
        ThoughtMapBattleReport report = simulator.Simulate(playerUnits, enemyUnits, maxRounds, SetTurn);
        WriteLog(report.ToMultilineLog());
        string resultLabel = $"{ToPlayerResult(report.winner)} / Rounds: {report.rounds}";
        WriteResult(resultLabel);
        if (battleAnimationRoutine != null)
        {
            StopCoroutine(battleAnimationRoutine);
        }
        battleAnimationRoutine = StartCoroutine(PlayBattleEvents(report, resultLabel));
    }

    public void PrepareBattle()
    {
        ClearStatus();
        loadedCards = LoadCards();
        playerPlacement.Clear();
        playerCardViews.Clear();
        selectedPlayerDeckIndex = -1;
        battleLocked = false;
        prepared = false;

        if (loadedCards.Count == 0)
        {
            WriteWarning("No cards loaded. Assign a cards.csv TextAsset or place cards.csv in StreamingAssets.");
            WriteLog("Battle setup did not start because cards.csv was not loaded.");
            EnsureGridCells();
            return;
        }

        WriteInfo($"Loaded {loadedCards.Count} cards. Select Player cards, then click Player-side grid cells to reposition.");

        ThoughtMapBattleDeckConfig deckConfig = LoadDeckConfig();
        ThoughtMapDeckData playerDeck = BuildPlayerDeck(loadedCards, deckConfig);
        ThoughtMapDeckData enemyDeck = BuildEnemyDeck(loadedCards, playerDeck);
        playerDeckCards = playerDeck.cards.Take(deckSize).ToList();
        enemyDeckCards = enemyDeck.cards.Take(deckSize).ToList();
        enemyDeployedCards = SelectDeployedCards(enemyDeck, enemyDeployedDeckIndexes);

        List<ThoughtMapBattleCardData> defaultPlayerCards = SelectDeployedCards(playerDeck, playerDeployedDeckIndexes, deckConfig);
        List<ThoughtMapGridPosition> defaultPositions = GetPlayerPositions(deckConfig);
        for (int index = 0; index < defaultPlayerCards.Count && index < deployedCount; index++)
        {
            ThoughtMapGridPosition position = index < defaultPositions.Count
                ? defaultPositions[index]
                : new ThoughtMapGridPosition(index, 0);
            playerPlacement[ToCellIndex(position.x, position.y)] = defaultPlayerCards[index];
        }

        RenderDeckCards(playerDeckRoot, "Player", playerDeckCards);
        RenderDeckCards(enemyDeckRoot, "Enemy", enemyDeployedCards);
        RenderGrid(BuildPlayerUnitsFromPlacement(), BuildUnits(enemyDeployedCards, "Enemy", enemyPositions));
        SetPlacementInteractivity(true);
        prepared = true;
    }

    public void ResetPlacementMode()
    {
        PrepareBattle();
    }

    public void SetUiTargets(
        Transform playerDeck,
        Transform enemyDeck,
        TMP_Text battleLog,
        ScrollRect battleLogScroll,
        TMP_Text battleResult,
        ThoughtMapBattleSummaryView battleSummary,
        TMP_Text turn,
        TMP_Text warning,
        Transform grid
    )
    {
        playerDeckRoot = playerDeck;
        enemyDeckRoot = enemyDeck;
        battleLogText = battleLog;
        battleLogScrollRect = battleLogScroll;
        battleResultText = battleResult;
        battleSummaryView = battleSummary;
        turnText = turn;
        warningText = warning;
        gridRoot = grid;
        if (gridRoot != null && !prepared)
        {
            PrepareBattle();
        }
    }

    public List<ThoughtMapBattleCardData> LoadCards()
    {
        try
        {
            if (cardsCsvAsset != null)
            {
                return ThoughtMapCardsCsvLoader.LoadFromText(cardsCsvAsset.text);
            }

            if (useStreamingAssetsFallback)
            {
                return ThoughtMapCardsCsvLoader.LoadFromStreamingAssets(streamingAssetsCsvPath);
            }
        }
        catch (System.Exception exc)
        {
            WriteWarning($"Could not load cards.csv: {exc.Message}");
        }

        return new List<ThoughtMapBattleCardData>();
    }

    private ThoughtMapDeckData BuildPlayerDeck(List<ThoughtMapBattleCardData> cards, ThoughtMapBattleDeckConfig deckConfig)
    {
        if (deckConfig != null && deckConfig.HasDeck())
        {
            List<ThoughtMapBattleCardData> ordered = ResolveCardsById(cards, deckConfig.deckCardIds);
            if (ordered.Count > 0)
            {
                return new ThoughtMapDeckData(ordered, deckSize);
            }
        }

        return new ThoughtMapDeckData(cards.Skip(Mathf.Max(0, playerDeckStartIndex)), deckSize);
    }

    private ThoughtMapDeckData BuildEnemyDeck(List<ThoughtMapBattleCardData> cards, ThoughtMapDeckData playerDeck)
    {
        List<ThoughtMapBattleCardData> enemySource = cards.Skip(Mathf.Max(0, enemyDeckStartIndex)).Take(deckSize).ToList();
        if (enemySource.Count < deployedCount && mirrorPlayerDeckWhenEnemyMissing)
        {
            enemySource = playerDeck.cards.AsEnumerable().Reverse().ToList();
        }
        return new ThoughtMapDeckData(enemySource, deckSize);
    }

    private List<ThoughtMapBattleCardData> SelectDeployedCards(
        ThoughtMapDeckData deck,
        List<int> indexes,
        ThoughtMapBattleDeckConfig deckConfig = null
    )
    {
        if (deckConfig != null && deckConfig.deployedCardIds != null && deckConfig.deployedCardIds.Count > 0)
        {
            List<ThoughtMapBattleCardData> configured = ResolveCardsById(deck.cards, deckConfig.deployedCardIds);
            if (configured.Count > 0)
            {
                return configured.Take(deployedCount).ToList();
            }
        }

        List<ThoughtMapBattleCardData> selected = new List<ThoughtMapBattleCardData>();
        List<int> safeIndexes = indexes == null || indexes.Count == 0
            ? Enumerable.Range(0, deployedCount).ToList()
            : indexes;

        foreach (int index in safeIndexes)
        {
            if (selected.Count >= deployedCount)
            {
                break;
            }

            if (index >= 0 && index < deck.cards.Count)
            {
                selected.Add(deck.cards[index]);
            }
        }

        foreach (ThoughtMapBattleCardData card in deck.cards)
        {
            if (selected.Count >= deployedCount)
            {
                break;
            }

            if (!selected.Contains(card))
            {
                selected.Add(card);
            }
        }

        return selected;
    }

    private List<ThoughtMapGridPosition> GetPlayerPositions(ThoughtMapBattleDeckConfig deckConfig)
    {
        if (deckConfig == null || deckConfig.gridPositions == null || deckConfig.gridPositions.Count == 0)
        {
            return playerPositions;
        }

        List<ThoughtMapGridPosition> positions = new List<ThoughtMapGridPosition>();
        foreach (ThoughtMapBattleDeckPosition position in deckConfig.gridPositions.Take(deployedCount))
        {
            positions.Add(new ThoughtMapGridPosition(position.x, position.y));
        }
        return positions.Count > 0 ? positions : playerPositions;
    }

    private ThoughtMapBattleDeckConfig LoadDeckConfig()
    {
        if (!useDeckConfigFromPersistentData)
        {
            return null;
        }

        string path = Path.Combine(Application.persistentDataPath, deckConfigFileName);
        if (!File.Exists(path))
        {
            return null;
        }

        try
        {
            ThoughtMapBattleDeckConfig config = JsonUtility.FromJson<ThoughtMapBattleDeckConfig>(File.ReadAllText(path, Encoding.UTF8));
            if (config != null && config.HasDeck())
            {
                WriteInfo($"Loaded deck.json: {path}");
                return config;
            }
        }
        catch (System.Exception exc)
        {
            WriteWarning($"Could not read deck.json: {exc.Message}");
        }

        return null;
    }

    private List<ThoughtMapBattleCardData> ResolveCardsById(IEnumerable<ThoughtMapBattleCardData> source, List<string> ids)
    {
        List<ThoughtMapBattleCardData> resolved = new List<ThoughtMapBattleCardData>();
        if (source == null || ids == null)
        {
            return resolved;
        }

        List<ThoughtMapBattleCardData> sourceList = source.Where(card => card != null).ToList();
        foreach (string id in ids)
        {
            ThoughtMapBattleCardData match = sourceList.FirstOrDefault(card => GetCardId(card) == id);
            if (match != null && !resolved.Contains(match))
            {
                resolved.Add(match);
            }
        }
        return resolved;
    }

    private List<ThoughtMapBattleUnit> BuildUnits(
        List<ThoughtMapBattleCardData> cards,
        string team,
        List<ThoughtMapGridPosition> positions
    )
    {
        List<ThoughtMapBattleUnit> units = new List<ThoughtMapBattleUnit>();
        for (int i = 0; i < cards.Count && i < deployedCount; i++)
        {
            ThoughtMapGridPosition position = i < positions.Count
                ? positions[i]
                : new ThoughtMapGridPosition(i % 5, team == "Player" ? 0 : 4);
            ThoughtMapBattleUnit unit = new ThoughtMapBattleUnit(cards[i], team, position);
            unit.battleId = $"{(team == "Player" ? "P" : "E")}{i + 1}";
            units.Add(unit);
        }
        return units;
    }

    private void RenderDeckCards(Transform root, string team, List<ThoughtMapBattleCardData> deployed)
    {
        if (root == null)
        {
            return;
        }

        ClearChildren(root);
        if (team == "Player")
        {
            playerCardViews.Clear();
        }
        for (int index = 0; index < deployed.Count; index++)
        {
            ThoughtMapBattleCardView cardView = CreateCardView(root, $"{team}Card_{index + 1:00}");
            string id = $"{(team == "Player" ? "P" : "E")}{index + 1}";
            cardView.Bind(deployed[index], index, team, id, team == "Player" && IsCardPlaced(deployed[index]));
            bool player = team == "Player";
            cardView.SetInteractable(player && !battleLocked);
            if (player)
            {
                cardView.SetClickHandler(OnPlayerDeckCardClicked);
            }
            else
            {
                cardView.SetClickHandler(null);
            }
            if (player)
            {
                playerCardViews.Add(cardView);
            }
        }
    }

    private void RenderGrid(List<ThoughtMapBattleUnit> playerUnits, List<ThoughtMapBattleUnit> enemyUnits)
    {
        if (gridRoot == null)
        {
            return;
        }

        EnsureGridCells();
        activeUnitCells.Clear();
        int cellIndex = 0;
        foreach (ThoughtMapBattleGridCellView cell in gridCells)
        {
            cell.BindEmpty(cellIndex % 5, cellIndex / 5);
            cellIndex++;
        }

        foreach (ThoughtMapBattleUnit unit in playerUnits.Concat(enemyUnits))
        {
            int index = unit.position.y * 5 + unit.position.x;
            if (index < 0 || index >= gridCells.Count)
            {
                continue;
            }

            gridCells[index].BindUnit(unit);
            if (!string.IsNullOrWhiteSpace(unit.battleId))
            {
                activeUnitCells[unit.battleId] = gridCells[index];
            }
        }

        if (!battleLocked)
        {
            UpdateGridHints();
        }
    }

    private void EnsureGridCells()
    {
        if (gridCells.Count == 25)
        {
            return;
        }

        gridCells.Clear();
        for (int i = gridRoot.childCount - 1; i >= 0; i--)
        {
            DestroyRuntimeObject(gridRoot.GetChild(i).gameObject);
        }

        GridLayoutGroup layout = gridRoot.GetComponent<GridLayoutGroup>();
        if (layout == null)
        {
            layout = gridRoot.gameObject.AddComponent<GridLayoutGroup>();
        }
        layout.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        layout.constraintCount = 5;
        layout.cellSize = new Vector2(140f, 56f);
        layout.spacing = new Vector2(6f, 6f);
        layout.padding = new RectOffset(0, 0, 0, 0);
        layout.childAlignment = TextAnchor.MiddleCenter;

        for (int i = 0; i < 25; i++)
        {
            ThoughtMapBattleGridCellView cell = CreateGridCellView(gridRoot, $"BattleCell_{i:00}");
            cell.BuildIfNeeded();
            cell.SetClickHandler(OnGridCellClicked);
            cell.BindEmpty(i % 5, i / 5);
            gridCells.Add(cell);
        }
    }

    private List<ThoughtMapBattleUnit> BuildPlayerUnitsFromPlacement()
    {
        List<ThoughtMapBattleUnit> units = new List<ThoughtMapBattleUnit>();
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> entry in playerPlacement.OrderBy(item => item.Key))
        {
            int x = entry.Key % 5;
            int y = entry.Key / 5;
            ThoughtMapBattleUnit unit = new ThoughtMapBattleUnit(entry.Value, "Player", new ThoughtMapGridPosition(x, y));
            int deckIndex = playerDeckCards.IndexOf(entry.Value);
            unit.battleId = $"P{(deckIndex >= 0 ? deckIndex + 1 : units.Count + 1)}";
            units.Add(unit);
        }
        return units;
    }

    private bool IsCardPlaced(ThoughtMapBattleCardData card)
    {
        return card != null && playerPlacement.ContainsValue(card);
    }

    private void OnPlayerDeckCardClicked(ThoughtMapBattleCardView cardView)
    {
        if (battleLocked || cardView == null || cardView.Card == null)
        {
            return;
        }

        selectedPlayerDeckIndex = cardView.SlotIndex;
        UpdateSelectionVisuals();
        WriteInfo($"Selected card: {cardView.Card.cardName}. Click a Player-side grid cell to place it.");
    }

    private void OnGridCellClicked(ThoughtMapBattleGridCellView cellView)
    {
        if (battleLocked || cellView == null)
        {
            return;
        }

        int cellIndex = ToCellIndex(cellView.X, cellView.Y);
        if (cellView.Unit != null && cellView.Unit.team == "Player")
        {
        playerPlacement.Remove(cellIndex);
            RenderDeckCards(playerDeckRoot, "Player", playerDeckCards);
            RenderGrid(BuildPlayerUnitsFromPlacement(), BuildUnits(enemyDeployedCards, "Enemy", enemyPositions));
            WriteInfo("Removed Player card from grid.");
            return;
        }

        if (!IsPlayerPlacementCell(cellView.X, cellView.Y))
        {
            WriteWarning("Player cards can only be placed on the lower Player-side rows.");
            return;
        }

        if (selectedPlayerDeckIndex < 0 || selectedPlayerDeckIndex >= playerDeckCards.Count)
        {
            WriteWarning("Select a Player Deck card first.");
            return;
        }

        ThoughtMapBattleCardData selectedCard = playerDeckCards[selectedPlayerDeckIndex];
        int previousCell = playerPlacement.FirstOrDefault(item => item.Value == selectedCard).Key;
        if (playerPlacement.ContainsValue(selectedCard) && previousCell != cellIndex)
        {
            playerPlacement.Remove(previousCell);
        }

        if (!playerPlacement.ContainsKey(cellIndex) && playerPlacement.Count >= deployedCount && !playerPlacement.ContainsValue(selectedCard))
        {
            WriteWarning($"Only {deployedCount} Player cards can be deployed in the MVP.");
            return;
        }

        playerPlacement[cellIndex] = selectedCard;
        RenderDeckCards(playerDeckRoot, "Player", playerDeckCards);
        RenderGrid(BuildPlayerUnitsFromPlacement(), BuildUnits(enemyDeployedCards, "Enemy", enemyPositions));
        UpdateSelectionVisuals();
        WriteInfo($"Placed {selectedCard.cardName} at ({cellView.X},{cellView.Y}).");
    }

    private void SetPlacementInteractivity(bool interactable)
    {
        foreach (ThoughtMapBattleCardView cardView in playerCardViews)
        {
            if (cardView != null)
            {
                cardView.SetInteractable(interactable);
                cardView.SetSelected(false);
            }
        }

        foreach (ThoughtMapBattleGridCellView cellView in gridCells)
        {
            if (cellView != null)
            {
                cellView.SetInteractable(interactable);
            }
        }
    }

    private void UpdateSelectionVisuals()
    {
        foreach (ThoughtMapBattleCardView cardView in playerCardViews)
        {
            if (cardView != null)
            {
                cardView.SetSelected(cardView.SlotIndex == selectedPlayerDeckIndex);
            }
        }

        UpdateGridHints();
    }

    private void UpdateGridHints()
    {
        foreach (ThoughtMapBattleGridCellView cellView in gridCells)
        {
            if (cellView != null)
            {
                cellView.SetPlacementHint(selectedPlayerDeckIndex >= 0 && IsPlayerPlacementCell(cellView.X, cellView.Y));
            }
        }
    }

    private IEnumerator PlayBattleEvents(ThoughtMapBattleReport report, string resultLabel)
    {
        if (report == null)
        {
            yield break;
        }

        foreach (ThoughtMapBattleEvent battleEvent in report.events)
        {
            SetTurn(battleEvent.round);
            activeUnitCells.TryGetValue(battleEvent.targetId, out ThoughtMapBattleGridCellView targetCell);
            if (activeUnitCells.TryGetValue(battleEvent.attackerId, out ThoughtMapBattleGridCellView attackerCell))
            {
                Vector3 targetPosition = targetCell == null ? attackerCell.transform.localPosition : targetCell.transform.localPosition;
                yield return attackerCell.PlayAttackToward(targetPosition);
            }

            if (targetCell != null)
            {
                targetCell.UpdateHp(battleEvent.targetHp, battleEvent.targetMaxHp);
                yield return targetCell.PlayHit(battleEvent.damage, battleEvent.defeated);
            }

            yield return new WaitForSeconds(0.08f);
        }

        ShowSummary(resultLabel, report);
    }

    private bool IsPlayerPlacementCell(int x, int y)
    {
        return x >= 0 && x < 5 && y >= 0 && y <= 2;
    }

    private int ToCellIndex(int x, int y)
    {
        return Mathf.Clamp(y, 0, 4) * 5 + Mathf.Clamp(x, 0, 4);
    }

    private ThoughtMapBattleCardView CreateCardView(Transform parent, string objectName)
    {
        ThoughtMapBattleCardView view;
        if (cardViewPrefab != null)
        {
            view = Instantiate(cardViewPrefab, parent, false);
            view.gameObject.name = objectName;
        }
        else
        {
            GameObject cardObject = new GameObject(objectName, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ThoughtMapBattleCardView));
            cardObject.transform.SetParent(parent, false);
            view = cardObject.GetComponent<ThoughtMapBattleCardView>();
        }

        return view;
    }

    private ThoughtMapBattleGridCellView CreateGridCellView(Transform parent, string objectName)
    {
        ThoughtMapBattleGridCellView view;
        if (gridCellViewPrefab != null)
        {
            view = Instantiate(gridCellViewPrefab, parent, false);
            view.gameObject.name = objectName;
        }
        else
        {
            GameObject cellObject = new GameObject(objectName, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ThoughtMapBattleGridCellView));
            cellObject.transform.SetParent(parent, false);
            view = cellObject.GetComponent<ThoughtMapBattleGridCellView>();
        }

        return view;
    }

    private string GetCardId(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return "";
        }

        if (!string.IsNullOrWhiteSpace(card.cardId))
        {
            return card.cardId;
        }

        return card.docId;
    }

    private string ToPlayerResult(string winner)
    {
        if (winner == "Player")
        {
            return "Victory";
        }

        if (winner == "Enemy")
        {
            return "Defeat";
        }

        return "Draw";
    }

    private void WriteLog(string message)
    {
        if (battleLogText != null)
        {
            battleLogText.text = message;
            ScrollLogToBottom();
        }
        Debug.Log("[ThoughtMapBattle]\n" + message, this);
    }

    private void WriteResult(string message)
    {
        if (battleResultText != null)
        {
            battleResultText.text = message;
        }
        Debug.Log("[ThoughtMapBattle] " + message, this);
    }

    private void ShowSummary(string resultLabel, ThoughtMapBattleReport report)
    {
        if (battleSummaryView != null)
        {
            battleSummaryView.ShowReport(resultLabel, report);
        }
        Debug.Log("[ThoughtMapBattle]\n" + report.ToSummaryText(), this);
    }

    private void SetTurn(int turn)
    {
        if (turnText != null)
        {
            turnText.text = $"Turn {turn}";
        }
    }

    private void WriteWarning(string message)
    {
        if (warningText != null)
        {
            warningText.text = message;
            warningText.gameObject.SetActive(true);
        }
        Debug.LogWarning("[ThoughtMapBattle] " + message, this);
    }

    private void WriteInfo(string message)
    {
        if (warningText != null)
        {
            warningText.text = message;
            warningText.gameObject.SetActive(true);
        }

        if (battleLogText != null)
        {
            battleLogText.text = message;
            ScrollLogToBottom();
        }

        Debug.Log("[ThoughtMapBattle] " + message, this);
    }

    private void ClearStatus()
    {
        if (warningText != null)
        {
            warningText.text = "";
            warningText.gameObject.SetActive(false);
        }
        if (battleResultText != null)
        {
            battleResultText.text = "Battle not started.";
        }
        if (battleSummaryView != null)
        {
            battleSummaryView.ShowPending();
        }
        if (turnText != null)
        {
            turnText.text = "Turn 0";
        }
        if (battleLogText != null)
        {
            battleLogText.text = "";
            ScrollLogToBottom();
        }
    }

    private void ScrollLogToBottom()
    {
        if (battleLogScrollRect != null)
        {
            Canvas.ForceUpdateCanvases();
            battleLogScrollRect.verticalNormalizedPosition = 0f;
        }
    }

    private void DestroyRuntimeObject(Object target)
    {
        if (target == null)
        {
            return;
        }

        if (Application.isPlaying)
        {
            Destroy(target);
        }
        else
        {
            DestroyImmediate(target);
        }
    }

    private void ClearChildren(Transform root)
    {
        if (root == null)
        {
            return;
        }

        for (int i = root.childCount - 1; i >= 0; i--)
        {
            DestroyRuntimeObject(root.GetChild(i).gameObject);
        }
    }
}
