"""Execute the CI workflow's steps locally, from the workflow file itself.

    python -m api.run_ci_locally
    python -m api.run_ci_locally --job python

GitHub Actions cannot be run here without pushing a branch, so this reads
`.github/workflows/thoughtmap-ci.yml` and runs each step's `run:` script in the
declared working directory with the declared environment.

It reads the *same file* CI reads rather than a copy of the commands, so a step
added to the workflow and never run locally cannot go unnoticed — and a step
that only passes locally because someone edited a duplicate cannot happen.

What it does not do: reproduce GitHub's runner. `uses:` steps (checkout, setup
actions, dependency caching) are reported as skipped, and the host's own
toolchain is used. A green run here means the commands are sound; it does not
replace one real Actions run.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "thoughtmap-ci.yml"


def _load_workflow(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return _load_workflow_without_yaml(path)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_workflow_without_yaml(path: Path) -> dict:
    """Minimal reader for this workflow's shape, when PyYAML is absent.

    Deliberately narrow: it understands jobs, per-job `working-directory`
    defaults, step names, and `run:` block scalars. Anything else it does not
    understand, it reports rather than guessing at.
    """
    jobs: dict[str, dict] = {}
    lines = path.read_text(encoding="utf-8").splitlines()

    job = None
    step: dict | None = None
    run_indent = None
    in_jobs = False

    for raw in lines:
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())

        if raw.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs or not stripped or stripped.startswith("#"):
            if run_indent is not None and step is not None and indent >= run_indent:
                step["run"] += raw[run_indent:] + "\n"
            continue

        if run_indent is not None:
            if indent >= run_indent and stripped:
                step["run"] += raw[run_indent:] + "\n"
                continue
            run_indent = None

        if indent == 2 and stripped.endswith(":"):
            job = stripped[:-1]
            jobs[job] = {"working_directory": "", "steps": []}
            step = None
            continue

        if job is None:
            continue

        match = re.match(r"working-directory:\s*(\S+)", stripped)
        if match:
            if step is not None and step.get("open"):
                step["working_directory"] = match.group(1)
            else:
                jobs[job]["working_directory"] = match.group(1)
            continue

        if stripped.startswith("- uses:"):
            step = {"uses": stripped.split(":", 1)[1].strip(), "open": True}
            jobs[job]["steps"].append(step)
            continue

        if stripped.startswith("- name:"):
            step = {"name": stripped.split(":", 1)[1].strip(), "open": True}
            jobs[job]["steps"].append(step)
            continue

        if stripped.startswith("uses:") and step is not None:
            step["uses"] = stripped.split(":", 1)[1].strip()
            continue

        if stripped.startswith("run:") and step is not None:
            remainder = stripped[4:].strip()
            if remainder in ("|", ">"):
                step["run"] = ""
                run_indent = indent + 2
            else:
                step["run"] = remainder
            continue

    return {"jobs": jobs}


def _job_default_directory(job: dict) -> str:
    """`defaults.run.working-directory`, as GitHub defines it."""
    defaults = job.get("defaults") or {}
    run_defaults = defaults.get("run") or {}
    return str(run_defaults.get("working-directory") or job.get("working_directory") or "")


def _expand(value: str) -> str:
    """Resolve the few workflow expressions this runner supports."""
    return value.replace("${{ github.workspace }}", str(REPO_ROOT))


def run_job(
    name: str, job: dict, python: str, skip: list[str] | None = None
) -> bool:
    print(f"\n{'=' * 70}\nJOB: {name}\n{'=' * 70}")
    default_dir = _job_default_directory(job)
    ok = True

    for step in job.get("steps", []):
        label = step.get("name") or step.get("uses") or "(unnamed)"

        if any(pattern.lower() in label.lower() for pattern in (skip or [])):
            print(f"\n[SKIP] {label}  (skipped by request - NOT verified here)")
            continue

        if "run" not in step:
            print(f"\n[SKIP] {label}  (runner-provided action)")
            continue

        directory = REPO_ROOT / (step.get("working-directory") or default_dir)
        script = step["run"]

        # The workflow targets ubuntu; on Windows the same commands run under
        # Git Bash, which is what the tooling here already uses.
        print(f"\n[RUN ] {label}\n       in {directory}")
        started = time.perf_counter()

        environment = dict(os.environ)
        environment.setdefault("PYTHONPATH", str(REPO_ROOT / "10_ThoughtMap" / "web"))
        environment["PYTHONIOENCODING"] = "utf-8"
        # A CI runner provides a writable temp directory; this host's default
        # is restricted, and pytest's tmp_path fixture cannot create its root
        # there. Supplying one is the runner's job, so it belongs in the
        # environment rather than in the workflow's commands.
        temp_root = Path(tempfile.gettempdir()) / "thoughtmap-ci-tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        environment["PYTEST_DEBUG_TEMPROOT"] = str(temp_root)

        for key, value in (step.get("env") or {}).items():
            environment[str(key)] = _expand(str(value))

        # CI has no artifact. Clearing these stops a developer's local corpus
        # from making a step pass here that would fail on the runner.
        for variable in (
            "THOUGHTMAP_EMBEDDINGS_PATH",
            "THOUGHTMAP_ENCODER_DIR",
            "THOUGHTMAP_ENCODER_PROVIDER",
            "THOUGHTMAP_DEPLOYMENT_MODE",
        ):
            environment.pop(variable, None)

        # `python` on PATH may be the Windows Store stub, so point the workflow's
        # `python` at this interpreter. A plain re.sub would read a Windows path
        # as regex escapes, hence the replacement function.
        # Quoted: on Windows the interpreter path contains backslashes,
        # which bash would otherwise consume as escapes.
        quoted = '"{}"'.format(python)
        script = re.sub(
            r"(?m)^(\s*)python\b", lambda match: match.group(1) + quoted, script
        )

        shell = shutil.which("bash") or "bash"
        completed = subprocess.run(
            [shell, "-lc", script],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = time.perf_counter() - started

        output = (completed.stdout or "") + (completed.stderr or "")
        tail = "\n".join(output.strip().splitlines()[-12:])
        if tail:
            print("       " + tail.replace("\n", "\n       "))

        if completed.returncode == 0:
            print(f"       -> PASS ({elapsed:.1f}s)")
        else:
            print(f"       -> FAIL (exit {completed.returncode}, {elapsed:.1f}s)")
            ok = False

    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--job", default=None, help="Run only this job.")
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        metavar="STEP",
        help=(
            "Skip a step by name. For steps this host genuinely cannot run - "
            "`npm ci` hits a Windows/OneDrive file lock on node_modules/.bin - "
            "never for steps that fail."
        ),
    )
    parser.add_argument("--workflow", type=Path, default=WORKFLOW)
    args = parser.parse_args(argv)

    if not args.workflow.exists():
        print(f"No workflow at {args.workflow}")
        return 1

    workflow = _load_workflow(args.workflow)
    jobs = workflow.get("jobs", {})
    if args.job:
        jobs = {name: job for name, job in jobs.items() if name == args.job}
        if not jobs:
            print(f"No job named {args.job!r}")
            return 1

    print(f"Running {args.workflow.relative_to(REPO_ROOT)} locally")
    print(f"interpreter: {sys.executable}")

    results = {
        name: run_job(name, job, sys.executable, args.skip)
        for name, job in jobs.items()
    }

    print(f"\n{'=' * 70}")
    for name, ok in results.items():
        print(f"  {name:<12} {'PASS' if ok else 'FAIL'}")
    everything = all(results.values())
    print("RESULT:", "OK" if everything else "FAILED")
    print(
        "\nNote: `uses:` steps are provided by the GitHub runner and were skipped."
        "\nThis validates the commands, not GitHub's environment."
    )
    if args.skip:
        print(f"Explicitly skipped, and therefore NOT verified: {args.skip}")
    return 0 if everything else 1


if __name__ == "__main__":
    sys.exit(main())
