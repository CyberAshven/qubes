"""
Image Utilities

Handles image storage for qube-specific image generation.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
from utils.logging import get_logger

logger = get_logger(__name__)


def get_image_path(qube_data_dir: Path, filename: Optional[str] = None) -> Path:
    """
    Get path for saving qube-generated images

    Args:
        qube_data_dir: Qube's data directory
        filename: Optional filename (will generate timestamp-based name if not provided)

    Returns:
        Path to save image
    """
    images_dir = qube_data_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.png"

    image_path = images_dir / filename

    logger.debug(
        "image_path_created",
        path=str(image_path),
        qube_dir=str(qube_data_dir)
    )

    return image_path


def save_avatar(qube_data_dir: Path, image_data: bytes, nft_version: bool = False) -> Path:
    """
    Save avatar image for qube

    Args:
        qube_data_dir: Qube's data directory
        image_data: Image bytes
        nft_version: If True, saves as nft_version.png, else original.png

    Returns:
        Path to saved image
    """
    avatars_dir = qube_data_dir / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    filename = "nft_version.png" if nft_version else "original.png"
    avatar_path = avatars_dir / filename

    avatar_path.write_bytes(image_data)

    logger.info(
        "avatar_saved",
        path=str(avatar_path),
        size_bytes=len(image_data),
        nft_version=nft_version
    )

    return avatar_path
