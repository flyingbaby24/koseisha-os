using System.Collections.Generic;
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
    [SerializeField] private Transform gridRoot;
    [SerializeField] private TMP_Text playerDeckText;
    [SerializeField] private TMP_Text enemyDeckText;
    [SerializeField] private TMP_Text battleLogText;

    private readonly List<TMP_Text> gridCells = new List<TMP_Text>();
    private List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();

    private void Start()
    {
        if (runOnStart)
        {
            RunBattle();
        }
    }

    [ContextMenu("Run ThoughtMap Battle MVP")]
    public void RunBattle()
    {
        loadedCards = LoadCards();
        if (loadedCards.Count == 0)
        {
            WriteLog("No cards loaded. Assign a cards.csv TextAsset or place cards.csv in StreamingAssets.");
            return;
        }

        ThoughtMapDeckData playerDeck = BuildPlayerDeck(loadedCards);
        ThoughtMapDeckData enemyDeck = BuildEnemyDeck(loadedCards, playerDeck);
        List<ThoughtMapBattleCardData> playerCards = SelectDeployedCards(playerDeck, playerDeployedDeckIndexes);
        List<ThoughtMapBattleCardData> enemyCards = SelectDeployedCards(enemyDeck, enemyDeployedDeckIndexes);

        List<ThoughtMapBattleUnit> playerUnits = BuildUnits(playerCards, "Player", playerPositions);
        List<ThoughtMapBattleUnit> enemyUnits = BuildUnits(enemyCards, "Enemy", enemyPositions);

        RenderDeckSummary(playerDeckText, "Player Deck", playerDeck.cards, playerCards);
        RenderDeckSummary(enemyDeckText, "Enemy Deck", enemyDeck.cards, enemyCards);
        RenderGrid(playerUnits, enemyUnits);

        ThoughtMapBattleSimulator simulator = new ThoughtMapBattleSimulator();
        ThoughtMapBattleReport report = simulator.Simulate(playerUnits, enemyUnits, maxRounds);
        WriteLog(report.ToMultilineLog());
    }

    public List<ThoughtMapBattleCardData> LoadCards()
    {
        if (cardsCsvAsset != null)
        {
            return ThoughtMapCardsCsvLoader.LoadFromText(cardsCsvAsset.text);
        }

        if (useStreamingAssetsFallback)
        {
            return ThoughtMapCardsCsvLoader.LoadFromStreamingAssets(streamingAssetsCsvPath);
        }

        return new List<ThoughtMapBattleCardData>();
    }

    private ThoughtMapDeckData BuildPlayerDeck(List<ThoughtMapBattleCardData> cards)
    {
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

    private List<ThoughtMapBattleCardData> SelectDeployedCards(ThoughtMapDeckData deck, List<int> indexes)
    {
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
            units.Add(new ThoughtMapBattleUnit(cards[i], team, position));
        }
        return units;
    }

    private void RenderDeckSummary(
        TMP_Text target,
        string title,
        List<ThoughtMapBattleCardData> deck,
        List<ThoughtMapBattleCardData> deployed
    )
    {
        if (target == null)
        {
            return;
        }

        StringBuilder builder = new StringBuilder();
        builder.AppendLine(title);
        builder.AppendLine($"Deck: {deck.Count} / Deployed: {deployed.Count}");
        foreach (ThoughtMapBattleCardData card in deployed)
        {
            builder.AppendLine(
                $"{card.cardName} [{card.primaryAttribute}/{card.secondaryAttribute}] " +
                $"ATK {card.statPhysicalAttack}/{card.statSkillAttack} DEF {card.statPhysicalDefense}/{card.statSkillDefense} HP {card.MaxHp}"
            );
        }
        target.text = builder.ToString();
    }

    private void RenderGrid(List<ThoughtMapBattleUnit> playerUnits, List<ThoughtMapBattleUnit> enemyUnits)
    {
        if (gridRoot == null)
        {
            return;
        }

        EnsureGridCells();
        foreach (TMP_Text cell in gridCells)
        {
            cell.text = "";
        }

        foreach (ThoughtMapBattleUnit unit in playerUnits.Concat(enemyUnits))
        {
            int index = unit.position.y * 5 + unit.position.x;
            if (index < 0 || index >= gridCells.Count)
            {
                continue;
            }

            string prefix = unit.team == "Player" ? "P" : "E";
            gridCells[index].text = $"{prefix}\n{ShortName(unit.card.cardName)}\n{unit.card.primaryAttribute}";
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
            layout.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
            layout.constraintCount = 5;
            layout.cellSize = new Vector2(120f, 78f);
            layout.spacing = new Vector2(8f, 8f);
        }

        for (int i = 0; i < 25; i++)
        {
            GameObject cellObject = new GameObject($"BattleCell_{i:00}", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
            cellObject.transform.SetParent(gridRoot, false);
            Image image = cellObject.GetComponent<Image>();
            image.color = new Color(0.02f, 0.11f, 0.16f, 0.78f);

            GameObject textObject = new GameObject("Label", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
            RectTransform textRect = textObject.GetComponent<RectTransform>();
            textRect.SetParent(cellObject.transform, false);
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = new Vector2(4f, 4f);
            textRect.offsetMax = new Vector2(-4f, -4f);
            TMP_Text text = textObject.GetComponent<TMP_Text>();
            text.fontSize = 14;
            text.alignment = TextAlignmentOptions.Center;
            text.color = Color.white;
            gridCells.Add(text);
        }
    }

    private string ShortName(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "Card";
        }
        return value.Length <= 18 ? value : value.Substring(0, 18) + "...";
    }

    private void WriteLog(string message)
    {
        if (battleLogText != null)
        {
            battleLogText.text = message;
        }
        Debug.Log("[ThoughtMapBattle]\n" + message, this);
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
}
