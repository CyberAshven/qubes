"""
Platform-aware path utilities for Qubes.

Handles proper data directory location across platforms:
- Windows: %APPDATA%/Qubes or relative ./data if dev mode
- macOS: ~/Library/Application Support/Qubes or relative ./data if dev mode
- Linux: $XDG_DATA_HOME/Qubes or ~/.local/share/Qubes or relative ./data if dev mode

For AppImage on Linux, this is critical because the AppImage mounts as read-only
at /tmp/.mount_QubesXXX/ - we must use a user-writable location.
"""

import os
import sys
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

# App name used in paths
APP_NAME = "Qubes"


def is_bundled_app() -> bool:
    """
    Check if we're running as a bundled application (PyInstaller, AppImage, etc.)
    vs running from source during development.
    """
    # PyInstaller sets this attribute
    if getattr(sys, 'frozen', False):
        return True

    # Check for AppImage environment
    if os.environ.get('APPIMAGE'):
        return True

    # Check if running from a typical bundle location
    exe_path = Path(sys.executable)

    # On macOS, check if we're in an .app bundle
    if '.app/Contents/MacOS' in str(exe_path):
        return True

    return False


def is_dev_mode() -> bool:
    """Check if running in development mode."""
    # If gui_bridge.py exists in the current directory, we're in dev mode
    if Path("gui_bridge.py").exists():
        return True

    # Check for common dev indicators
    if os.environ.get('QUBES_DEV_MODE'):
        return True

    return False


@lru_cache(maxsize=1)
def get_app_data_dir() -> Path:
    """
    Get the appropriate application data directory for the current platform.

    Returns a Path that is guaranteed to be writable (creates it if needed).

    Platform locations:
    - Windows: %APPDATA%/Qubes
    - macOS: ~/Library/Application Support/Qubes
    - Linux: $XDG_DATA_HOME/Qubes or ~/.local/share/Qubes

    In development mode (running from source), uses ./data relative to project.
    """
    bundled = is_bundled_app()
    dev_mode = is_dev_mode()

    # Log path resolution for debugging
    logger.debug(
        f"get_app_data_dir: platform={sys.platform}, bundled={bundled}, "
        f"dev_mode={dev_mode}, frozen={getattr(sys, 'frozen', False)}, "
        f"APPIMAGE={os.environ.get('APPIMAGE', 'not set')}"
    )

    # In dev mode, use relative path
    if dev_mode and not bundled:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        logger.debug(f"get_app_data_dir: using dev mode path: {data_dir.resolve()}")
        return data_dir.resolve()

    # Bundled app - use platform-appropriate location
    platform = sys.platform

    if platform == 'win32':
        # Windows: Use LOCALAPPDATA/Qubes/data to match existing installs
        # (Tauri installs the app to LOCALAPPDATA, and old versions stored data there)
        localappdata = os.environ.get('LOCALAPPDATA')
        if localappdata:
            data_dir = Path(localappdata) / APP_NAME / 'data'
        else:
            # Fallback to user home
            data_dir = Path.home() / 'AppData' / 'Local' / APP_NAME / 'data'

    elif platform == 'darwin':
        # macOS: Use Application Support
        data_dir = Path.home() / 'Library' / 'Application Support' / APP_NAME

    else:
        # Linux and other Unix: Use XDG_DATA_HOME or default
        xdg_data = os.environ.get('XDG_DATA_HOME')
        if xdg_data:
            data_dir = Path(xdg_data) / APP_NAME
        else:
            data_dir = Path.home() / '.local' / 'share' / APP_NAME

    logger.info(f"get_app_data_dir: using platform path: {data_dir}")

    # Create the directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir


def get_users_dir() -> Path:
    """Get the users data directory."""
    return get_app_data_dir() / "users"


def get_user_data_dir(user_id: str) -> Path:
    """Get data directory for a specific user."""
    user_dir = get_users_dir() / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_user_qubes_dir(user_id: str) -> Path:
    """Get qubes directory for a specific user."""
    qubes_dir = get_user_data_dir(user_id) / "qubes"
    qubes_dir.mkdir(parents=True, exist_ok=True)
    return qubes_dir


def get_cache_dir() -> Path:
    """
    Get the appropriate cache directory for the current platform.

    Platform locations:
    - Windows: %LOCALAPPDATA%/Qubes/cache
    - macOS: ~/Library/Caches/Qubes
    - Linux: $XDG_CACHE_HOME/Qubes or ~/.cache/Qubes
    """
    platform = sys.platform

    if platform == 'win32':
        local_appdata = os.environ.get('LOCALAPPDATA')
        if local_appdata:
            cache_dir = Path(local_appdata) / APP_NAME / 'cache'
        else:
            cache_dir = Path.home() / 'AppData' / 'Local' / APP_NAME / 'cache'

    elif platform == 'darwin':
        cache_dir = Path.home() / 'Library' / 'Caches' / APP_NAME

    else:
        xdg_cache = os.environ.get('XDG_CACHE_HOME')
        if xdg_cache:
            cache_dir = Path(xdg_cache) / APP_NAME
        else:
            cache_dir = Path.home() / '.cache' / APP_NAME

    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_config_dir() -> Path:
    """
    Get the appropriate config directory for the current platform.

    Platform locations:
    - Windows: %APPDATA%/Qubes (same as data)
    - macOS: ~/Library/Application Support/Qubes (same as data)
    - Linux: $XDG_CONFIG_HOME/Qubes or ~/.config/Qubes
    """
    platform = sys.platform

    if platform == 'win32' or platform == 'darwin':
        # On Windows and macOS, config goes with data
        return get_app_data_dir()

    else:
        # Linux: Use XDG_CONFIG_HOME
        xdg_config = os.environ.get('XDG_CONFIG_HOME')
        if xdg_config:
            config_dir = Path(xdg_config) / APP_NAME
        else:
            config_dir = Path.home() / '.config' / APP_NAME

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir


# For backwards compatibility - convert relative "data" paths
def migrate_relative_path(relative_path: Path | str) -> Path:
    """
    Convert a relative path like "data/users/xxx" to the proper platform path.

    This helps migrate code that uses hardcoded "data/" paths.
    """
    relative_path = Path(relative_path)

    # If it's absolute, return as-is
    if relative_path.is_absolute():
        return relative_path

    # If it starts with "data", replace with app data dir
    parts = relative_path.parts
    if parts and parts[0] == 'data':
        # Replace "data" with the actual app data directory
        new_path = get_app_data_dir().joinpath(*parts[1:])
        return new_path

    # Otherwise, return relative to app data dir
    return get_app_data_dir() / relative_path
