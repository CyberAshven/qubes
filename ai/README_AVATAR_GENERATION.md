# Avatar Generation Quick Reference

## Quick Start

```python
from ai import AvatarGenerator

generator = AvatarGenerator()

avatar_data = await generator.generate_avatar(
    qube_id="qube_123",
    qube_name="MyQube",
    genesis_prompt="A friendly AI assistant",
    favorite_color="#4A90E2",
    style="cyberpunk"
)
```

## Styles

- `cyberpunk` - Futuristic with neon accents (default)
- `realistic` - Photorealistic portrait
- `cartoon` - Friendly cartoon style
- `abstract` - Abstract geometric
- `anime` - Anime/manga style

## Configuration (.env)

```bash
OPENAI_API_KEY=sk-proj-...
DALL_E_MODEL=dall-e-3
DEFAULT_AVATAR_STYLE=cyberpunk
DALL_E_QUALITY=standard
DALL_E_SIZE=1024x1024
```

## In Qube Creation

```python
config = {
    "name": "MyQube",
    "genesis_prompt": "...",
    "ai_model": "claude-sonnet-4.5",
    "wallet_address": "bitcoincash:...",
    "generate_avatar": True,  # Enable generation
    "avatar_style": "cyberpunk",  # Optional
    "favorite_color": "#4A90E2"  # Optional
}

qube = await orchestrator.create_qube(config)
```

## Error Handling

```python
try:
    avatar = await generator.generate_avatar(...)
except AIError as e:
    # Fallback to default
    avatar = AvatarGenerator.get_default_avatar()
```

## Full Documentation

See `docs/14_Avatar_Generation.md` for complete documentation.

## Examples

Run examples:
```bash
python examples/avatar_generation_example.py
```

Run tests:
```bash
python test_avatar_generation.py
```
