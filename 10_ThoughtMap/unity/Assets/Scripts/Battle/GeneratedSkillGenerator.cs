using System.Collections.Generic;
using System.Linq;

public static class GeneratedSkillGenerator
{
    private static readonly string[] Triggers =
    {
        "battle_start", "turn_start", "on_attack", "on_damage_taken", "manual"
    };

    public static List<GeneratedSkillDto> GenerateForBattlePrep(
        IReadOnlyList<ThoughtMapBattleCardData> deckCards,
        IDictionary<int, ThoughtMapBattleCardData> placement,
        int maxPerCard = 1)
    {
        List<GeneratedSkillDto> skills = new List<GeneratedSkillDto>();
        if (deckCards == null || deckCards.Count == 0)
        {
            return skills;
        }

        HashSet<string> placedIds = new HashSet<string>();
        if (placement != null)
        {
            foreach (ThoughtMapBattleCardData card in placement.Values)
            {
                string placedId = GetStableCardId(card);
                if (!string.IsNullOrWhiteSpace(placedId))
                {
                    placedIds.Add(placedId);
                }
            }
        }

        for (int i = 0; i < deckCards.Count; i++)
        {
            ThoughtMapBattleCardData card = deckCards[i];
            if (card == null || string.IsNullOrWhiteSpace(card.docId))
            {
                continue;
            }

            string cardId = GetStableCardId(card);
            string thought = string.IsNullOrWhiteSpace(card.primaryAttribute) ? "thought" : card.primaryAttribute;
            string trigger = Triggers[StableIndex(card.docId, Triggers.Length)];
            bool placed = placedIds.Contains(cardId);
            int baseValue = 8 + StableIndex(cardId + ":value", 8);

            GeneratedSkillDto skill = new GeneratedSkillDto
            {
                skill_id = $"battle_prep_{Sanitize(card.docId)}_{i:00}",
                doc_id = card.docId,
                name_en = BuildSkillName(thought, placed),
                trigger = trigger,
                cooldown = placed ? 1 : 2,
                generation_version = 1,
                description_en = placed
                    ? $"Battle Prep generated skill for {card.cardName}. Uses formation-ready {thought} pressure."
                    : $"Battle Prep generated skill for {card.cardName}. Assign before deployment."
            };
            skill.concepts.Add(new GeneratedSkillConceptDto
            {
                label_en = thought,
                category = "battle_prep",
                similarity = 1f,
                rank = 1
            });
            skill.effects.Add(new GeneratedSkillEffectDto
            {
                effect_order = 1,
                effect_type = placed ? "increase" : "shield",
                target = placed ? "self" : "single_ally",
                parameter = placed ? thought : "hp",
                operation = "add",
                value = baseValue,
                value_type = "flat",
                duration = placed ? 2 : 1,
                probability = 1f
            });
            skill.cost = new GeneratedSkillCostDto
            {
                sp = placed ? 10 : 15,
                hp_percent = 0f,
                consume_action = false
            };
            skills.Add(skill);

            if (maxPerCard <= 1)
            {
                continue;
            }
        }

        return skills
            .Where(skill => skill != null && !string.IsNullOrWhiteSpace(skill.skill_id))
            .ToList();
    }

    private static string BuildSkillName(string thought, bool placed)
    {
        string label = string.IsNullOrWhiteSpace(thought) ? "Thought" : char.ToUpperInvariant(thought[0]) + thought.Substring(1);
        return placed ? $"{label} Formation" : $"{label} Guard";
    }

    private static string GetStableCardId(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return "";
        }
        if (!string.IsNullOrWhiteSpace(card.cardId))
        {
            return card.cardId.Trim();
        }
        if (!string.IsNullOrWhiteSpace(card.docId))
        {
            return card.docId.Trim();
        }
        if (!string.IsNullOrWhiteSpace(card.sourceDocId))
        {
            return card.sourceDocId.Trim();
        }
        return string.IsNullOrWhiteSpace(card.cardName) ? "" : $"runtime:{Sanitize(card.cardName)}";
    }

    private static int StableIndex(string value, int modulo)
    {
        if (modulo <= 0)
        {
            return 0;
        }

        unchecked
        {
            int hash = 17;
            string text = value ?? "";
            for (int i = 0; i < text.Length; i++)
            {
                hash = (hash * 31) + text[i];
            }
            return System.Math.Abs(hash == int.MinValue ? int.MaxValue : hash) % modulo;
        }
    }

    private static string Sanitize(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "unknown";
        }

        char[] chars = value.ToCharArray();
        for (int i = 0; i < chars.Length; i++)
        {
            if (!char.IsLetterOrDigit(chars[i]))
            {
                chars[i] = '_';
            }
        }
        return new string(chars);
    }
}
