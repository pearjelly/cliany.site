"""Session 加密存储 — Fernet 对称加密 + 系统 Keychain 密钥管理

加密流程：
  1. 首次使用时自动生成 Fernet 密钥并存入系统 Keychain
  2. save_session_data() 写入前用 Fernet 加密 JSON 文本
  3. load_session_data() 读取后自动解密

密钥存储优先级：
  - keyring（macOS Keychain / Linux Secret Service / Windows Credential Locker）
  - 降级到 ~/.cliany-site/.keyfile（无 Keychain 环境下的文件密钥）
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import portalocker

from cliany_site.config import get_config
from cliany_site.errors import LOCK_TIMEOUT, SessionError

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "cliany-site"
_KEYRING_USERNAME = "session-encryption-key"
_KEYFILE_NAME = ".keyfile"

_ENCRYPTED_HEADER = b"CLIANY_ENC_V1:"


# ── 密钥管理 ─────────────────────────────────────────────


def _generate_fernet_key() -> bytes:
    """生成一个新的 Fernet 密钥"""
    from cryptography.fernet import Fernet

    return Fernet.generate_key()


def _keyfile_path() -> Path:
    return get_config().home_dir / _KEYFILE_NAME


def _load_key_from_keyring() -> bytes | None:
    """尝试从系统 Keychain 读取密钥"""
    try:
        import keyring

        stored = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if stored:
            return stored.encode("utf-8")
    except Exception:  # noqa: BLE001
        logger.debug("Keychain 不可用，将回退到文件密钥")
    return None


def _save_key_to_keyring(key: bytes) -> bool:
    """尝试将密钥存入系统 Keychain，成功返回 True"""
    try:
        import keyring

        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, key.decode("utf-8"))
        return True
    except Exception:  # noqa: BLE001
        logger.debug("无法写入 Keychain，将回退到文件密钥")
    return False


def _load_key_from_file() -> bytes | None:
    """从 ~/.cliany-site/.keyfile 读取密钥"""
    path = _keyfile_path()
    if path.exists():
        try:
            return path.read_bytes().strip()
        except OSError:
            return None
    return None


def _save_key_to_file(key: bytes) -> None:
    """将密钥写入 ~/.cliany-site/.keyfile，权限 600"""
    path = _keyfile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(path, key)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    fd, temp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def get_encryption_key() -> bytes:
    """获取加密密钥（自动生成 + 持久化）

    优先从 Keychain 获取，回退到文件密钥。首次调用自动生成密钥。
    """
    key = _load_key_from_keyring()
    if key:
        return key

    key = _load_key_from_file()
    if key:
        _save_key_to_keyring(key)
        return key

    key_path = _keyfile_path()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(str(key_path.with_suffix(".lock")), timeout=10, mode="a"):
        key = _load_key_from_keyring() or _load_key_from_file()
        if key:
            return key
        key = _generate_fernet_key()
        if not _save_key_to_keyring(key):
            _save_key_to_file(key)
    logger.info("已生成 Session 加密密钥")
    return key


def rotate_key() -> tuple[bytes, bytes]:
    """轮换密钥：生成新密钥，返回 (旧密钥, 新密钥)

    调用方需负责用旧密钥解密现有数据，再用新密钥重新加密。
    """
    old_key = get_encryption_key()
    new_key = _generate_fernet_key()
    if not _save_key_to_keyring(new_key):
        _save_key_to_file(new_key)
    logger.info("Session 加密密钥已轮换")
    return old_key, new_key


# ── 加密 / 解密 ──────────────────────────────────────────


def encrypt_data(plaintext: str, key: bytes | None = None) -> bytes:
    """用 Fernet 加密文本，返回带头标记的密文"""
    from cryptography.fernet import Fernet

    if key is None:
        key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(plaintext.encode("utf-8"))
    return _ENCRYPTED_HEADER + encrypted


def decrypt_data(raw: bytes, key: bytes | None = None) -> str:
    """解密带头标记的密文，返回明文

    Raises:
        SessionError: 解密失败（密钥不匹配 / 数据损坏）
    """
    from cryptography.fernet import Fernet, InvalidToken

    if key is None:
        key = get_encryption_key()

    if not raw.startswith(_ENCRYPTED_HEADER):
        raise SessionError("数据不是加密格式")

    token = raw[len(_ENCRYPTED_HEADER) :]
    f = Fernet(key)
    try:
        return f.decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise SessionError("Session 解密失败：密钥不匹配或数据已损坏") from exc


def is_encrypted(raw: bytes) -> bool:
    """检测数据是否为加密格式"""
    return raw.startswith(_ENCRYPTED_HEADER)


# ── Session 加密读写 ─────────────────────────────────────


def save_encrypted_session(domain: str, data: dict[str, Any]) -> str:
    """加密并保存 Session 数据，返回文件路径"""
    from datetime import UTC, datetime

    path = _session_path(domain)
    payload = {
        "domain": domain,
        "cookies": data.get("cookies", []),
        "localStorage": data.get("localStorage", {}),
        "saved_at": datetime.now(UTC).isoformat(),
        "expires_hint": data.get("expires_hint"),
    }
    plaintext = json.dumps(payload, ensure_ascii=False, indent=2)
    encrypted = encrypt_data(plaintext)
    _write_session_bytes(path, encrypted)
    logger.info("Session 已加密保存: domain=%s path=%s", domain, path)
    return str(path)


def _write_session_bytes(path: Path, encrypted: bytes) -> None:
    try:
        with portalocker.Lock(str(path.with_suffix(".lock")), timeout=10, mode="a"):
            _atomic_write_bytes(path, encrypted)
    except portalocker.LockException as exc:
        error = SessionError(f"获取 session 锁超时，请稍后重试: {exc}")
        error.error_code = LOCK_TIMEOUT
        raise error from exc


def load_encrypted_session(domain: str) -> dict[str, Any] | None:
    """加载 Session 数据（自动识别加密 / 明文格式）

    兼容旧版明文文件：如果检测到明文 JSON，正常解析后自动迁移为加密格式。
    """
    path = _session_path(domain)
    if not path.exists():
        return None

    try:
        raw = path.read_bytes()
    except OSError:
        return None

    if is_encrypted(raw):
        try:
            plaintext = decrypt_data(raw)
            result: dict[str, Any] = json.loads(plaintext)
            return result
        except (SessionError, json.JSONDecodeError) as exc:
            logger.warning("Session 解密失败: domain=%s error=%s", domain, exc)
            return None

    # 明文兼容：旧版 JSON 文件
    try:
        data: dict[str, Any] = json.loads(raw.decode("utf-8"))
        # 自动迁移为加密格式
        if _migrate_to_encrypted(domain, data, path, raw):
            return data
        return None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _migrate_to_encrypted(domain: str, data: dict[str, Any], path: Path, original: bytes) -> bool:
    """将明文 Session 文件迁移为加密格式"""
    try:
        plaintext = json.dumps(data, ensure_ascii=False, indent=2)
        encrypted = encrypt_data(plaintext)
        with portalocker.Lock(str(path.with_suffix(".lock")), timeout=10, mode="a"):
            if path.read_bytes() != original:
                return False
            _atomic_write_bytes(path, encrypted)
        logger.info("Session 已自动迁移为加密格式: domain=%s", domain)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Session 加密迁移失败，拒绝使用明文: domain=%s error=%s", domain, exc)
        return False


def _session_path(domain: str) -> Path:
    sessions_dir = get_config().sessions_dir
    sessions_dir.mkdir(parents=True, exist_ok=True)
    safe_domain = domain.replace("/", "_").replace(":", "_")
    return sessions_dir / f"{safe_domain}.json"
