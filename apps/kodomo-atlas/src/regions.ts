import type { Region, Statistics } from "./types";

/** Map/search index only. City aggregates never enter statistical-unit totals. */
export function regionIndex(data: Statistics): Map<string, Region> {
  const index = new Map(
    data.municipalities.map((region) => [region.code, region]),
  );
  const parents = [...data.cities].sort((a, b) => b.code.localeCompare(a.code));
  const members = new Map<string, Region[]>();
  for (const ward of data.municipalities.filter(
    (region) => region.level === "0",
  )) {
    // In the frozen 2020 code hierarchy, ward codes follow their city's code.
    // Descending parent order distinguishes Osaka/Sakai and Yokohama/Kawasaki/Sagamihara.
    const parent = parents.find(
      (city) =>
        city.code.slice(0, 3) === ward.code.slice(0, 3) &&
        city.code < ward.code,
    );
    if (!parent) continue;
    const list = members.get(parent.code) ?? [];
    list.push(ward);
    members.set(parent.code, list);
  }
  for (const city of data.cities) {
    const wards = members.get(city.code) ?? [];
    const boxes = wards.flatMap((ward) => (ward.bounds ? [ward.bounds] : []));
    if (!boxes.length) {
      index.set(city.code, city);
      continue;
    }
    const south = Math.min(...boxes.map((box) => box[0][0]));
    const west = Math.min(...boxes.map((box) => box[0][1]));
    const north = Math.max(...boxes.map((box) => box[1][0]));
    const east = Math.max(...boxes.map((box) => box[1][1]));
    index.set(city.code, {
      ...city,
      memberCodes: wards.map((ward) => ward.code),
      bounds: [
        [south, west],
        [north, east],
      ],
      center: [(south + north) / 2, (west + east) / 2],
    });
  }
  return index;
}

export function unitCounts(data: Statistics) {
  return {
    cities: data.municipalities.filter((region) => region.level === "2").length,
    towns: data.municipalities.filter(
      (region) => region.level === "3" && region.name.endsWith("町"),
    ).length,
    villages: data.municipalities.filter(
      (region) => region.level === "3" && region.name.endsWith("村"),
    ).length,
    specialWards: data.municipalities.filter(
      (region) => region.level === "0" && region.prefCode === "13",
    ).length,
    cityWards: data.municipalities.filter(
      (region) => region.level === "0" && region.prefCode !== "13",
    ).length,
  };
}

/** Published national rates; count means are a separately labelled reference. */
export function comparisonReference(data: Statistics): Region {
  const count = data.municipalities.length;
  return {
    ...data.national,
    children:
      data.national.children === null ? null : data.national.children / count,
    ages: data.national.ages.map((value) =>
      value === null ? null : value / count,
    ) as Region["ages"],
  };
}
