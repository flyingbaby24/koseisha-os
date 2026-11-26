"""R2 API credentials kept in the OS credential vault (Windows Credential Manager).

The three values (Account ID, Access Key ID, Secret Access Key) are stored as one
generic credential so they are written and removed atomically. Nothing secret is
ever written to the config file, the log, or the history database.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE = "JinnMediaUploader/R2"
USERNAME = "s3-api"

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CredentialError(Exception):
    pass


@dataclass(frozen=True)
class R2Credentials:
    account_id: str
    access_key_id: str
    secret_access_key: str

    def cleaned(self) -> "R2Credentials":
        return R2Credentials(
            self.account_id.strip().lower(),
            self.access_key_id.strip(),
            self.secret_access_key.strip(),
        )

    def problems(self) -> list[str]:
        """Blocking problems (empty fields)."""
        out = []
        if not self.account_id.strip():
            out.append("Account ID が空です")
        if not self.access_key_id.strip():
            out.append("Access Key ID が空です")
        if not self.secret_access_key.strip():
            out.append("Secret Access Key が空です")
        return out

    def warnings(self) -> list[str]:
        """Non-blocking format hints (R2 uses 32/32/64 hex characters)."""
        c = self.cleaned()
        out = []
        if c.account_id and not _HEX32.match(c.account_id):
            out.append("Account ID は通常32桁の16進数です（アカウント名ではありません）")
        if c.access_key_id and not _HEX32.match(c.access_key_id.lower()):
            out.append("R2 の Access Key ID は通常32桁の16進数です")
        if c.secret_access_key and not _HEX64.match(c.secret_access_key.lower()):
            out.append("R2 の Secret Access Key は通常64桁の16進数です")
        return out

    def masked_access_key(self) -> str:
        k = self.access_key_id
        return (k[:4] + "…" + k[-4:]) if len(k) > 8 else "****"

    def __repr__(self) -> str:  # never leak the secret through logs or tracebacks
        return f"R2Credentials(account_id={self.account_id!r}, access_key_id={self.masked_access_key()!r}, secret=***)"

    __str__ = __repr__


def default_backend():
    """Return the platform vault explicitly on Windows.

    Keyring normally discovers backends through package entry points, which can be
    missing in a frozen EXE; pinning WinVaultKeyring avoids silently falling back to
    an insecure or failing backend.
    """
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring

        return WinVaultKeyring()
    return keyring.get_keyring()


def describe_backend(backend) -> str:
    name = type(backend).__name__
    module = type(backend).__module__
    if name == "MemoryKeyring":
        return "メモリ（テスト・デモ用）"
    if name == "WinVaultKeyring":
        return "Windows Credential Manager"
    if "macOS" in module:
        return "macOS Keychain"
    if "SecretService" in module:
        return "Secret Service (GNOME Keyring 等)"
    return f"{module}.{name}"


def is_secure_backend(backend) -> bool:
    module = type(backend).__module__
    name = type(backend).__name__
    if module.startswith("keyring.backends.fail") or module.startswith("keyring.backends.null"):
        return False
    if "Plaintext" in name or "plaintext" in module or "keyrings.alt" in module:
        return False
    if "chainer" in module:
        return any(is_secure_backend(b) for b in getattr(backend, "backends", []))
    return True


class CredentialStore:
    def __init__(self, backend=None, service: str = SERVICE, username: str = USERNAME):
        self.backend = backend if backend is not None else default_backend()
        self.service = service
        self.username = username

    @property
    def backend_label(self) -> str:
        return describe_backend(self.backend)

    @property
    def secure(self) -> bool:
        return is_secure_backend(self.backend)

    def load(self) -> R2Credentials | None:
        try:
            raw = self.backend.get_password(self.service, self.username)
        except KeyringError as exc:
            raise CredentialError(f"資格情報ストアを読み取れません: {exc}") from exc
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return R2Credentials(
                str(data["account_id"]), str(data["access_key_id"]), str(data["secret_access_key"])
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise CredentialError("保存されている資格情報の形式が不正です。設定から再登録してください。") from exc

    def save(self, creds: R2Credentials) -> None:
        if not self.secure:
            raise CredentialError(
                f"安全な資格情報ストアが利用できません（{self.backend_label}）。保存を中止しました。"
            )
        problems = creds.problems()
        if problems:
            raise CredentialError(" / ".join(problems))
        c = creds.cleaned()
        blob = json.dumps(
            {"account_id": c.account_id, "access_key_id": c.access_key_id, "secret_access_key": c.secret_access_key},
            separators=(",", ":"),
        )
        try:
            self.backend.set_password(self.service, self.username, blob)
        except KeyringError as exc:
            raise CredentialError(f"資格情報を保存できません: {exc}") from exc

    def delete(self) -> bool:
        try:
            self.backend.delete_password(self.service, self.username)
            return True
        except PasswordDeleteError:
            return False
        except KeyringError as exc:
            raise CredentialError(f"資格情報を削除できません: {exc}") from exc


class MemoryKeyring:
    """In-process store for tests and demo screenshots.

    Deliberately *not* a ``keyring.backend.KeyringBackend`` subclass: keyring
    auto-registers subclasses, and this one must never be picked as the real vault.
    """

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        try:
            del self._store[(service, username)]
        except KeyError as exc:
            raise PasswordDeleteError("not found") from exc


# ---------------------------------------------------------------------- GitHub
GITHUB_SERVICE = "JinnMediaUploader/GitHub"
GITHUB_USERNAME = "token"


def mask_token(token: str) -> str:
    return (token[:4] + "…" + token[-4:]) if len(token) > 12 else "****"


class GitHubTokenStore:
    """GitHub personal access token in the OS vault (Windows Credential Manager).

    Stored separately from the R2 keys under ``JinnMediaUploader/GitHub`` so either can
    be replaced or removed on its own.
    """

    def __init__(self, backend=None, service: str = GITHUB_SERVICE, username: str = GITHUB_USERNAME):
        self.backend = backend if backend is not None else default_backend()
        self.service = service
        self.username = username

    @property
    def backend_label(self) -> str:
        return describe_backend(self.backend)

    @property
    def secure(self) -> bool:
        return is_secure_backend(self.backend)

    def load(self) -> str | None:
        try:
            token = self.backend.get_password(self.service, self.username)
        except KeyringError as exc:
            raise CredentialError(f"資格情報ストアを読み取れません: {exc}") from exc
        return token.strip() if token else None

    def save(self, token: str) -> None:
        token = (token or "").strip()
        if not token:
            raise CredentialError("GitHub トークンが空です")
        if any(ch.isspace() for ch in token):
            raise CredentialError("GitHub トークンに空白が含まれています")
        if not self.secure:
            raise CredentialError(
                f"安全な資格情報ストアが利用できません（{self.backend_label}）。保存を中止しました。"
            )
        try:
            self.backend.set_password(self.service, self.username, token)
        except KeyringError as exc:
            raise CredentialError(f"GitHub トークンを保存できません: {exc}") from exc

    def delete(self) -> bool:
        try:
            self.backend.delete_password(self.service, self.username)
            return True
        except PasswordDeleteError:
            return False
        except KeyringError as exc:
            raise CredentialError(f"GitHub トークンを削除できません: {exc}") from exc
