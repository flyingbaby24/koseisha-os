"""Start the API in each broken configuration and check it fails honestly.

    python -m api.verify_failure_modes
    python -m api.verify_failure_modes --port 8099 --json report.json

Every deployment eventually meets one of these, and the requirement is the same
in all of them (T7 §28):

    the process stays alive       so an operator can reach it
    /health answers 200           so a platform does not kill it in a loop
    /ready answers 503            so no traffic is routed to it
    the reason is actionable      names the file and the variable to change
    no partial corpus is served   the wrong artifact is refused, not used

Simulated: missing embedding artifact, wrong artifact, missing query encoder,
corrupt query encoder, missing projection, corrupted vector cache. Then the
correct configuration is restored and the service must return to ready (§29).

Nothing is mutated permanently: broken states are built inside a temporary
directory, and the two real files this must move aside are restored in a
`finally` block.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


WEB_DIR = Path(__file__).resolve().parents[1]


def poll(base: str, path: str, timeout: float = 90.0) -> tuple[int, Any]:
    """Wait for the server to answer, then return (status, body)."""
    deadline = time.time() + timeout
    last: tuple[int, Any] = (0, {})
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + path, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read())
            except Exception:
                body = {}
            last = (exc.code, body)
            blocked = body.get("blocked_by") or []
            # Still warming is not an answer yet; wait for it to settle.
            if exc.code == 503 and blocked and all(
                b in ("search_engine", "embedding_model") for b in blocked
            ):
                pending = [
                    c for c in body.get("checks", [])
                    if c.get("status") == "pending"
                ]
                if pending:
                    time.sleep(1.5)
                    continue
            return last
        except Exception:
            time.sleep(1.0)
    return last


class Instance:
    """A uvicorn process with a specific environment, torn down reliably."""

    def __init__(self, port: int, environment: dict[str, str]) -> None:
        self.port = port
        self.environment = environment
        self.process: subprocess.Popen | None = None

    def __enter__(self) -> "Instance":
        env = dict(os.environ)
        env.update(self.environment)
        env["PYTHONIOENCODING"] = "utf-8"
        self.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "api.main:app",
                "--host", "127.0.0.1", "--port", str(self.port),
                "--log-level", "error",
            ],
            cwd=str(WEB_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return self

    def __exit__(self, *exc_info) -> None:
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
            time.sleep(1.0)


def check_case(
    name: str,
    port: int,
    environment: dict[str, str],
    expect_ready: bool,
    expect_in_detail: list[str],
) -> dict[str, Any]:
    print(f"\n--- {name} ---")
    base = f"http://127.0.0.1:{port}"

    with Instance(port, environment):
        health_status, _ = poll(base, "/health", timeout=60)
        ready_status, snapshot = poll(base, "/ready", timeout=120)

    ready = bool(snapshot.get("ready"))
    blocked = snapshot.get("blocked_by") or []
    details = " ".join(
        str(check.get("detail", "")) for check in snapshot.get("checks", [])
    )

    alive = health_status == 200
    correct = ready == expect_ready
    missing = [text for text in expect_in_detail if text not in details]
    actionable = not missing

    result: dict[str, Any] = {
        "name": name,
        "health": health_status,
        "ready_status": ready_status,
        "ready": ready,
        "blocked_by": blocked,
        "missing_from_detail": missing,
        "ok": alive and correct and (expect_ready or actionable),
    }

    print(f"  /health          : {health_status}  {'alive' if alive else 'PROCESS DIED'}")
    print(f"  /ready           : {ready_status} ready={ready}")
    print(f"  blocked_by       : {blocked or 'none'}")
    if not expect_ready:
        print(f"  names the cause  : {'yes' if actionable else 'NO -> missing ' + str(missing)}")
        first = next(
            (
                str(c.get("detail", "")).split("\n")[0]
                for c in snapshot.get("checks", [])
                if c.get("status") == "failed"
            ),
            "",
        )
        if first:
            print(f"  reason           : {first[:130]}")
    print(f"  -> {'PASS' if result['ok'] else 'FAIL'}")
    return result


def run(port: int) -> list[dict[str, Any]]:
    from .config import get_settings
    from .map_projection import DEFAULT_ARTIFACT_PATH
    from .repositories import _vector_cache_path

    settings = get_settings()
    artifact = settings.embeddings_path
    encoder = settings.encoder_dir

    if artifact is None or not artifact.exists():
        print("THOUGHTMAP_EMBEDDINGS_PATH must point at the real artifact.")
        return [{"name": "setup", "ok": False}]

    base_env = {
        "THOUGHTMAP_DEPLOYMENT_MODE": "public-demo",
        "THOUGHTMAP_EMBEDDINGS_PATH": str(artifact),
        "THOUGHTMAP_ENCODER_PROVIDER": "onnx",
        "THOUGHTMAP_ENCODER_DIR": str(encoder or ""),
        "THOUGHTMAP_WARMUP": "full",
    }

    results: list[dict[str, Any]] = []
    temporary = Path(tempfile.mkdtemp(prefix="thoughtmap-failure-"))

    try:
        results.append(check_case(
            "missing embedding artifact", port,
            {**base_env, "THOUGHTMAP_EMBEDDINGS_PATH": str(temporary / "absent.csv")},
            expect_ready=False, expect_in_detail=["absent.csv"],
        ))

        # Stands for any artifact that is not the pinned one: a truncated
        # download, or a superseded corpus.
        wrong = temporary / "thoughtmap_canonical_embeddings.csv"
        wrong.write_bytes(b"doc_id,embedding,model_name\n")
        results.append(check_case(
            "wrong embedding artifact", port,
            {**base_env, "THOUGHTMAP_EMBEDDINGS_PATH": str(wrong)},
            expect_ready=False,
            expect_in_detail=["expected", "THOUGHTMAP_EMBEDDINGS_PATH"],
        ))

        results.append(check_case(
            "missing query encoder", port,
            {**base_env, "THOUGHTMAP_ENCODER_DIR": str(temporary / "no-encoder")},
            expect_ready=False, expect_in_detail=["encoder"],
        ))

        if encoder and (encoder / "encoder_manifest.json").exists():
            broken = temporary / "broken-encoder"
            broken.mkdir()
            shutil.copyfile(
                encoder / "encoder_manifest.json", broken / "encoder_manifest.json"
            )
            (broken / "model.onnx").write_bytes(b"not a model")
            (broken / "tokenizer.json").write_text("{}", encoding="utf-8")
            results.append(check_case(
                "corrupt query encoder", port,
                {**base_env, "THOUGHTMAP_ENCODER_DIR": str(broken)},
                expect_ready=False, expect_in_detail=["size"],
            ))

        if DEFAULT_ARTIFACT_PATH.exists():
            moved = DEFAULT_ARTIFACT_PATH.with_suffix(".json.failuretest")
            DEFAULT_ARTIFACT_PATH.rename(moved)
            try:
                results.append(check_case(
                    "missing map projection", port, base_env,
                    expect_ready=False, expect_in_detail=["projection"],
                ))
            finally:
                moved.rename(DEFAULT_ARTIFACT_PATH)

        # A corrupt cache must NOT block readiness: it is recoverable by
        # reparsing the artifact, which is exactly what should happen.
        cache = _vector_cache_path(artifact)
        if cache.exists():
            backup = cache.with_suffix(cache.suffix + ".failuretest")
            cache.rename(backup)
            cache.write_bytes(b"this is not a valid npz archive")
            try:
                results.append(check_case(
                    "corrupted vector cache (recoverable)", port, base_env,
                    expect_ready=True, expect_in_detail=[],
                ))
            finally:
                cache.unlink(missing_ok=True)
                backup.rename(cache)

        results.append(check_case(
            "restored configuration (recovery)", port, base_env,
            expect_ready=True, expect_in_detail=[],
        ))
    finally:
        shutil.rmtree(temporary, ignore_errors=True)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    print("ThoughtMap startup failure simulation")
    results = run(args.port)

    print()
    passed = sum(1 for r in results if r.get("ok"))
    print(f"{passed}/{len(results)} cases behaved correctly")
    ok = passed == len(results)
    print("RESULT:", "OK" if ok else "FAILED")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
