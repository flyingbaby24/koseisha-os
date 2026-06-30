using UnityEngine;
using TMPro;

public class ThoughtMapDemoUI : MonoBehaviour
{
    public Transform content;
    public GameObject resultPrefab;
    public TMP_InputField searchInput;

    public void OnSearchClicked()
    {
        foreach (Transform child in content)
        {
            Destroy(child.gameObject);
        }

        string keyword = searchInput.text.ToLower();

        string[] results =
        {
            "Plato",
            "Nietzsche",
            "Charles Darwin",
            "Marcus Aurelius",
            "Jane Austen"
        };

        foreach (string name in results)
        {
            if (!string.IsNullOrEmpty(keyword) && !name.ToLower().Contains(keyword))
                continue;

            GameObject item = Instantiate(resultPrefab, content);
            TMP_Text text = item.GetComponent<TMP_Text>();

            if (text != null)
                text.text = name;
        }
    }
}