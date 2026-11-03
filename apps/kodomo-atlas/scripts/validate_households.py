"""Integrity checks for the household / marital-status layer (standard library only)."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ["general", "typeUnknown", "withElderly", "single", "coupleChildren", "under18",
          "elderlyOnly", "elderlySingle", "unmarried", "unmarriedMale", "unmarriedFemale",
          "unmarriedBase", "unmarriedBaseMale", "unmarriedBaseFemale"]
# share field -> (numerator, denominator rule)
SHARES = {
    "singleShare": ("single", "typed"),
    "coupleChildrenShare": ("coupleChildren", "typed"),
    "elderlySingleShare": ("elderlySingle", "typed"),
    "under18Share": ("under18", "general"),
    "elderlyOnlyShare": ("elderlyOnly", "general"),
    "unmarriedRate": ("unmarried", "unmarriedBase"),
    "unmarriedRateMale": ("unmarriedMale", "unmarriedBaseMale"),
    "unmarriedRateFemale": ("unmarriedFemale", "unmarriedBaseFemale"),
}


def main():
    stats = json.loads((ROOT / "public/data/statistics.json").read_text(encoding="utf-8"))
    data = json.loads((ROOT / "public/data/households.json").read_text(encoding="utf-8"))
    fields = data["fields"]
    assert sorted(fields) == sorted(COUNTS + list(SHARES)), "Unexpected field list"
    rec = {code: dict(zip(fields, values)) for code, values in data["regions"].items()}
    units = stats["municipalities"]
    expected = {r["code"] for g in ("municipalities", "cities", "prefectures") for r in stats[g]} | {"00000"}
    assert set(rec) == expected and len(units) == 1896 and len(rec) == 1965
    print("PASS: 1,965 regions (national, 47 prefectures, 21 city aggregates, 1,896 units) joined by 5-digit code")

    for code, r in rec.items():
        for key in COUNTS:
            assert isinstance(r[key], int) and r[key] >= 0, (code, key)
        typed = r["general"] - r["typeUnknown"]
        for key, (part, rule) in SHARES.items():
            whole = typed if rule == "typed" else r[rule]
            if whole == 0:
                assert r[key] is None, f"{code} {key}: zero denominator must stay null, never 0"
            else:
                assert r[key] is not None and abs(r[part] / whole * 100 - r[key]) < 0.00001, (code, key)
                assert 0 <= r[key] <= 100
        assert r["elderlySingle"] <= r["single"] <= r["general"], code
        assert r["elderlySingle"] <= r["elderlyOnly"] <= r["withElderly"] <= r["general"], code
        assert r["under18"] <= r["general"] and r["coupleChildren"] <= typed, code
        assert r["unmarriedMale"] + r["unmarriedFemale"] == r["unmarried"] <= r["unmarriedBase"], code
        assert r["unmarriedBaseMale"] + r["unmarriedBaseFemale"] == r["unmarriedBase"], code
    print("PASS: shares recomputed from counts with the stated denominators; zero denominators are null")
    print("PASS: 65+ single ⊂ single households; 65+ single ⊂ 65+-only ⊂ households with a 65+ member")

    national = rec["00000"]
    for key in COUNTS:
        assert sum(rec[u["code"]][key] for u in units) == national[key], f"Units do not sum to national: {key}"
        for pref in stats["prefectures"]:
            assert sum(rec[u["code"]][key] for u in units if u["prefCode"] == pref["prefCode"]) == rec[pref["code"]][key], (pref["code"], key)
    parents = sorted(stats["cities"], key=lambda c: c["code"], reverse=True)
    members = {}
    for ward in (u for u in units if u["level"] == "0"):
        parent = next(c for c in parents if c["code"][:3] == ward["code"][:3] and c["code"] < ward["code"])
        members.setdefault(parent["code"], []).append(ward["code"])
    assert sum(len(v) for v in members.values()) == 198 and len(members) == 21
    for city, wards in members.items():
        for key in COUNTS:
            assert sum(rec[w][key] for w in wards) == rec[city][key], (city, key)
    print("PASS: 1,896 units sum to the national and 47 prefectural totals; 21 city aggregates equal their 198 wards (no double counting)")

    # Official published figures (令和2年国勢調査 人口等基本集計 結果の概要).
    assert national["general"] == 55704949 and national["single"] == 21151042
    assert national["withElderly"] == 22655031 and national["elderlyOnly"] == 13073898
    assert national["elderlySingle"] == 6716806 and national["under18"] == 10733725
    assert national["coupleChildren"] == 13949190 and national["typeUnknown"] == 160120
    assert national["unmarried"] == 3730227 + 2510676 + 2020933
    assert round(national["singleShare"], 1) == 38.1, "単独世帯の割合 (official 38.1%)"
    assert round(national["coupleChildrenShare"], 1) == 25.1, "夫婦と子供から成る世帯 (official 25.1%)"
    assert round(national["withElderly"] / national["general"] * 100, 1) == 40.7, "65歳以上世帯員のいる世帯 (official 40.7%)"
    assert national["elderlyOnly"] < national["withElderly"], "高齢者のみ ≠ 高齢者のいる世帯"
    print("PASS: national counts and official shares (単独世帯 38.1%, 夫婦と子供 25.1%, 65歳以上世帯員のいる 40.7%) reproduced")

    meta = data["metadata"]
    assert meta["checks"]["published4_4Compared"] > 15000 and meta["checks"]["published4_4MaxDiff"] < 0.000051
    missing = {k: sum(rec[u["code"]][k] is None for u in units) for k in fields}
    assert missing == meta["missingByField"]
    null_units = {u["code"] for u in units for k in SHARES if rec[u["code"]][k] is None}
    assert null_units == {"07546"}, null_units  # 双葉町: 2020 population 0
    assert len(meta["sources"]) == 4
    for source in meta["sources"]:
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) and source["bytes"] > 1_000_000
        assert source["url"].startswith("https://www.e-stat.go.jp/stat-search/file-download?statInfId=")
    print(f"PASS: never-married shares match 第4-4表 ({meta['checks']['published4_4Compared']:,} published values); "
          "only 双葉町 (population 0) is null; four official sources with SHA-256")


if __name__ == "__main__":
    main()
