"""Download official Japanese statistics and build the browser data, without API keys.

Usage: python -m pip install -r scripts/requirements.txt
       npm install
       python scripts/prepare_data.py [--refresh] [--skip-geometry]
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import zipfile

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "public" / "data"
SOURCES = {
    "fertility-full.xlsx": {
        "url": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040174881&fileKind=0",
        "title": "厚生労働省 人口動態保健所・市区町村別統計 第2表",
        "period": "2018–2022年", "published": "2024-04-19",
        "page": "https://www.mhlw.go.jp/toukei/saikin/hw/jinkou/other/hoken24/index.html",
    },
    "census2020.xlsx": {
        "url": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032142410&fileKind=0",
        "title": "総務省統計局 令和2年国勢調査 人口等基本集計 第2-7表",
        "period": "2020年10月1日", "published": "2021-11-30",
        "page": "https://www.e-stat.go.jp/stat-search/files?stat_infid=000032142410",
    },
    "census-summary2020.xlsx": {
        "url": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032142402&fileKind=0",
        "title": "総務省統計局 令和2年国勢調査 人口等基本集計 第1-1表",
        "period": "2020年10月1日（人口増減は2015→2020年）", "published": "2021-11-30",
        "page": "https://www.e-stat.go.jp/stat-search/files?stat_infid=000032142402",
    },
    "N03-20200101_GML.zip": {
        "url": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2020/N03-20200101_GML.zip",
        "title": "国土交通省 国土数値情報 行政区域 N03（全国）",
        "period": "2020年1月1日", "published": "2020",
        "page": "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-v2_4.html",
    },
}


def download(item: tuple[str, dict], refresh: bool) -> dict:
    name, source = item
    dest = RAW / name
    if refresh or not dest.exists():
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))
        print(f"Downloading {name}…", flush=True)
        with session.get(source["url"], stream=True, timeout=(30, 180)) as response:
            response.raise_for_status()
            temp = dest.with_suffix(".part")
            with temp.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    output.write(chunk)
            temp.replace(dest)
    with dest.open("rb") as original:
        digest = hashlib.file_digest(original, "sha256").hexdigest()
    return {"file": name, **source, "bytes": dest.stat().st_size, "sha256": digest}


def number(value, zero_dash: bool = False):
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if text in ("-", "－") and zero_dash:
        return 0
    # Missing or suppressed observations remain null. Never substitute another region's value.
    try:
        n = float(text)
        return n if math.isfinite(n) else None
    except ValueError:
        return None


def int_count(value):
    n = number(value, zero_dash=True)
    return int(n) if n is not None else None


def get_fertility() -> dict:
    table = pd.read_excel(RAW / "fertility-full.xlsx", header=None)
    records = {}
    for row in table.itertuples(index=False, name=None):
        label = str(row[0]).strip()
        if label.startswith("全国"):
            code = "00000"
        elif match := re.match(r"^(\d{5})(\D.*)", label):
            code = match[1]
        elif match := re.match(r"^(\d{2})([^\d].*)", label):
            code = match[1] + "000"
        else:
            continue  # Four digit health-center codes are not municipalities.
        records[code] = number(row[1])  # Bayesian estimate, not the unadjusted column 9.
    assert records["00000"] == 1.33
    assert records["46530"] == 2.25
    assert records["26105"] == 0.76
    return records


def get_statistics(fertility: dict):
    summary = pd.read_excel(RAW / "census-summary2020.xlsx", header=None)
    summary = summary[summary[0].astype(str).isin(["a", "0", "1", "2", "3"])]
    summaries = {str(row[5]).zfill(5): row for row in summary.itertuples(index=False, name=None)}
    age = pd.read_excel(RAW / "census2020.xlsx", header=None)
    age = age[(age[0] == "0_国籍総数") & (age[1] == "0_総数")
              & age[2].astype(str).isin(["a", "0", "1", "2", "3"])]
    records = []
    for row in age.itertuples(index=False, name=None):
        code = str(row[7]).zfill(5)
        extra = summaries[code]
        population, children = int_count(row[9]), int_count(row[32])
        ages = [int_count(row[i]) for i in (10, 11, 12)]
        unknown = int_count(row[31])
        area = number(extra[14])
        name = str(row[8]).split("_", 1)[1]
        pref = str(row[6]).split("_", 1)[1]
        records.append({
            "code": code, "name": name, "prefecture": pref,
            "prefCode": code[:2], "level": str(row[2]),
            "population": population, "children": children, "ages": ages,
            "unknownAge": unknown, "childShare": number(row[38]),
            "tfr": fertility.get(code), "area": area,
            "childDensity": round(children / area, 3) if children is not None and area and area > 0 else None,
            "population2015": int_count(extra[10]), "change": number(extra[12]),
        })
    assert len({r["code"] for r in records}) == len(records), "Duplicate municipal codes"
    national = next(r for r in records if r["code"] == "00000")
    prefectures = [r for r in records if r["level"] == "a" and r["code"] != "00000"]
    municipalities = [r for r in records if r["level"] in ("0", "2", "3")]
    cities = [r for r in records if r["level"] == "1"]
    assert len(municipalities) == 1896
    assert sum(r["population"] for r in municipalities) == national["population"]
    assert sum(r["children"] for r in municipalities) == national["children"]
    return national, prefectures, municipalities, cities


def build_geometry(force: bool):
    destination = OUT / "municipalities.geojson"
    if destination.exists() and not force:
        return
    geo_file = RAW / "N03-20_200101.geojson"
    if not geo_file.exists() or force:
        with zipfile.ZipFile(RAW / "N03-20200101_GML.zip") as archive:
            archive.extract("N03-20_200101.geojson", RAW)
    cli = ROOT / "node_modules" / "mapshaper" / "bin" / "mapshaper"
    if not cli.exists():
        raise RuntimeError("Run npm install before preparing geographic data.")
    print("Dissolving and simplifying official boundaries (shared topology preserved)…", flush=True)
    subprocess.run([
        "node", "--max-old-space-size=6144", str(cli), str(geo_file),
        "-filter", '/^[0-9]{5}$/.test(N03_007 || "")',
        "-dissolve", "N03_007", "copy-fields=N03_001,N03_003,N03_004",
        "-simplify", "weighted", "interval=120", "keep-shapes",
        "-rename-fields", "code=N03_007,prefecture=N03_001,city=N03_003,name=N03_004",
        "-o", "format=geojson", "precision=0.00001", str(destination),
    ], check=True, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Re-download official source files")
    parser.add_argument("--skip-geometry", action="store_true", help="Reuse the prepared GeoJSON")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        manifest = list(pool.map(lambda item: download(item, args.refresh), SOURCES.items()))
    national, prefectures, municipalities, cities = get_statistics(get_fertility())
    if not args.skip_geometry:
        build_geometry(args.refresh)
    geo = json.loads((OUT / "municipalities.geojson").read_text(encoding="utf-8"))
    by_code = {r["code"]: r for r in municipalities}
    geographic_codes = set()
    unmatched_geometry = []
    for feature in geo["features"]:
        prop = feature["properties"]
        code = prop["code"]
        geographic_codes.add(code)
        geometry = shape(feature["geometry"])
        west, south, east, north = geometry.bounds
        record = by_code.get(code)
        if record is None:
            unmatched_geometry.append({"code": code, "name": prop["name"], "prefecture": prop["prefecture"]})
            continue
        record["bounds"] = [[round(south, 5), round(west, 5)], [round(north, 5), round(east, 5)]]
        point = geometry.representative_point()
        record["center"] = [round(point.y, 5), round(point.x, 5)]
    missing_geometry = [r["code"] for r in municipalities if r["code"] not in geographic_codes]
    # A changed/missing boundary must be fixed explicitly instead of silently dropping a municipality.
    assert not missing_geometry, f"Statistics without geometry: {missing_geometry}"
    metadata = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sources": manifest, "municipalityCount": len(municipalities),
        "geometryCount": len(geo["features"]),
        "missingTfr": [r["code"] for r in municipalities if r["tfr"] is None],
        "unmatchedGeometry": unmatched_geometry,
        "missingByMetric": {key: sum(r[key] is None for r in municipalities)
                            for key in ("tfr", "children", "childShare", "childDensity", "change")},
        "definitions": {
            "tfr": "2018–2022年の人口動態統計に基づく合計特殊出生率（ベイズ推定値）。日本人女性を分母とする。単年の出生率ではない。",
            "children": "2020年10月1日現在の0–14歳人口。男女・国籍総数。年齢不詳を補完していない。",
            "childShare": "年齢が判明している人口に占める0–14歳人口の割合。国勢調査の公表比率を使用。",
            "childDensity": "0–14歳人口 ÷ 国勢調査第1-1表の面積（参考、km²）。可住地面積による密度ではない。",
            "change": "2015年（2020年境域への組替値）から2020年の総人口増減率。子ども人口の増減率ではない。",
            "geography": "2020年1月1日時点の国土数値情報。120m間隔のトポロジー簡略化を適用した表示用境界。測量用ではない。",
            "units": "政令指定都市は行政区を表示。市全体・東京都区部の合計値はランキングと自治体数から除外。",
        },
    }
    result = {"metadata": metadata, "national": national, "prefectures": prefectures,
              "municipalities": municipalities, "cities": cities}
    (OUT / "statistics.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(json.dumps({"municipalities": len(municipalities), "geometries": len(geo["features"]),
                      "missing": metadata["missingByMetric"], "unmatchedGeometry": unmatched_geometry}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
