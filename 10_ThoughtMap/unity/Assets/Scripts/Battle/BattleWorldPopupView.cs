using System.Collections;
using TMPro;
using UnityEngine;

/// <summary>Projects a PresentationAnchor world position into the overlay canvas.</summary>
public sealed class BattleWorldPopupView : MonoBehaviour
{
    private TMP_Text template;
    private RectTransform canvasRoot;
    private Camera worldCamera;

    public void Initialize(TMP_Text sourceTemplate)
    {
        template=sourceTemplate;worldCamera=Camera.main;
        Canvas canvas=sourceTemplate==null?null:sourceTemplate.GetComponentInParent<Canvas>();
        canvasRoot=canvas==null?null:canvas.transform as RectTransform;
    }

    public void Show(Transform anchor,string value,Color color,float duration=1f)
    {
        if(anchor==null||template==null||canvasRoot==null)return;
        StartCoroutine(ShowRoutine(anchor,value,color,duration));
    }

    private IEnumerator ShowRoutine(Transform anchor,string value,Color color,float duration)
    {
        TMP_Text popup=Instantiate(template,canvasRoot);popup.name="BattleWorldDamageText";popup.text=value;popup.fontSize=Mathf.Max(template.fontSize*1.35f,28f);popup.color=color;popup.alignment=TextAlignmentOptions.Center;popup.raycastTarget=false;
        RectTransform rect=popup.rectTransform;rect.anchorMin=rect.anchorMax=Vector2.zero;rect.pivot=new Vector2(.5f,.5f);rect.sizeDelta=new Vector2(190f,70f);
        Vector2 randomOffset=new Vector2(Random.Range(-22f,22f),Random.Range(4f,18f));float elapsed=0f;
        while(elapsed<duration&&anchor!=null){elapsed+=Time.unscaledDeltaTime;float t=Mathf.Clamp01(elapsed/Mathf.Max(.01f,duration));Vector3 screen=(worldCamera==null?Camera.main:worldCamera).WorldToScreenPoint(anchor.position);rect.position=screen+(Vector3)(randomOffset+Vector2.up*Mathf.Lerp(0f,58f,t));Color c=color;c.a=1f-t;popup.color=c;yield return null;}
        if(popup!=null)Destroy(popup.gameObject);
    }
}
