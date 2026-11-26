"""Command line entry point.

No arguments → GUI. The extra modes exist so the frozen EXE itself can be verified
headlessly (CI, troubleshooting); results are written as JSON because a windowed
EXE has no console.

  JinnMediaUploader.exe --selftest --report out.json [--endpoint URL]
  JinnMediaUploader.exe --r2-verify --report out.json [--size-mib 320] [--cleanup]
  JinnMediaUploader.exe --screenshot out.png [--tab N]
"""

from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import sys
import traceback
from pathlib import Path


def setup_logging() -> None:
    from .config import app_data_dir

    log_dir = app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("jinn_uploader")
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(log_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(message)s"))
    logger.addHandler(fh)
    if sys.stderr is not None:
        sh = logging.StreamHandler()
        sh.setLevel(logging.WARNING)
        logger.addHandler(sh)
    # Never let library debug logs record request headers.
    for name in ("botocore", "boto3", "urllib3", "s3transfer"):
        logging.getLogger(name).setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="JinnMediaUploader", add_help=True)
    parser.add_argument("--selftest", action="store_true", help="offline checks of the packaged app")
    parser.add_argument("--r2-verify", action="store_true", help="live verification against the configured R2 bucket")
    parser.add_argument("--screenshot", metavar="PNG", help="render the main window with demo data")
    parser.add_argument("--tab", type=int, default=0)
    parser.add_argument("--report", metavar="JSON", help="where to write the verification report")
    parser.add_argument("--endpoint", help="S3-compatible endpoint for --selftest upload checks")
    parser.add_argument("--size-mib", type=int, default=320)
    parser.add_argument("--cleanup", action="store_true", help="delete only the test objects this run created")
    parser.add_argument("--store-env-credentials", action="store_true",
                        help="copy R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY into the credential vault first")
    parser.add_argument("--forget-credentials", action="store_true", help="remove the stored credential after --r2-verify")
    args = parser.parse_args(argv)

    setup_logging()

    if args.screenshot:
        from .gui.app import screenshot

        return screenshot(args.screenshot, tab=args.tab)

    if args.selftest or args.r2_verify:
        from . import selftest

        report_path = Path(args.report) if args.report else None
        try:
            if args.selftest:
                report = selftest.offline_selftest(endpoint=args.endpoint)
            else:
                report = selftest.r2_verify(
                    size_mib=args.size_mib,
                    cleanup=args.cleanup,
                    store_env_credentials=args.store_env_credentials,
                    forget_credentials=args.forget_credentials,
                )
        except Exception as exc:  # noqa: BLE001
            report = {"ok": False, "fatal": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}
        text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        if report_path:
            report_path.write_text(text, encoding="utf-8")
        if sys.stdout is not None:
            try:
                print(text)
            except Exception:  # noqa: BLE001
                pass
        return 0 if report.get("ok") else 1

    from .gui.app import run_gui

    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
