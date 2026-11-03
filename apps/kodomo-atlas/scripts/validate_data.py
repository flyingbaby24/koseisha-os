"""Integrity checks for the shipped official-statistics snapshot (standard library only)."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / "public/data/statistics.json").read_text(encoding="utf-8"))
    geo = json.loads((ROOT / "public/data/municipalities.geojson").read_text(encoding="utf-8"))
    municipalities = data["municipalities"]
    national = data["national"]
    codes = [r["code"] for r in municipalities]
    geographic_codes = [f["properties"]["code"] for f in geo["features"]]
    assert len(codes) == len(set(codes)) == 1896
    assert len(geographic_codes) == len(set(geographic_codes)) == 1902
    assert set(codes).issubset(geographic_codes), "Population records without boundaries"
    assert len(data["prefectures"]) == 47
    assert len(data["cities"]) == 21
    assert all(r["level"] in ["0", "2", "3"] for r in municipalities)
    assert sum(r["population"] for r in municipalities) == national["population"] == 126146099
    assert sum(r["children"] for r in municipalities) == national["children"] == 14955692
    for age_index, expected in enumerate([4516082, 5089093, 5350517]):
        assert sum(r["ages"][age_index] for r in municipalities) == national["ages"][age_index] == expected
    for r in municipalities + data["prefectures"] + data["cities"] + [national]:
        assert r["code"].isdigit() and len(r["code"]) == 5
        assert sum(r["ages"]) == r["children"], f"Age totals disagree: {r['code']}"
        assert 0 <= r["children"] <= r["population"]
        assert r["unknownAge"] >= 0
        denominator = r["population"] - r["unknownAge"]
        if denominator:
            assert abs(r["children"] / denominator * 100 - r["childShare"]) < 0.00002, r["code"]
        else:
            assert r["childShare"] is None
        assert abs(r["children"] / r["area"] - r["childDensity"]) <= 0.00051
        if r["change"] is not None:
            assert r["population2015"] > 0
            assert abs((r["population"] / r["population2015"] - 1) * 100 - r["change"]) < 0.00002
        if r["tfr"] is not None:
            assert 0 <= r["tfr"] < 4
    for r in municipalities:
        assert "bounds" in r and "center" in r
        south_west, north_east = r["bounds"]
        assert south_west[0] <= r["center"][0] <= north_east[0]
        assert south_west[1] <= r["center"][1] <= north_east[1]
    missing_tfr = {r["code"] for r in municipalities if r["tfr"] is None}
    assert missing_tfr == {"07542", "07543", "07544", "07545", "07546", "07547", "07548", "07564", "43513"}
    assert missing_tfr == set(data["metadata"]["missingTfr"])
    by_code = {r["code"]: r for r in municipalities}
    assert by_code["46530"]["name"] == "徳之島町" and by_code["46530"]["tfr"] == 2.25
    assert by_code["26105"]["name"] == "京都市東山区" and by_code["26105"]["tfr"] == 0.76
    assert national["tfr"] == 1.33
    for metric in ("tfr", "children", "childShare", "childDensity", "change"):
        assert sum(r[metric] is None for r in municipalities) == data["metadata"]["missingByMetric"][metric]
    for source in data["metadata"]["sources"]:
        assert source["url"].startswith(("https://www.e-stat.go.jp/", "https://nlftp.mlit.go.jp/"))
        assert len(source["sha256"]) == 64
    assert not any(token in json.dumps(data) for token in ["NaN", "Infinity"])
    print("PASS: unique 5-digit codes; 1,896 statistical units; 1,902 boundaries; 47 prefectures")
    print("PASS: national population and all three age-group sums agree with the official totals")
    print("PASS: age ratios, land-area densities, and 2015–2020 growth calculations")
    print("PASS: 9 non-published fertility rates remain null; official max/min spot checks")
    print("PASS: complete geographic joins, source URLs, and recorded SHA-256 hashes")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
