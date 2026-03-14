"""Secure configuration management.

Stores non-sensitive config (paths, preferences) in a gitignored local JSON file.
Sensitive values (credentials, API keys) go through macOS Keychain via the
keyring library if available.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Local config (gitignored) ─────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LOCAL_CONFIG_PATH = _PROJECT_ROOT / "config" / "local.json"

_KEYRING_SERVICE = "financial-manager"

# Lazy keyring import
_keyring_available = False
try:
    import keyring  # noqa: F401

    _keyring_available = True
except ImportError:
    pass


def _ensure_config_file() -> Path:
    """Ensure the local config file exists.

    Returns:
        Path to the config file.
    """
    _LOCAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _LOCAL_CONFIG_PATH.exists():
        _LOCAL_CONFIG_PATH.write_text("{}\n", encoding="utf-8")
    return _LOCAL_CONFIG_PATH


def get_config() -> dict[str, object]:
    """Load the local config file.

    Returns:
        The full config dict.
    """
    path = _ensure_config_file()
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[return-value]
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to read config file, returning empty config")
        return {}


def set_config(key: str, value: object) -> None:
    """Set a key in the local config file.

    Args:
        key: Config key.
        value: Config value (must be JSON-serializable).
    """
    config = get_config()
    config[key] = value
    path = _ensure_config_file()
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    logger.info("Config updated: %s", key)


def get_config_value(key: str, default: object = None) -> object:
    """Get a single config value.

    Args:
        key: Config key.
        default: Default value if key not found.

    Returns:
        The config value, or default.
    """
    return get_config().get(key, default)


# ── Document source path (convenience) ────────────────────────────────


def get_document_source_path() -> str | None:
    """Get the configured path to the tax documents folder.

    Returns:
        The filesystem path, or None if not configured.
    """
    val = get_config_value("document_source_path")
    return str(val) if val else None


def set_document_source_path(path: str) -> None:
    """Set the path to the tax documents folder.

    Args:
        path: Filesystem path to the folder (e.g., iCloud).
    """
    set_config("document_source_path", path)


# ── Keychain integration (macOS) ──────────────────────────────────────


def store_secret(key: str, value: str) -> bool:
    """Store a secret in the system keychain.

    Args:
        key: The secret identifier.
        value: The secret value.

    Returns:
        True if stored successfully, False if keyring unavailable.
    """
    if not _keyring_available:
        logger.warning("keyring not available — secret '%s' not stored", key)
        return False
    import keyring

    keyring.set_password(_KEYRING_SERVICE, key, value)
    logger.info("Secret stored in keychain: %s", key)
    return True


def get_secret(key: str) -> str | None:
    """Retrieve a secret from the system keychain.

    Args:
        key: The secret identifier.

    Returns:
        The secret value, or None if not found or keyring unavailable.
    """
    if not _keyring_available:
        logger.debug("keyring not available — cannot retrieve '%s'", key)
        return None
    import keyring

    return keyring.get_password(_KEYRING_SERVICE, key)


def delete_secret(key: str) -> bool:
    """Delete a secret from the system keychain.

    Args:
        key: The secret identifier.

    Returns:
        True if deleted, False if keyring unavailable.
    """
    if not _keyring_available:
        return False
    import keyring

    try:
        keyring.delete_password(_KEYRING_SERVICE, key)
        logger.info("Secret deleted from keychain: %s", key)
        return True
    except keyring.errors.PasswordDeleteError:
        logger.debug("Secret '%s' not found in keychain", key)
        return False
