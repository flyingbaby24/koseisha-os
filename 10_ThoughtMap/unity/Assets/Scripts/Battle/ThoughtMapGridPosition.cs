using System;
using UnityEngine;

[Serializable]
public struct ThoughtMapGridPosition
{
    [Range(0, 4)] public int x;
    [Range(0, 4)] public int y;

    public ThoughtMapGridPosition(int x, int y)
    {
        this.x = Mathf.Clamp(x, 0, 4);
        this.y = Mathf.Clamp(y, 0, 4);
    }

    public int ManhattanDistance(ThoughtMapGridPosition other)
    {
        return Mathf.Abs(x - other.x) + Mathf.Abs(y - other.y);
    }

    public override string ToString()
    {
        return $"({x},{y})";
    }
}
