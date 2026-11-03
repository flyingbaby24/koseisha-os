// Focused regression checks for the comparison/legend changes; no browser automation.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import ts from "typescript";

const root = new URL("../", import.meta.url);
const statisticsBytes = await readFile(
  new URL("public/data/statistics.json", root),
);
const geometryBytes = await readFile(
  new URL("public/data/municipalities.geojson", root),
);
const data = JSON.parse(statisticsBytes);
const geography = JSON.parse(geometryBytes);
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");

async function sourceModule(path) {
  const source = await readFile(new URL(path, root), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  return import(
    `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
  );
}
const { regionIndex, unitCounts, comparisonReference } =
  await sourceModule("src/regions.ts");
const { colorOf, formatValue, metrics, MISSING_COLOR } =
  await sourceModule("src/metrics.ts");

assert.equal(
  digest(statisticsBytes),
  "44870cc74deeb73fe2e4a9050ab8fc2f6e75ed095302f80675554c597e04e7af",
);
assert.equal(
  digest(geometryBytes),
  "56730f5d6bccf875abf6618cc0791396b22a7224c2128a6995fa62af65f9c288",
);
console.log(
  "PASS: original statistics and nationwide boundaries unchanged (SHA-256)",
);

const index = regionIndex(data);
const expected = [
  ["27100", "大阪市", 1.16, 10.95042],
  ["27203", "豊中市", 1.5, 13.69162],
  ["28203", "明石市", 1.63, 13.79143],
];
for (const [code, name, tfr, share] of expected) {
  const region = index.get(code);
  assert.equal(region.name, name);
  assert.equal(region.tfr, tfr);
  assert.equal(region.childShare, share);
  assert(region.bounds && region.center);
}
assert.equal(index.get("27100").memberCodes.length, 24);
assert.deepEqual(unitCounts(data), {
  cities: 772,
  towns: 743,
  villages: 183,
  specialWards: 23,
  cityWards: 175,
});
assert.equal(data.municipalities.length, 1896);
assert.equal(
  data.municipalities.filter((region) => region.level === "1").length,
  0,
);
const allMembers = data.cities.flatMap(
  (city) => index.get(city.code).memberCodes,
);
assert.equal(allMembers.length, 198);
assert.equal(new Set(allMembers).size, 198);
const geometryByCode = new Map(
  geography.features.map((feature) => [
    feature.properties.code,
    feature.properties,
  ]),
);
for (const city of data.cities) {
  const mapped = index.get(city.code);
  const wards = mapped.memberCodes.map((code) => index.get(code));
  assert.equal(
    wards.reduce((sum, ward) => sum + ward.population, 0),
    city.population,
  );
  assert.equal(
    wards.reduce((sum, ward) => sum + ward.children, 0),
    city.children,
  );
  for (const ward of wards) {
    if (city.code !== "13100")
      assert.equal(geometryByCode.get(ward.code).city, city.name);
    assert(
      mapped.bounds[0][0] <= ward.bounds[0][0] &&
        mapped.bounds[1][0] >= ward.bounds[1][0],
    );
    assert(
      mapped.bounds[0][1] <= ward.bounds[0][1] &&
        mapped.bounds[1][1] >= ward.bounds[1][1],
    );
  }
}
console.log(
  "PASS: Osaka's 24 wards, Toyonaka, Akashi; 1,896 units; 21 aggregates excluded; no duplicate wards",
);

const reference = comparisonReference(data);
assert.equal(reference.tfr, 1.33);
assert.equal(reference.childShare, 12.13796);
assert(
  Math.abs(
    reference.childShare -
      (data.national.children /
        (data.national.population - data.national.unknownAge)) *
        100,
  ) < 0.00001,
);
for (const key of ["tfr", "childShare"]) {
  const valid = data.municipalities.filter((region) => region[key] !== null);
  const simpleMean =
    valid.reduce((sum, region) => sum + region[key], 0) / valid.length;
  assert.notEqual(reference[key], simpleMean);
}
console.log(
  "PASS: fertility/share use published national aggregates, not municipal arithmetic means",
);

assert.equal(formatValue(null, "tfr"), "—");
assert.equal(formatValue(0, "tfr"), "0.00");
assert.equal(colorOf(null, "tfr"), MISSING_COLOR);
assert.equal(colorOf(0, "tfr"), metrics.tfr.colors[0]);
assert.notEqual(colorOf(null, "tfr"), colorOf(0, "tfr"));
assert.equal(
  data.municipalities.filter((region) => region.tfr === null).length,
  9,
);
assert.equal(
  data.municipalities.filter((region) => region.tfr === 0).length,
  0,
);
assert.notDeepEqual(metrics.tfr.colors, metrics.childShare.colors);
const luminance = (hex) => {
  const channels = hex
    .slice(1)
    .match(/../g)
    .map((value) => {
      const s = parseInt(value, 16) / 255;
      return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
};
for (const key of ["tfr", "childShare"]) {
  const colors = metrics[key].colors;
  assert.equal(new Set(colors).size, 7);
  colors
    .slice(1)
    .forEach((color, i) => assert(luminance(color) < luminance(colors[i])));
}
console.log(
  "PASS: null vs zero; green/blue legends; seven ordered lightness steps (not visual browser QA)",
);
