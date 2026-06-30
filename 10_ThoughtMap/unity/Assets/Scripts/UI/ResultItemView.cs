using TMPro;
using UnityEngine;

public class ResultItemView : MonoBehaviour
{
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private TMP_Text authorText;

    public void Bind(ThoughtMapSearchResult result)
    {
        titleText.text = string.IsNullOrWhiteSpace(result.title) ? "Untitled" : result.title;
        authorText.text = string.IsNullOrWhiteSpace(result.author) ? "Unknown" : result.author;
    }
}
