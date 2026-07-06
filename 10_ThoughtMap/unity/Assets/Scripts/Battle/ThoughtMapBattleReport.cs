using System.Collections.Generic;

public class ThoughtMapBattleReport
{
    public readonly List<string> logLines = new List<string>();
    public string winner = "Draw";
    public int rounds;

    public string ToMultilineLog()
    {
        return string.Join("\n", logLines);
    }
}
