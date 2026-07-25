using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using System;
using System.Collections.Generic;

public class ProductBattleUnitCardView : MonoBehaviour
{
    [SerializeField] private Image frameImage;
    [SerializeField] private Image artImage;
    [SerializeField] private Image attributeIconImage;
    [SerializeField] private Slider hpSlider;
    [SerializeField] private TMP_Text unitIdText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private TMP_Text attributeText;

    private RectTransform cachedRectTransform;
    private Color baseFrameColor;
    private Image hpFillImage;
    private CanvasGroup canvasGroup;
    private int popupSequence;
    private Action<ProductBattleUnitCardView> selectionHandler;
    public ThoughtMapBattleCardData Card { get; private set; }
    public string UnitId { get; private set; }
    public bool EnemySide { get; private set; }
    public int CurrentHp { get; private set; }
    public int MaxHp { get; private set; }
    public int CurrentSp { get; private set; }
    public int PhysicalAttack { get; private set; }
    public int SkillAttack { get; private set; }
    public int PhysicalDefense { get; private set; }
    public int SkillDefense { get; private set; }
    public int Speed { get; private set; }
    public GeneratedSkillDto EquippedSkill { get; private set; }
    public Sprite CardSprite => artImage == null ? null : artImage.sprite;
    public RectTransform RectTransform => transform as RectTransform;

    public void Bind(string unitId, ThoughtMapBattleCardData card, Sprite artSprite, Sprite attributeSprite, bool enemySide)
    {
        SetCardData(unitId, card, enemySide);
        SetCardSprite(artSprite);
        SetAttributeSprite(attributeSprite);
        cachedRectTransform = transform as RectTransform;
        ResolveRuntimeReferences();
    }

    public void SetCardData(string unitId, ThoughtMapBattleCardData card, bool enemySide)
    {
        UnitId = unitId; Card = card; EnemySide = enemySide;
        CurrentHp = MaxHp = card == null ? 1 : card.MaxHp; CurrentSp = card == null ? 0 : card.MaxSp;
        PhysicalAttack = card == null ? 0 : card.statPhysicalAttack; SkillAttack = card == null ? 0 : card.statSkillAttack;
        PhysicalDefense = card == null ? 0 : card.statPhysicalDefense; SkillDefense = card == null ? 0 : card.statSkillDefense; Speed = card == null ? 0 : card.statSpeed;
        SetText(unitIdText, unitId);
        SetText(cardNameText, card == null ? "Empty" : card.cardName);
        SetText(hpText, card == null ? "HP -" : $"{card.MaxHp} / {card.MaxHp}");
        SetText(attributeText, card == null ? "-" : card.primaryAttribute);

        if (hpSlider != null)
        {
            hpSlider.minValue = 0;
            hpSlider.maxValue = card == null ? 1 : card.MaxHp;
            hpSlider.value = card == null ? 0 : card.MaxHp;
        }

        if (frameImage != null)
        {
            baseFrameColor = enemySide
                ? new Color(0.42f, 0.06f, 0.07f, 0.95f)
                : new Color(0.02f, 0.20f, 0.36f, 0.95f);
            frameImage.color = baseFrameColor;
        }
        if (attributeText != null)
        {
            attributeText.color = enemySide ? new Color(1f, 0.62f, 0.58f) : new Color(0.48f, 0.86f, 1f);
            attributeText.gameObject.SetActive(false);
        }
        EnsureSelectionButton();
    }

    public void SetCardSprite(Sprite sprite)
    {
        if (artImage != null)
        {
            artImage.sprite = sprite;
            artImage.enabled = sprite != null;
            artImage.preserveAspect = true;
        }
    }

    public void SetAttributeSprite(Sprite sprite)
    {
        if (attributeIconImage != null)
        {
            attributeIconImage.sprite = sprite;
            attributeIconImage.enabled = sprite != null;
            attributeIconImage.preserveAspect = true;
        }
    }

    public void SetHp(int currentHp, int maxHp)
    {
        int safeMax = Mathf.Max(1, maxHp);
        int safeCurrent = Mathf.Clamp(currentHp, 0, safeMax);
        CurrentHp = safeCurrent; MaxHp = safeMax;
        SetText(hpText, $"{safeCurrent} / {safeMax}");
        ResolveRuntimeReferences();
        if (hpSlider != null)
        {
            hpSlider.minValue = 0;
            hpSlider.maxValue = safeMax;
            hpSlider.value = safeCurrent;
        }
        if (hpFillImage != null)
        {
            hpFillImage.fillAmount = safeCurrent / (float)safeMax;
        }
    }

    public void SetSelectionHandler(Action<ProductBattleUnitCardView> handler)
    {
        selectionHandler = handler;
        EnsureSelectionButton();
    }

