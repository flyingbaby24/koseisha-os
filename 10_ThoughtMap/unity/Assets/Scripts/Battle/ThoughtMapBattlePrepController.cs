using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

public class ThoughtMapBattlePrepController : MonoBehaviour
{
    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private string deckFileName = "deck.json";

    [Header("MVP Selection")]
    [SerializeField] private int deckSize = 10;
    [SerializeField] private int deploySize = 5;
    [SerializeField] private string battleSceneName = "BattleScene";
    [SerializeField] private List<ThoughtMapGridPosition> defaultDeployPositions = new List<ThoughtMapGridPosition>
    {
        new ThoughtMapGridPosition(0, 0),
        new ThoughtMapGridPosition(1, 0),
        new ThoughtMapGridPosition(2, 0),
        new ThoughtMapGridPosition(3, 0),
        new ThoughtMapGridPosition(4, 0),
    };

    [Header("Optional UI")]
    [SerializeField] private TMP_Text savedWorksListText;
    [SerializeField] private TMP_Text cardPreviewText;
    [SerializeField] private TMP_Text deckSlotsText;
    [SerializeField] private TMP_Text deploySlotsText;
    [SerializeField] private TMP_Text placementPreviewText;
    [SerializeField] private TMP_Text statusText;

    private List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();
    private List<ThoughtMapBattleCardData> deckCards = new List<ThoughtMapBattleCardData>();
    private List<ThoughtMapBattleCardData> deployedCards = new List<ThoughtMapBattleCardData>();

    public string DeckSavePath => Path.Combine(Application.persistentDataPath, deckFileName);

    public void SetUiTargets(
        TMP_Text savedWorksList,
        TMP_Text cardPreview,
        TMP_Text deckSlots,
        TMP_Text deploySlots,
        TMP_Text placementPreview,
        TMP_Text status
    )
    {
        savedWorksListText = savedWorksList;
        cardPreviewText = cardPreview;
        deckSlotsText = deckSlots;
        deploySlotsText = deploySlots;
        placementPreviewText = placementPreview;
        statusText = status;
    }

    public void GenerateCards()
    {
        loadedCards = LoadCards();
        if (loadedCards.Count == 0)
        {
            WriteStatus("No cards loaded. Place cards.csv in StreamingAssets or assign a TextAsset.");
            ClearPreview();
            return;
        }

        deckCards = loadedCards.Take(deckSize).ToList();
        deployedCards = deckCards.Take(deploySize).ToList();
        RenderAll();
        WriteStatus($"Loaded {loadedCards.Count} cards. Deck {deckCards.Count}, Deploy {deployedCards.Count}.");
    }

    public void SaveDeck()
    {
        if (deckCards.Count == 0)
        {
            GenerateCards();
        }

        if (deckCards.Count == 0)
        {
            return;
        }

        ThoughtMapBattleDeckConfig config = BuildConfig();
        string json = JsonUtility.ToJson(config, true);
        File.WriteAllText(DeckSavePath, json, Encoding.UTF8);
        WriteStatus($"Saved deck.json: {DeckSavePath}");
    }

