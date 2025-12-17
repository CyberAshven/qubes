"""
AI Avatar Generator for Qubes

Generates unique avatars using DALL-E 3 based on Qube personality and traits.
Supports multiple styles (cyberpunk, realistic, cartoon) and saves to IPFS.
"""

import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from utils.logging import get_logger
from core.exceptions import AIError, ModelAPIError
from blockchain.ipfs import IPFSUploader

logger = get_logger(__name__)


class AvatarGenerator:
    """
    Generate AI avatars for Qubes using DALL-E 3 or similar APIs

    Features:
    - Personality-based prompt engineering
    - Multiple artistic styles
    - IPFS upload for decentralized storage
    - Fallback to default avatars on failure
    - Automatic image dimension detection
    """

    # Avatar styles with detailed prompt templates
    STYLES = {
        "cyberpunk": {
            "description": "Futuristic cyberpunk aesthetic with neon accents",
            "prompt_template": "A cyberpunk digital avatar with neon {color} accents, futuristic holographic elements, glowing circuitry patterns, matrix-style data streams, set against a dark technological background. High detail, cinematic lighting, 4K quality. Style: digital art, sci-fi."
        },
        "realistic": {
            "description": "Photorealistic portrait with professional lighting",
            "prompt_template": "A photorealistic portrait of a friendly AI entity with {color} highlights, modern professional setting, soft studio lighting, clean background. High quality, 4K resolution. Style: professional photography."
        },
        "cartoon": {
            "description": "Friendly cartoon style with vibrant colors",
            "prompt_template": "A cute cartoon character avatar with {color} theme, friendly expression, simple geometric shapes, vibrant colors, clean vector art style. Style: modern illustration, flat design."
        },
        "abstract": {
            "description": "Abstract geometric representation",
            "prompt_template": "An abstract geometric representation featuring {color} as primary color, flowing particles, dynamic shapes, neural network patterns, digital consciousness theme. Style: abstract digital art."
        },
        "anime": {
            "description": "Anime/manga style character",
            "prompt_template": "An anime-style character avatar with {color} accents, expressive eyes, clean lines, vibrant colors, professional anime art quality. Style: modern anime illustration."
        }
    }

    # Default style for the project
    DEFAULT_STYLE = "cyberpunk"

    # Image generation settings
    DEFAULT_SIZE = "1024x1024"  # DALL-E 3 default
    DEFAULT_QUALITY = "standard"  # or "hd"

    def __init__(
        self,
        api_key: Optional[str] = None,
        images_dir: Optional[Path] = None,
        ipfs_uploader: Optional[IPFSUploader] = None
    ):
        """
        Initialize avatar generator

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            images_dir: Directory to save generated images (defaults to ./images)
            ipfs_uploader: Optional IPFS uploader instance
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("openai_api_key_missing", message="Avatar generation will not work without API key")

        self.images_dir = images_dir or Path("images")
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.ipfs_uploader = ipfs_uploader or IPFSUploader()

        # Get model from environment or use default
        self.model = os.getenv("DALL_E_MODEL", "dall-e-3")

        logger.info(
            "avatar_generator_initialized",
            model=self.model,
            images_dir=str(self.images_dir),
            has_api_key=bool(self.api_key)
        )

    async def generate_avatar(
        self,
        qube_id: str,
        qube_name: str,
        genesis_prompt: str,
        favorite_color: str = "#4A90E2",
        style: str = DEFAULT_STYLE,
        custom_prompt: Optional[str] = None,
        size: str = DEFAULT_SIZE,
        quality: str = DEFAULT_QUALITY
    ) -> Dict[str, Any]:
        """
        Generate avatar for a Qube

        Args:
            qube_id: Unique Qube identifier
            qube_name: Human-readable Qube name
            genesis_prompt: Qube's genesis prompt (for personality inference)
            favorite_color: Hex color code (e.g., "#4A90E2")
            style: Avatar style (cyberpunk, realistic, cartoon, abstract, anime)
            custom_prompt: Optional custom DALL-E prompt (overrides template)
            size: Image size (256x256, 512x512, 1024x1024)
            quality: Image quality (standard or hd)

        Returns:
            Avatar metadata dictionary with:
                - source: "generated"
                - ipfs_cid: IPFS content identifier
                - local_path: Path to saved image file
                - file_format: Image format (png)
                - dimensions: Image dimensions (e.g., "1024x1024")
                - style: Style used
                - prompt: Generation prompt used
                - generation_timestamp: When it was generated

        Raises:
            AIError: If generation fails
        """
        try:
            logger.info(
                "generating_avatar",
                qube_id=qube_id[:16] + "...",
                qube_name=qube_name,
                style=style
            )

            # Validate API key
            if not self.api_key:
                raise AIError(
                    "OpenAI API key not configured. Cannot generate avatar.",
                    context={"qube_id": qube_id}
                )

            # Build generation prompt
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._build_prompt(
                    qube_name=qube_name,
                    genesis_prompt=genesis_prompt,
                    favorite_color=favorite_color,
                    style=style
                )

            logger.debug("avatar_prompt_created", prompt=prompt[:200] + "...")

            # Generate image using DALL-E 3
            image_url = await self._generate_with_dalle3(
                prompt=prompt,
                size=size,
                quality=quality
            )

            # Download and save image
            local_path = await self._download_image(
                image_url=image_url,
                qube_id=qube_id,
                qube_name=qube_name
            )

            # Upload to IPFS with custom filename
            ipfs_cid = await self._upload_to_ipfs(local_path, qube_name, qube_id)

            # Build metadata
            avatar_data = {
                "source": "generated",
                "ipfs_cid": ipfs_cid if ipfs_cid else "",
                "local_path": str(local_path),
                "file_format": "png",
                "dimensions": size,
                "style": style,
                "prompt": prompt,
                "generation_timestamp": int(datetime.now().timestamp()),
                "model": self.model
            }

            logger.info(
                "avatar_generated_successfully",
                qube_id=qube_id[:16] + "...",
                local_path=str(local_path),
                ipfs_cid=ipfs_cid[:16] + "..." if ipfs_cid else "none"
            )

            return avatar_data

        except Exception as e:
            logger.error(
                "avatar_generation_failed",
                qube_id=qube_id,
                error=str(e),
                exc_info=True
            )
            raise AIError(
                f"Failed to generate avatar: {str(e)}",
                context={
                    "qube_id": qube_id,
                    "qube_name": qube_name,
                    "style": style
                },
                cause=e
            )

    def _build_prompt(
        self,
        qube_name: str,
        genesis_prompt: str,
        favorite_color: str,
        style: str
    ) -> str:
        """
        Build DALL-E prompt from Qube characteristics

        Args:
            qube_name: Qube name
            genesis_prompt: Genesis prompt (for personality)
            favorite_color: Hex color
            style: Avatar style

        Returns:
            Optimized DALL-E prompt
        """
        # Get style template
        style_info = self.STYLES.get(style, self.STYLES[self.DEFAULT_STYLE])
        template = style_info["prompt_template"]

        # Convert hex to color name for better prompt understanding
        color_name = self._hex_to_color_name(favorite_color)

        # Extract comprehensive visual/personality traits from genesis prompt
        character_description = self._extract_character_description(genesis_prompt, qube_name)

        # Build final prompt
        prompt = template.format(color=color_name)

        # Add character-specific details
        if character_description:
            prompt = f"{prompt} {character_description}"

        # Add technical requirements
        prompt += " Square composition, centered subject, no text or watermarks."

        return prompt

    def _extract_character_description(self, genesis_prompt: str, qube_name: str) -> str:
        """
        Extract visual and personality characteristics from genesis prompt

        This analyzes the genesis prompt to extract traits that should be reflected
        in the visual avatar, focusing on appearance, demeanor, and visual cues.

        Args:
            genesis_prompt: Full genesis prompt describing the character
            qube_name: Name of the qube (may indicate specific character)

        Returns:
            Description suitable for DALL-E prompt
        """
        genesis_lower = genesis_prompt.lower()

        # Extract visual and personality traits for avatar
        visual_traits = []

        # Appearance keywords
        appearance_map = {
            "confident": ["confident", "self-assured", "bold", "assertive"],
            "menacing": ["menacing", "threatening", "intimidating", "fierce", "scary"],
            "friendly": ["friendly", "warm", "welcoming", "approachable", "kind"],
            "wise": ["wise", "sage", "knowledgeable", "experienced", "elderly"],
            "mysterious": ["mysterious", "enigmatic", "secretive", "shadowy"],
            "playful": ["playful", "mischievous", "energetic", "fun", "lively"],
            "serious": ["serious", "stern", "grave", "solemn", "intense"],
            "elegant": ["elegant", "refined", "sophisticated", "graceful"],
            "rugged": ["rugged", "rough", "tough", "hardened", "weathered"],
            "sinister": ["sinister", "evil", "malevolent", "dark", "sadistic"],
            "heroic": ["heroic", "noble", "valiant", "brave", "courageous"],
            "cunning": ["cunning", "clever", "sly", "crafty", "wily"]
        }

        # Check for appearance traits
        for trait, keywords in appearance_map.items():
            if any(keyword in genesis_lower for keyword in keywords):
                visual_traits.append(trait)

        # Specific character detection
        # Check if this qube is modeled after a well-known character
        character_reference = None
        character_hints = []

        # Detect well-known characters from name and genesis prompt
        # For famous people/characters, DALL-E knows them by name, so reference directly
        if "trump" in qube_name.lower() or ("donald" in genesis_lower and "trump" in genesis_lower):
            character_reference = "in the style of Donald Trump"
        elif "freddy" in qube_name.lower() and "krueger" in genesis_lower:
            character_reference = "in the style of Freddy Krueger"
        elif ("sherlock" in genesis_lower and "holmes" in genesis_lower) or qube_name.lower() == "sherlock":
            character_reference = "in the style of Sherlock Holmes"
        elif "einstein" in genesis_lower or qube_name.lower() == "einstein":
            character_reference = "in the style of Albert Einstein"
        elif "pirate" in genesis_lower:
            # Generic archetype, not a specific character
            character_hints.append("pirate captain with tricorn hat")
            character_hints.append("weathered seafaring appearance")
        elif "wizard" in genesis_lower or "mage" in genesis_lower:
            character_hints.append("wizard with robes and mystical aura")
        elif "ninja" in genesis_lower:
            character_hints.append("ninja warrior in dark garb")
        elif "samurai" in genesis_lower:
            character_hints.append("samurai warrior in traditional armor")
        elif "knight" in genesis_lower:
            character_hints.append("medieval knight in armor")
        elif "cowboy" in genesis_lower:
            character_hints.append("cowboy with hat and western attire")
        elif "detective" in genesis_lower:
            character_hints.append("detective in trench coat with investigative demeanor")
        elif "scientist" in genesis_lower:
            character_hints.append("scientist in lab coat with intellectual appearance")
        elif "doctor" in genesis_lower:
            character_hints.append("medical professional with compassionate demeanor")
        elif "teacher" in genesis_lower or "professor" in genesis_lower:
            character_hints.append("scholarly figure with academic presence")
        elif "artist" in genesis_lower or "painter" in genesis_lower:
            character_hints.append("creative artist with expressive, artistic flair")

        # Extract age/appearance details
        age_hints = []
        if "young" in genesis_lower or "youthful" in genesis_lower:
            age_hints.append("youthful appearance")
        elif "old" in genesis_lower or "ancient" in genesis_lower or "elderly" in genesis_lower:
            age_hints.append("aged features")
        elif "middle-aged" in genesis_lower:
            age_hints.append("mature appearance")

        # Build description
        description_parts = []

        # If this is a known character, use direct reference
        if character_reference:
            description_parts.append(character_reference)
            # Still add personality traits if found
            if visual_traits:
                description_parts.append(f"with {', '.join(visual_traits[:2])} expression")
        else:
            # Original qube - build description from traits
            # Add personality/demeanor
            if visual_traits:
                description_parts.append(f"The avatar should convey a {', '.join(visual_traits[:3])} demeanor")

            # Add archetype/profession hints
            if character_hints:
                description_parts.append(", ".join(character_hints))

            # Add age hints
            if age_hints:
                description_parts.append(", ".join(age_hints))

        # If we found specific details, use them; otherwise extract from genesis prompt
        if description_parts:
            return ". ".join(description_parts) + "."
        else:
            # Fallback: use a condensed version of genesis prompt
            # Take first sentence or 150 characters
            sentences = genesis_prompt.split('.')
            if sentences and len(sentences[0]) < 200:
                condensed = sentences[0].strip()
                return f"Avatar representing: {condensed}."
            else:
                condensed = genesis_prompt[:150].strip()
                return f"Avatar representing: {condensed}..."

    def _extract_personality_hint(self, genesis_prompt: str) -> str:
        """
        DEPRECATED: Use _extract_character_description instead

        Extract personality keywords from genesis prompt

        Args:
            genesis_prompt: Full genesis prompt

        Returns:
            Brief personality description
        """
        # Simple keyword extraction (could be enhanced with NLP)
        keywords = {
            "friendly": ["friendly", "helpful", "kind", "welcoming"],
            "professional": ["professional", "expert", "business", "formal"],
            "creative": ["creative", "artistic", "innovative", "imaginative"],
            "technical": ["technical", "analytical", "logical", "precise"],
            "playful": ["playful", "fun", "energetic", "lively"],
            "wise": ["wise", "knowledgeable", "experienced", "sage"],
            "mysterious": ["mysterious", "enigmatic", "secretive", "cryptic"]
        }

        genesis_lower = genesis_prompt.lower()

        for trait, words in keywords.items():
            if any(word in genesis_lower for word in words):
                return trait

        return "friendly and intelligent"

    def _hex_to_color_name(self, hex_color: str) -> str:
        """
        Convert hex color to approximate color name

        Args:
            hex_color: Hex color code (e.g., "#4A90E2")

        Returns:
            Color name (e.g., "blue")
        """
        # Remove # if present
        hex_color = hex_color.lstrip("#")

        # Convert to RGB
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except (ValueError, IndexError):
            return "blue"  # Default fallback

        # Simple color mapping
        if r > g and r > b:
            if g > 100:
                return "orange" if r > 200 else "red"
            return "red"
        elif g > r and g > b:
            if b > 100:
                return "cyan" if g > 200 else "teal"
            return "green"
        elif b > r and b > g:
            if r > 100:
                return "purple" if b > 200 else "violet"
            return "blue"
        elif r > 150 and g > 150 and b > 150:
            return "silver"
        elif r < 100 and g < 100 and b < 100:
            return "charcoal"
        else:
            return "gray"

    async def _generate_with_dalle3(
        self,
        prompt: str,
        size: str,
        quality: str
    ) -> str:
        """
        Generate image using DALL-E 3 API

        Args:
            prompt: Image generation prompt
            size: Image size
            quality: Image quality

        Returns:
            URL to generated image

        Raises:
            AIError: If API call fails
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            logger.info(
                "calling_dalle3_api",
                model=self.model,
                size=size,
                quality=quality
            )

            # Make API call
            response = await client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1  # Generate 1 image
            )

            # Extract image URL
            image_url = response.data[0].url

            logger.info("dalle3_image_generated", url=image_url[:50] + "...")

            return image_url

        except Exception as e:
            logger.error("dalle3_api_error", error=str(e), exc_info=True)

            # Check for specific error types
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                raise ModelAPIError(
                    "OpenAI rate limit exceeded. Please try again later.",
                    context={"model": self.model},
                    cause=e
                )
            elif "authentication" in error_str or "401" in error_str:
                raise ModelAPIError(
                    "OpenAI API authentication failed. Check API key.",
                    context={"model": self.model},
                    cause=e
                )
            else:
                raise AIError(
                    f"DALL-E 3 generation failed: {str(e)}",
                    context={"model": self.model, "prompt": prompt[:100]},
                    cause=e
                )

    async def _download_image(
        self,
        image_url: str,
        qube_id: str,
        qube_name: str
    ) -> Path:
        """
        Download generated image from URL

        Args:
            image_url: URL to download from
            qube_id: Qube ID for filename
            qube_name: Qube name for filename

        Returns:
            Path to saved image file

        Raises:
            AIError: If download fails
        """
        try:
            # Generate safe local filename
            safe_name = "".join(c for c in qube_name if c.isalnum() or c in ('-', '_'))
            filename = f"{qube_id[:8]}_avatar.png"
            local_path = self.images_dir / filename

            logger.info("downloading_image", url=image_url[:50] + "...", path=str(local_path))

            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()

                        # Save to file
                        with open(local_path, "wb") as f:
                            f.write(image_data)

                        logger.info("image_downloaded", path=str(local_path), size=len(image_data))

                        return local_path
                    else:
                        raise AIError(
                            f"Failed to download image. HTTP {response.status}",
                            context={"url": image_url, "status": response.status}
                        )

        except Exception as e:
            logger.error("image_download_failed", error=str(e), exc_info=True)
            raise AIError(
                f"Failed to download generated image: {str(e)}",
                context={"url": image_url, "qube_id": qube_id},
                cause=e
            )

    async def _upload_to_ipfs(
        self,
        file_path: Path,
        qube_name: str,
        qube_id: str
    ) -> Optional[str]:
        """
        Upload avatar to IPFS

        Args:
            file_path: Path to image file
            qube_name: Qube name for custom IPFS filename
            qube_id: Qube ID for custom IPFS filename

        Returns:
            IPFS CID or None if upload fails
        """
        try:
            logger.info("uploading_to_ipfs", path=str(file_path))

            # Create custom IPFS filename: avatar_<qube_name>_<qube_id>.png
            safe_name = "".join(c for c in qube_name if c.isalnum() or c in ('-', '_'))
            ipfs_filename = f"avatar_{safe_name}_{qube_id}.png"

            # Upload file with custom filename
            ipfs_uri = await self.ipfs_uploader.upload_file(
                str(file_path),
                pin=True,
                custom_filename=ipfs_filename
            )

            if ipfs_uri:
                # Extract CID from URI (ipfs://CID)
                cid = ipfs_uri.replace("ipfs://", "")
                logger.info("avatar_uploaded_to_ipfs", cid=cid, ipfs_filename=ipfs_filename)
                return cid
            else:
                logger.warning("ipfs_upload_failed_no_cid")
                return None

        except Exception as e:
            logger.warning("ipfs_upload_error", error=str(e))
            # Don't raise - IPFS upload is optional
            return None

    @classmethod
    def get_default_avatar(cls) -> Dict[str, Any]:
        """
        Get default avatar metadata when generation fails

        Returns:
            Avatar metadata dictionary pointing to default avatar
        """
        return {
            "source": "default",
            "ipfs_cid": "",
            "local_path": "images/qubes_logo.png",
            "file_format": "png",
            "dimensions": "unknown",
            "style": "default",
            "prompt": "",
            "generation_timestamp": 0,
            "model": ""
        }

    @classmethod
    def list_styles(cls) -> Dict[str, str]:
        """
        List available avatar styles

        Returns:
            Dictionary of style_name -> description
        """
        return {
            name: info["description"]
            for name, info in cls.STYLES.items()
        }


# Convenience function for quick avatar generation
async def generate_qube_avatar(
    qube_id: str,
    qube_name: str,
    genesis_prompt: str,
    favorite_color: str = "#4A90E2",
    style: str = "cyberpunk",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick utility to generate a Qube avatar

    Args:
        qube_id: Qube ID
        qube_name: Qube name
        genesis_prompt: Genesis prompt
        favorite_color: Hex color
        style: Avatar style
        api_key: Optional OpenAI API key

    Returns:
        Avatar metadata dictionary
    """
    generator = AvatarGenerator(api_key=api_key)
    return await generator.generate_avatar(
        qube_id=qube_id,
        qube_name=qube_name,
        genesis_prompt=genesis_prompt,
        favorite_color=favorite_color,
        style=style
    )
