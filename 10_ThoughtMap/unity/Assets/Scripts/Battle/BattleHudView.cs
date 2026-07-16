using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class BattleHudView : MonoBehaviour
{
    [SerializeField] private TMP_Text roundText;
    [SerializeField] private TMP_Text turnText;
    [SerializeField] private TMP_Text battleSpeedText;
    [SerializeField] private Button pauseButton;

    public void SetState(int round, int turn, string speedLabel)
    {
        if (roundText != null)
        {
            roundText.text = $"Round {Mathf.Max(1, round)}";
        }

        if (turnText != null)
        {
            turnText.text = $"Turn {Mathf.Max(1, turn)}";
        }

        if (battleSpeedText != null)
        {
            battleSpeedText.text = string.IsNullOrWhiteSpace(speedLabel) ? "Speed x1" : speedLabel;
        }
    }

    private void Awake()
    {
        if (pauseButton != null)
        {
            pauseButton.onClick.RemoveListener(HandlePauseClicked);
            pauseButton.onClick.AddListener(HandlePauseClicked);
        }
    }

    private void HandlePauseClicked()
    {
        Debug.Log("[Battle] Pause button clicked. Battle logic is not connected yet.", this);
    }
}