    public void StartBattle()
    {
        SaveDeck();
        if (!File.Exists(DeckSavePath))
        {
            WriteStatus("Battle not started. deck.json was not saved.");
            return;
        }

        SceneManager.LoadScene(battleSceneName);
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
            WriteStatus($"Could not load cards.csv: {exc.Message}");
            return new List<ThoughtMapBattleCardData>();
        }
    }

    private ThoughtMapBattleDeckConfig BuildConfig()
    {
        ThoughtMapBattleDeckConfig config = new ThoughtMapBattleDeckConfig();
        config.deckCardIds = deckCards.Select(GetCardId).ToList();
        config.deployedCardIds = deployedCards.Select(GetCardId).ToList();

        for (int i = 0; i < deployedCards.Count; i++)
        {
            ThoughtMapGridPosition position = i < defaultDeployPositions.Count
                ? defaultDeployPositions[i]
                : new ThoughtMapGridPosition(i % 5, 0);
            config.gridPositions.Add(new ThoughtMapBattleDeckPosition(GetCardId(deployedCards[i]), position.x, position.y));
        }

        return config;
    }

    private void RenderAll()
    {
        RenderSavedWorks();
        RenderCardPreview();
        RenderDeckSlots();
        RenderDeploySlots();
        RenderPlacementPreview();
    }

    private void RenderSavedWorks()
    {
        if (savedWorksListText == null)
        {
            return;
        }

        StringBuilder builder = new StringBuilder();
        builder.AppendLine("Saved Works List");
        builder.AppendLine("MVP source: cards.csv");
        foreach (ThoughtMapBattleCardData card in loadedCards.Take(12))
        {
            builder.AppendLine($"- {card.cardName} ({card.source})");
        }
        savedWorksListText.text = builder.ToString();
    }

    private void RenderCardPreview()
    {
        if (cardPreviewText == null)
        {
            return;
        }

        StringBuilder builder = new StringBuilder();
        builder.AppendLine("Card Preview");
        foreach (ThoughtMapBattleCardData card in loadedCards.Take(10))
        {
            builder.AppendLine($"{card.cardName} | {card.primaryAttribute}/{card.secondaryAttribute} | HP {card.MaxHp} | ATK {GetAttack(card)}");
        }
        cardPreviewText.text = builder.ToString();
    }

    private void RenderDeckSlots()
    {
        if (deckSlotsText == null)
        {
            return;
        }

        StringBuilder builder = new StringBuilder();
        builder.AppendLine("Deck Slots 10");
        for (int i = 0; i < deckSize; i++)
        {
            ThoughtMapBattleCardData card = i < deckCards.Count ? deckCards[i] : null;
            builder.AppendLine(card == null
                ? $"{i + 1:00}. Empty"
                : $"{i + 1:00}. {card.cardName} | {card.primaryAttribute} | HP {card.MaxHp} | ATK {GetAttack(card)}");
        }
        deckSlotsText.text = builder.ToString();
    }

    private void RenderDeploySlots()
    {
        if (deploySlotsText == null)
        {
            return;
        }

        StringBuilder builder = new StringBuilder();
        builder.AppendLine("Deploy Slots 5");
        for (int i = 0; i < deploySize; i++)
        {
            ThoughtMapBattleCardData card = i < deployedCards.Count ? deployedCards[i] : null;
            builder.AppendLine(card == null
                ? $"{i + 1}. Empty"
                : $"{i + 1}. {card.cardName} | {card.primaryAttribute} | HP {card.MaxHp} | ATK {GetAttack(card)}");
        }
        deploySlotsText.text = builder.ToString();
    }

    private void RenderPlacementPreview()
    {
        if (placementPreviewText == null)
        {
            return;
        }

        string[,] cells = new string[5, 5];
        for (int y = 0; y < 5; y++)
        {
            for (int x = 0; x < 5; x++)
            {
                cells[x, y] = "\u25A1";
            }
        }

        for (int i = 0; i < deployedCards.Count; i++)
        {
            ThoughtMapGridPosition position = i < defaultDeployPositions.Count
                ? defaultDeployPositions[i]
                : new ThoughtMapGridPosition(i % 5, 0);
            cells[position.x, position.y] = $"P{i + 1}";
        }

        StringBuilder builder = new StringBuilder();
        builder.AppendLine("5x5 Placement Preview");
        for (int y = 4; y >= 0; y--)
        {
            for (int x = 0; x < 5; x++)
            {
                builder.Append(cells[x, y].PadRight(4));
            }
            builder.AppendLine();
        }
        placementPreviewText.text = builder.ToString();
    }

    private void ClearPreview()
    {
        if (savedWorksListText != null) savedWorksListText.text = "Saved Works List\nNo cards loaded.";
        if (cardPreviewText != null) cardPreviewText.text = "Card Preview\nNo cards loaded.";
        if (deckSlotsText != null) deckSlotsText.text = "Deck Slots 10\nNo cards loaded.";
        if (deploySlotsText != null) deploySlotsText.text = "Deploy Slots 5\nNo cards loaded.";
        if (placementPreviewText != null) placementPreviewText.text = "5x5 Placement Preview\nNo cards loaded.";
    }

    private void WriteStatus(string message)
    {
        if (statusText != null)
        {
            statusText.text = message;
        }

        Debug.Log("[ThoughtMapBattlePrep] " + message, this);
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

    private int GetAttack(ThoughtMapBattleCardData card)
    {
        return card == null ? 0 : Mathf.Max(card.statPhysicalAttack, card.statSkillAttack);
    }
}
