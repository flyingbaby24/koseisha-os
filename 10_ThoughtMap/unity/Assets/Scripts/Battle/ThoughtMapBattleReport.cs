using System.Collections.Generic;

public class ThoughtMapBattleReport
{
    public readonly List<string> logLines = new List<string>();
    public string winner = "Draw";
    public int rounds;
    public int playerDamageDone;
    public int enemyDamageDone;
    public int playerDamageTaken;
    public int enemyDamageTaken;
    public int playerCardsSurvived;
    public int enemyCardsSurvived;
    public int playerCardsLost;
    public int enemyCardsLost;

    public string ToMultilineLog()
    {
        return string.Join("\n", logLines);
    }

    public string ToSummaryText()
    {
        return
            "Battle Summary\n" +
            $"Player Damage Done: {playerDamageDone}\n" +
            $"Player Damage Taken: {playerDamageTaken}\n" +
            $"Player Cards Survived: {playerCardsSurvived}\n" +
            $"Player Cards Lost: {playerCardsLost}\n" +
            $"Enemy Damage Done: {enemyDamageDone}\n" +
            $"Enemy Damage Taken: {enemyDamageTaken}\n" +
            $"Enemy Cards Survived: {enemyCardsSurvived}\n" +
            $"Enemy Cards Lost: {enemyCardsLost}";
    }
}
