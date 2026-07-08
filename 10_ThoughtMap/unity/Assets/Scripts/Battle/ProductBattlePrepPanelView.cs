using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public class ProductBattlePrepPanelView : MonoBehaviour
{
    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private string deckFileName = "deck.json";
    [SerializeField] private string battleSceneName = "BattleScene";
    [SerializeField] private bool loadCardsOnStart = true;

    [Header("Prefabs")]
    [SerializeField] private ProductBattleCardView cardViewPrefab;
    [SerializeField] private ProductBattleGridCellView gridCellPrefab;

    [Header("Scene References")]
    [SerializeField] private Transform cardListContent;
    [SerializeField] private Transform deckListContent;
    [SerializeField] private Transform formationGridContent;
    [SerializeField] private ProductBattleCardDetailPanelView cardDetailPanel;
    [SerializeField] private ProductBattleLogPanelView debugLogPanel;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private Button loadCardsButton;
    [SerializeField] private Button saveDeckButton;
    [SerializeField] private Button startBattleButton;
    [SerializeField] private Button simulateButton;
    [SerializeField] private Button clearButton;

    [Header("Sprites")]
    [SerializeField] private Sprite defaultCardArt;
    [SerializeField] private Sprite defaultAttributeIcon;
    [SerializeField] private Sprite[] cardArtPool;
    [SerializeField] private AttributeSpriteMap[] attributeSprites;

    [Header("Rules")]
    [SerializeField] private int deckLimit = 10;
    [SerializeField] private int deployLimit = 5;
    [SerializeField] private int cardListRenderLimit = 60;
    [SerializeField] private int playerRows = 3;

    private readonly List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();
    private readonly List<ThoughtMapBattleCardData> deckCards = new List<ThoughtMapBattleCardData>();
    private readonly Dictionary<int, ThoughtMapBattleCardData> placement = new Dictionary<int, ThoughtMapBattleCardData>();
    private readonly List<ProductBattleGridCellView> gridCells = new List<ProductBattleGridCellView>();
    private int selectedDeckIndex = -1;

    private void Awake()
    {
        WireButtons();
        CollectSceneGridCells();
        RenderGrid();
        cardDetailPanel?.Clear();
    }

    private void Start()
    {
        if (loadCardsOnStart)
        {
            LoadCards();
        }
    }

    private void WireButtons()
    {
        AddClick(loadCardsButton, LoadCards);
        AddClick(saveDeckButton, SaveDeckJson);
        AddClick(startBattleButton, StartBattleScene);
        AddClick(simulateButton, SimulatePreview);
        AddClick(clearButton, ClearPlacement);
    }

    [ContextMenu("Load Cards")]
    public void LoadCards()
    {
        loadedCards.Clear();
        deckCards.Clear();
        placement.Clear();
        selectedDeckIndex = -1;

        try
        {
            List<ThoughtMapBattleCardData> cards = cardsCsvAsset != null
                ? ThoughtMapCardsCsvLoader.LoadFromText(cardsCsvAsset.text)
                : ThoughtMapCardsCsvLoader.LoadFromStreamingAssets(streamingAssetsCsvPath);

            loadedCards.AddRange(cards);
            deckCards.AddRange(cards.Take(deckLimit));
            WriteStatus($"Loaded {loadedCards.Count} cards. Select a deck card, then place up to {deployLimit} cards.");
        }
        catch (System.Exception exc)
        {
            WriteStatus("Could not load cards.csv: " + exc.Message);
        }

        RenderAll();
    }

    public void ClearPlacement()
    {
        placement.Clear();
        selectedDeckIndex = -1;
        RenderAll();
        WriteStatus("Cleared formation.");
    }

    private void RenderAll()
    {
        RenderCardLibrary();
        RenderDeck();
        RenderGrid();
        ShowSelectedDetail();
    }

    private void RenderCardLibrary()
    {
        ClearChildren(cardListContent);
        if (cardViewPrefab == null || cardListContent == null)
        {
            return;
        }

        int count = Mathf.Min(loadedCards.Count, cardListRenderLimit);
        for (int i = 0; i < count; i++)
        {
            ProductBattleCardView view = Instantiate(cardViewPrefab, cardListContent);
            view.Bind(loadedCards[i], i, $"C{i + 1}", false, deckCards.Contains(loadedCards[i]), ResolveCardArt(i), ResolveAttributeIcon(loadedCards[i]));
        }
    }

    private void RenderDeck()
    {
        ClearChildren(deckListContent);
        if (cardViewPrefab == null || deckListContent == null)
        {
            return;
        }

        for (int i = 0; i < deckCards.Count; i++)
        {
            ProductBattleCardView view = Instantiate(cardViewPrefab, deckListContent);
            view.Bind(deckCards[i], i, $"P{i + 1}", i == selectedDeckIndex, placement.ContainsValue(deckCards[i]), ResolveCardArt(i), ResolveAttributeIcon(deckCards[i]));
            view.SetClickHandler(OnDeckCardClicked);
        }
    }

    private void RenderGrid()
    {
        EnsureGridCells();
        for (int index = 0; index < gridCells.Count; index++)
        {
            int x = index % 5;
            int y = index / 5;
            bool available = y < playerRows;
            if (placement.TryGetValue(index, out ThoughtMapBattleCardData card))
            {
                int deckIndex = deckCards.IndexOf(card);
                gridCells[index].BindCard(x, y, card, $"P{deckIndex + 1}", ResolveCardArt(deckIndex), ResolveAttributeIcon(card));
            }
            else
            {
                gridCells[index].BindEmpty(x, y, available);
            }
            gridCells[index].SetClickHandler(OnGridCellClicked);
        }
    }

    private void EnsureGridCells()
    {
        CollectSceneGridCells();
        if (gridCells.Count >= 25 || gridCellPrefab == null || formationGridContent == null)
        {
            return;
        }

        ClearChildren(formationGridContent);
        gridCells.Clear();
        for (int i = 0; i < 25; i++)
        {
            ProductBattleGridCellView cell = Instantiate(gridCellPrefab, formationGridContent);
            gridCells.Add(cell);
        }
    }

    private void CollectSceneGridCells()
    {
        if (formationGridContent == null)
        {
            return;
        }
        gridCells.Clear();
        gridCells.AddRange(formationGridContent.GetComponentsInChildren<ProductBattleGridCellView>(true));
    }

    private void OnDeckCardClicked(ProductBattleCardView view)
    {
        selectedDeckIndex = view == null ? -1 : view.Index;
        RenderDeck();
        ShowSelectedDetail();
        WriteStatus(selectedDeckIndex >= 0 ? $"Selected P{selectedDeckIndex + 1}." : "No card selected.");
    }

    private void OnGridCellClicked(ProductBattleGridCellView cell)
    {
        if (cell == null)
        {
            return;
        }

        int index = cell.Y * 5 + cell.X;
        if (placement.ContainsKey(index))
        {
            placement.Remove(index);
            RenderAll();
            WriteStatus("Removed card from formation.");
            return;
        }

        if (cell.Y >= playerRows)
        {
            WriteStatus("Place player cards on the near-side rows.");
            return;
        }

        if (selectedDeckIndex < 0 || selectedDeckIndex >= deckCards.Count)
        {
            WriteStatus("Select a deck card first.");
            return;
        }

        ThoughtMapBattleCardData selected = deckCards[selectedDeckIndex];
        int oldCell = placement.FirstOrDefault(pair => pair.Value == selected).Key;
        if (placement.ContainsValue(selected))
        {
            placement.Remove(oldCell);
        }
        else if (placement.Count >= deployLimit)
        {
            WriteStatus($"Deploy limit is {deployLimit}. Remove a card before placing another.");
            return;
        }

        placement[index] = selected;
        RenderAll();
        WriteStatus($"Placed P{selectedDeckIndex + 1} at ({cell.X + 1},{cell.Y + 1}).");
    }

    private void ShowSelectedDetail()
    {
        if (cardDetailPanel == null)
        {
            return;
        }

        if (selectedDeckIndex < 0 || selectedDeckIndex >= deckCards.Count)
        {
            cardDetailPanel.Clear();
            return;
        }

        ThoughtMapBattleCardData card = deckCards[selectedDeckIndex];
        cardDetailPanel.Show(card, ResolveCardArt(selectedDeckIndex), ResolveAttributeIcon(card));
    }

    public void SimulatePreview()
    {
        StringBuilder builder = new StringBuilder();
        builder.AppendLine("=== Battle Prep Preview ===");
        builder.AppendLine($"Deck Cards: {deckCards.Count}");
        builder.AppendLine($"Placed Cards: {placement.Count}/{deployLimit}");
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(pair => pair.Key))
        {
            int x = pair.Key % 5;
            int y = pair.Key / 5;
            builder.AppendLine($"P{deckCards.IndexOf(pair.Value) + 1} {pair.Value.cardName} @({x + 1},{y + 1})");
        }
        debugLogPanel?.SetCollapsed(false);
        debugLogPanel?.SetLog(builder.ToString());
        WriteStatus("Preview updated.");
    }

    public void SaveDeckJson()
    {
        ThoughtMapBattleDeckConfig config = new ThoughtMapBattleDeckConfig();
        config.deckCardIds = deckCards.Select(GetCardId).ToList();
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(pair => pair.Key))
        {
            int x = pair.Key % 5;
            int y = pair.Key / 5;
            config.deployedCardIds.Add(GetCardId(pair.Value));
            config.gridPositions.Add(new ThoughtMapBattleDeckPosition(GetCardId(pair.Value), x, y));
        }

        string path = Path.Combine(Application.persistentDataPath, deckFileName);
        File.WriteAllText(path, JsonUtility.ToJson(config, true), Encoding.UTF8);
        WriteStatus("Saved deck: " + path);
    }

    public void StartBattleScene()
    {
        SaveDeckJson();
        WriteStatus("Opening BattleScene: " + battleSceneName);
        SceneManager.LoadScene(battleSceneName);
    }

    private Sprite ResolveCardArt(int index)
    {
        if (cardArtPool != null && cardArtPool.Length > 0)
        {
            return cardArtPool[Mathf.Abs(index) % cardArtPool.Length];
        }
        return defaultCardArt;
    }

    private Sprite ResolveAttributeIcon(ThoughtMapBattleCardData card)
    {
        string key = card == null ? "" : card.primaryAttribute;
        if (attributeSprites != null)
        {
            foreach (AttributeSpriteMap map in attributeSprites)
            {
                if (!string.IsNullOrWhiteSpace(map.attribute) && map.attribute == key)
                {
                    return map.sprite;
                }
            }
        }
        return defaultAttributeIcon;
    }

    private void AddClick(Button button, UnityEngine.Events.UnityAction action)
    {
        if (button == null)
        {
            return;
        }
        button.onClick.RemoveListener(action);
        button.onClick.AddListener(action);
    }

    private void WriteStatus(string value)
    {
        if (statusText != null)
        {
            statusText.text = value;
        }
        Debug.Log("[ProductBattlePrep] " + value, this);
    }

    private string GetCardId(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return "";
        }
        return !string.IsNullOrWhiteSpace(card.cardId) ? card.cardId : card.docId;
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

[System.Serializable]
public class AttributeSpriteMap
{
    public string attribute;
    public Sprite sprite;
}