    public void SetPreparedData(ThoughtMapBattlePreparedUnitData prepared, IReadOnlyList<GeneratedSkillDto> skills)
    {
        if (prepared != null)
        {
            PhysicalAttack = prepared.physicalAttack; SkillAttack = prepared.skillAttack;
            PhysicalDefense = prepared.physicalDefense; SkillDefense = prepared.skillDefense; Speed = prepared.speed;
            SetHp(prepared.maxHp, prepared.maxHp);
        }
        EquippedSkill = skills != null && skills.Count > 0 ? skills[0] : null;
    }

    public void SetRuntimeUnit(ThoughtMapBattleUnit unit)
    {
        if (unit == null) return;
        CurrentHp = unit.hp; MaxHp = unit.maxHp; CurrentSp = unit.sp;
        PhysicalAttack = unit.physicalAttack; SkillAttack = unit.skillAttack;
        PhysicalDefense = unit.physicalDefense; SkillDefense = unit.skillDefense; Speed = unit.speed;
        EquippedSkill = unit.assignedGeneratedSkills.Count > 0 ? unit.assignedGeneratedSkills[0] : EquippedSkill;
    }

    private void EnsureSelectionButton()
    {
        Button button = GetComponent<Button>() ?? gameObject.AddComponent<Button>();
        button.targetGraphic = frameImage != null ? frameImage : GetComponent<Image>();
        button.onClick.RemoveListener(HandleSelected);
        button.onClick.AddListener(HandleSelected);
    }

    private void HandleSelected() => selectionHandler?.Invoke(this);

    public IEnumerator PlayAttackAnimation(ProductBattleUnitCardView target, float duration, float distance = 26f)
    {
        if (cachedRectTransform == null)
        {
            cachedRectTransform = transform as RectTransform;
        }
        if (cachedRectTransform == null)
        {
            yield break;
        }

        Vector2 origin = cachedRectTransform.anchoredPosition;
        Vector3 worldDirection = target == null ? Vector3.right : target.transform.position - transform.position;
        Vector2 direction = new Vector2(worldDirection.x, worldDirection.y).normalized;
        if (direction.sqrMagnitude < 0.01f)
        {
            direction = Vector2.right;
        }
        Vector2 attackPosition = origin + direction * distance;
        float halfDuration = Mathf.Max(0.01f, duration * 0.5f);
        yield return MoveRect(origin, attackPosition, halfDuration);
        yield return MoveRect(attackPosition, origin, halfDuration);
        cachedRectTransform.anchoredPosition = origin;
    }

