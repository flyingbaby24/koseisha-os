"""Build the household-structure / marital-status layer from the official 2020 Census tables.

Usage: python -m pip install -r scripts/requirements.txt
       python scripts/prepare_households.py [--refresh]

Reads only official Excel files from e-Stat (令和2年国勢調査 人口等基本集計) and writes
public/data/households.json. The existing statistics.json / boundaries are not touched.
Columns are located by their published labels, never by position. "-" (該当数値なし) is 0;
any other non-numeric cell aborts the build instead of being guessed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import openpyxl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "public" / "data"
E_STAT = "https://www.e-stat.go.jp/stat-search"
SOURCES = {
    "b09_01.xlsx": {
        "id": "000032142495",
        "title": "総務省統計局 令和2年国勢調査 人口等基本集計 第9-1表",
        "table": "世帯の家族類型，世帯員の年齢による世帯の種類別一般世帯数及び3世代世帯数－全国，都道府県，市区町村",
        "use": "一般世帯数、単独世帯、夫婦と子供から成る世帯、18歳未満世帯員のいる一般世帯、65歳以上の単独世帯",
    },
    "b27_04.xlsx": {
        "id": "000032142643",
        "title": "総務省統計局 令和2年国勢調査 人口等基本集計 第27-4表",
        "table": "世帯の家族類型，65歳以上世帯員の有無による世帯の類型別一般世帯数－全国，都道府県，市区町村",
        "use": "65歳以上世帯員のみの世帯、65歳以上世帯員がいる世帯（参考）、65歳以上の単独世帯（照合）",
    },
    "b04_03.xlsx": {
        "id": "000032142476",
        "title": "総務省統計局 令和2年国勢調査 人口等基本集計 第4-3表",
        "table": "男女，年齢（5歳階級），配偶関係，国籍総数か日本人別人口及び平均年齢（15歳以上）－全国，都道府県，市区町村",
        "use": "25〜39歳の配偶関係別人口（国籍総数、男女別）",
    },
    "b04_04.xlsx": {
        "id": "000032142477",
        "title": "総務省統計局 令和2年国勢調査 人口等基本集計 第4-4表",
        "table": "男女，年齢（5歳階級），配偶関係，国籍総数か日本人別人口構成比［配偶関係別］（15歳以上）－全国，都道府県，市区町村",
        "use": "照合のみ：公表された5歳階級別の未婚割合と、算出方法（配偶関係「不詳」を除く）の一致を確認",
    },
}
for source in SOURCES.values():
    source.update({
        "period": "2020年10月1日",
        "published": "2021-11-30",
        "page": f"{E_STAT}/files?stat_infid={source['id']}",
        "url": f"{E_STAT}/file-download?statInfId={source['id']}&fileKind=0",
    })

FIELDS = [
    "general", "typeUnknown", "withElderly",
    "single", "singleShare",
    "coupleChildren", "coupleChildrenShare",
    "under18", "under18Share",
    "elderlyOnly", "elderlyOnlyShare",
    "elderlySingle", "elderlySingleShare",
    "unmarried", "unmarriedMale", "unmarriedFemale",
    "unmarriedBase", "unmarriedBaseMale", "unmarriedBaseFemale",
    "unmarriedRate", "unmarriedRateMale", "unmarriedRateFemale",
]
AGES = ["03_25～29歳", "04_30～34歳", "05_35～39歳"]
SEXES = {"0_総数": "", "1_男": "Male", "2_女": "Female"}


def download(name: str, refresh: bool) -> dict:
    source = SOURCES[name]
    dest = RAW / name
    RAW.mkdir(parents=True, exist_ok=True)
    if refresh or not dest.exists():
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))
        print(f"Downloading {name}…", flush=True)
        with session.get(source["url"], stream=True, timeout=(30, 300)) as response:
            response.raise_for_status()
            temp = dest.with_suffix(".part")
            with temp.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    output.write(chunk)
            temp.replace(dest)
    with dest.open("rb") as original:
        digest = hashlib.file_digest(original, "sha256").hexdigest()
    return {"file": name, **{k: v for k, v in source.items() if k != "id"},
            "statInfId": source["id"], "bytes": dest.stat().st_size, "sha256": digest}


def count(value) -> int:
    """Published counts: integers, or "-" for 該当数値なし. Anything else is an error."""
    if isinstance(value, bool):
        raise ValueError(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip() in ("-", "－"):
        return 0
    raise ValueError(f"Unexpected cell value {value!r}")


def ratio(value) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str) and value.strip() in ("-", "－"):
        return None
    raise ValueError(f"Unexpected ratio cell {value!r}")


def share(part: int, whole: int) -> float | None:
    """Percentage with five decimals; undefined (None) when the denominator is zero."""
    return round(part / whole * 100, 5) if whole > 0 else None


def rows(name: str):
    """Yield (columns, row) where columns maps published column labels to indices."""
    workbook = openpyxl.load_workbook(RAW / name, read_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    labels: dict[str, int] = {}
    started = False
    for row in sheet.iter_rows(values_only=True):
        if not started:
            if row[0] == "地域識別コード":
                started = True
                continue
            for index, value in enumerate(row):
                if isinstance(value, str) and "_" in value and value.split("_")[0].replace("R", "").isdigit():
                    labels.setdefault(value, index)
            continue
        if row[0] is None:
            continue
        yield labels, row
    workbook.close()


def region_code(cell) -> str:
    code = str(cell).split("_")[0]
    assert len(code) == 5 and code.isdigit(), cell
    return code


def read_family_types():
    """第9-1表: family-type rows × age-based household columns."""
    out: dict[str, dict] = {}
    for labels, row in rows("b09_01.xlsx"):
        total, under18 = labels["0_総数"], labels["4_うち18歳未満世帯員のいる一般世帯"]
        code, family = region_code(row[2]), row[4]
        record = out.setdefault(code, {"level": row[0], "name": str(row[2]).split("_", 1)[1]})
        if family == "0_総数":
            record["general"] = count(row[total])
            record["under18"] = count(row[under18])
        elif family == "3_単独世帯":
            record["single"] = count(row[total])
        elif family == "112_夫婦と子供から成る世帯":
            record["coupleChildren"] = count(row[total])
        elif family == "4_世帯の家族類型「不詳」":
            record["typeUnknown"] = count(row[total])
        elif family == "R7_（再掲）65歳以上の単独世帯":
            record["elderlySingle"] = count(row[total])
    return out


def read_elderly():
    """第27-4表: 65歳以上世帯員の有無 rows × family-type columns."""
    out: dict[str, dict] = {}
    for labels, row in rows("b27_04.xlsx"):
        total, single, elderly_single = labels["0_総数"], labels["3_単独世帯"], labels["R7_（再掲）65歳以上の単独世帯"]
        code, kind = region_code(row[2]), row[3]
        record = out.setdefault(code, {})
        if kind == "0_総数":
            record["general"] = count(row[total])
            record["single"] = count(row[single])
            record["elderlySingle"] = count(row[elderly_single])
        elif kind == "1_うち65歳以上世帯員がいる世帯":
            record["withElderly"] = count(row[total])
        elif kind == "11_65歳以上世帯員のみの世帯":
            record["elderlyOnly"] = count(row[total])
            record["elderlyOnlySingle"] = count(row[single])
    return out


def read_marital():
    """第4-3表 (国籍総数): 25–39歳 never-married and status-known population by sex."""
    out: dict[str, dict] = {}
    for labels, row in rows("b04_03.xlsx"):
        if row[3] != "0_国籍総数" or row[4] not in SEXES:
            continue
        code, suffix, status = region_code(row[2]), SEXES[row[4]], row[5]
        values = [count(row[labels[age]]) for age in AGES]
        record = out.setdefault(code, {})
        if status == "0_総数":
            record[f"total{suffix}"] = values
        elif status == "1_未婚":
            record[f"unmarried{suffix}"] = values
        elif status == "5_配偶関係「不詳」":
            record[f"unknown{suffix}"] = values
    return out


def read_published_unmarried():
    """第4-4表: published never-married shares (%), used only for verification."""
    out: dict[tuple[str, str], list] = {}
    for labels, row in rows("b04_04.xlsx"):
        if row[3] == "0_国籍総数" and row[4] in SEXES and row[5] == "1_未婚":
            out[(region_code(row[2]), SEXES[row[4]])] = [ratio(row[labels[age]]) for age in AGES]
    return out


def build(statistics: dict) -> tuple[dict, dict]:
    family, elderly, marital = read_family_types(), read_elderly(), read_marital()
    published = read_published_unmarried()
    expected = {r["code"] for group in ("municipalities", "cities", "prefectures") for r in statistics[group]}
    expected.add(statistics["national"]["code"])
    assert set(family) == set(elderly) == set(marital) == expected, "Region codes differ between tables"
    checks = {"published4_4Compared": 0, "published4_4MaxDiff": 0.0}
    regions: dict[str, list] = {}
    for code in sorted(expected):
        f, e, m = family[code], elderly[code], marital[code]
        # Cross-table identities: the same published counts must agree exactly.
        assert f["general"] == e["general"], code
        assert f["single"] == e["single"], code
        assert f["elderlySingle"] == e["elderlySingle"] == e["elderlyOnlySingle"], code
        assert e["elderlyOnly"] <= e["withElderly"] <= f["general"], code
        record = {
            "general": f["general"], "typeUnknown": f["typeUnknown"], "withElderly": e["withElderly"],
            "single": f["single"], "coupleChildren": f["coupleChildren"], "under18": f["under18"],
            "elderlyOnly": e["elderlyOnly"], "elderlySingle": f["elderlySingle"],
        }
        typed = f["general"] - f["typeUnknown"]  # 家族類型「不詳」を除く一般世帯
        record["singleShare"] = share(record["single"], typed)
        record["coupleChildrenShare"] = share(record["coupleChildren"], typed)
        record["elderlySingleShare"] = share(record["elderlySingle"], typed)
        record["under18Share"] = share(record["under18"], f["general"])
        record["elderlyOnlyShare"] = share(record["elderlyOnly"], f["general"])
        for suffix in SEXES.values():
            unmarried = m[f"unmarried{suffix}"]
            known = [t - u for t, u in zip(m[f"total{suffix}"], m[f"unknown{suffix}"])]
            # Verify the denominator rule against every published 5-year share in 第4-4表.
            for value, base, official in zip(unmarried, known, published[(code, suffix)]):
                if official is None:  # published "-": no status-known population, or no never-married
                    assert base == 0 or value == 0, (code, suffix, value, base)
                    continue
                assert base > 0, (code, suffix)
                diff = abs(value / base * 100 - official)
                assert diff < 0.000051, (code, suffix, value / base * 100, official)
                checks["published4_4Compared"] += 1
                checks["published4_4MaxDiff"] = max(checks["published4_4MaxDiff"], diff)
            record[f"unmarried{suffix}"] = sum(unmarried)
            record[f"unmarriedBase{suffix}"] = sum(known)
            record[f"unmarriedRate{suffix}"] = share(sum(unmarried), sum(known))
        regions[code] = [record[field] for field in FIELDS]
    checks["published4_4MaxDiff"] = round(checks["published4_4MaxDiff"], 8)
    return regions, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="download the Excel files again")
    args = parser.parse_args()
    sources = [download(name, args.refresh) for name in SOURCES]
    statistics = json.loads((OUT / "statistics.json").read_text(encoding="utf-8"))
    regions, checks = build(statistics)
    index = {field: i for i, field in enumerate(FIELDS)}
    units = [r["code"] for r in statistics["municipalities"]]
    metadata = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "baseDate": "2020年10月1日",
        "regionCount": len(regions),
        "unitCount": len(units),
        "sources": sources,
        "checks": checks,
        "missingByField": {field: sum(regions[c][index[field]] is None for c in units) for field in FIELDS},
        "definitions": {
            "single": "単独世帯（世帯人員が1人の世帯）。一般世帯に限る。未婚者の数・割合とは別の指標。",
            "singleShare": "単独世帯数 ÷（一般世帯数 − 世帯の家族類型「不詳」）×100。第9-1表。",
            "coupleChildren": "世帯の家族類型「夫婦と子供から成る世帯」（核家族世帯の内訳）。子供の年齢は問わない。",
            "coupleChildrenShare": "夫婦と子供から成る世帯数 ÷（一般世帯数 − 世帯の家族類型「不詳」）×100。第9-1表。",
            "under18": "18歳未満の世帯員がいる一般世帯（世帯員の年齢による世帯の種類）。",
            "under18Share": "18歳未満世帯員のいる一般世帯数 ÷ 一般世帯数 ×100。年齢による世帯の種類に「不詳」の区分はないため分母は一般世帯総数。第9-1表。",
            "elderlyOnly": "世帯員が全員65歳以上の一般世帯（65歳以上世帯員のみの世帯）。65歳以上の世帯員が「いる」世帯とは別。",
            "elderlyOnlyShare": "65歳以上世帯員のみの世帯数 ÷ 一般世帯数 ×100。第27-4表。",
            "elderlySingle": "65歳以上の単独世帯（65歳以上の人が1人で住む世帯）。単独世帯・65歳以上世帯員のみの世帯の一部。",
            "elderlySingleShare": "65歳以上の単独世帯数 ÷（一般世帯数 − 世帯の家族類型「不詳」）×100。第9-1表（第27-4表と照合）。",
            "unmarried": "25〜39歳（25〜29・30〜34・35〜39歳の合計）の配偶関係「未婚」の人口。国籍総数。不詳補完値ではなく原数値。",
            "unmarriedRate": "25〜39歳の未婚者 ÷（25〜39歳人口 − 配偶関係「不詳」）×100。第4-4表の人口構成比と同じく不詳を分母から除く。第4-3表。",
            "denominators": "家族類型による割合は家族類型「不詳」を除く一般世帯、世帯員の年齢による割合は一般世帯総数を分母とする（結果の概要：単独世帯38.1%、65歳以上世帯員のいる世帯40.7%と同じ算出）。施設等の世帯は含まない。",
        },
    }
    payload = {"metadata": metadata, "fields": FIELDS, "regions": regions}
    (OUT / "households.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    national = dict(zip(FIELDS, regions["00000"]))
    print(json.dumps({"regions": len(regions), "checks": checks, "missing": metadata["missingByField"],
                      "national": {k: national[k] for k in ("singleShare", "coupleChildrenShare", "under18Share",
                                                            "elderlyOnlyShare", "elderlySingleShare", "unmarriedRate",
                                                            "unmarriedRateMale", "unmarriedRateFemale")}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
