import type {
  HouseholdData,
  HouseholdField,
  Households,
  Region,
  Statistics,
} from "./types";

/** Household counts compared with the 1,896-unit simple mean, like child counts. */
const COUNT_FIELDS: HouseholdField[] = [
  "single",
  "coupleChildren",
  "under18",
  "elderlyOnly",
  "elderlySingle",
  "unmarried",
  "unmarriedMale",
  "unmarriedFemale",
];

/** Attach the household layer to every region by its 5-digit code (no row is added or merged). */
export function joinHouseholds(
  data: Statistics,
  households: HouseholdData,
): Statistics {
  const decode = (code: string): Households | null => {
    const row = households.regions[code];
    if (!row) return null;
    return Object.fromEntries(
      households.fields.map((field, i) => [field, row[i]]),
    ) as Households;
  };
  const attach = (region: Region): Region => ({
    ...region,
    households: decode(region.code),
  });
  return {
    ...data,
    national: attach(data.national),
    prefectures: data.prefectures.map(attach),
    cities: data.cities.map(attach),
    municipalities: data.municipalities.map(attach),
  };
}

/** Shares keep the national aggregate; counts become the reference mean (自治体平均〈参考〉). */
export function householdReference(data: Statistics): Households | null {
  const national = data.national.households;
  if (!national) return null;
  const units = data.municipalities.length;
  const reference = { ...national };
  for (const field of COUNT_FIELDS) {
    const value = national[field];
    reference[field] = value === null ? null : value / units;
  }
  return reference;
}

/** 65歳以上世帯員の「いる」世帯の割合（一般世帯総数が分母）: shown only as a reference next to 「のみ」. */
export function withElderlyShare(households: Households | null | undefined) {
  if (!households?.general || households.withElderly === null) return null;
  return (households.withElderly / households.general) * 100;
}
