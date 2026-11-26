import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jinn_uploader.config import AppConfig  # noqa: E402
from jinn_uploader.credentials import R2Credentials  # noqa: E402
from jinn_uploader.history import History, ResumeStore  # noqa: E402
from jinn_uploader.r2client import R2Service, make_client  # noqa: E402
from jinn_uploader.uploader import UploadEngine  # noqa: E402

BUCKET = "jinn-mv-portfolio"
PUBLIC = "https://pub-14a29b5d61e944bfa82071f29c1817f1.r2.dev"


def pytest_configure(config):
    config.addinivalue_line("markers", "large: uploads 300MB+ files (run with -m large)")
    config.addinivalue_line("markers", "ffmpeg: needs ffmpeg/ffprobe on PATH")


@pytest.fixture(autouse=True)
def app_home(tmp_path, monkeypatch):
    home = tmp_path / "apphome"
    monkeypatch.setenv("JINN_UPLOADER_HOME", str(home))
    return home


@pytest.fixture(scope="session")
def moto_url():
    from moto.server import ThreadedMotoServer

    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    yield f"http://{host}:{port}"
    server.stop()


@pytest.fixture
def s3(moto_url):
    import requests

    requests.post(f"{moto_url}/moto-api/reset", timeout=30)
    creds = R2Credentials("0" * 32, "test-access-key-id-000000000000", "test-secret")
    client = make_client(creds, endpoint_override=moto_url)
    import boto3

    admin = boto3.client(
        "s3", endpoint_url=moto_url, region_name="us-east-1",
        aws_access_key_id="x", aws_secret_access_key="y",
    )
    admin.create_bucket(Bucket=BUCKET)  # the bucket already exists on R2; created here only for the fake
    return client


@pytest.fixture
def config(tmp_path):
    cfg = AppConfig()
    cfg.part_size_mib = 5
    cfg.multipart_threshold_mib = 8
    cfg.concurrency = 4
    cfg.max_retries = 3
    cfg.generate_thumbnails = False
    cfg.export_dir = str(tmp_path / "export")
    return cfg.normalized()


@pytest.fixture
def service(s3):
    return R2Service(s3, BUCKET, PUBLIC)


@pytest.fixture
def make_engine(service, config, app_home):
    def factory(**kw):
        return UploadEngine(
            service,
            config,
            History(app_home / "history.sqlite3"),
            ResumeStore(app_home / "resume"),
            retry_base_delay=0.01,
            **kw,
        )

    return factory


@pytest.fixture
def ffmpeg_bins():
    f, p = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not (f and p):
        pytest.skip("ffmpeg not available")
    return f, p


def write_random(path: Path, size: int, seed: int = 1) -> Path:
    import random

    rnd = random.Random(seed)
    block = rnd.randbytes(1024 * 1024)
    with open(path, "wb") as fh:
        remaining = size
        i = 0
        while remaining > 0:
            # Vary each MiB so parts differ.
            chunk = (i.to_bytes(8, "little") + block[8:])[: min(len(block), remaining)]
            fh.write(chunk)
            remaining -= len(chunk)
            i += 1
    return path
