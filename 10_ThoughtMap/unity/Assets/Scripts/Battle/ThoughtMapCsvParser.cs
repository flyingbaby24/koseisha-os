using System.Collections.Generic;
using System.Text;

public static class ThoughtMapCsvParser
{
    public static List<Dictionary<string, string>> Parse(string csvText)
    {
        List<List<string>> rows = ParseRows(csvText);
        List<Dictionary<string, string>> output = new List<Dictionary<string, string>>();
        if (rows.Count == 0)
        {
            return output;
        }

        List<string> headers = rows[0];
        for (int rowIndex = 1; rowIndex < rows.Count; rowIndex++)
        {
            List<string> row = rows[rowIndex];
            if (row.Count == 0)
            {
                continue;
            }

            Dictionary<string, string> item = new Dictionary<string, string>();
            for (int i = 0; i < headers.Count; i++)
            {
                string key = headers[i].Trim();
                string value = i < row.Count ? row[i] : "";
                item[key] = value;
            }
            output.Add(item);
        }

        return output;
    }

    private static List<List<string>> ParseRows(string text)
    {
        List<List<string>> rows = new List<List<string>>();
        if (string.IsNullOrEmpty(text))
        {
            return rows;
        }

        List<string> row = new List<string>();
        StringBuilder cell = new StringBuilder();
        bool inQuotes = false;

        for (int i = 0; i < text.Length; i++)
        {
            char c = text[i];
            if (c == '"')
            {
                if (inQuotes && i + 1 < text.Length && text[i + 1] == '"')
                {
                    cell.Append('"');
                    i++;
                }
                else
                {
                    inQuotes = !inQuotes;
                }
            }
            else if (c == ',' && !inQuotes)
            {
                row.Add(cell.ToString());
                cell.Length = 0;
            }
            else if ((c == '\n' || c == '\r') && !inQuotes)
            {
                if (c == '\r' && i + 1 < text.Length && text[i + 1] == '\n')
                {
                    i++;
                }
                row.Add(cell.ToString());
                cell.Length = 0;
                if (!IsEmptyRow(row))
                {
                    rows.Add(row);
                }
                row = new List<string>();
            }
            else
            {
                cell.Append(c);
            }
        }

        row.Add(cell.ToString());
        if (!IsEmptyRow(row))
        {
            rows.Add(row);
        }

        return rows;
    }

    private static bool IsEmptyRow(List<string> row)
    {
        foreach (string value in row)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                return false;
            }
        }
        return true;
    }
}
