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
    private const float LightweightRowHeight = 50f;
    private const float LightweightRowSpacing = 4f;
    private static readonly string[] ExpectedTemplateKeys =
    {
        "philosophy", "psychology", "science", "economy", "karma",
        "emotion", "morality", "ideology", "individual", "community"
    };
    private static readonly ThoughtParameterDefinition[] ThoughtParameterOrder =
    {
        new ThoughtParameterDefinition("philosophy", "philosophy", "\u54F2\u5B66"),
        new ThoughtParameterDefinition("psychology", "psychology", "\u5FC3\u7406"),
        new ThoughtParameterDefinition("science", "science", "\u79D1\u5B66"),
        new ThoughtParameterDefinition("economy", "economy", "economics", "\u7D4C\u6E08"),
        new ThoughtParameterDefinition("karma", "karma", "\u30AB\u30EB\u30DE"),
        new ThoughtParameterDefinition("emotion", "emotion", "\u611F\u60C5"),
        new ThoughtParameterDefinition("morality", "morality", "moral", "\u30E2\u30E9\u30EB"),
        new ThoughtParameterDefinition("ideology", "ideology", "ideal", "\u7406\u5FF5"),
        new ThoughtParameterDefinition("individual", "individual", "\u500B\u4EBA"),
        new ThoughtParameterDefinition("community", "community", "\u5171\u540C\u4F53")
    };
    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private string deckFileName = "deck.json";
    [SerializeField] private string battleSceneName = "BattleScene";
    [SerializeField] private string generatedSkillsRelativePath = GeneratedSkillLibrary.DefaultRelativePath;
    [SerializeField] private bool loadCardsOnStart = true;
    [SerializeField] private bool autoFillDeckOnLoad;
    [SerializeField] private bool debugGeneratedSkills;
    [SerializeField] private bool debugBattlePrepLayout;
    [SerializeField] private bool showAllGeneratedSkillsWhenNoDeckMatch = true;

    [Header("Personal Library API")]
    [SerializeField] private ThoughtMapPersonalLibraryApiClient personalLibraryApiClient;
    [SerializeField] private TMP_InputField personalEmailInput;
    [SerializeField] private Button loadPersonalLibraryButton;
    [SerializeField] private string personalLibraryEmail;
    [SerializeField] private bool fallbackToSampleCardsOnApiError = true;

    [Header("Prefabs")]
    [SerializeField] private ProductBattleCardListRowView cardListRowPrefab;
    [SerializeField] private ProductBattleCardListRowView deckListRowPrefab;
    [SerializeField] private ProductBattleGridCellView gridCellPrefab;

    [Header("Scene References")]
    [SerializeField] private Transform cardListContent;
    [SerializeField] private Transform deckListContent;
    [SerializeField] private Transform formationGridContent;
    [SerializeField] private ProductBattleCardDetailPanelView cardDetailPanel;
    [SerializeField] private ProductBattleGeneratedSkillsPanelView generatedSkillsPanel;
    [SerializeField] private ProductBattleLogPanelView debugLogPanel;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private Button loadCardsButton;
    [SerializeField] private Button addToDeckButton;
    [SerializeField] private Button saveDeckButton;
    [SerializeField] private Button startBattleButton;
    [SerializeField] private Button simulateButton;
    [SerializeField] private Button clearButton;

    [Header("Background")]
    [SerializeField] private Sprite battlePrepBackground;
    [SerializeField] private Image backgroundImage;
    [SerializeField] private Image darkOverlayImage;
    [SerializeField] private Color darkOverlayColor = new Color(0f, 0f, 0f, 0.25f);
    [SerializeField] private bool softenPanelForBackground = true;
    [SerializeField, Range(0f, 1f)] private float battlePrepOverlayAlpha = 0.25f;
    [SerializeField, Range(0f, 1f)] private float panelBackgroundAlpha = 0.62f;

    [Header("Sprites")]
    [SerializeField] private Sprite defaultCardArt;
    [SerializeField] private Sprite defaultAttributeIcon;
    [SerializeField] private Sprite[] cardArtPool;
    [SerializeField] private AttributeSpriteMap[] attributeSprites;
    [SerializeField] private AttributeSpriteMap[] cardTemplateSprites;

    [Header("Fonts")]
    [SerializeField] private TMP_FontAsset cjkFontAsset;

    [Header("Rules")]
    [SerializeField] private int deckLimit = 10;
    [SerializeField] private int deployLimit = 5;
    [SerializeField] private int cardListRenderLimit = 60;
    [SerializeField] private int playerRows = 5;
    [SerializeField] private bool logFormationGridCells;
    [SerializeField] private ThoughtMapBattleResonanceConfig resonanceConfig;

    private readonly List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();
    private readonly List<ThoughtMapBattleCardData> deckCards = new List<ThoughtMapBattleCardData>();
    private readonly Dictionary<int, ThoughtMapBattleCardData> placement = new Dictionary<int, ThoughtMapBattleCardData>();
    private readonly List<GeneratedSkillDto> loadedGeneratedSkills = new List<GeneratedSkillDto>();
    private readonly List<GeneratedSkillDto> generatedSkills = new List<GeneratedSkillDto>();
    private readonly Dictionary<string, GeneratedSkillDto> generatedSkillById = new Dictionary<string, GeneratedSkillDto>();
    private readonly Dictionary<string, List<string>> assignedSkillIdsByCardId = new Dictionary<string, List<string>>();
    private readonly List<ProductBattleGridCellView> gridCells = new List<ProductBattleGridCellView>();
    private int selectedDeckIndex = -1;
    private int selectedLibraryIndex = -1;
    private string selectedGeneratedSkillId = "";
    private ThoughtMapBattleResonanceCalculator resonanceCalculator;

    private void Awake()
    {
        EnsureFormationRules();
        EnsureResonanceCalculator();
        EnsurePersonalLibraryApiClient();
        WireButtons();
        EnsureTopControlReadability();
        EnsureBattlePrepBackground();
        EnsurePanelTransparency();
        EnsureReadableTextEffects();
        ApplyResolvedFontToBattlePrepTexts();
        EnsureListContentReferences();
        if (cardListContent != null)
        {
            NormalizeLightweightListScrollArea(cardListContent);
        }
        else
        {
            WarnMissingListContent("Card List", "CardListPanel/Viewport/Content");
        }

        if (deckListContent != null)
        {
            NormalizeLightweightListScrollArea(deckListContent);
        }
        else
        {
            WarnMissingListContent("Deck 10", "DeckListPanel/Viewport/Content");
        }
        CollectSceneGridCells();
        EnsureFormationGridCellArtImages();
        EnsureFormationGridLayout();
        EnsureGeneratedSkillsPanel();
        WireGeneratedSkillsPanel();
        RenderGrid();
        cardDetailPanel?.Clear();
    }

    private void EnsureFormationRules()
    {
        if (playerRows != 5)
        {
            if (debugBattlePrepLayout)
            {
                Debug.Log($"[Battle] playerRows changed from {playerRows} to 5 so all 5x5 formation cells are placeable.", this);
            }
            playerRows = 5;
        }
    }

    private void Start()
    {
        if (debugBattlePrepLayout)
        {
            LogRuntimeSpriteState();
        }
        if (loadCardsOnStart)
        {
            LoadCards();
        }
        LoadGeneratedSkills();
    }

    private void WireButtons()
    {
        AddClick(loadCardsButton, LoadCards);
        AddClick(loadPersonalLibraryButton, LoadPersonalLibrary);
        AddClick(addToDeckButton, AddSelectedCardToDeck);
        AddClick(saveDeckButton, SaveDeckJson);
        AddClick(startBattleButton, StartBattleScene);
        AddClick(simulateButton, SimulatePreview);
        AddClick(clearButton, ClearPlacement);
    }

    private void ApplyResolvedFontToBattlePrepTexts()
    {
        TMP_FontAsset resolved = ThoughtMapTmpFontResolver.Resolve(null);
        if (resolved == null)
        {
            resolved = ThoughtMapTmpFontResolver.Resolve(cjkFontAsset);
        }
        if (resolved == null)
        {
            return;
        }

        cjkFontAsset = resolved;
        ThoughtMapTmpFontResolver.ApplyToChildren(gameObject, resolved, true);
        if (cardDetailPanel != null)
        {
            cardDetailPanel.SetFontAsset(resolved);
        }
        if (generatedSkillsPanel != null)
        {
            generatedSkillsPanel.SetFontAsset(resolved);
        }
    }

    [ContextMenu("Load Cards")]
    public void LoadCards()
    {
        loadedCards.Clear();
        deckCards.Clear();
        placement.Clear();
        assignedSkillIdsByCardId.Clear();
        selectedDeckIndex = -1;
        selectedLibraryIndex = -1;
        selectedGeneratedSkillId = "";

        try
        {
            List<ThoughtMapBattleCardData> cards = cardsCsvAsset != null
                ? ThoughtMapCardsCsvLoader.LoadFromText(cardsCsvAsset.text)
                : ThoughtMapCardsCsvLoader.LoadFromStreamingAssets(streamingAssetsCsvPath);

            loadedCards.AddRange(cards);
            if (autoFillDeckOnLoad)
            {
                deckCards.AddRange(cards.Take(deckLimit));
            }
            string spriteWarning = GetSpriteWarning();
            WriteStatus(string.IsNullOrEmpty(spriteWarning)
                ? $"Loaded {loadedCards.Count} cards. Select a card, then Add to Deck."
                : $"{spriteWarning}. Loaded {loadedCards.Count} cards.");
        }
        catch (System.Exception exc)
        {
            WriteStatus("Could not load cards.csv: " + exc.Message);
        }

        RefreshGeneratedSkills("Load Cards");
        RenderAll();
    }

    [ContextMenu("Load Personal Library")]
    public void LoadPersonalLibrary()
    {
        EnsurePersonalLibraryApiClient();
        if (personalLibraryApiClient == null)
        {
            WriteStatus("Personal Library API client is not assigned.");
            Debug.LogWarning("[Battle] Personal Library API client is not assigned.", this);
            return;
        }

        string email = GetPersonalLibraryEmail();
        if (string.IsNullOrWhiteSpace(email))
        {
            WriteStatus("Enter a registered email address first.");
            Debug.LogWarning("[Battle] Personal Library email field is empty.", this);
            return;
        }

        WriteStatus("Loading Personal Library...");
        StartCoroutine(personalLibraryApiClient.GetSavedByEmail(
            email,
            ApplyPersonalLibraryResponse,
            HandlePersonalLibraryError
        ));
    }

    private void ApplyPersonalLibraryResponse(PersonalLibraryResponse response)
    {
        if (response == null)
        {
            WriteStatus("Personal Library JSON parse failure: response object is null.");
            Debug.LogError("[Battle] Personal Library JSON parse failure: response object is null.", this);
            return;
        }

        SavedDocument[] works = response.WorksOrItems;

        loadedCards.Clear();
        deckCards.Clear();
        placement.Clear();
        assignedSkillIdsByCardId.Clear();
        selectedDeckIndex = -1;
        selectedLibraryIndex = -1;
        selectedGeneratedSkillId = "";

        List<ThoughtMapBattleCardData> personalCards = new List<ThoughtMapBattleCardData>();
        HashSet<string> seenIds = new HashSet<string>();

        for (int i = 0; i < works.Length; i++)
        {
            SavedDocument work = works[i];
            ThoughtMapBattleCardData card = ThoughtMapBattleCardFactory.FromSavedDocument(work, "personal");
            if (card == null)
            {
                Debug.LogWarning($"[Battle] Personal card conversion returned null for index={i}.", this);
                continue;
            }

            string id = GetCardId(card);
            if (string.IsNullOrWhiteSpace(id) || !seenIds.Add(id))
            {
                Debug.LogWarning($"[Battle] Skipping duplicate or empty Personal card id='{id}' title='{CardName(card)}'.", this);
                continue;
            }

            personalCards.Add(card);
        }

        loadedCards.AddRange(personalCards);

        RefreshGeneratedSkills("Load Personal");
        RenderAll();
        if (personalCards.Count == 0)
        {
            string status = string.Equals(response.parse_status, "actual_empty", System.StringComparison.OrdinalIgnoreCase)
                ? "Personal Library is actually empty."
                : $"Personal Library returned {works.Length} works, but 0 cards were converted. Check Console logs.";
            WriteStatus(status);
        }
        else
        {
            WriteStatus($"Loaded {personalCards.Count} Personal Library cards.");
        }
    }

    private int CountSavedDocumentParameters(SavedDocument document)
    {
        if (document == null)
        {
            return 0;
        }

        int count = document.parameters == null ? 0 : document.parameters.Length;
        foreach (ThoughtParameterDefinition definition in ThoughtParameterOrder)
        {
            if (GetSavedDocumentParameter(document, definition, out _))
            {
                count++;
            }
        }
        return count;
    }

    private string FormatSavedDocumentParameters(SavedDocument document)
    {
        if (document == null)
        {
            return "<null>";
        }

        StringBuilder builder = new StringBuilder();
        builder.Append("array=[");
        if (document.parameters != null)
        {
            for (int i = 0; i < document.parameters.Length; i++)
            {
                ThoughtMapParameterScore parameter = document.parameters[i];
                if (i > 0)
                {
                    builder.Append(", ");
                }
                builder.Append(parameter == null ? "<null>" : $"{parameter.key}:{parameter.value:0.###}");
            }
        }
        builder.Append("] direct=[");
        for (int i = 0; i < ThoughtParameterOrder.Length; i++)
        {
            ThoughtParameterDefinition definition = ThoughtParameterOrder[i];
            if (i > 0)
            {
                builder.Append(", ");
            }
            builder.Append(definition.key);
            builder.Append(':');
            builder.Append(GetSavedDocumentParameter(document, definition, out float value) ? value.ToString("0.###") : "missing");
        }
        builder.Append(']');
        return builder.ToString();
    }

    private bool GetSavedDocumentParameter(SavedDocument document, ThoughtParameterDefinition definition, out float value)
    {
        value = 0f;
        if (document == null || definition.aliases == null)
        {
            return false;
        }

        foreach (string alias in definition.aliases)
        {
            string key = NormalizeAttributeKey(alias);
            switch (key)
            {
                case "philosophy": value = document.philosophy; break;
                case "psychology": value = document.psychology; break;
                case "science": value = document.science; break;
                case "economy": value = document.economy != 0f ? document.economy : document.economics; break;
                case "karma": value = document.karma; break;
                case "emotion": value = document.emotion; break;
                case "morality": value = document.morality != 0f ? document.morality : document.moral; break;
                case "ideology": value = document.ideology != 0f ? document.ideology : document.ideal; break;
                case "individual": value = document.individual; break;
                case "community": value = document.community; break;
                default: continue;
            }

            if (Mathf.Abs(value) > 0.000001f)
            {
                return true;
            }
        }

        return false;
    }

    private string FormatCardParameterValues(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return "<null>";
        }

        StringBuilder builder = new StringBuilder();
        builder.Append('[');
        for (int i = 0; i < ThoughtParameterOrder.Length; i++)
        {
            ThoughtParameterDefinition definition = ThoughtParameterOrder[i];
            if (i > 0)
            {
                builder.Append(", ");
            }
            builder.Append(definition.key);
            builder.Append(':');
            builder.Append(TryGetThoughtParameterScore(card, definition, out float score) ? score.ToString("0.###") : "missing");
        }
        builder.Append(']');
        return builder.ToString();
    }

    private void HandlePersonalLibraryError(string message)
    {
        string reason = string.IsNullOrWhiteSpace(message) ? "HTTP failure or JSON parse failure." : message;
        WriteStatus("Could not load Personal Library. " + ShortStatusText(reason, "HTTP failure or JSON parse failure."));
        Debug.LogWarning("[Battle] Personal Library load error: " + reason, this);
        if (fallbackToSampleCardsOnApiError && loadedCards.Count == 0)
        {
            LoadCards();
            WriteStatus("Personal Library unavailable. Loaded sample cards instead.");
        }
    }

    public void ClearPlacement()
    {
        placement.Clear();
        selectedDeckIndex = -1;
        selectedLibraryIndex = -1;
        RefreshGeneratedSkills("Clear Placement");
        RenderAll();
        WriteStatus("Cleared formation.");
    }

    public void AddSelectedCardToDeck()
    {
        if (selectedLibraryIndex < 0 || selectedLibraryIndex >= loadedCards.Count)
        {
            WriteStatus("Select a Card List card first.");
            return;
        }

        ThoughtMapBattleCardData selected = loadedCards[selectedLibraryIndex];
        int existingIndex = deckCards.IndexOf(selected);
        if (existingIndex >= 0)
        {
            selectedDeckIndex = existingIndex;
            selectedLibraryIndex = -1;
            RenderAll();
            WriteStatus($"Card already in Deck as P{existingIndex + 1}.");
            return;
        }

        if (deckCards.Count >= deckLimit)
        {
            WriteStatus($"Deck limit is {deckLimit}. Remove a deck card before adding another.");
            return;
        }

        deckCards.Add(selected);
        selectedDeckIndex = deckCards.Count - 1;
        selectedLibraryIndex = -1;
        RefreshGeneratedSkills("Add Deck");
        RenderAll();
        WriteStatus($"Added P{selectedDeckIndex + 1} to Deck.");
    }

    private void RenderAll()
    {
        RenderCardLibrary();
        RenderDeck();
        RenderGrid();
        ShowSelectedDetail();
        RenderGeneratedSkills();
        ApplyResolvedFontToBattlePrepTexts();
        UpdateBattleButtonState(false);
    }

    private void RenderCardLibrary()
    {
        if (cardListContent == null)
        {
            EnsureListContentReferences();
        }
        if (cardListContent == null)
        {
            WarnMissingListContent("Card List", "CardListPanel/Viewport/Content");
            return;
        }

        ScrollRect scroll = GetScrollRectForContent(cardListContent);
        float scrollPosition = scroll == null ? 1f : scroll.verticalNormalizedPosition;
        NormalizeLightweightListScrollArea(cardListContent);
        ClearChildren(cardListContent);

        int count = Mathf.Min(loadedCards.Count, cardListRenderLimit);
        for (int i = 0; i < count; i++)
        {
            ProductBattleCardListRowView view = CreateListRow(cardListContent, cardListRowPrefab, "CardListRow");
            string state = FormatCardListState(loadedCards[i], deckCards.Contains(loadedCards[i]) ? "In Deck" : "");
            Sprite artSprite = ResolveCardArtForTarget(loadedCards[i], i, "Card List");
            view.Bind(loadedCards[i], i, $"C{i + 1}", i == selectedLibraryIndex, deckCards.Contains(loadedCards[i]), state, artSprite);
            view.SetClickHandler(OnLibraryCardClicked);
        }
        RestoreScrollPosition(scroll, scrollPosition);
    }

    private void RenderDeck()
    {
        if (deckListContent == null)
        {
            EnsureListContentReferences();
        }
        if (deckListContent == null)
        {
            WarnMissingListContent("Deck 10", "DeckListPanel/Viewport/Content");
            return;
        }

        ScrollRect scroll = GetScrollRectForContent(deckListContent);
        float scrollPosition = scroll == null ? 1f : scroll.verticalNormalizedPosition;
        NormalizeLightweightListScrollArea(deckListContent);
        ClearChildren(deckListContent);

        for (int i = 0; i < deckCards.Count; i++)
        {
            ProductBattleCardListRowView view = CreateListRow(deckListContent, deckListRowPrefab, "DeckListRow");
            string state = FormatCardListState(deckCards[i], placement.ContainsValue(deckCards[i]) ? "Placed" : "Ready");
            Sprite artSprite = ResolveCardArtForTarget(deckCards[i], i, "Deck List");
            view.Bind(deckCards[i], i, $"P{i + 1}", i == selectedDeckIndex, placement.ContainsValue(deckCards[i]), state, artSprite);
            view.SetClickHandler(OnDeckCardClicked);
        }
        RestoreScrollPosition(scroll, scrollPosition);
    }

    private void RenderGrid()
    {
        EnsureGridCells();
        EnsureFormationGridLayout();
        Dictionary<int, ThoughtMapResonanceResult> resonanceResults = CalculatePlacementResonanceByCell();
        for (int index = 0; index < gridCells.Count; index++)
        {
            int x = index % 5;
            int y = index / 5;
            bool available = IsFormationCellAvailable(y);
            if (placement.TryGetValue(index, out ThoughtMapBattleCardData card))
            {
                int deckIndex = deckCards.IndexOf(card);
                gridCells[index].BindCard(
                    x,
                    y,
                    card,
                    $"P{deckIndex + 1}",
                    ResolveCardArtForTarget(card, deckIndex, $"Grid Cell ({x + 1},{y + 1})"),
                    ResolveAttributeIconForTarget(card, $"Grid Cell ({x + 1},{y + 1})")
                );
                if (resonanceResults.TryGetValue(index, out ThoughtMapResonanceResult resonanceResult))
                {
                    gridCells[index].SetResonanceModifier(resonanceResult.totalModifier);
                }
            }
            else
            {
                gridCells[index].BindEmpty(x, y, available);
            }
            gridCells[index].SetClickHandler(OnGridCellClicked);
            if (logFormationGridCells)
            {
                if (debugBattlePrepLayout)
                {
                    Debug.Log($"[Battle] gridCell index={index} x={x} y={y} available={available} hasCard={placement.ContainsKey(index)}", gridCells[index]);
                }
            }
        }
    }

    private void EnsureGridCells()
    {
        CollectSceneGridCells();
        EnsureFormationGridLayout();
        if (gridCells.Count == 25 || gridCellPrefab == null || formationGridContent == null)
        {
            return;
        }

        if (debugBattlePrepLayout)
        {
            Debug.Log($"[Battle] rebuilding formation grid cells. existing={gridCells.Count} required=25", this);
        }
        ClearChildrenImmediate(formationGridContent);
        gridCells.Clear();
        for (int i = 0; i < 25; i++)
        {
            ProductBattleGridCellView cell = Instantiate(gridCellPrefab, formationGridContent);
            cell.gameObject.name = $"FormationCell_{i:00}";
            cell.EnsureArtImage();
            gridCells.Add(cell);
        }
    }

    private void EnsureFormationGridLayout()
    {
        if (formationGridContent == null)
        {
            return;
        }

        RectTransform contentRect = formationGridContent as RectTransform;
        GridLayoutGroup grid = formationGridContent.GetComponent<GridLayoutGroup>();
        if (grid == null)
        {
            grid = formationGridContent.gameObject.AddComponent<GridLayoutGroup>();
        }

        grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        grid.constraintCount = 5;
        if (grid.cellSize.x <= 0f || grid.cellSize.y <= 0f)
        {
            grid.cellSize = new Vector2(132f, 112f);
        }
        grid.spacing = new Vector2(Mathf.Max(0f, grid.spacing.x), Mathf.Max(0f, grid.spacing.y));
        grid.childAlignment = TextAnchor.MiddleCenter;

        if (contentRect != null)
        {
            float width = (grid.cellSize.x * 5f) + (grid.spacing.x * 4f) + grid.padding.left + grid.padding.right;
            float height = (grid.cellSize.y * 5f) + (grid.spacing.y * 4f) + grid.padding.top + grid.padding.bottom;
            contentRect.SetSizeWithCurrentAnchors(RectTransform.Axis.Horizontal, Mathf.Max(contentRect.rect.width, width));
            contentRect.SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical, Mathf.Max(contentRect.rect.height, height));
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
        EnsureFormationGridCellArtImages();
    }

    public void EnsureFormationGridCellArtImages()
    {
        foreach (ProductBattleGridCellView cell in gridCells)
        {
            if (cell != null)
            {
                cell.EnsureArtImage();
            }
        }
    }

    private void OnDeckCardClicked(ProductBattleCardListRowView view)
    {
        selectedDeckIndex = view == null ? -1 : view.Index;
        selectedLibraryIndex = -1;
        RenderDeck();
        RenderCardLibrary();
        ShowSelectedDetail();
        RenderGeneratedSkills();
        WriteStatus(selectedDeckIndex >= 0 ? $"Selected P{selectedDeckIndex + 1}." : "No card selected.");
    }

    private void OnLibraryCardClicked(ProductBattleCardListRowView view)
    {
        selectedLibraryIndex = view == null ? -1 : view.Index;
        RenderCardLibrary();
        ShowSelectedDetail();
        RenderGeneratedSkills();
        WriteStatus(selectedLibraryIndex >= 0 ? $"Previewing C{selectedLibraryIndex + 1}." : "No card selected.");
    }

    private void OnGridCellClicked(ProductBattleGridCellView cell)
    {
        if (cell == null)
        {
            return;
        }

        int index = cell.Y * 5 + cell.X;
        if (debugBattlePrepLayout)
        {
            Debug.Log($"[Battle] clicked grid cell index={index} x={cell.X} y={cell.Y} available={IsFormationCellAvailable(cell.Y)} hasCard={placement.ContainsKey(index)}", cell);
        }
        if (placement.ContainsKey(index))
        {
            placement.Remove(index);
            RefreshGeneratedSkills("Remove Placement");
            RenderAll();
            WriteStatus("Removed card from formation.");
            return;
        }

        if (!IsFormationCellAvailable(cell.Y))
        {
            WriteStatus("This formation cell is not available.");
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
        RefreshGeneratedSkills("Place Card");
        RenderAll();
        WriteStatus($"Placed P{selectedDeckIndex + 1} at ({cell.X + 1},{cell.Y + 1}).");
    }

    private bool IsFormationCellAvailable(int row)
    {
        return row >= 0 && row < Mathf.Clamp(playerRows, 0, 5);
    }

    [ContextMenu("Load Generated Skills")]
    public void LoadGeneratedSkills()
    {
        loadedGeneratedSkills.Clear();
        generatedSkills.Clear();
        generatedSkillById.Clear();

        List<GeneratedSkillDto> loaded = GeneratedSkillLibrary.LoadFromStreamingAssets(generatedSkillsRelativePath, debugGeneratedSkills);
        loadedGeneratedSkills.AddRange(loaded);
        RefreshGeneratedSkills("Load Generated Skills");

        if (debugGeneratedSkills)
        {
            Debug.Log($"[GeneratedSkill] loadedFromJson={loadedGeneratedSkills.Count} total={generatedSkills.Count} path={generatedSkillsRelativePath}", this);
        }
        if (generatedSkills.Count == 0)
        {
            WriteStatus("No generated skills. Put generated_skills.json under StreamingAssets/GeneratedSkills.");
        }

        RenderGeneratedSkills();
        ShowSelectedDetail();
    }

    private void RefreshGeneratedSkills(string reason)
    {
        int deckCount = deckCards.Count;
        int placedCount = placement.Count;
        List<GeneratedSkillDto> runtimeGenerated = GeneratedSkillGenerator.GenerateForBattlePrep(deckCards, placement, 1);
        int candidateCount = deckCount + loadedGeneratedSkills.Count;

        generatedSkills.Clear();
        generatedSkillById.Clear();
        AddGeneratedSkills(loadedGeneratedSkills);
        AddGeneratedSkills(runtimeGenerated);

        Debug.Log(
            $"[GeneratedSkill] deckCount={deckCount} placedCount={placedCount} candidateCount={candidateCount} generatedCount={generatedSkills.Count} reason={reason}",
            this
        );
    }

    private void AddGeneratedSkills(IEnumerable<GeneratedSkillDto> skills)
    {
        if (skills == null)
        {
            return;
        }

        foreach (GeneratedSkillDto skill in skills)
        {
            if (skill == null || string.IsNullOrWhiteSpace(skill.skill_id))
            {
                continue;
            }

            if (generatedSkillById.ContainsKey(skill.skill_id))
            {
                continue;
            }

            generatedSkillById[skill.skill_id] = skill;
            generatedSkills.Add(skill);
        }
    }

    public void AssignGeneratedSkill(GeneratedSkillDto skill)
    {
        if (skill == null || string.IsNullOrWhiteSpace(skill.skill_id))
        {
            WriteStatus("Select a generated skill first.");
            return;
        }

        ThoughtMapBattleCardData card = GetSelectedDeckCard();
        if (card == null)
        {
            WriteStatus("Select a deck card first.");
            Debug.Log($"[GeneratedSkill] assign=blocked reason=SelectDeckCard skill_id={skill.skill_id}", this);
            return;
        }

        string cardId = GetCardId(card);
        string alreadyAssignedCardId = FindAssignedCardIdForSkill(skill.skill_id);
        if (!string.IsNullOrWhiteSpace(alreadyAssignedCardId) && alreadyAssignedCardId != cardId)
        {
            WriteStatus("Skill already assigned to another deck card.");
            Debug.Log($"[GeneratedSkill] assign=blocked reason=OtherCard skill_id={skill.skill_id} targetCard={cardId} assignedCard={alreadyAssignedCardId}", this);
            return;
        }

        if (!assignedSkillIdsByCardId.TryGetValue(cardId, out List<string> skillIds))
        {
            skillIds = new List<string>();
            assignedSkillIdsByCardId[cardId] = skillIds;
        }

        if (skillIds.Contains(skill.skill_id))
        {
            WriteStatus("Skill already assigned to this card.");
            Debug.Log($"[GeneratedSkill] assign=blocked reason=SameCard skill_id={skill.skill_id} targetCard={cardId}", this);
            return;
        }

        if (skillIds.Count >= 1)
        {
            WriteStatus("This card already has an assigned skill.");
            Debug.Log($"[GeneratedSkill] assign=blocked reason=AlreadyHasSkill skill_id={skill.skill_id} targetCard={cardId}", this);
            return;
        }

        skillIds.Add(skill.skill_id);
        selectedGeneratedSkillId = skill.skill_id;
        Debug.Log($"[GeneratedSkill] assign=success skill_id={skill.skill_id} targetCard={cardId}", this);
        WriteStatus($"Assigned {skill.DisplayName} to P{selectedDeckIndex + 1}.");
        RenderGeneratedSkills();
        ShowSelectedDetail();
    }

    public void RemoveGeneratedSkill(GeneratedSkillDto skill)
    {
        if (skill == null || string.IsNullOrWhiteSpace(skill.skill_id))
        {
            WriteStatus("Select an assigned skill to remove.");
            return;
        }

        ThoughtMapBattleCardData card = GetSelectedDeckCard();
        if (card == null)
        {
            WriteStatus("Select a deck card first.");
            return;
        }

        string cardId = GetCardId(card);
        if (!assignedSkillIdsByCardId.TryGetValue(cardId, out List<string> skillIds) || !skillIds.Remove(skill.skill_id))
        {
            WriteStatus("That skill is not assigned to the selected card.");
            return;
        }

        if (debugGeneratedSkills)
        {
            Debug.Log($"[GeneratedSkill] remove=success skill_id={skill.skill_id} cardId={cardId}", this);
        }
        WriteStatus($"Removed {skill.DisplayName} from P{selectedDeckIndex + 1}.");
        RenderGeneratedSkills();
        ShowSelectedDetail();
    }

    private void OnGeneratedSkillSelected(GeneratedSkillDto skill)
    {
        selectedGeneratedSkillId = skill == null ? "" : skill.skill_id;
        if (generatedSkillsPanel != null)
        {
            generatedSkillsPanel.SetSelectedSkill(selectedGeneratedSkillId);
        }
        RenderGeneratedSkills();
        WriteStatus(skill == null
            ? "No generated skill selected."
            : $"Selected skill: {skill.DisplayName} - {ShortStatusText(skill.description_en, "")}");
    }

    private void RenderGeneratedSkills()
    {
        EnsureGeneratedSkillsPanel();
        WireGeneratedSkillsPanel();
        if (generatedSkillsPanel == null)
        {
            return;
        }

        ThoughtMapBattleCardData selectedCard = GetSelectedCard();
        List<GeneratedSkillDto> deckMatchedSkills = GetDeckMatchedGeneratedSkills();
        bool usedDebugFallback = false;
        if (deckCards.Count > 0 && deckMatchedSkills.Count == 0 && showAllGeneratedSkillsWhenNoDeckMatch && generatedSkills.Count > 0)
        {
            usedDebugFallback = true;
            deckMatchedSkills = generatedSkills
                .Where(skill => skill != null && !string.IsNullOrWhiteSpace(skill.skill_id))
                .OrderBy(skill => skill.DisplayName)
                .ThenBy(skill => skill.skill_id)
                .ToList();
        }
        generatedSkillsPanel.SetSelectedSkill(selectedGeneratedSkillId);
        generatedSkillsPanel.Render(
            deckMatchedSkills,
            selectedCard == null ? "" : selectedCard.docId,
            GetAssignedSkillIdsForCard(selectedCard),
            BuildSkillAssignmentLabels(),
            GetSelectedDeckCard() != null,
            GetSelectedDeckCard() != null && GetAssignedSkillIdsForCard(GetSelectedDeckCard()).Count == 0
        );

        if (debugGeneratedSkills || usedDebugFallback)
        {
            Debug.Log($"[GeneratedSkill] deckMatched={GetDeckMatchedGeneratedSkills().Count} displayed={deckMatchedSkills.Count} deckCount={deckCards.Count} fallbackAll={usedDebugFallback}", this);
            LogGeneratedSkillDocIdMatching();
        }
    }

    private List<GeneratedSkillDto> GetDeckMatchedGeneratedSkills()
    {
        List<GeneratedSkillDto> filtered = new List<GeneratedSkillDto>();
        if (generatedSkills.Count == 0 || deckCards.Count == 0)
        {
            return filtered;
        }

        HashSet<string> addedSkillIds = new HashSet<string>();
        foreach (ThoughtMapBattleCardData card in deckCards)
        {
            string docId = NormalizeDocId(card == null ? "" : card.docId);
            if (string.IsNullOrWhiteSpace(docId))
            {
                continue;
            }

            IEnumerable<GeneratedSkillDto> matches = generatedSkills
                .Where(skill => skill != null
                    && !string.IsNullOrWhiteSpace(skill.skill_id)
                    && NormalizeDocId(skill.doc_id) == docId)
                .OrderBy(skill => skill.DisplayName)
                .ThenBy(skill => skill.skill_id);

            foreach (GeneratedSkillDto skill in matches)
            {
                if (addedSkillIds.Add(skill.skill_id))
                {
                    filtered.Add(skill);
                }
            }
        }

        return filtered;
    }

    private void LogGeneratedSkillDocIdMatching()
    {
        Debug.Log($"[GeneratedSkill] matching deckCardCount={deckCards.Count} skillCount={generatedSkills.Count}", this);
        foreach (ThoughtMapBattleCardData card in deckCards)
        {
            Debug.Log($"[GeneratedSkill] deckCard title='{(card == null ? "null" : card.cardName)}' doc_id='{(card == null ? "" : card.docId)}'", this);
        }

        int matchCount = 0;
        foreach (GeneratedSkillDto skill in generatedSkills)
        {
            if (skill == null)
            {
                continue;
            }

            bool matched = deckCards.Any(card => card != null
                && !string.IsNullOrWhiteSpace(card.docId)
                && NormalizeDocId(card.docId) == NormalizeDocId(skill.doc_id));
            if (matched)
            {
                matchCount++;
            }
            Debug.Log($"[GeneratedSkill] candidate name='{skill.DisplayName}' doc_id='{skill.doc_id}' matched={matched}", this);
        }
        Debug.Log($"[GeneratedSkill] matchingComplete matchCount={matchCount}", this);
    }

    private string NormalizeDocId(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? "" : value.Trim();
    }

    private ThoughtMapBattleCardData GetSelectedCard()
    {
        if (selectedDeckIndex >= 0 && selectedDeckIndex < deckCards.Count)
        {
            return deckCards[selectedDeckIndex];
        }
        if (selectedLibraryIndex >= 0 && selectedLibraryIndex < loadedCards.Count)
        {
            return loadedCards[selectedLibraryIndex];
        }
        return null;
    }

    private ThoughtMapBattleCardData GetSelectedDeckCard()
    {
        return selectedDeckIndex >= 0 && selectedDeckIndex < deckCards.Count
            ? deckCards[selectedDeckIndex]
            : null;
    }

    private List<string> GetAssignedSkillIdsForCard(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return new List<string>();
        }

        return assignedSkillIdsByCardId.TryGetValue(GetCardId(card), out List<string> ids)
            ? ids.Where(id => !string.IsNullOrWhiteSpace(id)).Take(1).ToList()
            : new List<string>();
    }

    private string FindAssignedCardIdForSkill(string skillId)
    {
        if (string.IsNullOrWhiteSpace(skillId))
        {
            return "";
        }

        foreach (ThoughtMapBattleCardData deckCard in deckCards)
        {
            string cardId = GetCardId(deckCard);
            if (string.IsNullOrWhiteSpace(cardId))
            {
                continue;
            }

            if (assignedSkillIdsByCardId.TryGetValue(cardId, out List<string> skillIds)
                && skillIds != null
                && skillIds.Contains(skillId))
            {
                return cardId;
            }
        }

        return "";
    }

    private Dictionary<string, string> BuildSkillAssignmentLabels()
    {
        Dictionary<string, string> labels = new Dictionary<string, string>();
        for (int i = 0; i < deckCards.Count; i++)
        {
            ThoughtMapBattleCardData card = deckCards[i];
            string cardId = GetCardId(card);
            if (!assignedSkillIdsByCardId.TryGetValue(cardId, out List<string> skillIds) || skillIds == null)
            {
                continue;
            }

            foreach (string skillId in skillIds)
            {
                if (string.IsNullOrWhiteSpace(skillId) || labels.ContainsKey(skillId))
                {
                    continue;
                }

                labels[skillId] = $"P{i + 1} {ShortCardName(card)}";
            }
        }
        return labels;
    }

    private string ShortCardName(ThoughtMapBattleCardData card)
    {
        if (card == null || string.IsNullOrWhiteSpace(card.cardName))
        {
            return "Card";
        }
        return card.cardName.Length <= 18 ? card.cardName : card.cardName.Substring(0, 18) + "...";
    }

    private List<GeneratedSkillDto> GetAssignedSkillsForCard(ThoughtMapBattleCardData card)
    {
        List<GeneratedSkillDto> result = new List<GeneratedSkillDto>();
        foreach (string skillId in GetAssignedSkillIdsForCard(card))
        {
            if (generatedSkillById.TryGetValue(skillId, out GeneratedSkillDto skill))
            {
                result.Add(skill);
            }
        }
        return result;
    }

    private void WireGeneratedSkillsPanel()
    {
        if (generatedSkillsPanel != null)
        {
            generatedSkillsPanel.SetHandlers(OnGeneratedSkillSelected, AssignGeneratedSkill, RemoveGeneratedSkill);
        }
    }

    private void ShowSelectedDetail()
    {
        if (cardDetailPanel == null)
        {
            return;
        }

        if (selectedLibraryIndex >= 0 && selectedLibraryIndex < loadedCards.Count)
        {
            ThoughtMapBattleCardData libraryCard = loadedCards[selectedLibraryIndex];
            List<GeneratedSkillDto> assignedSkills = GetAssignedSkillsForCard(libraryCard);
            LogSelectedCardSkillState(libraryCard, assignedSkills);
            cardDetailPanel.Show(
                libraryCard,
                ResolveCardArtForTarget(libraryCard, selectedLibraryIndex, "Detail Panel"),
                ResolveAttributeIconForTarget(libraryCard, "Detail Panel"),
                ResolveDominantThoughtAttributeKey(libraryCard),
                assignedSkills
            );
            return;
        }

        if (selectedDeckIndex < 0 || selectedDeckIndex >= deckCards.Count)
        {
            cardDetailPanel.Clear();
            return;
        }

        ThoughtMapBattleCardData card = deckCards[selectedDeckIndex];
        List<GeneratedSkillDto> deckAssignedSkills = GetAssignedSkillsForCard(card);
        LogSelectedCardSkillState(card, deckAssignedSkills);
        ThoughtMapResonanceResult resonanceResult = GetSelectedCardResonanceResult(card) ?? new ThoughtMapResonanceResult(null);
        bool hasPositionBonus = TryGetPlacedPosition(card, out ThoughtMapGridPosition selectedPosition);
        ThoughtMapGridBonus positionBonus = hasPositionBonus
            ? ThoughtMapGridBonusCalculator.GetBonus(selectedPosition, "Player")
            : default(ThoughtMapGridBonus);
        cardDetailPanel.Show(
            card,
            ResolveCardArtForTarget(card, selectedDeckIndex, "Detail Panel"),
            ResolveAttributeIconForTarget(card, "Detail Panel"),
            ResolveDominantThoughtAttributeKey(card),
            deckAssignedSkills,
            resonanceResult,
            hasPositionBonus,
            positionBonus
        );
    }

    [ContextMenu("Refresh Resonance Display")]
    public void RefreshResonanceDisplay()
    {
        EnsureResonanceCalculator();
        RenderGrid();
        ShowSelectedDetail();
        WriteStatus("Resonance display refreshed.");
    }

    private void EnsureResonanceCalculator()
    {
        resonanceCalculator = new ThoughtMapBattleResonanceCalculator(
            resonanceConfig == null ? ThoughtMapBattleResonanceConfig.RuntimeDefault : resonanceConfig
        );
    }

    private Dictionary<int, ThoughtMapResonanceResult> CalculatePlacementResonanceByCell()
    {
        EnsureResonanceCalculator();
        Dictionary<int, ThoughtMapResonanceResult> results = new Dictionary<int, ThoughtMapResonanceResult>();
        List<ThoughtMapBattleUnit> units = BuildPlacedBattleUnits();
        foreach (ThoughtMapBattleUnit unit in units)
        {
            int index = unit.position.y * 5 + unit.position.x;
            results[index] = resonanceCalculator.CalculateTotalModifier(unit, units);
        }
        return results;
    }

    private ThoughtMapResonanceResult GetSelectedCardResonanceResult(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return null;
        }

        Dictionary<int, ThoughtMapResonanceResult> results = CalculatePlacementResonanceByCell();
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement)
        {
            if (pair.Value == card && results.TryGetValue(pair.Key, out ThoughtMapResonanceResult result))
            {
                return result;
            }
        }

        return null;
    }

    private bool TryGetPlacedPosition(ThoughtMapBattleCardData card, out ThoughtMapGridPosition position)
    {
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement)
        {
            if (pair.Value == card)
            {
                position = new ThoughtMapGridPosition(pair.Key % 5, pair.Key / 5);
                return true;
            }
        }

        position = new ThoughtMapGridPosition(0, 0);
        return false;
    }

    private List<ThoughtMapBattleUnit> BuildPlacedBattleUnits()
    {
        List<ThoughtMapBattleUnit> units = new List<ThoughtMapBattleUnit>();
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(item => item.Key))
        {
            if (pair.Value == null)
            {
                continue;
            }

            int x = pair.Key % 5;
            int y = pair.Key / 5;
            ThoughtMapBattleUnit unit = new ThoughtMapBattleUnit(pair.Value, "Player", new ThoughtMapGridPosition(x, y));
            int deckIndex = deckCards.IndexOf(pair.Value);
            unit.battleId = $"P{(deckIndex >= 0 ? deckIndex + 1 : units.Count + 1)}";
            units.Add(unit);
        }

        return units;
    }

    private void LogSelectedCardSkillState(ThoughtMapBattleCardData card, List<GeneratedSkillDto> resolvedSkills)
    {
        if (!debugGeneratedSkills)
        {
            return;
        }

        List<string> assignedIds = GetAssignedSkillIdsForCard(card);
        Debug.Log($"[GeneratedSkill] selectedCard='{(card == null ? "null" : card.cardName)}' cardId='{GetCardId(card)}' assignedIds='{string.Join(", ", assignedIds)}' renderedCount={(resolvedSkills == null ? 0 : resolvedSkills.Count)}", this);
    }

    public void SimulatePreview()
    {
        StringBuilder builder = new StringBuilder();
        RefreshGeneratedSkills("Preview");
        RenderGeneratedSkills();
        ShowSelectedDetail();
        EnsureResonanceCalculator();

        builder.AppendLine("=== Battle Prep Preview ===");
        builder.AppendLine($"Deck Cards: {deckCards.Count}");
        builder.AppendLine($"Placed Cards: {placement.Count}/{deployLimit}");
        builder.AppendLine($"Generated Skills: {GetDeckMatchedGeneratedSkills().Count}");
        builder.AppendLine();
        builder.AppendLine("Final status at battle start:");
        Dictionary<int, ThoughtMapResonanceResult> resonanceResults = CalculatePlacementResonanceByCell();
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(pair => pair.Key))
        {
            int x = pair.Key % 5;
            int y = pair.Key / 5;
            ThoughtMapBattleCardData card = pair.Value;
            ThoughtMapGridBonus positionBonus = ThoughtMapGridBonusCalculator.GetBonus(new ThoughtMapGridPosition(x, y), "Player");
            float resonance = resonanceResults.TryGetValue(pair.Key, out ThoughtMapResonanceResult result) ? result.totalModifier : 0f;
            List<GeneratedSkillDto> cardSkills = GetAssignedSkillsForCard(card);
            builder.AppendLine(
                $"P{deckCards.IndexOf(card) + 1} {card.cardName} @({x + 1},{y + 1}) " +
                $"Final HP {PreviewFinal(card.MaxHp, positionBonus.hpMultiplier, 0f)} " +
                $"ATK {PreviewFinal(Mathf.Max(card.statPhysicalAttack, card.statSkillAttack), positionBonus.attackMultiplier, resonance)} " +
                $"DEF {PreviewFinal(Mathf.Max(card.statPhysicalDefense, card.statSkillDefense), positionBonus.defenseMultiplier, resonance)} " +
                $"HatePreview {positionBonus.hateMultiplier:0.00}x " +
                $"Resonance {FormatSignedPercent(resonance)} " +
                $"Skills {cardSkills.Count}"
            );
        }
        builder.AppendLine();
        builder.AppendLine("Generated skill candidates:");
        foreach (GeneratedSkillDto skill in GetDeckMatchedGeneratedSkills())
        {
            builder.AppendLine($"- {skill.DisplayName} | {skill.trigger} | {GeneratedSkillLibrary.EffectSummary(skill)} | {GeneratedSkillLibrary.CostSummary(skill)} | CT {skill.cooldown}");
        }
        debugLogPanel?.SetCollapsed(false);
        debugLogPanel?.SetLog(builder.ToString());
        Debug.Log($"[Preview] deckCount={deckCards.Count} placedCount={placement.Count} generatedCount={GetDeckMatchedGeneratedSkills().Count}", this);
        WriteStatus("Preview updated.");
        UpdateBattleButtonState(false);
    }

    public void SaveDeckJson()
    {
        RefreshGeneratedSkills("Save Deck");
        ThoughtMapBattleDeckConfig config = new ThoughtMapBattleDeckConfig();
        config.deckCardIds = deckCards.Select(GetCardId).ToList();
        config.assignedSkills = BuildAssignedSkillSaveData();
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(pair => pair.Key))
        {
            int x = pair.Key % 5;
            int y = pair.Key / 5;
            config.deployedCardIds.Add(GetCardId(pair.Value));
            config.gridPositions.Add(new ThoughtMapBattleDeckPosition(GetCardId(pair.Value), x, y));
        }

        string path = Path.Combine(Application.persistentDataPath, deckFileName);
        File.WriteAllText(path, JsonUtility.ToJson(config, true), Encoding.UTF8);
        if (debugGeneratedSkills)
        {
            int count = config.assignedSkills == null ? 0 : config.assignedSkills.Sum(item => item.skillIds == null ? 0 : item.skillIds.Count);
            Debug.Log($"[GeneratedSkill] savedAssignedSkillCount={count} path={path}", this);
        }
        WriteStatus("Saved deck: " + path);
    }

    [ContextMenu("Restore Assigned Skills From Deck JSON")]
    public void RestoreAssignedSkillsFromDeckJson()
    {
        string path = Path.Combine(Application.persistentDataPath, deckFileName);
        if (!File.Exists(path))
        {
            Debug.LogWarning("[GeneratedSkill] deck.json not found for assigned skill restore: " + path, this);
            return;
        }

        ThoughtMapBattleDeckConfig config = JsonUtility.FromJson<ThoughtMapBattleDeckConfig>(File.ReadAllText(path));
        RestoreAssignedSkills(config);
        RenderAll();
    }

    [ContextMenu("Load Deck JSON")]
    public void LoadDeckJson()
    {
        string path = Path.Combine(Application.persistentDataPath, deckFileName);
        if (!File.Exists(path))
        {
            WriteStatus("deck.json not found: " + path);
            return;
        }

        ThoughtMapBattleDeckConfig config = JsonUtility.FromJson<ThoughtMapBattleDeckConfig>(File.ReadAllText(path));
        if (config == null || config.deckCardIds == null)
        {
            WriteStatus("deck.json could not be read.");
            return;
        }

        deckCards.Clear();
        placement.Clear();
        foreach (string cardId in config.deckCardIds)
        {
            ThoughtMapBattleCardData card = loadedCards.FirstOrDefault(candidate => GetCardId(candidate) == cardId);
            if (card != null)
            {
                deckCards.Add(card);
            }
        }

        if (config.gridPositions != null)
        {
            foreach (ThoughtMapBattleDeckPosition position in config.gridPositions)
            {
                ThoughtMapBattleCardData card = deckCards.FirstOrDefault(candidate => GetCardId(candidate) == position.cardId);
                if (card == null)
                {
                    continue;
                }

                int x = Mathf.Clamp(position.x, 0, 4);
                int y = Mathf.Clamp(position.y, 0, 4);
                placement[y * 5 + x] = card;
            }
        }

        RestoreAssignedSkills(config);
        selectedDeckIndex = deckCards.Count > 0 ? 0 : -1;
        selectedLibraryIndex = -1;
        RefreshGeneratedSkills("Load Deck");
        RenderAll();
        WriteStatus("Loaded deck: " + path);
    }

    private List<CardAssignedSkillData> BuildAssignedSkillSaveData()
    {
        List<CardAssignedSkillData> result = new List<CardAssignedSkillData>();
        HashSet<string> savedSkillIds = new HashSet<string>();
        foreach (ThoughtMapBattleCardData card in deckCards)
        {
            string cardId = GetCardId(card);
            if (!assignedSkillIdsByCardId.TryGetValue(cardId, out List<string> skillIds))
            {
                continue;
            }

            List<string> validIds = new List<string>();
            foreach (string skillId in skillIds.Where(id => !string.IsNullOrWhiteSpace(id)).Distinct())
            {
                if (savedSkillIds.Contains(skillId))
                {
                    Debug.LogWarning($"[GeneratedSkill] duplicate assigned skill ignored during save. skill_id={skillId} cardId={cardId}", this);
                    continue;
                }
                if (validIds.Count >= 1)
                {
                    Debug.LogWarning($"[GeneratedSkill] extra assigned skill ignored during save because each card can have only one skill. skill_id={skillId} cardId={cardId}", this);
                    break;
                }

                validIds.Add(skillId);
                savedSkillIds.Add(skillId);
            }
            if (validIds.Count > 0)
            {
                result.Add(new CardAssignedSkillData(cardId, validIds));
            }
        }
        return result;
    }

    private void RestoreAssignedSkills(ThoughtMapBattleDeckConfig config)
    {
        assignedSkillIdsByCardId.Clear();
        if (config == null || config.assignedSkills == null)
        {
            return;
        }

        int restored = 0;
        HashSet<string> restoredSkillIds = new HashSet<string>();
        HashSet<string> deckCardIds = new HashSet<string>(deckCards.Select(GetCardId).Where(id => !string.IsNullOrWhiteSpace(id)));
        foreach (CardAssignedSkillData item in config.assignedSkills)
        {
            if (item == null || string.IsNullOrWhiteSpace(item.cardId) || item.skillIds == null)
            {
                continue;
            }
            if (!deckCardIds.Contains(item.cardId))
            {
                Debug.LogWarning($"[GeneratedSkill] saved assigned skill entry ignored because card is not in current deck. cardId={item.cardId}", this);
                continue;
            }

            List<string> valid = new List<string>();
            foreach (string skillId in item.skillIds)
            {
                if (string.IsNullOrWhiteSpace(skillId))
                {
                    continue;
                }
                if (!generatedSkillById.ContainsKey(skillId))
                {
                    Debug.LogWarning($"[GeneratedSkill] saved skill_id not found in generated skill list: {skillId}", this);
                    continue;
                }
                if (restoredSkillIds.Contains(skillId))
                {
                    Debug.LogWarning($"[GeneratedSkill] duplicate assigned skill ignored during restore. skill_id={skillId} cardId={item.cardId}", this);
                    continue;
                }
                if (valid.Count >= 1)
                {
                    Debug.LogWarning($"[GeneratedSkill] extra assigned skill ignored during restore because each card can have only one skill. skill_id={skillId} cardId={item.cardId}", this);
                    continue;
                }
                if (!valid.Contains(skillId))
                {
                    valid.Add(skillId);
                    restoredSkillIds.Add(skillId);
                }
            }

            if (valid.Count > 0)
            {
                assignedSkillIdsByCardId[item.cardId] = valid;
                restored += valid.Count;
            }
        }

        if (debugGeneratedSkills)
        {
            Debug.Log($"[GeneratedSkill] restoredAssignedSkillCount={restored}", this);
        }
    }

    public void StartBattleScene()
    {
        if (!CanStartBattle(out string reason))
        {
            WriteStatus(reason);
            UpdateBattleButtonState(true);
            return;
        }

        SaveDeckJson();
        WriteStatus("Opening BattleScene: " + battleSceneName);
        SceneManager.LoadScene(battleSceneName);
    }

    private bool CanStartBattle(out string reason)
    {
        if (deckCards.Count < deckLimit)
        {
            reason = "Need 10 deck cards.";
            return false;
        }

        if (placement.Count < deployLimit)
        {
            reason = "Need 5 deployed cards.";
            return false;
        }

        if (GetDeckMatchedGeneratedSkills().Count == 0)
        {
            reason = "Generate skills first.";
            return false;
        }

        reason = "";
        return true;
    }

    private void UpdateBattleButtonState(bool showReason)
    {
        if (startBattleButton == null)
        {
            return;
        }

        bool canStart = CanStartBattle(out string reason);
        startBattleButton.interactable = canStart;
        if (showReason && !canStart)
        {
            WriteStatus(reason);
        }
    }

    private int PreviewFinal(int baseValue, float positionMultiplier, float resonanceModifier)
    {
        return Mathf.Max(0, Mathf.RoundToInt(baseValue * positionMultiplier * (1f + resonanceModifier)));
    }

    private string FormatSignedPercent(float modifier)
    {
        float percent = modifier * 100f;
        return percent >= 0f ? $"+{percent:0}%" : $"{percent:0}%";
    }

    private Sprite ResolveCardArt(ThoughtMapBattleCardData card, int index)
    {
        string thoughtAttribute = ResolveDominantThoughtAttributeKey(card);
        if (string.IsNullOrWhiteSpace(thoughtAttribute))
        {
            return defaultCardArt;
        }

        Sprite template = ResolveAttributeSprite(cardTemplateSprites, thoughtAttribute);
        if (template != null)
        {
            return template;
        }

        return defaultCardArt;
    }

    private Sprite ResolveAttributeIcon(ThoughtMapBattleCardData card)
    {
        string thoughtAttribute = ResolveDominantThoughtAttributeKey(card);
        return ResolveAttributeSprite(attributeSprites, thoughtAttribute) ?? defaultAttributeIcon;
    }

    private Sprite ResolveCardArtForTarget(ThoughtMapBattleCardData card, int index, string target)
    {
        Sprite sprite = ResolveCardArt(card, index);
        if (sprite == null)
        {
            string thoughtAttribute = ResolveDominantThoughtAttributeKey(card);
            Debug.LogWarning(
                $"[Battle] Missing card template/default art for target={target}, doc_id='{(card == null ? "" : card.docId)}', card='{CardName(card)}', battleAttribute='{AttributeName(card)}', dominant='{FormatThoughtAttributeForLog(thoughtAttribute)}', spriteKey='{NormalizeAttributeKey(thoughtAttribute)}'.",
                this
            );
        }
        return sprite;
    }

    private Sprite ResolveAttributeIconForTarget(ThoughtMapBattleCardData card, string target)
    {
        Sprite sprite = ResolveAttributeIcon(card);
        return sprite;
    }

    private string ResolveDominantThoughtAttributeKey(ThoughtMapBattleCardData card)
    {
        if (card == null || card.parameterScores == null || card.parameterScores.Count == 0)
        {
            return "";
        }

        string bestKey = "";
        float bestScore = float.NegativeInfinity;
        bool found = false;

        foreach (ThoughtParameterDefinition definition in ThoughtParameterOrder)
        {
            if (!TryGetThoughtParameterScore(card, definition, out float score))
            {
                continue;
            }

            if (!found || score > bestScore)
            {
                bestKey = definition.key;
                bestScore = score;
                found = true;
            }
        }

        return found ? bestKey : "";
    }

    private bool TryGetThoughtParameterScore(ThoughtMapBattleCardData card, ThoughtParameterDefinition definition, out float score)
    {
        score = 0f;
        if (card == null || card.parameterScores == null || definition.aliases == null)
        {
            return false;
        }

        foreach (string alias in definition.aliases)
        {
            if (card.parameterScores.TryGetValue(alias, out score))
            {
                return true;
            }

            string normalizedAlias = NormalizeAttributeKey(alias);
            foreach (KeyValuePair<string, float> pair in card.parameterScores)
            {
                if (NormalizeAttributeKey(pair.Key) == normalizedAlias)
                {
                    score = pair.Value;
                    return true;
                }
            }
        }

        return false;
    }

    private void EnsureBattlePrepBackground()
    {
        if (battlePrepBackground == null)
        {
            Debug.LogWarning(
                "[Battle] Missing battle_prep_bg.png / battlePrepBackground Inspector reference is null. Runtime uses Inspector references; Resources.Load is not used.",
                this
            );
            return;
        }

        RectTransform root = transform as RectTransform;
        RectTransform parent = transform.parent as RectTransform;
        if (root == null || parent == null)
        {
            return;
        }

        if (backgroundImage == null)
        {
            Transform existing = FindDirectChild(parent, "BattlePrepBackground");
            GameObject backgroundObject = existing == null
                ? new GameObject("BattlePrepBackground", typeof(RectTransform), typeof(Image))
                : existing.gameObject;
            backgroundObject.transform.SetParent(parent, false);
            backgroundImage = backgroundObject.GetComponent<Image>();
            if (backgroundImage == null)
            {
                backgroundImage = backgroundObject.AddComponent<Image>();
            }
        }

        RectTransform backgroundRect = backgroundImage.GetComponent<RectTransform>();
        backgroundRect.anchorMin = Vector2.zero;
        backgroundRect.anchorMax = Vector2.one;
        backgroundRect.offsetMin = Vector2.zero;
        backgroundRect.offsetMax = Vector2.zero;
        backgroundRect.SetAsFirstSibling();
        backgroundImage.sprite = battlePrepBackground;
        backgroundImage.enabled = true;
        backgroundImage.preserveAspect = false;
        backgroundImage.raycastTarget = false;
        if (debugBattlePrepLayout)
        {
            Debug.Log($"[Battle] backgroundSprite={SpriteName(backgroundImage.sprite)} method=Inspector", this);
        }

        if (darkOverlayImage == null)
        {
            Transform existing = FindDirectChild(parent, "BattlePrepDarkOverlay");
            GameObject overlayObject = existing == null
                ? new GameObject("BattlePrepDarkOverlay", typeof(RectTransform), typeof(Image))
                : existing.gameObject;
            overlayObject.transform.SetParent(parent, false);
            darkOverlayImage = overlayObject.GetComponent<Image>();
            if (darkOverlayImage == null)
            {
                darkOverlayImage = overlayObject.AddComponent<Image>();
            }
        }

        RectTransform overlayRect = darkOverlayImage.GetComponent<RectTransform>();
        overlayRect.anchorMin = Vector2.zero;
        overlayRect.anchorMax = Vector2.one;
        overlayRect.offsetMin = Vector2.zero;
        overlayRect.offsetMax = Vector2.zero;
        overlayRect.SetSiblingIndex(Mathf.Min(1, parent.childCount - 1));
        darkOverlayColor.a = Mathf.Clamp(battlePrepOverlayAlpha, 0.20f, 0.30f);
        darkOverlayImage.color = darkOverlayColor;
        darkOverlayImage.raycastTarget = false;
        if (debugBattlePrepLayout)
        {
            Debug.Log($"[Battle] darkOverlayAlpha={darkOverlayImage.color.a}", this);
        }

        root.SetAsLastSibling();

        if (softenPanelForBackground)
        {
            Image panelImage = GetComponent<Image>();
            if (panelImage != null)
            {
                Color color = panelImage.color;
                color.a = Mathf.Min(color.a, panelBackgroundAlpha);
                panelImage.color = color;
            }
        }
    }

    private void EnsurePanelTransparency()
    {
        CanvasGroup[] canvasGroups = GetComponentsInChildren<CanvasGroup>(true);
        foreach (CanvasGroup group in canvasGroups)
        {
            if (group.alpha < 1f)
            {
                group.alpha = 1f;
            }
        }

        string[] panelNames =
        {
            "CardListPanel", "DeckListPanel", "FormationGridPanel", "CardDetailPanel", "DebugLogPanel", "GeneratedSkillsPanel"
        };

        foreach (string panelName in panelNames)
        {
            Transform panel = FindDescendant(transform, panelName);
            if (panel == null)
            {
                continue;
            }

            Image image = panel.GetComponent<Image>();
            if (image == null)
            {
                continue;
            }

            Color color = image.color;
            color.a = Mathf.Clamp(panelBackgroundAlpha, 0.55f, 0.70f);
            image.color = color;
            if (debugBattlePrepLayout)
            {
                Debug.Log($"[Battle] panelAlpha panel={panelName} alpha={color.a}", image);
            }
        }
    }

    private void EnsureTopControlReadability()
    {
        RectTransform root = transform as RectTransform;
        if (root == null)
        {
            return;
        }

        RectTransform title = FindDescendant(transform, "TitleText") as RectTransform;
        if (title != null)
        {
            AnchorTo(title, new Vector2(0.02f, 0.925f), new Vector2(0.48f, 0.99f));
            TMP_Text titleText = title.GetComponent<TMP_Text>();
            if (titleText != null)
            {
                titleText.fontSize = Mathf.Max(titleText.fontSize, 30f);
                titleText.enableWordWrapping = false;
                titleText.overflowMode = TextOverflowModes.Overflow;
                AddTextShadow(titleText);
            }
        }

        NormalizeTopButton(loadCardsButton, "Load Cards", new Vector2(0.50f, 0.93f), new Vector2(0.595f, 0.985f));
        NormalizeTopButton(addToDeckButton, "Add Deck", new Vector2(0.605f, 0.93f), new Vector2(0.715f, 0.985f));
        NormalizeTopButton(saveDeckButton, "Save Deck", new Vector2(0.725f, 0.93f), new Vector2(0.805f, 0.985f));
        NormalizeTopButton(simulateButton, "Preview", new Vector2(0.815f, 0.93f), new Vector2(0.905f, 0.985f));
        NormalizeTopButton(startBattleButton, "Battle", new Vector2(0.915f, 0.93f), new Vector2(0.985f, 0.985f));
        NormalizeEmailInput(personalEmailInput, new Vector2(0.70f, 0.01f), new Vector2(0.86f, 0.07f));
        NormalizeTopButton(loadPersonalLibraryButton, "Load Personal", new Vector2(0.865f, 0.01f), new Vector2(0.985f, 0.07f));
    }

    private void NormalizeTopButton(Button button, string label, Vector2 min, Vector2 max)
    {
        if (button == null)
        {
            return;
        }

        RectTransform rect = button.transform as RectTransform;
        if (rect != null)
        {
            AnchorTo(rect, min, max);
        }

        TMP_Text labelText = button.GetComponentInChildren<TMP_Text>(true);
        if (labelText != null)
        {
            labelText.text = label;
            labelText.fontSize = 14f;
            labelText.enableWordWrapping = false;
            labelText.overflowMode = TextOverflowModes.Overflow;
            AddTextShadow(labelText);
        }
    }

    private void NormalizeEmailInput(TMP_InputField input, Vector2 min, Vector2 max)
    {
        if (input == null)
        {
            return;
        }

        RectTransform rect = input.transform as RectTransform;
        if (rect != null)
        {
            AnchorTo(rect, min, max);
        }

        TMP_Text text = input.textComponent;
        if (text != null)
        {
            text.fontSize = 14f;
            text.enableWordWrapping = false;
            text.overflowMode = TextOverflowModes.Ellipsis;
        }

        TMP_Text placeholder = input.placeholder as TMP_Text;
        if (placeholder != null)
        {
            placeholder.text = "email";
            placeholder.fontSize = 14f;
            placeholder.enableWordWrapping = false;
            placeholder.overflowMode = TextOverflowModes.Ellipsis;
        }
    }

    private void EnsureReadableTextEffects()
    {
        AddTextShadow(statusText);
        TMP_Text[] headings = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in headings)
        {
            if (text == null)
            {
                continue;
            }

            string lower = text.gameObject.name.ToLowerInvariant();
            if (lower.Contains("title") || lower.Contains("heading") || lower.Contains("status"))
            {
                AddTextShadow(text);
            }
        }
    }

    private static void AddTextShadow(TMP_Text text)
    {
        if (text == null)
        {
            return;
        }

        Shadow shadow = text.GetComponent<Shadow>();
        if (shadow == null)
        {
            shadow = text.gameObject.AddComponent<Shadow>();
        }
        shadow.effectColor = new Color(0f, 0f, 0f, 0.75f);
        shadow.effectDistance = new Vector2(1f, -1f);
    }

    private static void AnchorTo(RectTransform rect, Vector2 min, Vector2 max)
    {
        if (rect == null)
        {
            return;
        }

        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
    }

    private void LogRuntimeSpriteState()
    {
        Debug.Log("[Battle] spriteLoading=InspectorSerializedReferences resourcesLoad=false", this);
        Debug.Log($"[Battle] spriteState backgroundNull={battlePrepBackground == null} templateCount={CountNonNullTemplateSprites()} cardArtPoolCount={(cardArtPool == null ? 0 : cardArtPool.Count(sprite => sprite != null))} attributeIconCount={CountNonNullAttributeSprites(attributeSprites)}", this);

        if (battlePrepBackground == null)
        {
            Debug.LogWarning("[Battle] Missing battle_prep_bg.png reference.", this);
        }

        foreach (string expected in ExpectedTemplateKeys)
        {
            if (!HasTemplateSprite(expected))
            {
                Debug.LogWarning($"[Battle] Missing card template sprite: {expected}", this);
            }
        }

        if (cardTemplateSprites != null)
        {
            foreach (AttributeSpriteMap map in cardTemplateSprites)
            {
                Debug.Log($"[Battle] templateSprite {map.attribute}={SpriteName(map.sprite)}", this);
            }
        }
    }

    private int CountNonNullTemplateSprites()
    {
        return CountNonNullAttributeSprites(cardTemplateSprites);
    }

    private int CountNonNullAttributeSprites(AttributeSpriteMap[] maps)
    {
        if (maps == null)
        {
            return 0;
        }
        return maps.Count(map => map != null && map.sprite != null);
    }

    private bool HasTemplateSprite(string normalizedKey)
    {
        if (cardTemplateSprites == null)
        {
            return false;
        }

        foreach (AttributeSpriteMap map in cardTemplateSprites)
        {
            if (map != null && map.sprite != null && NormalizeAttributeKey(map.attribute) == normalizedKey)
            {
                return true;
            }
        }
        return false;
    }

    private string SpriteName(Sprite sprite)
    {
        return sprite == null ? "null" : sprite.name;
    }

    private string CardName(ThoughtMapBattleCardData card)
    {
        return card == null ? "null" : card.cardName;
    }

    private void EnsurePersonalLibraryApiClient()
    {
        if (personalLibraryApiClient != null)
        {
            return;
        }

        personalLibraryApiClient = GetComponent<ThoughtMapPersonalLibraryApiClient>();
        if (personalLibraryApiClient == null)
        {
            personalLibraryApiClient = gameObject.AddComponent<ThoughtMapPersonalLibraryApiClient>();
        }
    }

    private string GetPersonalLibraryEmail()
    {
        if (personalEmailInput != null && !string.IsNullOrWhiteSpace(personalEmailInput.text))
        {
            return personalEmailInput.text.Trim();
        }

        return string.IsNullOrWhiteSpace(personalLibraryEmail) ? "" : personalLibraryEmail.Trim();
    }

    private string FormatCardListState(ThoughtMapBattleCardData card, string state)
    {
        string scope = card == null ? "" : card.dataScope;
        bool isPersonal = string.Equals(scope, "personal", System.StringComparison.OrdinalIgnoreCase);
        if (!isPersonal)
        {
            return state;
        }

        return string.IsNullOrWhiteSpace(state) ? "Personal" : $"Personal / {state}";
    }

    private string AttributeName(ThoughtMapBattleCardData card)
    {
        return card == null ? "" : card.primaryAttribute;
    }

    private string FormatThoughtAttributeForLog(string thoughtAttribute)
    {
        return string.IsNullOrWhiteSpace(thoughtAttribute) ? "none" : thoughtAttribute;
    }

    private Sprite ResolveAttributeSprite(AttributeSpriteMap[] maps, string attributeName)
    {
        string key = NormalizeAttributeKey(attributeName);
        if (maps != null)
        {
            foreach (AttributeSpriteMap map in maps)
            {
                if (map == null || map.sprite == null)
                {
                    continue;
                }

                string mapKey = !string.IsNullOrWhiteSpace(map.attribute)
                    ? NormalizeAttributeKey(map.attribute)
                    : NormalizeAttributeKey(map.sprite.name);
                if (mapKey == key)
                {
                    return map.sprite;
                }
            }
        }
        return null;
    }

    private string NormalizeAttributeKey(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "";
        }

        string key = value.Trim().ToLowerInvariant();
        switch (key)
        {
            case "\u54F2\u5B66": return "philosophy";
            case "\u5FC3\u7406": return "psychology";
            case "\u79D1\u5B66": return "science";
            case "\u7D4C\u6E08": return "economy";
            case "economics": return "economy";
            case "\u30AB\u30EB\u30DE": return "karma";
            case "\u611F\u60C5": return "emotion";
            case "\u30E2\u30E9\u30EB": return "morality";
            case "moral": return "morality";
            case "\u7406\u5FF5": return "ideology";
            case "ideal": return "ideology";
            case "\u500B\u4EBA": return "individual";
            case "\u5171\u540C\u4F53": return "community";
            default: return key;
        }
    }
    private string GetSpriteWarning()
    {
        bool cardPoolEmpty = cardArtPool == null || cardArtPool.Length == 0;
        bool templatePoolEmpty = cardTemplateSprites == null || cardTemplateSprites.Length == 0;
        bool hasDefaultCardArt = defaultCardArt != null;
        bool hasDefaultAttributeIcon = defaultAttributeIcon != null;

        if (templatePoolEmpty && cardPoolEmpty && !hasDefaultCardArt)
        {
            return "Card Template Sprites and Card Art Pool are empty, and Default Card Art is not assigned";
        }

        if (templatePoolEmpty && cardPoolEmpty)
        {
            return "Card Template Sprites and Card Art Pool are empty";
        }

        if (!hasDefaultAttributeIcon)
        {
            return "Default Attribute Icon is not assigned";
        }

        return "";
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

    [ContextMenu("Log Runtime Layout Diagnostics")]
    public void LogRuntimeLayoutDiagnostics()
    {
        LogScrollAreaDiagnostics("CardListPanel", cardListContent);
        LogScrollAreaDiagnostics("DeckListPanel", deckListContent);
    }

    private ProductBattleCardListRowView CreateListRow(Transform parent, ProductBattleCardListRowView prefab, string objectName)
    {
        ProductBattleCardListRowView view;
        if (prefab != null)
        {
            view = Instantiate(prefab, parent);
        }
        else
        {
            GameObject row = new GameObject(objectName, typeof(RectTransform));
            row.transform.SetParent(parent, false);
            view = row.AddComponent<ProductBattleCardListRowView>();
        }

        view.NormalizeForList(LightweightRowHeight);
        return view;
    }

    [ContextMenu("Ensure Generated Skills Panel")]
    public void EnsureGeneratedSkillsPanel()
    {
        if (generatedSkillsPanel == null)
        {
            Transform existing = FindDescendant(transform, "GeneratedSkillsPanel");
            if (existing == null)
            {
                GameObject panelObject = new GameObject("GeneratedSkillsPanel", typeof(RectTransform), typeof(Image), typeof(ScrollRect), typeof(ProductBattleGeneratedSkillsPanelView));
                panelObject.transform.SetParent(transform, false);
                RectTransform rect = panelObject.GetComponent<RectTransform>();
                rect.anchorMin = new Vector2(0.78f, 0.06f);
                rect.anchorMax = new Vector2(0.985f, 0.40f);
                rect.offsetMin = Vector2.zero;
                rect.offsetMax = Vector2.zero;
                Image image = panelObject.GetComponent<Image>();
                image.color = new Color(0.015f, 0.025f, 0.035f, panelBackgroundAlpha);
                generatedSkillsPanel = panelObject.GetComponent<ProductBattleGeneratedSkillsPanelView>();
            }
            else
            {
                generatedSkillsPanel = existing.GetComponent<ProductBattleGeneratedSkillsPanelView>();
                if (generatedSkillsPanel == null)
                {
                    generatedSkillsPanel = existing.gameObject.AddComponent<ProductBattleGeneratedSkillsPanelView>();
                }
            }
        }

        generatedSkillsPanel?.EnsureBuilt();
    }

    private void EnsureListContentReferences()
    {
        if (cardListContent == null)
        {
            cardListContent = FindPanelContent("CardListPanel");
        }

        if (deckListContent == null)
        {
            deckListContent = FindPanelContent("DeckListPanel");
        }
    }

    private Transform FindPanelContent(string panelName)
    {
        Transform panel = FindDescendant(transform, panelName);
        if (panel == null)
        {
            return null;
        }

        Transform viewport = FindDirectChild(panel, "Viewport");
        if (viewport != null)
        {
            Transform content = FindDirectChild(viewport, "Content");
            if (content != null)
            {
                return content;
            }
        }

        return FindDirectChild(panel, "Content");
    }

    private Transform FindDescendant(Transform root, string objectName)
    {
        if (root == null)
        {
            return null;
        }

        if (root.name == objectName)
        {
            return root;
        }

        for (int i = 0; i < root.childCount; i++)
        {
            Transform found = FindDescendant(root.GetChild(i), objectName);
            if (found != null)
            {
                return found;
            }
        }

        return null;
    }

    private Transform FindDirectChild(Transform root, string objectName)
    {
        if (root == null)
        {
            return null;
        }

        for (int i = 0; i < root.childCount; i++)
        {
            Transform child = root.GetChild(i);
            if (child.name == objectName)
            {
                return child;
            }
        }

        return null;
    }

    private void WarnMissingListContent(string label, string expectedPath)
    {
        string message = $"{label} Content is not assigned. Expected {expectedPath}. Run Tools > Source of Thought > Repair Product Battle Prep ScrollViews.";
        if (statusText != null)
        {
            statusText.text = message;
        }
        Debug.LogWarning("[Battle] " + message, this);
    }

    private void NormalizeLightweightListScrollArea(Transform content)
    {
        if (content == null)
        {
            Debug.LogWarning("[Battle] Cannot normalize lightweight list because Content is null.", this);
            return;
        }

        if (IsUnderPanel(content, "FormationGridPanel"))
        {
            Debug.LogWarning($"[Battle] Skipped lightweight list normalization for {content.name} because it belongs to FormationGridPanel.", this);
            return;
        }

        RectTransform contentRect = content as RectTransform;
        if (contentRect == null)
        {
            Debug.LogWarning($"[Battle] Cannot normalize lightweight list because {content.name} is not a RectTransform.", this);
            return;
        }

        RectTransform viewport = EnsureRuntimeViewportContent(contentRect);
        if (viewport == null)
        {
            Debug.LogWarning($"[Battle] Cannot normalize lightweight list because Viewport is missing for {content.name}.", this);
            return;
        }

        contentRect.anchorMin = new Vector2(0f, 1f);
        contentRect.anchorMax = new Vector2(1f, 1f);
        contentRect.pivot = new Vector2(0.5f, 1f);
        contentRect.anchoredPosition = Vector2.zero;
        contentRect.sizeDelta = Vector2.zero;
        contentRect.offsetMin = new Vector2(0f, contentRect.offsetMin.y);
        contentRect.offsetMax = new Vector2(0f, contentRect.offsetMax.y);

        RemoveConflictingListLayoutGroups(content);

        VerticalLayoutGroup vertical = content.GetComponent<VerticalLayoutGroup>();
        if (vertical == null)
        {
            vertical = content.gameObject.AddComponent<VerticalLayoutGroup>();
        }
        if (vertical == null)
        {
            Debug.LogWarning($"[Battle] Could not create VerticalLayoutGroup on {content.name}.", this);
            return;
        }
        vertical.padding = new RectOffset(6, 6, 6, 6);
        vertical.spacing = LightweightRowSpacing;
        vertical.childAlignment = TextAnchor.UpperCenter;
        vertical.childControlWidth = true;
        vertical.childControlHeight = true;
        vertical.childForceExpandWidth = true;
        vertical.childForceExpandHeight = false;

        ContentSizeFitter fitter = content.GetComponent<ContentSizeFitter>();
        if (fitter == null)
        {
            fitter = content.gameObject.AddComponent<ContentSizeFitter>();
        }
        if (fitter == null)
        {
            Debug.LogWarning($"[Battle] Could not create ContentSizeFitter on {content.name}.", this);
            return;
        }
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        if (viewport != null)
        {
            Image viewportImage = viewport.GetComponent<Image>();
            if (viewportImage == null)
            {
                viewportImage = viewport.gameObject.AddComponent<Image>();
                viewportImage.color = new Color(0f, 0f, 0f, 0.08f);
            }
            viewportImage.raycastTarget = true;

            Mask mask = viewport.GetComponent<Mask>();
            if (mask == null)
            {
                mask = viewport.gameObject.AddComponent<Mask>();
            }
            mask.showMaskGraphic = false;

            RectTransform panel = viewport.parent as RectTransform;
            if (panel != null)
            {
                ScrollRect scroll = panel.GetComponent<ScrollRect>();
                if (scroll == null)
                {
                    scroll = panel.gameObject.AddComponent<ScrollRect>();
                }
                scroll.viewport = viewport;
                scroll.content = contentRect;
                scroll.horizontal = false;
                scroll.vertical = true;
                scroll.movementType = ScrollRect.MovementType.Clamped;
                scroll.inertia = true;
            }
        }
    }

    private void RemoveConflictingListLayoutGroups(Transform content)
    {
        LayoutGroup[] groups = content.GetComponents<LayoutGroup>();
        foreach (LayoutGroup group in groups)
        {
            if (group is VerticalLayoutGroup)
            {
                continue;
            }

            if (debugBattlePrepLayout)
            {
                Debug.Log($"[Battle] replacing {group.GetType().Name} on {content.name} with VerticalLayoutGroup for lightweight list content.", this);
            }
            RemoveComponentImmediate(group);
        }
    }

    private bool IsUnderPanel(Transform target, string panelName)
    {
        Transform current = target;
        while (current != null)
        {
            if (current.name == panelName)
            {
                return true;
            }
            current = current.parent;
        }
        return false;
    }

    private RectTransform EnsureRuntimeViewportContent(RectTransform contentRect)
    {
        if (contentRect == null)
        {
            return null;
        }

        RectTransform viewport = contentRect.parent != null && contentRect.parent.name == "Viewport"
            ? contentRect.parent as RectTransform
            : null;
        RectTransform panel = viewport == null ? contentRect.parent as RectTransform : viewport.parent as RectTransform;
        if (panel == null)
        {
            return viewport;
        }

        if (viewport == null)
        {
            viewport = FindDirectChild(panel, "Viewport") as RectTransform;
        }

        if (viewport == null)
        {
            GameObject viewportObject = new GameObject("Viewport", typeof(RectTransform), typeof(Image), typeof(Mask));
            viewportObject.transform.SetParent(panel, false);
            viewport = viewportObject.GetComponent<RectTransform>();
        }

        viewport.SetParent(panel, false);
        viewport.SetSiblingIndex(Mathf.Min(1, panel.childCount - 1));
        viewport.anchorMin = new Vector2(0.03f, 0.03f);
        viewport.anchorMax = new Vector2(0.97f, 0.90f);
        viewport.pivot = new Vector2(0.5f, 0.5f);
        viewport.anchoredPosition = Vector2.zero;
        viewport.sizeDelta = Vector2.zero;
        viewport.offsetMin = Vector2.zero;
        viewport.offsetMax = Vector2.zero;

        if (contentRect.parent != viewport)
        {
            contentRect.SetParent(viewport, false);
        }
        contentRect.gameObject.name = "Content";
        return viewport;
    }

    private ScrollRect GetScrollRectForContent(Transform content)
    {
        RectTransform contentRect = content as RectTransform;
        RectTransform viewport = contentRect == null ? null : contentRect.parent as RectTransform;
        RectTransform panel = viewport == null ? null : viewport.parent as RectTransform;
        return panel == null ? null : panel.GetComponent<ScrollRect>();
    }

    private void RestoreScrollPosition(ScrollRect scroll, float position)
    {
        if (scroll == null)
        {
            return;
        }

        Canvas.ForceUpdateCanvases();
        scroll.verticalNormalizedPosition = Mathf.Clamp01(position);
    }

    private void RemoveComponentImmediate(Component component)
    {
        if (component == null)
        {
            return;
        }

        if (component is Behaviour behaviour)
        {
            behaviour.enabled = false;
        }

        DestroyImmediate(component);
    }

    private void LogScrollAreaDiagnostics(string label, Transform content)
    {
        if (content == null)
        {
            Debug.LogWarning($"[Battle] {label}: content is not assigned.", this);
            return;
        }

        GridLayoutGroup grid = content.GetComponent<GridLayoutGroup>();
        VerticalLayoutGroup vertical = content.GetComponent<VerticalLayoutGroup>();
        ContentSizeFitter fitter = content.GetComponent<ContentSizeFitter>();
        RectTransform viewport = content.parent as RectTransform;
        ScrollRect scroll = viewport == null || viewport.parent == null ? null : viewport.parent.GetComponent<ScrollRect>();
        Mask mask = viewport == null ? null : viewport.GetComponent<Mask>();
        string gridCell = grid == null || !grid.enabled ? "missing" : grid.cellSize.ToString();
        string verticalInfo = vertical == null ? "missing" : "spacing " + vertical.spacing;
        string fitterInfo = fitter == null ? "missing" : fitter.horizontalFit + "/" + fitter.verticalFit;
        string scrollViewport = scroll == null || scroll.viewport == null ? "missing" : scroll.viewport.name;
        string scrollContent = scroll == null || scroll.content == null ? "missing" : scroll.content.name;
        string maskInfo = mask == null ? "missing" : mask.showMaskGraphic.ToString();

        if (debugBattlePrepLayout)
        {
            Debug.Log(
                $"[Battle] {label}: " +
                $"Grid cellSize={gridCell}, " +
                $"VerticalLayout={verticalInfo}, " +
                $"Fitter={fitterInfo}, " +
                $"Scroll viewport={scrollViewport}, " +
                $"Scroll content={scrollContent}, " +
                $"Mask={maskInfo}",
                this
            );
        }

        ProductBattleCardListRowView[] rows = content.GetComponentsInChildren<ProductBattleCardListRowView>(true);
        for (int i = 0; i < rows.Length; i++)
        {
            RectTransform rect = rows[i].GetComponent<RectTransform>();
            LayoutElement layout = rows[i].GetComponent<LayoutElement>();
            Graphic[] graphics = rows[i].GetComponentsInChildren<Graphic>(true);
            int raycastTargets = graphics.Count(graphic => graphic.raycastTarget);
            string cardSize = rect == null ? "missing" : rect.rect.size.ToString();
            string layoutInfo = layout == null
                ? "missing"
                : "min " + layout.minWidth + "x" + layout.minHeight + " preferred " + layout.preferredWidth + "x" + layout.preferredHeight;
            if (debugBattlePrepLayout)
            {
                Debug.Log(
                    $"[Battle] {label} Row {i}: " +
                    $"size={cardSize}, " +
                    $"Layout={layoutInfo}, " +
                    $"raycastTargetGraphics={raycastTargets}",
                    rows[i]
                );
            }
        }
    }

    private void WriteStatus(string value)
    {
        if (statusText != null)
        {
            statusText.text = value;
        }
    }

    private string ShortStatusText(string primary, string fallback)
    {
        string value = string.IsNullOrWhiteSpace(primary) ? fallback : primary;
        if (string.IsNullOrWhiteSpace(value))
        {
            return "";
        }
        return value.Length <= 120 ? value : value.Substring(0, 120) + "...";
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

    private void ClearChildrenImmediate(Transform root)
    {
        if (root == null)
        {
            return;
        }

        for (int i = root.childCount - 1; i >= 0; i--)
        {
            DestroyImmediate(root.GetChild(i).gameObject);
        }
    }
}

[System.Serializable]
public class AttributeSpriteMap
{
    public string attribute;
    public Sprite sprite;
}

public struct ThoughtParameterDefinition
{
    public readonly string key;
    public readonly string[] aliases;

    public ThoughtParameterDefinition(string key, params string[] aliases)
    {
        this.key = key;
        this.aliases = aliases;
    }
}


