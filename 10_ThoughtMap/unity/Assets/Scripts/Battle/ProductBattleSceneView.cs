using System.Collections.Generic;
using System.IO;
using System.Linq;
using TMPro;
using UnityEngine;

public class ProductBattleSceneView : MonoBehaviour
{
    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private string deckFileName = "deck.json";
    [SerializeField] private bool loadOnStart = true;

    [Header("Prefabs")]
    [SerializeField] private ProductBattleUnitCardView battleUnitCardPrefab;

    [Header("Scene References")]
    [SerializeField] private Transform playerBoardRoot;
    [SerializeField] private Transform enemyBoardRoot;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private ProductBattleLogPanelView battleLogPanel;

    [Header("Sprites")]
    [SerializeField] private Sprite defaultCardArt;
    [SerializeField] private Sprite defaultAttributeIcon;
    [SerializeField] private Sprite[] cardArtPool;
    [SerializeField] private AttributeSpriteMap[] attributeSprites;

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

        List<ThoughtMapBattleCardData> playerCards = ResolveCards(cards, config != null ? config.deployedCardIds : null);
        if (playerCards.Count == 0)
        {
            playerCards = cards.Take(5).ToList();
        }

        List<ThoughtMapBattleCardData> enemyCards = cards.Skip(10).Take(5).ToList();
        if (enemyCards.Count < 5)
        {
            enemyCards = playerCards.AsEnumerable().Reverse().ToList();
        }

        RenderUnits(playerBoardRoot, playerCards, "P", false);
        RenderUnits(enemyBoardRoot, enemyCards, "E", true);
        battleLogPanel?.SetLog("Loaded deck.json preview. Battle logic will be connected in a later BattleScene phase.");
        WriteStatus($"BattleScene loaded {playerCards.Count} player cards and {enemyCards.Count} enemy cards.");
    }

    private void Start()
    {
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
            WriteStatus("deck.json not found yet. Showing fallback battle preview.");
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

    private void RenderUnits(Transform root, List<ThoughtMapBattleCardData> cards, string prefix, bool enemySide)
    {
        if (root == null || battleUnitCardPrefab == null)
        {
            return;
        }

        for (int i = 0; i < cards.Count; i++)
        {
            ProductBattleUnitCardView view = Instantiate(battleUnitCardPrefab, root);
            view.Bind($"{prefix}{i + 1}", cards[i], ResolveCardArt(i), ResolveAttributeIcon(cards[i]), enemySide);
        }
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
