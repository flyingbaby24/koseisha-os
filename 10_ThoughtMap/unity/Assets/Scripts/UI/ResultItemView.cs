using TMPro;
using UnityEngine;

public class ResultItemView : MonoBehaviour
{
    [SerializeField] private TMP_Text text;

    public void Bind(ThoughtMapSearchResult result)
    {
        text.text = $"{result.title}\n<color=#AAAAAA>{result.author}</color>";
    }
}