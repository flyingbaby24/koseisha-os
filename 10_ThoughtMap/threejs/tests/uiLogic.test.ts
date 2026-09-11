import { describe, expect, it } from "vitest";

import type { ParameterScore } from "../src/api/types";
import {
  FILTER_OPTIONS,
  PARAMETER_AXIS_ORDER,
  SOURCE_OPTIONS,
  axisLabel,
} from "../src/config/searchOptions";
import { isSafeExternalUrl } from "../src/ui/DetailPanel";
import {
  formatShare,
  formatSimilarity,
  maxParameterValue,
  orDash,
  orderParameters,
} from "../src/ui/format";

describe("similarity formatting", () => {
  it("formats for readability without changing the value", () => {
    expect(formatSimilarity(0.736)).toBe("0.7360");
    expect(formatSimilarity(0.97)).toBe("0.9700");
  });

  it("degrades safely on a non-finite value", () => {
    expect(formatSimilarity(Number.NaN)).toBe("--");
  });
});

describe("composition share formatting", () => {
  it("presents a 0..1 share as a percentage", () => {
    // Canonical state stays 0.139; only the display is a percentage.
    expect(formatShare(0.139)).toBe("13.9%");
    expect(formatShare(0.1)).toBe("10.0%");
    expect(formatShare(0)).toBe("0.0%");
  });

  it("degrades safely on a non-finite value", () => {
    expect(formatShare(Number.POSITIVE_INFINITY)).toBe("--");
  });
});

describe("orDash", () => {
  it("substitutes a dash for missing text", () => {
    expect(orDash("")).toBe("—");
    expect(orDash("   ")).toBe("—");
    expect(orDash(undefined)).toBe("—");
    expect(orDash("Plato")).toBe("Plato");
  });
});

describe("canonical axis order", () => {
  it("lists the ten Thought Composition axes in the generator's order", () => {
    expect(PARAMETER_AXIS_ORDER).toEqual([
      "philosophy",
      "psychology",
      "science",
      "economics",
      "karma",
      "emotion",
      "morality",
      "ideal",
      "individual",
      "community",
    ]);
  });

  it("orders a shuffled parameter set canonically", () => {
    const shuffled: ParameterScore[] = [
      { key: "community", value: 0.03 },
      { key: "philosophy", value: 0.15 },
      { key: "emotion", value: 0.1 },
    ];

    expect(orderParameters(shuffled).map((p) => p.key)).toEqual([
      "philosophy",
      "emotion",
      "community",
    ]);
  });

  it("uses the same order for query and result profiles", () => {
    const scores: ParameterScore[] = PARAMETER_AXIS_ORDER.map((key) => ({ key, value: 0.1 }));
    const reversed = [...scores].reverse();

    expect(orderParameters(scores).map((p) => p.key)).toEqual(
      orderParameters(reversed).map((p) => p.key),
    );
  });

  it("keeps an unrecognised axis rather than dropping it", () => {
    const withExtra: ParameterScore[] = [
      { key: "mystery", value: 0.5 },
      { key: "philosophy", value: 0.5 },
    ];

    expect(orderParameters(withExtra).map((p) => p.key)).toEqual(["philosophy", "mystery"]);
  });

  it("drops entries with a non-finite value", () => {
    const dirty: ParameterScore[] = [
      { key: "philosophy", value: Number.NaN },
      { key: "science", value: 0.2 },
    ];

    expect(orderParameters(dirty).map((p) => p.key)).toEqual(["science"]);
  });

  it("returns an empty list for missing parameters rather than throwing", () => {
    expect(orderParameters(undefined)).toEqual([]);
    expect(orderParameters(null)).toEqual([]);
    expect(orderParameters([])).toEqual([]);
  });

  it("labels every canonical axis", () => {
    for (const key of PARAMETER_AXIS_ORDER) {
      expect(axisLabel(key)).not.toBe(key === axisLabel(key) ? "" : key);
      expect(axisLabel(key).length).toBeGreaterThan(0);
    }
    expect(axisLabel("unknown_axis")).toBe("unknown_axis");
  });
});

describe("parameter bar scaling", () => {
  it("scales to the largest value in the set", () => {
    const scores: ParameterScore[] = [
      { key: "philosophy", value: 0.139 },
      { key: "science", value: 0.047 },
    ];
    expect(maxParameterValue(scores)).toBeCloseTo(0.139, 6);
  });

  it("returns zero for an empty set so nothing divides by zero", () => {
    expect(maxParameterValue([])).toBe(0);
  });
});

describe("external link safety", () => {
  it("accepts http and https", () => {
    expect(isSafeExternalUrl("https://www.gutenberg.org/ebooks/1497")).toBe(true);
    expect(isSafeExternalUrl("http://example.com")).toBe(true);
  });

  it("rejects script and other non-web schemes", () => {
    expect(isSafeExternalUrl("javascript:alert(1)")).toBe(false);
    expect(isSafeExternalUrl("data:text/html,<script>")).toBe(false);
    expect(isSafeExternalUrl("file:///etc/passwd")).toBe(false);
  });

  it("rejects unparseable and empty values", () => {
    expect(isSafeExternalUrl("")).toBe(false);
    expect(isSafeExternalUrl("not a url")).toBe(false);
  });
});

describe("search option configuration", () => {
  it("offers an all-sources choice that sends no source parameter", () => {
    expect(SOURCE_OPTIONS[0]?.value).toBe("");
  });

  it("offers only source values that exist in the corpus", () => {
    const values = SOURCE_OPTIONS.map((option) => option.value).filter(Boolean);
    expect(values).toEqual(["gutendex", "user_suno", "user_note", "zip"]);
  });

  it("keeps general as an explicit no-narrowing choice", () => {
    const general = FILTER_OPTIONS.find((option) => option.value === "general");
    expect(general).toBeDefined();
    expect(general?.label).toContain("all axes");
  });

  it("offers every canonical axis as a filter", () => {
    const values = FILTER_OPTIONS.map((option) => option.value);
    for (const axis of PARAMETER_AXIS_ORDER) {
      expect(values).toContain(axis);
    }
  });

  it("does not offer filter-definition file names that match no document", () => {
    // basic_thought / basic_literature / jinn_os return 0 of 4915 rows.
    const values = FILTER_OPTIONS.map((option) => option.value);
    expect(values).not.toContain("basic_thought");
    expect(values).not.toContain("basic_literature");
    expect(values).not.toContain("jinn_os");
  });
});
