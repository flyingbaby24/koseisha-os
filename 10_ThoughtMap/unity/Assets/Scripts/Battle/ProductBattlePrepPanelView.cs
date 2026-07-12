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
    private const float LightweightRowHeight = 46f;
    private const float LightweightRowSpacing = 4f;
    private static readonly string[] ExpectedTemplateKeys =
    {
        "philosophy", "psychology", "science", "economy", "karma",
        "emotion", "moral", "ideal", "individual", "community"
    };
    private static readonly ThoughtParameterDefinition[] ThoughtParameterOrder =
    {
        new ThoughtParameterDefinition("philosophy", "philosophy", "哲学"),
        new ThoughtParameterDefinition("psychology", "psychology", "心理"),
        new ThoughtParameterDefinition("science", "science", "科学"),
        new ThoughtParameterDefinition("economy", "economy", "economics", "経済"),
        new ThoughtParameterDefinition("karma", "karma", "カルマ"),
        new ThoughtParameterDefinition("emotion", "emotion", "感情"),
        new ThoughtParameterDefinition("moral", "moral", "morality", "モラル"),
        new ThoughtParameterDefinition("ideal", "ideal", "理念"),
        new ThoughtParameterDefinition("individual", "individual", "個人"),
        new ThoughtParameterDefinition("community", "community", "共同体")
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
    [SerializeField] private bool showAllGeneratedSkillsWhenNoDeckMatch = true;

    [Header("Fonts")]
    [SerializeField] private TMP_FontAsset japaneseFontAsset;
    [SerializeField] private TMP_Text fontReferenceText;

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

    [Header("Rules")]
    [SerializeField] private int deckLimit = 10;
    [SerializeField] private int deployLimit = 5;
    [SerializeField] private int cardListRenderLimit = 60;
    [SerializeField] private int playerRows = 5;
    [SerializeField] private bool logFormationGridCells;

    private readonly List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();
    private readonly List<ThoughtMapBattleCardData> deckCards = new List<ThoughtMapBattleCardData>();
    private readonly Dictionary<int, ThoughtMapBattleCardData> placement = new Dictionary<int, ThoughtMapBattleCardData>();
    private readonly List<GeneratedSkillDto> generatedSkills = new List<GeneratedSkillDto>();
    private readonly Dictionary<string, GeneratedSkillDto> generatedSkillById = new Dictionary<string, GeneratedSkillDto>();
    private readonly Dictionary<string, List<string>> assignedSkillIdsByCardId = new Dictionary<string, List<string>>();
    private readonly List<ProductBattleGridCellView> gridCells = new List<ProductBattleGridCellView>();
    private int selectedDeckIndex = -1;
    private int selectedLibraryIndex = -1;
    private string selectedGeneratedSkillId = "";

    private void Awake()
    {
        EnsureFormationRules();
        WireButtons();
        EnsureBattlePrepBackground();
        EnsurePanelTransparency();
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
        ApplyJapaneseFontReferences();
        WireGeneratedSkillsPanel();
        RenderGrid();
        cardDetailPanel?.Clear();
    }

    private void EnsureFormationRules()
    {
        if (playerRows != 5)
        {
            Debug.Log($"[ProductBattlePrep Grid] playerRows changed from {playerRows} to 5 so all 5x5 formation cells are placeable.", this);
            playerRows = 5;
        }
    }

    private void Start()
    {
        LogRuntimeSpriteState();
        if (loadCardsOnStart)
        {
            LoadCards();
        }
        LoadGeneratedSkills();
    }

    private void WireButtons()
    {
        AddClick(loadCardsButton, LoadCards);
        AddClick(addToDeckButton, AddSelectedCardToDeck);
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

        RenderAll();
        RenderGeneratedSkills();
    }

    public void ClearPlacement()
    {
        placement.Clear();
        selectedDeckIndex = -1;
        selectedLibraryIndex = -1;
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
            string state = deckCards.Contains(loadedCards[i]) ? "In Deck" : "";
            Sprite artSprite = ResolveCardArtForTarget(loadedCards[i], i, "Card List");
            view.Bind(loadedCards[i], i, GetCardId(loadedCards[i]), i == selectedLibraryIndex, deckCards.Contains(loadedCards[i]), state, artSprite);
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
            string state = placement.ContainsValue(deckCards[i]) ? "Placed" : "Ready";
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
            }
            else
            {
                gridCells[index].BindEmpty(x, y, available);
            }
            gridCells[index].SetClickHandler(OnGridCellClicked);
            if (logFormationGridCells)
            {
                Debug.Log($"[ProductBattlePrep Grid] cell index={index} x={x} y={y} available={available} hasCard={placement.ContainsKey(index)}", gridCells[index]);
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

        Debug.Log($"[ProductBattlePrep Grid] Rebuilding Formation Grid cells. Existing count={gridCells.Count}, required=25.", this);
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
        Debug.Log($"[ProductBattlePrep Grid] clicked cell index={index} x={cell.X} y={cell.Y} available={IsFormationCellAvailable(cell.Y)} hasCard={placement.ContainsKey(index)}", cell);
        if (placement.ContainsKey(index))
        {
            placement.Remove(index);
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
        generatedSkills.Clear();
        generatedSkillById.Clear();

        List<GeneratedSkillDto> loaded = GeneratedSkillLibrary.LoadFromStreamingAssets(generatedSkillsRelativePath, debugGeneratedSkills);
        generatedSkills.AddRange(loaded);
        foreach (GeneratedSkillDto skill in loaded)
        {
            if (skill == null || string.IsNullOrWhiteSpace(skill.skill_id))
            {
                continue;
            }
            generatedSkillById[skill.skill_id] = skill;
        }

        if (debugGeneratedSkills)
        {
            Debug.Log($"[GeneratedSkills] Runtime skill count={generatedSkills.Count} path={generatedSkillsRelativePath}", this);
        }
        if (generatedSkills.Count == 0)
        {
            WriteStatus("No generated skills. Put generated_skills.json under StreamingAssets/GeneratedSkills.");
        }

        RenderGeneratedSkills();
        ShowSelectedDetail();
    }

    public void ApplyJapaneseFontAsset(TMP_FontAsset fontAsset)
    {
        japaneseFontAsset = fontAsset;
        ApplyJapaneseFontReferences();
    }

    public void ApplyJapaneseFontReferences()
    {
        TMP_FontAsset font = ResolveJapaneseFontAsset();
        if (font == null)
        {
            if (debugGeneratedSkills)
            {
                Debug.LogWarning("[GeneratedSkills] Japanese TMP Font Asset is not assigned. Generated skill Japanese text may render as missing glyphs.", this);
            }
            return;
        }

        japaneseFontAsset = font;
        if (statusText != null)
        {
            statusText.font = font;
        }
        if (cardDetailPanel != null)
        {
            cardDetailPanel.SetFontAsset(font);
        }
        if (generatedSkillsPanel != null)
        {
            generatedSkillsPanel.SetFontAsset(font);
        }
    }

    private TMP_FontAsset ResolveJapaneseFontAsset()
    {
        if (japaneseFontAsset != null)
        {
            return japaneseFontAsset;
        }
        if (fontReferenceText != null && fontReferenceText.font != null)
        {
            return fontReferenceText.font;
        }
        if (statusText != null && statusText.font != null)
        {
            return statusText.font;
        }
        TMP_Text existingText = GetComponentInChildren<TMP_Text>(true);
        return existingText == null ? null : existingText.font;
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
            WriteStatus("Assign requires a Deck 10 card. Select a deck card first.");
            return;
        }

        string cardId = GetCardId(card);
        if (!assignedSkillIdsByCardId.TryGetValue(cardId, out List<string> skillIds))
        {
            skillIds = new List<string>();
            assignedSkillIdsByCardId[cardId] = skillIds;
        }

        if (skillIds.Contains(skill.skill_id))
        {
            WriteStatus("This skill is already assigned to the selected card.");
            return;
        }

        if (skillIds.Count >= 3)
        {
            WriteStatus("Each card can have up to 3 assigned skills.");
            return;
        }

        skillIds.Add(skill.skill_id);
        selectedGeneratedSkillId = skill.skill_id;
        if (debugGeneratedSkills)
        {
            Debug.Log($"[GeneratedSkills] Assigned skill_id={skill.skill_id} cardId={cardId}", this);
        }
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
            WriteStatus("Remove requires a Deck 10 card. Select a deck card first.");
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
            Debug.Log($"[GeneratedSkills] Removed skill_id={skill.skill_id} cardId={cardId}", this);
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
            : $"Selected skill: {skill.DisplayName} - {ShortStatusText(skill.description_ja, skill.description_en)}");
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
            GetAssignedSkillIdsForCard(selectedCard)
        );

        if (debugGeneratedSkills || usedDebugFallback)
        {
            Debug.Log($"[GeneratedSkills] Deck matched skill count={GetDeckMatchedGeneratedSkills().Count} displayed={deckMatchedSkills.Count} deck cards={deckCards.Count} fallbackAll={usedDebugFallback}", this);
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
        Debug.Log($"[GeneratedSkills] Matching debug: deckCardCount={deckCards.Count} skillCount={generatedSkills.Count}", this);
        foreach (ThoughtMapBattleCardData card in deckCards)
        {
            Debug.Log($"[GeneratedSkills] Deck card: title='{(card == null ? "null" : card.cardName)}' doc_id='{(card == null ? "" : card.docId)}'", this);
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
            Debug.Log($"[GeneratedSkills] Skill: name='{skill.DisplayName}' doc_id='{skill.doc_id}' Matched: {matched}", this);
        }
        Debug.Log($"[GeneratedSkills] Matching debug complete. matchCount={matchCount}", this);
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
            ? ids.Where(id => !string.IsNullOrWhiteSpace(id)).Take(3).ToList()
            : new List<string>();
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
            cardDetailPanel.Show(
                libraryCard,
                ResolveCardArtForTarget(libraryCard, selectedLibraryIndex, "Detail Panel"),
                ResolveAttributeIconForTarget(libraryCard, "Detail Panel"),
                ResolveDominantThoughtAttributeKey(libraryCard),
                GetAssignedSkillsForCard(libraryCard)
            );
            return;
        }

        if (selectedDeckIndex < 0 || selectedDeckIndex >= deckCards.Count)
        {
            cardDetailPanel.Clear();
            return;
        }

        ThoughtMapBattleCardData card = deckCards[selectedDeckIndex];
        cardDetailPanel.Show(
            card,
            ResolveCardArtForTarget(card, selectedDeckIndex, "Detail Panel"),
            ResolveAttributeIconForTarget(card, "Detail Panel"),
            ResolveDominantThoughtAttributeKey(card),
            GetAssignedSkillsForCard(card)
        );
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
            Debug.Log($"[GeneratedSkills] Saved assigned skill count={count} path={path}", this);
        }
        WriteStatus("Saved deck: " + path);
    }

    [ContextMenu("Restore Assigned Skills From Deck JSON")]
    public void RestoreAssignedSkillsFromDeckJson()
    {
        string path = Path.Combine(Application.persistentDataPath, deckFileName);
        if (!File.Exists(path))
        {
            Debug.LogWarning("[GeneratedSkills] deck.json not found for assigned skill restore: " + path, this);
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
        RenderAll();
        WriteStatus("Loaded deck: " + path);
    }

    private List<CardAssignedSkillData> BuildAssignedSkillSaveData()
    {
        List<CardAssignedSkillData> result = new List<CardAssignedSkillData>();
        foreach (ThoughtMapBattleCardData card in deckCards)
        {
            string cardId = GetCardId(card);
            if (!assignedSkillIdsByCardId.TryGetValue(cardId, out List<string> skillIds))
            {
                continue;
            }

            List<string> validIds = skillIds
                .Where(id => !string.IsNullOrWhiteSpace(id))
                .Distinct()
                .Take(3)
                .ToList();
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
        foreach (CardAssignedSkillData item in config.assignedSkills)
        {
            if (item == null || string.IsNullOrWhiteSpace(item.cardId) || item.skillIds == null)
            {
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
                    Debug.LogWarning($"[GeneratedSkills] Saved skill_id not found in generated skill JSON: {skillId}", this);
                    continue;
                }
                if (!valid.Contains(skillId) && valid.Count < 3)
                {
                    valid.Add(skillId);
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
            Debug.Log($"[GeneratedSkills] Restored assigned skill count={restored}", this);
        }
    }

    public void StartBattleScene()
    {
        SaveDeckJson();
        WriteStatus("Opening BattleScene: " + battleSceneName);
        SceneManager.LoadScene(battleSceneName);
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
        string thoughtAttribute = ResolveDominantThoughtAttributeKey(card);
        Debug.Log(
            $"[ProductBattlePrep Art] {target}: card title='{CardName(card)}' battle attribute='{AttributeName(card)}' resolved thought attribute='{FormatThoughtAttributeForLog(thoughtAttribute)}' assigned sprite name='{SpriteName(sprite)}'",
            this
        );
        if (sprite == null)
        {
            Debug.LogWarning(
                $"[ProductBattlePrep Art] Missing: card template/default art for target={target}, card='{CardName(card)}', battle attribute='{AttributeName(card)}', resolved thought attribute='{FormatThoughtAttributeForLog(thoughtAttribute)}'.",
                this
            );
        }
        return sprite;
    }

    private Sprite ResolveAttributeIconForTarget(ThoughtMapBattleCardData card, string target)
    {
        Sprite sprite = ResolveAttributeIcon(card);
        string thoughtAttribute = ResolveDominantThoughtAttributeKey(card);
        Debug.Log(
            $"[ProductBattlePrep Art] {target}: Attribute Image.sprite candidate={SpriteName(sprite)} card title='{CardName(card)}' battle attribute='{AttributeName(card)}' resolved thought attribute='{FormatThoughtAttributeForLog(thoughtAttribute)}'",
            this
        );
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
                "[ProductBattlePrep Art] Missing: battle_prep_bg.png / battlePrepBackground Inspector reference is null. Runtime uses Inspector references; Resources.Load is not used.",
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
        Debug.Log(
            $"[ProductBattlePrep Art] Background Image.sprite assigned={SpriteName(backgroundImage.sprite)} method=Inspector/serialized reference",
            this
        );

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
        Debug.Log($"[ProductBattlePrep Art] Dark Overlay configured above background alpha={darkOverlayImage.color.a}.", this);

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
            "CardListPanel", "DeckListPanel", "FormationGridPanel", "CardDetailPanel", "DebugLogPanel"
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
            Debug.Log($"[ProductBattlePrep Art] Panel alpha normalized: {panelName} alpha={color.a}", image);
        }
    }

    private void LogRuntimeSpriteState()
    {
        Debug.Log(
            "[ProductBattlePrep Art] Runtime loading method: Inspector serialized Sprite references. AssetDatabase is Editor/Repair only. Resources.Load is not used.",
            this
        );
        Debug.Log($"[ProductBattlePrep Art] Start: Battle Prep Background == null ? {battlePrepBackground == null}", this);
        Debug.Log($"[ProductBattlePrep Art] Start: Card Template Sprite Count = {CountNonNullTemplateSprites()}", this);
        Debug.Log($"[ProductBattlePrep Art] Start: Card Art Pool Count = {(cardArtPool == null ? 0 : cardArtPool.Count(sprite => sprite != null))}", this);
        Debug.Log($"[ProductBattlePrep Art] Start: Attribute Sprite Count = {CountNonNullAttributeSprites(attributeSprites)}", this);

        if (battlePrepBackground == null)
        {
            Debug.LogWarning("[ProductBattlePrep Art] Missing: battle_prep_bg.png", this);
        }

        foreach (string expected in ExpectedTemplateKeys)
        {
            if (!HasTemplateSprite(expected))
            {
                Debug.LogWarning($"[ProductBattlePrep Art] Missing template: {expected}", this);
            }
        }

        if (cardTemplateSprites != null)
        {
            foreach (AttributeSpriteMap map in cardTemplateSprites)
            {
                Debug.Log($"[ProductBattlePrep Art] Template runtime ref: {map.attribute} => {SpriteName(map.sprite)}", this);
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
                if (!string.IsNullOrWhiteSpace(map.attribute) && NormalizeAttributeKey(map.attribute) == key)
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
            case "哲学": return "philosophy";
            case "心理": return "psychology";
            case "科学": return "science";
            case "経済": return "economy";
            case "economics": return "economy";
            case "カルマ": return "karma";
            case "感情": return "emotion";
            case "モラル": return "moral";
            case "morality": return "moral";
            case "理念": return "ideal";
            case "個人": return "individual";
            case "共同体": return "community";
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
        ApplyJapaneseFontReferences();
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
        Debug.LogWarning("[ProductBattlePrep] " + message, this);
    }

    private void NormalizeLightweightListScrollArea(Transform content)
    {
        if (content == null)
        {
            Debug.LogWarning("[ProductBattlePrep] Cannot normalize lightweight list because Content is null.", this);
            return;
        }

        if (IsUnderPanel(content, "FormationGridPanel"))
        {
            Debug.LogWarning($"[ProductBattlePrep] Skipped lightweight list normalization for {content.name} because it belongs to FormationGridPanel.", this);
            return;
        }

        RectTransform contentRect = content as RectTransform;
        if (contentRect == null)
        {
            Debug.LogWarning($"[ProductBattlePrep] Cannot normalize lightweight list because {content.name} is not a RectTransform.", this);
            return;
        }

        RectTransform viewport = EnsureRuntimeViewportContent(contentRect);
        if (viewport == null)
        {
            Debug.LogWarning($"[ProductBattlePrep] Cannot normalize lightweight list because Viewport is missing for {content.name}.", this);
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
            Debug.LogWarning($"[ProductBattlePrep] Could not create VerticalLayoutGroup on {content.name}.", this);
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
            Debug.LogWarning($"[ProductBattlePrep] Could not create ContentSizeFitter on {content.name}.", this);
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

            Debug.Log($"[ProductBattlePrep] Replacing {group.GetType().Name} on {content.name} with VerticalLayoutGroup for lightweight list content.", this);
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
            Debug.LogWarning($"[ProductBattlePrep] {label}: content is not assigned.", this);
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

        Debug.Log(
            $"[ProductBattlePrep] {label}: " +
            $"Grid cellSize={gridCell}, " +
            $"VerticalLayout={verticalInfo}, " +
            $"Fitter={fitterInfo}, " +
            $"Scroll viewport={scrollViewport}, " +
            $"Scroll content={scrollContent}, " +
            $"Mask={maskInfo}",
            this
        );

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
            Debug.Log(
                $"[ProductBattlePrep] {label} Row {i}: " +
                $"size={cardSize}, " +
                $"Layout={layoutInfo}, " +
                $"raycastTargetGraphics={raycastTargets}",
                rows[i]
            );
        }
    }

    private void WriteStatus(string value)
    {
        if (statusText != null)
        {
            statusText.text = value;
        }
        Debug.Log("[ProductBattlePrep] " + value, this);
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