    public IEnumerator UpdateHpAnimated(int currentHp, int maxHp, float duration)
    {
        int safeMax = Mathf.Max(1, maxHp);
        int safeCurrent = Mathf.Clamp(currentHp, 0, safeMax);
        float startValue = hpSlider == null ? safeCurrent : hpSlider.value;
        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float t = duration <= 0f ? 1f : Mathf.Clamp01(elapsed / duration);
            int displayedHp = Mathf.RoundToInt(Mathf.Lerp(startValue, safeCurrent, t));
            SetText(hpText, $"{displayedHp} / {safeMax}");
            if (hpSlider != null)
            {
                hpSlider.minValue = 0f;
                hpSlider.maxValue = safeMax;
                hpSlider.value = Mathf.Lerp(startValue, safeCurrent, t);
            }
            if (hpFillImage != null)
            {
                hpFillImage.fillAmount = Mathf.Lerp(startValue / safeMax, safeCurrent / (float)safeMax, t);
            }
            yield return null;
        }
        SetHp(safeCurrent, safeMax);
    }

    public void ShowDamage(string value, float duration = 1f)
    {
        StartCoroutine(ShowDamageRoutine(value, duration));
    }

    public void PlaySkillAnimation(string skillName)
    {
        StartCoroutine(PlaySkillRoutine(skillName));
    }

    public void ShowSkill(string skillName)
    {
        StartCoroutine(ShowDamageRoutine($"Skill\n{skillName}\nActivated", 1.2f, new Color(1f, 0.82f, 0.2f)));
    }

    public void SetDead(bool dead)
    {
        ResolveRuntimeReferences();
        canvasGroup.alpha = dead ? 0.5f : 1f;
        canvasGroup.interactable = !dead;
        if (artImage != null)
        {
            artImage.color = dead ? new Color(0.35f, 0.35f, 0.35f, 1f) : Color.white;
        }
        if (frameImage != null && dead)
        {
            frameImage.color = Color.Lerp(baseFrameColor, Color.black, 0.65f);
        }
    }

    public void SetTargetHighlight(bool highlighted)
    {
        if (frameImage != null)
        {
            frameImage.color = highlighted ? new Color(1f, 0.08f, 0.05f, 1f) : baseFrameColor;
        }
    }

    private IEnumerator MoveRect(Vector2 from, Vector2 to, float duration)
    {
        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            cachedRectTransform.anchoredPosition = Vector2.Lerp(from, to, Mathf.Clamp01(elapsed / duration));
            yield return null;
        }
        cachedRectTransform.anchoredPosition = to;
    }

    private IEnumerator ShowDamageRoutine(string value, float duration)
    {
        yield return ShowDamageRoutine(value, duration, new Color(1f, 0.25f, 0.18f, 1f));
    }

    private IEnumerator ShowDamageRoutine(string value, float duration, Color popupColor)
    {
        if (hpText == null)
        {
            yield break;
        }

        TMP_Text popup = Instantiate(hpText, transform);
        popup.name = "BattleDamageText";
        popup.text = value;
        popup.fontSize = Mathf.Max(hpText.fontSize * 1.65f, 24f);
        popup.color = popupColor;
        popup.alignment = TextAlignmentOptions.Center;
        popup.raycastTarget = false;
        RectTransform rect = popup.rectTransform;
        rect.anchorMin = rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        popupSequence++;
        float randomX = UnityEngine.Random.Range(-28f, 28f);
        float randomY = UnityEngine.Random.Range(-8f, 14f) + (popupSequence % 3) * 12f;
        Vector2 origin = new Vector2(randomX, randomY);
        rect.anchoredPosition = origin;
        rect.sizeDelta = new Vector2(180f, 60f);

        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float t = Mathf.Clamp01(elapsed / Mathf.Max(0.01f, duration));
            rect.anchoredPosition = origin + Vector2.up * Mathf.Lerp(0f, 58f, t);
            Color color = popup.color;
            color.a = 1f - t;
            popup.color = color;
            yield return null;
        }
        Destroy(popup.gameObject);
    }

    private IEnumerator PlaySkillRoutine(string skillName)
    {
        ShowSkill(skillName);
        if (frameImage == null)
        {
            yield break;
        }
        Color original = frameImage.color;
        float duration = 0.45f;
        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            float pulse = Mathf.Sin(Mathf.Clamp01(elapsed / duration) * Mathf.PI);
            frameImage.color = Color.Lerp(original, new Color(1f, 0.82f, 0.18f, 1f), pulse);
            yield return null;
        }
        frameImage.color = original;
    }

    private void ResolveRuntimeReferences()
    {
        if (hpFillImage == null && hpSlider != null && hpSlider.fillRect != null)
        {
            hpFillImage = hpSlider.fillRect.GetComponent<Image>();
            if (hpFillImage != null)
            {
                hpFillImage.type = Image.Type.Filled;
                hpFillImage.fillMethod = Image.FillMethod.Horizontal;
                hpFillImage.fillOrigin = 0;
            }
        }
        if (hpFillImage == null)
        {
            Transform existing = transform.Find("HpBarBackground/HpBarFill");
            if (existing == null)
            {
                GameObject backgroundObject = new GameObject("HpBarBackground", typeof(RectTransform), typeof(Image));
                backgroundObject.transform.SetParent(transform, false);
                RectTransform backgroundRect = (RectTransform)backgroundObject.transform;
                backgroundRect.anchorMin = new Vector2(0.08f, 0f);
                backgroundRect.anchorMax = new Vector2(0.92f, 0f);
                backgroundRect.pivot = new Vector2(0.5f, 0f);
                backgroundRect.anchoredPosition = new Vector2(0f, 34f);
                backgroundRect.sizeDelta = new Vector2(0f, 12f);
                Image background = backgroundObject.GetComponent<Image>();
                background.color = new Color(0.05f, 0.06f, 0.08f, 0.9f);
                background.raycastTarget = false;

                GameObject fillObject = new GameObject("HpBarFill", typeof(RectTransform), typeof(Image));
                fillObject.transform.SetParent(backgroundObject.transform, false);
                RectTransform fillRect = (RectTransform)fillObject.transform;
                fillRect.anchorMin = Vector2.zero;
                fillRect.anchorMax = Vector2.one;
                fillRect.offsetMin = new Vector2(2f, 2f);
                fillRect.offsetMax = new Vector2(-2f, -2f);
                existing = fillObject.transform;
            }
            hpFillImage = existing.GetComponent<Image>();
            hpFillImage.color = new Color(0.2f, 0.9f, 0.35f, 1f);
            hpFillImage.type = Image.Type.Filled;
            hpFillImage.fillMethod = Image.FillMethod.Horizontal;
            hpFillImage.fillOrigin = 0;
            hpFillImage.raycastTarget = false;
        }
        if (canvasGroup == null)
        {
            canvasGroup = GetComponent<CanvasGroup>();
            if (canvasGroup == null)
            {
                canvasGroup = gameObject.AddComponent<CanvasGroup>();
            }
        }
    }

    private void SetText(TMP_Text text, string value)
    {
        if (text != null)
        {
            text.text = value;
        }
    }
}
