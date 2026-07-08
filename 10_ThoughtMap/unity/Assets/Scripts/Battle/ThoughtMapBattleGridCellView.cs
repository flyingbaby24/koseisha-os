using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ThoughtMapBattleGridCellView : MonoBehaviour
{
    [SerializeField] private TMP_Text positionText;
    [SerializeField] private TMP_Text teamText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private TMP_Text damageText;
    [SerializeField] private TMP_Text koText;
    [SerializeField] private Image background;
    [SerializeField] private Image hpBarBackground;
    [SerializeField] private Image hpBarFill;
    [SerializeField] private Button button;

    private int gridX;
    private int gridY;
    private ThoughtMapBattleUnit boundUnit;
    private UnityAction<ThoughtMapBattleGridCellView> clickHandler;

    public int X => gridX;
    public int Y => gridY;
    public ThoughtMapBattleUnit Unit => boundUnit;

    public void BuildIfNeeded()
    {
        RectTransform root = EnsureRectTransform(gameObject);
        background = EnsureImage(gameObject, new Color(0.012f, 0.09f, 0.13f, 0.9f));
        button = EnsureButton(gameObject);

        VerticalLayoutGroup layout = gameObject.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<VerticalLayoutGroup>();
        }
        layout.padding = new RectOffset(3, 3, 2, 2);
        layout.spacing = 0f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        positionText = positionText == null ? CreateText(root, "PositionText", 8, new Color(0.45f, 0.9f, 1f, 1f)) : positionText;
        teamText = teamText == null ? CreateText(root, "TeamText", 7, new Color(0.82f, 0.9f, 1f, 1f)) : teamText;
        cardNameText = cardNameText == null ? CreateText(root, "CardNameText", 8, Color.white) : cardNameText;
        attributeText = attributeText == null ? CreateText(root, "AttributeText", 7, new Color(0.74f, 1f, 0.82f, 1f)) : attributeText;
        hpText = hpText == null ? CreateText(root, "HpText", 7, new Color(1f, 0.84f, 0.58f, 1f)) : hpText;
        hpBarBackground = hpBarBackground == null ? CreateHpBar(root, "HpBarBackground", new Color(0.02f, 0.02f, 0.03f, 0.95f)) : hpBarBackground;
        hpBarFill = hpBarFill == null ? CreateHpBar(hpBarBackground.rectTransform, "HpBarFill", new Color(0.3f, 1f, 0.72f, 1f)) : hpBarFill;
        damageText = damageText == null ? CreateText(root, "DamageText", 8, new Color(1f, 0.55f, 0.35f, 1f)) : damageText;
        koText = koText == null ? CreateText(root, "KoText", 9, new Color(1f, 0.28f, 0.28f, 1f)) : koText;
        damageText.fontStyle = FontStyles.Bold;
        koText.fontStyle = FontStyles.Bold;
        damageText.text = "";
        koText.text = "";
    }

    public void BindEmpty(int x, int y)
    {
        BuildIfNeeded();
        gridX = x;
        gridY = y;
        boundUnit = null;
        background.color = new Color(0.012f, 0.09f, 0.13f, 0.9f);
        positionText.text = $"{x},{y}";
        teamText.text = "";
        cardNameText.text = "\u25A1";
        attributeText.text = "";
        hpText.text = "";
        damageText.text = "";
        koText.text = "";
        SetHpRatio(0f);
    }

    public void BindUnit(ThoughtMapBattleUnit unit)
    {
        BuildIfNeeded();
        if (unit == null || unit.card == null)
        {
            BindEmpty(0, 0);
            return;
        }

        gridX = unit.position.x;
        gridY = unit.position.y;
        boundUnit = unit;
        bool player = unit.team == "Player";
        background.color = player
            ? new Color(0.0f, 0.24f, 0.34f, 0.96f)
            : new Color(0.26f, 0.06f, 0.12f, 0.96f);
        teamText.text = player ? "Player" : "Enemy";
        positionText.text = string.IsNullOrWhiteSpace(unit.battleId) ? $"{unit.position.x},{unit.position.y}" : unit.battleId;
        cardNameText.text = Short(unit.card.cardName, 15);
        attributeText.text = Short(unit.card.primaryAttribute, 12);
        hpText.text = $"HP {unit.hp}";
        damageText.text = "";
        koText.text = unit.IsAlive ? "" : "KO";
        SetHpRatio(unit.maxHp <= 0 ? 0f : (float)unit.hp / unit.maxHp);
        if (!unit.IsAlive)
        {
            background.color = new Color(0.04f, 0.04f, 0.05f, 0.96f);
        }
    }

    public void UpdateHp(int hp, int maxHp)
    {
        hpText.text = $"HP {Mathf.Max(0, hp)}";
        SetHpRatio(maxHp <= 0 ? 0f : (float)Mathf.Max(0, hp) / maxHp);
        if (hp <= 0)
        {
            koText.text = "KO";
            background.color = new Color(0.04f, 0.04f, 0.05f, 0.96f);
        }
    }

    public IEnumerator PlayAttackPulse()
    {
        Vector3 start = transform.localScale;
        transform.localScale = start * 1.08f;
        yield return new WaitForSeconds(0.08f);
        transform.localScale = start;
    }

    public IEnumerator PlayAttackToward(Vector3 targetLocalPosition)
    {
        Vector3 startPosition = transform.localPosition;
        Vector3 direction = targetLocalPosition - startPosition;
        if (direction.sqrMagnitude < 0.01f)
        {
            direction = Vector3.up;
        }
        direction.Normalize();

        Vector3 startScale = transform.localScale;
        transform.localPosition = startPosition + direction * 10f;
        transform.localScale = startScale * 1.06f;
        yield return new WaitForSeconds(0.08f);
        transform.localPosition = startPosition;
        transform.localScale = startScale;
    }

    public IEnumerator PlayHit(int damage, bool defeated)
    {
        damageText.text = damage > 0 ? $"-{damage}" : "MISS";
        Vector3 start = transform.localPosition;
        for (int i = 0; i < 5; i++)
        {
            transform.localPosition = start + new Vector3(i % 2 == 0 ? 6f : -6f, 0f, 0f);
            yield return new WaitForSeconds(0.035f);
        }
        transform.localPosition = start;
        yield return new WaitForSeconds(0.18f);
        damageText.text = "";
        if (defeated)
        {
            koText.text = "KO";
        }
    }

    public void SetClickHandler(UnityAction<ThoughtMapBattleGridCellView> handler)
    {
        BuildIfNeeded();
        if (clickHandler != null)
        {
            button.onClick.RemoveListener(HandleClicked);
        }

        clickHandler = handler;
        if (clickHandler != null)
        {
            button.onClick.AddListener(HandleClicked);
        }
    }

    public void SetPlacementHint(bool available)
    {
        if (boundUnit != null)
        {
            return;
        }

        background.color = available
            ? new Color(0.0f, 0.24f, 0.23f, 0.96f)
            : new Color(0.012f, 0.09f, 0.13f, 0.9f);
    }

    public void SetInteractable(bool interactable)
    {
        BuildIfNeeded();
        button.interactable = interactable;
    }

    private void HandleClicked()
    {
        clickHandler?.Invoke(this);
    }

    private TMP_Text CreateText(RectTransform parent, string name, int fontSize, Color color)
    {
        GameObject textObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.fontSize = fontSize;
        text.color = color;
        text.alignment = TextAlignmentOptions.Center;
        text.enableWordWrapping = false;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
        return text;
    }

    private Image CreateHpBar(RectTransform parent, string name, Color color)
    {
        GameObject barObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = barObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        Image image = barObject.GetComponent<Image>();
        image.color = color;
        image.raycastTarget = false;
        LayoutElement element = barObject.AddComponent<LayoutElement>();
        element.preferredHeight = 5f;
        element.minHeight = 5f;
        if (name == "HpBarFill")
        {
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }
        return image;
    }

    private void SetHpRatio(float ratio)
    {
        if (hpBarFill == null)
        {
            return;
        }
        RectTransform rect = hpBarFill.rectTransform;
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = new Vector2(Mathf.Clamp01(ratio), 1f);
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
    }

    private Image EnsureImage(GameObject target, Color color)
    {
        Image image = target.GetComponent<Image>();
        if (image == null)
        {
            image = target.AddComponent<Image>();
        }
        image.color = color;
        image.raycastTarget = true;
        return image;
    }

    private Button EnsureButton(GameObject target)
    {
        Button existingButton = target.GetComponent<Button>();
        if (existingButton == null)
        {
            existingButton = target.AddComponent<Button>();
        }
        existingButton.targetGraphic = target.GetComponent<Graphic>();
        return existingButton;
    }

    private RectTransform EnsureRectTransform(GameObject target)
    {
        RectTransform rect = target.GetComponent<RectTransform>();
        if (rect == null)
        {
            rect = target.AddComponent<RectTransform>();
        }
        return rect;
    }

    private string Short(string value, int maxLength)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "Card";
        }

        return value.Length <= maxLength ? value : value.Substring(0, maxLength) + "...";
    }
}
