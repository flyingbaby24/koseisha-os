"""Print a self-test / R2 verification report and add it to the GitHub job summary."""

import json
import os
import sys
from pathlib import Path


def main(path: str) -> int:
    p = Path(path)
    if not p.is_file():
        print(f"report not found: {p}")
        return 1
    r = json.loads(p.read_text(encoding="utf-8"))
    lines = [f"### {r.get('title', 'report')} — {'PASS' if r.get('ok') else 'FAIL'}", ""]
    if r.get("fatal"):
        lines += [f"**fatal:** `{r['fatal']}`", ""]
    meta = {k: r[k] for k in ("app_version", "platform", "frozen", "credential_store", "bucket", "test_prefix") if k in r}
    lines += [f"- {k}: `{v}`" for k, v in meta.items()]
    lines += ["", "| | check | seconds | details |", "|---|---|---:|---|"]
    for c in r.get("checks", []):
        details = {k: v for k, v in c.items() if k not in ("name", "ok", "seconds")}
        text = json.dumps(details, ensure_ascii=False)
        if len(text) > 400:
            text = text[:400] + "…"
        lines.append(f"| {'✅' if c['ok'] else '❌'} | {c['name']} | {c.get('seconds', '')} | `{text}` |")
    out = "\n".join(lines)
    print(out)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(out + "\n\n")
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
