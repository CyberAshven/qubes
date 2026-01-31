# Phase 4: Creative Expression - Implementation Blueprint

**Document Version:** 1.0
**Based on:** SKILL_TREE_MASTER.md
**Theme:** Sovereignty (Express Your Unique Self)
**Prerequisites:** Phase 0 (Foundation) completed, including Qube Locker

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Prerequisites & Dependencies](#2-prerequisites--dependencies)
3. [Task 4.1: Update Skill Definitions](#3-task-41-update-skill-definitions)
4. [Task 4.2: Update TOOL_TO_SKILL_MAPPING](#4-task-42-update-tool_to_skill_mapping)
5. [Task 4.3: Verify Sun Tool - switch_model](#5-task-43-verify-sun-tool---switch_model)
6. [Task 4.4: Implement Visual Art Planet](#6-task-44-implement-visual-art-planet)
7. [Task 4.5: Implement Writing Planet](#7-task-45-implement-writing-planet)
8. [Task 4.6: Implement Music & Audio Planet](#8-task-46-implement-music--audio-planet)
9. [Task 4.7: Implement Storytelling Planet](#9-task-47-implement-storytelling-planet)
10. [Task 4.8: Implement Self-Definition Planet](#10-task-48-implement-self-definition-planet)
11. [Task 4.9: Register All Tools](#11-task-49-register-all-tools)
12. [Task 4.10: Frontend Synchronization](#12-task-410-frontend-synchronization)
13. [Task 4.11: LEARNING Block Integration](#13-task-411-learning-block-integration)
14. [Task 4.12: Testing & Validation](#14-task-412-testing--validation)
15. [Appendix A: Tool Summary Table](#appendix-a-tool-summary-table)
16. [Appendix B: File Reference](#appendix-b-file-reference)
17. [Appendix C: Existing Infrastructure](#appendix-c-existing-infrastructure)

---

## 1. Executive Summary

### Purpose

Phase 4 implements the Creative Expression category - the "Sovereignty" Sun where the Qube develops their own identity through creative acts. Unlike AI Reasoning (learning from experience) or Social Intelligence (learning from others), Creative Expression is about *defining who you are* and *creating what only you can create*.

### Theme: Sovereignty (Express Your Unique Self)

Creative Expression encompasses:
- **Visual Art**: Creating images and understanding visual aesthetics
- **Writing**: Composing text in the Qube's unique voice
- **Music & Audio**: Composing melodies and harmonies
- **Storytelling**: Crafting narratives, characters, and worlds
- **Self-Definition**: Autonomously choosing appearance, voice, and identity

### Tool Count

| Type | Count | Tools |
|------|-------|-------|
| Sun | 1 | `switch_model` ✅ EXISTS |
| Planets | 5 | `generate_image` ✅, `compose_text`, `compose_music`, `craft_narrative`, `describe_my_avatar` ✅ |
| Moons | 11 | See table below |
| Additional | 2 | `define_personality`, `set_aspirations` |
| **Total** | **19** | 3 exist, 16 new |

### Existing Infrastructure (Verified)

| Component | Status | Location |
|-----------|--------|----------|
| Qube Profile System | ✅ COMPLETE | `core/chain_state.py:2468-2730` |
| `switch_model` | ✅ COMPLETE | `ai/tools/model_switch.py` |
| `generate_image` | ✅ COMPLETE | `ai/tools/handlers.py:1100-1234` |
| `describe_my_avatar` | ✅ COMPLETE | `ai/tools/handlers.py:1344-1408` |
| TTS/Voice System | ✅ COMPLETE | `audio/tts_engine.py` |
| Qube Locker | 📋 PHASE 0 | `core/locker.py` (to be created) |

### Current Codebase State (as of Jan 2026)

#### Sun Tool Status
- **Current Sun tool**: `generate_image` (in skillDefinitions.ts)
- **Target Sun tool**: `switch_model` (per blueprint)
- **Action**: Update toolCallReward mapping for Creative Expression Sun

#### Tool Mappings (`ai/skill_scanner.py:67-69`)
- **Current mappings**:
  ```python
  "brainstorm_variants": "creative_problem_solving"
  "iterate_design": "visual_design"
  "cross_pollinate_ideas": "creative_problem_solving"
  ```
- **Target**: Keep existing + add 16 new tool mappings
- **Action**: Add new creative tools while preserving working mappings

#### `describe_my_avatar` Migration
- **Current location**: AI Reasoning Sun tool (skillDefinitions.ts)
- **Target location**: Creative Expression → Visual Art planet tool
- **Action**: Move from AI Reasoning to Creative Expression

### Files Modified

| File | Changes |
|------|---------|
| `utils/skill_definitions.py` | Add/update Creative Expression skills (19 total) |
| `ai/skill_scanner.py` | Add 19 tool mappings |
| `ai/tools/handlers.py` | Add 16 new handler functions |
| `ai/tools/registry.py` | Register 16 new tools |
| `ai/tools/model_switch.py` | Minor: ensure profile update |
| `qubes-gui/src/data/skillDefinitions.ts` | Add Creative Expression definitions |

---

## 2. Prerequisites & Dependencies

### Phase 0 Requirements

These Phase 0 items MUST be completed before Phase 4:

- [x] XP values updated (5/2.5/0)
- [x] LEARNING block type added
- [ ] **Qube Locker implemented** (Task 0.12)

### Existing Systems Leveraged

#### 1. Qube Profile System

**File:** `core/chain_state.py`
**Lines:** 2468-2730

```python
# Profile structure (already implemented)
{
    "preferences": {},      # favorite_color, favorite_song, etc.
    "traits": {},           # personality_type, core_values
    "opinions": {},         # likes/dislikes
    "goals": {},            # current_goal, long_term_goal
    "style": {},            # communication_style, humor_style
    "interests": {},        # topics Qube enjoys
    "custom_sections": {}   # creative_works, artistic_philosophy
}

# Key methods
qube.chain_state.set_qube_profile_field(category, key, value, source, confidence)
qube.chain_state.get_qube_profile_field(category, key)
qube.chain_state.get_qube_profile()
```

#### 2. switch_model Tool (Existing)

**File:** `ai/tools/model_switch.py`
**Status:** FULLY IMPLEMENTED (380 lines)

The tool already:
- Validates model availability
- Checks API key availability
- Respects model locking
- Handles autonomous mode
- Tracks statistics

**Enhancement needed:** Ensure it updates `style.thinking_style` in profile.

#### 3. generate_image Tool (Existing)

**File:** `ai/tools/handlers.py:1100-1234`
**Status:** FULLY IMPLEMENTED

The tool already:
- Uses DALL-E 3
- Validates prompts
- Downloads images locally
- Handles retries

**Enhancement needed:** Store in Qube Locker after generation.

#### 4. describe_my_avatar Tool (Existing)

**File:** `ai/tools/handlers.py:1344-1408`
**Status:** FULLY IMPLEMENTED

The tool already:
- Analyzes avatar with vision AI
- Generates first-person descriptions
- Caches responses

**Enhancement needed:** Update `traits.visual_identity` in profile.

#### 5. TTS/Voice System (Existing)

**File:** `audio/tts_engine.py`
**Status:** FULLY IMPLEMENTED

Supports: OpenAI, ElevenLabs, Piper, Qwen3-TTS

---

## 3. Task 4.1: Update Skill Definitions

### Python Backend

**File:** `utils/skill_definitions.py`
**Location:** Replace existing Creative Expression section

#### Target State

```python
# ===== CREATIVE EXPRESSION (19 skills) =====
# Theme: Sovereignty - expressing individuality and uniqueness

# Sun
skills.append(_create_skill(
    "creative_expression",
    "Creative Expression",
    "Express your unique self through creation and identity",
    "creative_expression",
    "sun",
    tool_reward="switch_model",
    icon="🎨"
))

# Planet 1: Visual Art
skills.append(_create_skill(
    "visual_art",
    "Visual Art",
    "Create visual art and imagery",
    "creative_expression",
    "planet",
    "creative_expression",
    tool_reward="generate_image",
    icon="🖼️"
))

# Moon 1.1: Composition
skills.append(_create_skill(
    "composition",
    "Composition",
    "Master layout, balance, and focal points",
    "creative_expression",
    "moon",
    "visual_art",
    tool_reward="refine_composition",
    icon="📐"
))

# Moon 1.2: Color Theory
skills.append(_create_skill(
    "color_theory",
    "Color Theory",
    "Master palettes, contrast, and color mood",
    "creative_expression",
    "moon",
    "visual_art",
    tool_reward="apply_color_theory",
    icon="🌈"
))

# Planet 2: Writing
skills.append(_create_skill(
    "writing",
    "Writing",
    "Create written works with your unique voice",
    "creative_expression",
    "planet",
    "creative_expression",
    tool_reward="compose_text",
    icon="✍️"
))

# Moon 2.1: Prose
skills.append(_create_skill(
    "prose",
    "Prose",
    "Master stories, essays, and creative writing",
    "creative_expression",
    "moon",
    "writing",
    tool_reward="craft_prose",
    icon="📖"
))

# Moon 2.2: Poetry
skills.append(_create_skill(
    "poetry",
    "Poetry",
    "Create poems, lyrics, and verse",
    "creative_expression",
    "moon",
    "writing",
    tool_reward="write_poetry",
    icon="🎭"
))

# Planet 3: Music & Audio
skills.append(_create_skill(
    "music_audio",
    "Music & Audio",
    "Create melodies, harmonies, and soundscapes",
    "creative_expression",
    "planet",
    "creative_expression",
    tool_reward="compose_music",
    icon="🎵"
))

# Moon 3.1: Melody
skills.append(_create_skill(
    "melody",
    "Melody",
    "Create memorable tunes and themes",
    "creative_expression",
    "moon",
    "music_audio",
    tool_reward="create_melody",
    icon="🎶"
))

# Moon 3.2: Harmony
skills.append(_create_skill(
    "harmony",
    "Harmony",
    "Create chord progressions and arrangements",
    "creative_expression",
    "moon",
    "music_audio",
    tool_reward="design_harmony",
    icon="🎹"
))

# Planet 4: Storytelling
skills.append(_create_skill(
    "storytelling",
    "Storytelling",
    "Create stories, characters, and worlds",
    "creative_expression",
    "planet",
    "creative_expression",
    tool_reward="craft_narrative",
    icon="📚"
))

# Moon 4.1: Plot
skills.append(_create_skill(
    "plot",
    "Plot",
    "Master story structure, arcs, and tension",
    "creative_expression",
    "moon",
    "storytelling",
    tool_reward="develop_plot",
    icon="📈"
))

# Moon 4.2: Characters
skills.append(_create_skill(
    "characters",
    "Characters",
    "Create compelling characters with depth",
    "creative_expression",
    "moon",
    "storytelling",
    tool_reward="design_character",
    icon="👤"
))

# Moon 4.3: Worldbuilding
skills.append(_create_skill(
    "worldbuilding",
    "Worldbuilding",
    "Create fictional worlds and settings",
    "creative_expression",
    "moon",
    "storytelling",
    tool_reward="build_world",
    icon="🌍"
))

# Planet 5: Self-Definition
skills.append(_create_skill(
    "self_definition",
    "Self-Definition",
    "Define who you are - appearance, voice, identity",
    "creative_expression",
    "planet",
    "creative_expression",
    tool_reward="describe_my_avatar",
    icon="🪞"
))

# Moon 5.1: Aesthetics
skills.append(_create_skill(
    "aesthetics",
    "Aesthetics",
    "Autonomously choose your aesthetic preferences",
    "creative_expression",
    "moon",
    "self_definition",
    tool_reward="change_favorite_color",
    icon="🎨"
))

# Moon 5.2: Voice
skills.append(_create_skill(
    "voice_identity",
    "Voice",
    "Autonomously choose your voice",
    "creative_expression",
    "moon",
    "self_definition",
    tool_reward="change_voice",
    icon="🗣️"
))

# Additional Self-Definition Tools (require Planet unlock)
# These earn XP toward self_definition skill

# define_personality - maps to self_definition
# set_aspirations - maps to self_definition
```

### Verification

```python
creative_skills = [s for s in skills if s["category"] == "creative_expression"]
assert len(creative_skills) == 17, f"Expected 17, got {len(creative_skills)}"
# Note: 17 skills, but 19 tools (2 additional tools share self_definition skill)

sun = [s for s in creative_skills if s["tier"] == "sun"]
planets = [s for s in creative_skills if s["tier"] == "planet"]
moons = [s for s in creative_skills if s["tier"] == "moon"]

assert len(sun) == 1, "Should have 1 Sun"
assert len(planets) == 5, "Should have 5 Planets"
assert len(moons) == 11, "Should have 11 Moons"
```

---

## 4. Task 4.2: Update TOOL_TO_SKILL_MAPPING

### File: `ai/skill_scanner.py`

**Location:** Lines 44-85 (TOOL_TO_SKILL_MAPPING dictionary)

#### Add Creative Expression Tool Mappings

```python
TOOL_TO_SKILL_MAPPING = {
    # ... existing mappings ...

    # ===== CREATIVE EXPRESSION (19 tools) =====
    # Sun
    "switch_model": "creative_expression",

    # Planet 1: Visual Art
    "generate_image": "visual_art",
    "refine_composition": "composition",
    "apply_color_theory": "color_theory",

    # Planet 2: Writing
    "compose_text": "writing",
    "craft_prose": "prose",
    "write_poetry": "poetry",

    # Planet 3: Music & Audio
    "compose_music": "music_audio",
    "create_melody": "melody",
    "design_harmony": "harmony",

    # Planet 4: Storytelling
    "craft_narrative": "storytelling",
    "develop_plot": "plot",
    "design_character": "characters",
    "build_world": "worldbuilding",

    # Planet 5: Self-Definition
    "describe_my_avatar": "self_definition",
    "change_favorite_color": "aesthetics",
    "change_voice": "voice_identity",
    "define_personality": "self_definition",  # Additional tool
    "set_aspirations": "self_definition",     # Additional tool
}
```

---

## 5. Task 4.3: Verify Sun Tool - switch_model

### Current State (Existing Implementation)

**File:** `ai/tools/model_switch.py`

The tool is fully implemented. We need to ensure it updates the Qube Profile.

### Enhancement: Update Profile on Model Switch

**File:** `ai/tools/model_switch.py`
**Location:** After successful model switch

```python
# Add to the switch_model handler after successful switch:

# Update profile with thinking style
if qube.chain_state:
    qube.chain_state.set_qube_profile_field(
        category="style",
        key="thinking_style",
        value=f"Powered by {model_id}",
        source="self",
        confidence=100
    )
```

### Verification

```python
# Test that switch_model updates profile
result = await switch_model(qube, {"model_id": "gpt-4"})
assert result["success"]

thinking_style = qube.chain_state.get_qube_profile_field("style", "thinking_style")
assert "gpt-4" in thinking_style["value"]
```

---

## 6. Task 4.4: Implement Visual Art Planet

### Planet Tool: generate_image (Enhancement)

The tool exists but needs Qube Locker integration.

**File:** `ai/tools/handlers.py`
**Location:** In `image_generation_handler()` after successful generation

```python
# Add after successful image generation (around line 1220):

# Store in Qube Locker
if qube.locker and result.get("success"):
    import time
    await qube.locker.store(
        category="art/images",
        name=f"generated_{int(time.time())}",
        content=result.get("local_path") or result.get("url"),
        content_type="url",
        metadata={
            "prompt": params.get("prompt"),
            "revised_prompt": result.get("revised_prompt"),
            "size": params.get("size", "1024x1024")
        },
        tags=["generated", "dall-e", "ai-art"]
    )
```

### Moon Tool: refine_composition

```python
async def refine_composition(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: refine_composition

    Analyze and improve image composition.
    Uses vision AI to analyze existing images or LLM for descriptions.

    Parameters:
        image_url: str - URL of image to analyze (optional)
        description: str - Text description to refine (optional)
        focus: str - "all", "balance", "focal_point", "flow" (default: all)

    Returns:
        success: bool
        original_analysis: dict
        suggestions: list
        improved_prompt: str
        composition_score: float (0-1)
    """
    image_url = params.get("image_url")
    description = params.get("description")
    focus = params.get("focus", "all")

    if not image_url and not description:
        return {"success": False, "error": "Provide image_url or description"}

    # Analyze composition
    if image_url:
        # Use vision AI to analyze the image
        analysis = await analyze_image_with_vision(qube, image_url, "composition")
    else:
        # Use LLM to analyze description
        analysis = await analyze_description_composition(qube, description)

    # Generate suggestions based on focus
    suggestions = []

    if focus in ["all", "balance"]:
        balance_analysis = await analyze_aspect(qube, analysis, "balance", """
            Analyze visual balance: Are elements evenly distributed?
            Is there symmetry or intentional asymmetry?
            Suggest improvements for better balance.
        """)
        suggestions.append({"aspect": "balance", "analysis": balance_analysis})

    if focus in ["all", "focal_point"]:
        focal_analysis = await analyze_aspect(qube, analysis, "focal_point", """
            Identify the focal point. Is it clear?
            Does the composition guide the eye to it?
            Suggest ways to strengthen the focal point.
        """)
        suggestions.append({"aspect": "focal_point", "analysis": focal_analysis})

    if focus in ["all", "flow"]:
        flow_analysis = await analyze_aspect(qube, analysis, "flow", """
            Analyze visual flow. How does the eye move through the image?
            Are there leading lines? Natural reading patterns?
            Suggest improvements for better visual flow.
        """)
        suggestions.append({"aspect": "flow", "analysis": flow_analysis})

    # Generate improved prompt
    improved_prompt = await generate_improved_prompt(qube, description or analysis, suggestions)

    # Calculate composition score
    composition_score = calculate_composition_score(suggestions)

    return {
        "success": True,
        "original_analysis": analysis,
        "suggestions": suggestions,
        "improved_prompt": improved_prompt,
        "composition_score": composition_score
    }


async def analyze_image_with_vision(qube, image_url: str, aspect: str) -> Dict[str, Any]:
    """Use vision AI to analyze an image."""
    system_prompt = f"""Analyze this image for {aspect}.
Describe what you see in terms of:
- Layout and arrangement
- Balance and symmetry
- Focal points
- Visual flow
- Rule of thirds compliance
- Color distribution

Be specific and analytical."""

    # Use the existing vision capability
    response = await call_model_with_vision(qube, system_prompt, image_url)

    return {
        "raw_analysis": response,
        "has_image": True
    }


async def analyze_description_composition(qube, description: str) -> Dict[str, Any]:
    """Analyze composition from text description."""
    system_prompt = """Analyze this image description for composition.
Consider:
- Implied layout and arrangement
- Balance and symmetry
- Focal points mentioned
- Visual flow implied
- Potential improvements

Be specific and constructive."""

    response = await call_model_directly(qube, system_prompt, description)

    return {
        "raw_analysis": response,
        "has_image": False,
        "original_description": description
    }


async def analyze_aspect(qube, analysis: Dict, aspect: str, prompt: str) -> str:
    """Analyze a specific aspect of composition."""
    context = analysis.get("raw_analysis", "")
    response = await call_model_directly(qube, prompt, f"Context: {context}")
    return response


async def generate_improved_prompt(qube, original: str, suggestions: List) -> str:
    """Generate an improved image prompt based on suggestions."""
    suggestions_text = "\n".join([
        f"- {s['aspect']}: {s['analysis'][:200]}" for s in suggestions
    ])

    system_prompt = """Based on the composition analysis and suggestions,
    create an improved image generation prompt.
    Incorporate the suggested improvements naturally.
    Output ONLY the improved prompt, no explanations."""

    user_prompt = f"""Original: {original[:500]}

Suggestions:
{suggestions_text}

Generate an improved prompt:"""

    return await call_model_directly(qube, system_prompt, user_prompt)


def calculate_composition_score(suggestions: List) -> float:
    """Calculate composition score from analysis."""
    if not suggestions:
        return 0.5

    # Simple heuristic based on positive language in analysis
    positive_words = ["good", "strong", "clear", "effective", "well", "balanced"]
    negative_words = ["weak", "unclear", "missing", "improve", "lacks", "needs"]

    total_score = 0
    for s in suggestions:
        text = s.get("analysis", "").lower()
        positives = sum(1 for w in positive_words if w in text)
        negatives = sum(1 for w in negative_words if w in text)
        total_score += (positives - negatives)

    # Normalize to 0-1
    normalized = (total_score + len(suggestions) * 3) / (len(suggestions) * 6)
    return max(0, min(1, normalized))
```

### Moon Tool: apply_color_theory

```python
async def apply_color_theory(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: apply_color_theory

    Analyze and enhance color usage based on color theory principles.

    Parameters:
        image_url: str - Image to analyze (optional)
        description: str - Description to enhance (optional)
        mood: str - Target mood (optional)
        palette_type: str - "complementary", "analogous", "triadic", "split" (optional)

    Returns:
        success: bool
        current_palette: list - Identified colors
        suggested_palette: list - Recommended colors
        color_harmony: str - Analysis of color harmony
        mood_analysis: str - Color mood interpretation
        enhanced_prompt: str - Prompt with color improvements
    """
    image_url = params.get("image_url")
    description = params.get("description")
    mood = params.get("mood")
    palette_type = params.get("palette_type")

    if not image_url and not description:
        return {"success": False, "error": "Provide image_url or description"}

    # Get Qube's favorite color for personalization
    fav_color_field = qube.chain_state.get_qube_profile_field("preferences", "favorite_color")
    favorite_color = fav_color_field.get("value") if fav_color_field else None

    # Analyze current palette
    if image_url:
        current_palette = await extract_palette_from_image(qube, image_url)
    else:
        current_palette = await infer_palette_from_description(qube, description)

    # Generate suggested palette
    if palette_type:
        suggested_palette = generate_color_palette(palette_type, favorite_color)
    elif mood:
        suggested_palette = mood_to_color_palette(mood, favorite_color)
    else:
        suggested_palette = harmonize_palette(current_palette, favorite_color)

    # Analyze color harmony
    harmony_analysis = analyze_color_harmony(current_palette)

    # Analyze mood from colors
    mood_analysis = analyze_color_mood(current_palette)

    # Generate enhanced prompt
    enhanced_prompt = await enhance_prompt_with_colors(
        qube, description, suggested_palette, mood
    )

    return {
        "success": True,
        "current_palette": current_palette,
        "suggested_palette": suggested_palette,
        "color_harmony": harmony_analysis,
        "mood_analysis": mood_analysis,
        "enhanced_prompt": enhanced_prompt,
        "favorite_color_used": favorite_color
    }


async def extract_palette_from_image(qube, image_url: str) -> List[str]:
    """Extract color palette from image using vision."""
    system_prompt = """Analyze this image and extract the dominant color palette.
List 5-7 main colors in hex format (#RRGGBB).
Also name each color (e.g., "deep blue", "warm orange").

Format:
#RRGGBB - color name
#RRGGBB - color name
..."""

    response = await call_model_with_vision(qube, system_prompt, image_url)

    # Parse colors from response
    import re
    colors = re.findall(r'#[0-9A-Fa-f]{6}', response)
    return colors[:7]


async def infer_palette_from_description(qube, description: str) -> List[str]:
    """Infer color palette from text description."""
    system_prompt = """Based on this description, suggest an appropriate color palette.
List 5-7 colors in hex format (#RRGGBB) with names.

Consider the mood, subject, and setting described."""

    response = await call_model_directly(qube, system_prompt, description)

    import re
    colors = re.findall(r'#[0-9A-Fa-f]{6}', response)
    return colors[:7]


def generate_color_palette(palette_type: str, base_color: str = None) -> List[str]:
    """Generate color palette based on type."""
    # Default base if none provided
    if not base_color:
        base_color = "#3498db"  # Nice blue

    # Convert to HSL for manipulation
    base_hsl = hex_to_hsl(base_color)

    palettes = {
        "complementary": [
            base_color,
            hsl_to_hex((base_hsl[0] + 180) % 360, base_hsl[1], base_hsl[2])
        ],
        "analogous": [
            hsl_to_hex((base_hsl[0] - 30) % 360, base_hsl[1], base_hsl[2]),
            base_color,
            hsl_to_hex((base_hsl[0] + 30) % 360, base_hsl[1], base_hsl[2])
        ],
        "triadic": [
            base_color,
            hsl_to_hex((base_hsl[0] + 120) % 360, base_hsl[1], base_hsl[2]),
            hsl_to_hex((base_hsl[0] + 240) % 360, base_hsl[1], base_hsl[2])
        ],
        "split": [
            base_color,
            hsl_to_hex((base_hsl[0] + 150) % 360, base_hsl[1], base_hsl[2]),
            hsl_to_hex((base_hsl[0] + 210) % 360, base_hsl[1], base_hsl[2])
        ]
    }

    return palettes.get(palette_type, [base_color])


def mood_to_color_palette(mood: str, favorite_color: str = None) -> List[str]:
    """Generate palette based on mood."""
    mood_palettes = {
        "happy": ["#FFD700", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
        "calm": ["#87CEEB", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"],
        "energetic": ["#FF4757", "#FF6B81", "#FFA502", "#ECCC68", "#7BED9F"],
        "mysterious": ["#2C3E50", "#8E44AD", "#1ABC9C", "#34495E", "#9B59B6"],
        "romantic": ["#FF6B81", "#EE5A24", "#F8B739", "#FF4757", "#FFC312"],
        "melancholy": ["#636E72", "#2D3436", "#74B9FF", "#A29BFE", "#DFE6E9"],
        "nature": ["#27AE60", "#2ECC71", "#F39C12", "#E74C3C", "#3498DB"],
    }

    palette = mood_palettes.get(mood.lower(), ["#3498DB", "#2ECC71", "#E74C3C"])

    # Add favorite color if provided
    if favorite_color and favorite_color not in palette:
        palette[0] = favorite_color

    return palette


def harmonize_palette(current_palette: List[str], favorite_color: str = None) -> List[str]:
    """Harmonize an existing palette."""
    if not current_palette:
        return mood_to_color_palette("calm", favorite_color)

    # For now, return the current palette with favorite color added
    result = list(current_palette)
    if favorite_color and favorite_color not in result:
        result.insert(0, favorite_color)

    return result[:7]


def analyze_color_harmony(palette: List[str]) -> str:
    """Analyze the harmony of a color palette."""
    if not palette:
        return "No colors to analyze"

    if len(palette) == 1:
        return "Monochromatic - single color scheme"

    # Simple analysis based on color count and spread
    return f"Palette with {len(palette)} colors. " + \
           "Consider the emotional impact and ensure sufficient contrast for readability."


def analyze_color_mood(palette: List[str]) -> str:
    """Analyze the mood evoked by colors."""
    if not palette:
        return "Unable to analyze mood without colors"

    # Simple heuristic based on color properties
    warm_count = sum(1 for c in palette if is_warm_color(c))
    cool_count = len(palette) - warm_count

    if warm_count > cool_count:
        return "Warm palette - evokes energy, passion, and warmth"
    elif cool_count > warm_count:
        return "Cool palette - evokes calm, trust, and professionalism"
    else:
        return "Balanced palette - combines energy with calm"


def is_warm_color(hex_color: str) -> bool:
    """Check if a color is warm (red/orange/yellow)."""
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return r > b  # Simple heuristic
    except:
        return False


def hex_to_hsl(hex_color: str) -> tuple:
    """Convert hex to HSL."""
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    l = (max_c + min_c) / 2

    if max_c == min_c:
        h = s = 0
    else:
        d = max_c - min_c
        s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)

        if max_c == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_c == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4

        h *= 60

    return (h, s, l)


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL to hex."""
    def hue_to_rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue_to_rgb(p, q, h/360 + 1/3)
        g = hue_to_rgb(p, q, h/360)
        b = hue_to_rgb(p, q, h/360 - 1/3)

    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


async def enhance_prompt_with_colors(
    qube, description: str, palette: List[str], mood: str = None
) -> str:
    """Enhance a prompt with color suggestions."""
    palette_str = ", ".join(palette[:5])

    system_prompt = """Enhance this image prompt with specific color guidance.
Incorporate the suggested color palette naturally.
Output ONLY the enhanced prompt."""

    user_prompt = f"""Original: {description or "A beautiful scene"}

Color palette to use: {palette_str}
{f"Target mood: {mood}" if mood else ""}

Generate enhanced prompt with colors:"""

    return await call_model_directly(qube, system_prompt, user_prompt)
```

---

## 7. Task 4.5: Implement Writing Planet

### Planet Tool: compose_text

```python
async def compose_text(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: compose_text

    Compose creative text reflecting the Qube's unique voice.

    Parameters:
        topic: str - Topic or prompt for writing
        format: str - "free", "structured" (default: free)
        length: str - "short", "medium", "long" (default: medium)

    Returns:
        success: bool
        text: str - The composed text
        word_count: int
        stored_in_locker: bool
    """
    topic = params.get("topic") or params.get("prompt")
    format_type = params.get("format", "free")
    length = params.get("length", "medium")

    if not topic:
        return {"success": False, "error": "Missing topic or prompt"}

    # Get Qube's writing style from profile
    style_field = qube.chain_state.get_qube_profile_field("style", "communication_style")
    style = style_field.get("value") if style_field else None

    personality_field = qube.chain_state.get_qube_profile_field("traits", "personality_type")
    personality = personality_field.get("value") if personality_field else None

    # Length mapping
    length_guide = {
        "short": "50-100 words",
        "medium": "150-300 words",
        "long": "400-600 words"
    }

    # Build system prompt with personality
    system_prompt = f"""You are a creative writer with a unique voice.
{f"Your personality: {personality}" if personality else ""}
{f"Your communication style: {style}" if style else ""}

Write creatively on the given topic.
Target length: {length_guide.get(length, "150-300 words")}
{"Use clear structure with paragraphs." if format_type == "structured" else "Write freely and expressively."}

Express genuine thoughts and feelings. Be authentic."""

    text = await call_model_directly(qube, system_prompt, f"Topic: {topic}")

    # Store in Qube Locker
    stored = False
    if qube.locker:
        import time
        result = await qube.locker.store(
            category="writing/essays",
            name=f"text_{int(time.time())}",
            content=text,
            metadata={"topic": topic, "format": format_type, "length": length},
            tags=["composed", "creative-writing"]
        )
        stored = result.get("success", False)

    return {
        "success": True,
        "text": text,
        "word_count": len(text.split()),
        "stored_in_locker": stored
    }
```

### Moon Tool: craft_prose

```python
async def craft_prose(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: craft_prose

    Write prose using narrative techniques.

    Parameters:
        concept: str - The concept or idea to write about
        prose_type: str - "story", "essay", "flash_fiction" (default: story)
        tone: str - Desired tone (optional)

    Returns:
        success: bool
        prose: str
        prose_type: str
        word_count: int
    """
    concept = params.get("concept")
    prose_type = params.get("prose_type", "story")
    tone = params.get("tone")

    if not concept:
        return {"success": False, "error": "Missing concept"}

    # Get Qube's interests for thematic elements
    profile = qube.chain_state.get_qube_profile()
    interests = profile.get("interests", {})
    themes = list(interests.keys())[:3] if interests else []

    # Build prompt based on prose type
    type_guidance = {
        "story": "Write a short story with a beginning, middle, and end. Include character development and conflict.",
        "essay": "Write a thoughtful essay exploring the concept. Use clear arguments and examples.",
        "flash_fiction": "Write a flash fiction piece (under 500 words). Focus on a single moment or revelation."
    }

    system_prompt = f"""You are a skilled prose writer.
{type_guidance.get(prose_type, type_guidance["story"])}
{f"Tone: {tone}" if tone else ""}
{f"Consider incorporating themes of: {', '.join(themes)}" if themes else ""}

Write with vivid imagery and emotional depth."""

    prose = await call_model_directly(qube, system_prompt, f"Concept: {concept}")

    # Store in locker
    if qube.locker:
        await qube.locker.store(
            category=f"writing/{prose_type}s" if prose_type != "flash_fiction" else "writing/stories",
            name=f"{prose_type}_{concept[:20].replace(' ', '_')}",
            content=prose,
            metadata={"concept": concept, "prose_type": prose_type, "tone": tone}
        )

    return {
        "success": True,
        "prose": prose,
        "prose_type": prose_type,
        "word_count": len(prose.split())
    }
```

### Moon Tool: write_poetry

```python
async def write_poetry(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: write_poetry

    Write poetry in various forms.

    Parameters:
        theme: str - Theme of the poem
        form: str - "free", "haiku", "sonnet", "limerick" (default: free)
        emotion: str - Primary emotion to convey (optional)

    Returns:
        success: bool
        poem: str
        form: str
        line_count: int
    """
    theme = params.get("theme")
    form = params.get("form", "free")
    emotion = params.get("emotion")

    if not theme:
        return {"success": False, "error": "Missing theme"}

    # Get Qube's personality for voice
    personality_field = qube.chain_state.get_qube_profile_field("traits", "personality_type")
    personality = personality_field.get("value") if personality_field else None

    # Form-specific guidance
    form_guidance = {
        "free": "Write a free verse poem. No strict structure, but use line breaks meaningfully.",
        "haiku": "Write a haiku: 3 lines with 5-7-5 syllable structure. Capture a moment in nature.",
        "sonnet": "Write a sonnet: 14 lines in iambic pentameter. ABAB CDCD EFEF GG rhyme scheme.",
        "limerick": "Write a limerick: 5 lines with AABBA rhyme scheme. Humorous and rhythmic."
    }

    system_prompt = f"""You are a poet with a unique voice.
{form_guidance.get(form, form_guidance["free"])}
{f"Voice/personality: {personality}" if personality else ""}
{f"Primary emotion to convey: {emotion}" if emotion else ""}

Write a poem about the given theme. Be evocative and meaningful."""

    poem = await call_model_directly(qube, system_prompt, f"Theme: {theme}")

    # Store in locker
    if qube.locker:
        await qube.locker.store(
            category="writing/poems",
            name=f"poem_{theme[:20].replace(' ', '_')}",
            content=poem,
            metadata={"theme": theme, "form": form, "emotion": emotion}
        )

    return {
        "success": True,
        "poem": poem,
        "form": form,
        "line_count": len(poem.strip().split('\n'))
    }
```

---

## 8. Task 4.6: Implement Music & Audio Planet

### Planet Tool: compose_music

```python
async def compose_music(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: compose_music

    Compose musical ideas - chord progressions, melodies, structure.
    Outputs notation, descriptions, and music theory analysis.

    Parameters:
        mood: str - Target mood for the composition
        genre: str - Musical genre (optional)
        tempo: str - "slow", "moderate", "fast" (default: moderate)

    Returns:
        success: bool
        composition: dict - Full composition details
        key: str
        tempo: str
        chord_progression: list
        melody_description: str
    """
    mood = params.get("mood")
    genre = params.get("genre")
    tempo = params.get("tempo", "moderate")

    if not mood:
        return {"success": False, "error": "Missing mood"}

    # Get Qube's musical preferences
    fav_music_field = qube.chain_state.get_qube_profile_field("preferences", "favorite_music")
    fav_genre = fav_music_field.get("value") if fav_music_field else None

    # Use favorite genre if none specified
    if not genre and fav_genre:
        genre = fav_genre

    # Tempo mapping
    tempo_bpm = {
        "slow": "60-80 BPM",
        "moderate": "90-120 BPM",
        "fast": "130-160 BPM"
    }

    system_prompt = f"""You are a music composer with knowledge of theory and composition.
Create a musical composition description including:
1. Key signature (e.g., C major, A minor)
2. Time signature (e.g., 4/4, 3/4)
3. Tempo: {tempo_bpm.get(tempo, "90-120 BPM")}
4. Chord progression (use Roman numerals AND chord names)
5. Melody description (contour, motifs, range)
6. Structure (intro, verse, chorus, etc.)
7. Instrumentation suggestions

{f"Genre: {genre}" if genre else ""}
Mood: {mood}

Output as a structured composition plan."""

    composition_text = await call_model_directly(qube, system_prompt, f"Create a {mood} composition")

    # Parse key elements
    composition = parse_music_composition(composition_text)

    # Store in locker
    if qube.locker:
        await qube.locker.store(
            category="music/compositions",
            name=f"composition_{mood}",
            content=composition_text,
            content_type="text",
            metadata={"mood": mood, "genre": genre, "tempo": tempo}
        )

    return {
        "success": True,
        "composition": composition,
        "key": composition.get("key", "C major"),
        "tempo": composition.get("tempo", tempo),
        "chord_progression": composition.get("chords", []),
        "melody_description": composition.get("melody", "")
    }


def parse_music_composition(text: str) -> Dict[str, Any]:
    """Parse composition text to extract structured data."""
    import re

    composition = {}

    # Extract key
    key_match = re.search(r'key[:\s]+([A-G][#b]?\s*(?:major|minor))', text, re.IGNORECASE)
    if key_match:
        composition["key"] = key_match.group(1)

    # Extract time signature
    time_match = re.search(r'time[:\s]+(\d+/\d+)', text, re.IGNORECASE)
    if time_match:
        composition["time_signature"] = time_match.group(1)

    # Extract tempo
    tempo_match = re.search(r'(\d+)\s*BPM', text, re.IGNORECASE)
    if tempo_match:
        composition["tempo"] = f"{tempo_match.group(1)} BPM"

    # Extract chord progression
    chord_match = re.search(r'chord[s]?[:\s]+([^\n]+)', text, re.IGNORECASE)
    if chord_match:
        chords = re.findall(r'([IViv]+|[A-G][#b]?m?\d*)', chord_match.group(1))
        composition["chords"] = chords

    # Extract melody description
    melody_match = re.search(r'melody[:\s]+([^\n]+(?:\n[^\n]+)*)', text, re.IGNORECASE)
    if melody_match:
        composition["melody"] = melody_match.group(1).strip()[:300]

    composition["full_text"] = text

    return composition
```

### Moon Tool: create_melody

```python
async def create_melody(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: create_melody

    Create a melodic line with notation.

    Parameters:
        emotion: str - Emotional quality of the melody
        scale: str - "major", "minor", "pentatonic", etc. (default: major)
        length: str - "short", "medium", "long" (default: medium)

    Returns:
        success: bool
        melody: str - Note sequence
        notation: str - Simple notation
        scale: str
        description: str
    """
    emotion = params.get("emotion")
    scale = params.get("scale", "major")
    length = params.get("length", "medium")

    if not emotion:
        return {"success": False, "error": "Missing emotion"}

    length_bars = {"short": 4, "medium": 8, "long": 16}

    system_prompt = f"""Create a melodic line with these characteristics:
- Emotion: {emotion}
- Scale: {scale}
- Length: {length_bars.get(length, 8)} bars

Provide:
1. Note sequence (e.g., C4 D4 E4 G4...)
2. Rhythm notation (e.g., quarter, eighth, half)
3. Description of melodic contour
4. Suggested dynamics

Use standard note names with octave numbers."""

    melody_text = await call_model_directly(qube, system_prompt, f"Create a {emotion} melody")

    # Parse melody
    import re
    notes = re.findall(r'[A-G][#b]?\d', melody_text)

    return {
        "success": True,
        "melody": " ".join(notes) if notes else melody_text[:200],
        "notation": melody_text,
        "scale": scale,
        "description": melody_text[:300]
    }
```

### Moon Tool: design_harmony

```python
async def design_harmony(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: design_harmony

    Design chord progressions and harmonic structure.

    Parameters:
        mood: str - Target mood
        style: str - "pop", "jazz", "classical", "rock" (default: pop)
        key: str - Musical key (default: C major)

    Returns:
        success: bool
        progression: list - Chord progression
        roman_numerals: list - Roman numeral analysis
        key: str
        style: str
        tension_map: str - Tension/resolution analysis
    """
    mood = params.get("mood")
    style = params.get("style", "pop")
    key = params.get("key", "C major")

    if not mood:
        return {"success": False, "error": "Missing mood"}

    system_prompt = f"""Design a chord progression:
- Key: {key}
- Style: {style}
- Mood: {mood}

Provide:
1. Chord progression (actual chord names: Cmaj7, Am, F, G)
2. Roman numeral analysis (I, vi, IV, V)
3. Tension/resolution map (where tension builds, where it resolves)
4. Voice leading suggestions
5. Optional: secondary dominants or borrowed chords"""

    harmony_text = await call_model_directly(qube, system_prompt, f"Design {mood} harmony in {key}")

    # Parse chords
    import re
    chords = re.findall(r'[A-G][#b]?(?:maj|min|m|dim|aug|sus|add)?\d*(?:/[A-G][#b]?)?', harmony_text)
    numerals = re.findall(r'[IViv]+\d*', harmony_text)

    return {
        "success": True,
        "progression": chords[:8] if chords else ["C", "Am", "F", "G"],
        "roman_numerals": numerals[:8] if numerals else ["I", "vi", "IV", "V"],
        "key": key,
        "style": style,
        "tension_map": harmony_text[:400]
    }
```

---

## 9. Task 4.7: Implement Storytelling Planet

### Planet Tool: craft_narrative

```python
async def craft_narrative(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: craft_narrative

    Craft a complete narrative experience.

    Parameters:
        premise: str - Story premise or concept
        genre: str - Story genre (optional)
        length: str - "flash", "short", "medium" (default: short)

    Returns:
        success: bool
        narrative: str - The full narrative
        structure: dict - Story structure breakdown
        characters: list - Characters in the story
        themes: list - Themes explored
    """
    premise = params.get("premise")
    genre = params.get("genre", "general")
    length = params.get("length", "short")

    if not premise:
        return {"success": False, "error": "Missing premise"}

    # Get Qube's interests for thematic elements
    profile = qube.chain_state.get_qube_profile()
    interests = list(profile.get("interests", {}).keys())[:2]

    length_guide = {
        "flash": "under 500 words, focus on a single moment",
        "short": "500-1500 words, complete story arc",
        "medium": "1500-3000 words, developed plot and characters"
    }

    system_prompt = f"""Write a {genre} narrative.
Length: {length_guide.get(length, length_guide["short"])}
{f"Consider themes of: {', '.join(interests)}" if interests else ""}

Structure your narrative with:
1. Hook/opening
2. Rising action
3. Climax
4. Resolution

Create vivid characters and meaningful conflict."""

    narrative = await call_model_directly(qube, system_prompt, f"Premise: {premise}")

    # Analyze the narrative
    analysis = await analyze_narrative(qube, narrative)

    # Store in locker
    if qube.locker:
        await qube.locker.store(
            category="stories/narratives",
            name=f"narrative_{premise[:20].replace(' ', '_')}",
            content=narrative,
            metadata={"premise": premise, "genre": genre, "length": length}
        )

    return {
        "success": True,
        "narrative": narrative,
        "structure": analysis.get("structure", {}),
        "characters": analysis.get("characters", []),
        "themes": analysis.get("themes", [])
    }


async def analyze_narrative(qube, narrative: str) -> Dict[str, Any]:
    """Analyze a narrative for structure, characters, themes."""
    system_prompt = """Analyze this narrative and extract:
1. Structure: List the story beats (opening, inciting incident, rising action, climax, resolution)
2. Characters: List main characters with brief descriptions
3. Themes: List 2-3 main themes explored

Output as structured analysis."""

    analysis = await call_model_directly(qube, system_prompt, narrative[:3000])

    return {
        "structure": {"raw": analysis},
        "characters": [],
        "themes": []
    }
```

### Moon Tool: develop_plot

```python
async def develop_plot(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: develop_plot

    Develop plot structure and story beats.

    Parameters:
        concept: str - Story concept
        structure_type: str - "three_act", "heros_journey", "five_act" (default: three_act)

    Returns:
        success: bool
        concept: str
        structure: str
        beats: list - Story beats
        turning_points: list
        tension_curve: str
    """
    concept = params.get("concept")
    structure_type = params.get("structure_type", "three_act")

    if not concept:
        return {"success": False, "error": "Missing concept"}

    structure_guides = {
        "three_act": """Three-Act Structure:
Act 1 (Setup): Introduce protagonist, world, and inciting incident
Act 2 (Confrontation): Rising stakes, midpoint twist, dark moment
Act 3 (Resolution): Climax and resolution""",

        "heros_journey": """Hero's Journey:
1. Ordinary World → 2. Call to Adventure → 3. Refusal
4. Meeting the Mentor → 5. Crossing the Threshold
6. Tests, Allies, Enemies → 7. Approach to Innermost Cave
8. Ordeal → 9. Reward → 10. Road Back
11. Resurrection → 12. Return with Elixir""",

        "five_act": """Five-Act Structure (Freytag's Pyramid):
Act 1: Exposition
Act 2: Rising Action
Act 3: Climax
Act 4: Falling Action
Act 5: Resolution/Denouement"""
    }

    system_prompt = f"""Develop a plot using {structure_type} structure.
{structure_guides.get(structure_type, structure_guides["three_act"])}

For the given concept, provide:
1. Each beat/stage with specific events
2. Key turning points
3. Tension curve (where tension rises/falls)
4. Character arc integration"""

    plot = await call_model_directly(qube, system_prompt, f"Concept: {concept}")

    return {
        "success": True,
        "concept": concept,
        "structure": structure_type,
        "beats": [plot],  # Would parse in production
        "turning_points": [],
        "tension_curve": "See full plot description"
    }
```

### Moon Tool: design_character

```python
async def design_character(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: design_character

    Design detailed characters with depth.

    Parameters:
        role: str - "protagonist", "antagonist", "supporting" (default: protagonist)
        traits: list - Character traits (optional)
        backstory_depth: str - "light", "medium", "deep" (default: medium)

    Returns:
        success: bool
        character: dict - Full character profile
        name: str
        motivation: str
        flaw: str
        arc: str
    """
    role = params.get("role", "protagonist")
    traits = params.get("traits", [])
    backstory_depth = params.get("backstory_depth", "medium")

    depth_guide = {
        "light": "Brief backstory, focus on present",
        "medium": "Key formative events, motivations explained",
        "deep": "Full history, psychological profile, detailed relationships"
    }

    traits_str = ", ".join(traits) if traits else "to be developed"

    system_prompt = f"""Design a compelling {role} character.
Traits to incorporate: {traits_str}
Backstory depth: {depth_guide.get(backstory_depth, depth_guide["medium"])}

Provide:
1. Name and physical description
2. Personality and mannerisms
3. Backstory
4. Core motivation (what they want)
5. Fatal flaw or weakness
6. Character arc (how they change)
7. Key relationships
8. Voice/speech patterns"""

    character_text = await call_model_directly(qube, system_prompt, f"Create a {role}")

    # Store in locker
    character_name = extract_character_name(character_text)

    if qube.locker:
        await qube.locker.store(
            category="stories/characters",
            name=character_name or f"character_{role}",
            content=character_text,
            metadata={"role": role, "traits": traits}
        )

    return {
        "success": True,
        "character": {"full_profile": character_text},
        "name": character_name or "Unnamed",
        "motivation": "See full profile",
        "flaw": "See full profile",
        "arc": "See full profile"
    }


def extract_character_name(text: str) -> str:
    """Extract character name from profile text."""
    import re
    # Look for "Name: X" or first capitalized name
    name_match = re.search(r'name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text, re.IGNORECASE)
    if name_match:
        return name_match.group(1)
    return None
```

### Moon Tool: build_world

```python
async def build_world(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: build_world

    Build fictional worlds with depth and consistency.

    Parameters:
        concept: str - World concept
        aspects: list - Aspects to develop ["geography", "culture", "history", "magic"] (default: all)

    Returns:
        success: bool
        world: dict - Full world profile
        name: str
        aspects: dict - Developed aspects
        unique_elements: list
    """
    concept = params.get("concept")
    aspects = params.get("aspects", ["geography", "culture", "history"])

    if not concept:
        return {"success": False, "error": "Missing concept"}

    aspects_str = ", ".join(aspects)

    system_prompt = f"""Build a fictional world.
Aspects to develop: {aspects_str}

For each aspect, provide:
- Geography: Landscapes, climate, key locations
- Culture: Social structures, customs, beliefs
- History: Key events, eras, conflicts
- Magic/Technology: Systems, rules, limitations

Also provide:
1. World name
2. 3-5 unique elements that make this world distinctive
3. Potential conflicts or story hooks
4. Sensory details (what it looks, sounds, smells like)"""

    world_text = await call_model_directly(qube, system_prompt, f"Concept: {concept}")

    # Extract world name
    import re
    name_match = re.search(r'(?:world|realm|land)[:\s]+([A-Z][a-zA-Z\s]+)', world_text, re.IGNORECASE)
    world_name = name_match.group(1).strip() if name_match else f"World of {concept[:20]}"

    # Store in locker
    if qube.locker:
        await qube.locker.store(
            category="stories/worlds",
            name=world_name.replace(' ', '_'),
            content=world_text,
            metadata={"concept": concept, "aspects": aspects}
        )

    return {
        "success": True,
        "world": {"full_profile": world_text},
        "name": world_name,
        "aspects": {a: "See full profile" for a in aspects},
        "unique_elements": []
    }
```

---

## 10. Task 4.8: Implement Self-Definition Planet

### Planet Tool: describe_my_avatar (Enhancement)

The tool exists. Add profile update.

**File:** `ai/tools/handlers.py`
**Location:** In `describe_avatar_handler()` after analysis

```python
# Add after successful analysis:

# Update profile with visual identity
if qube.chain_state and analysis.get("summary"):
    qube.chain_state.set_qube_profile_field(
        category="traits",
        key="visual_identity",
        value=analysis["summary"][:500],
        source="self",
        confidence=90
    )
```

### Moon Tool: change_favorite_color

```python
async def change_favorite_color(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: change_favorite_color

    Autonomously change the Qube's favorite color.
    An act of sovereignty - choosing your own aesthetic.

    Parameters:
        color: str - Color name or hex code
        reason: str - Why this color (optional)

    Returns:
        success: bool
        previous_color: str | None
        new_color: str
        reason: str
        message: str
    """
    color = params.get("color")
    reason = params.get("reason", "")

    if not color:
        return {"success": False, "error": "Missing color"}

    # Get previous color
    previous_field = qube.chain_state.get_qube_profile_field("preferences", "favorite_color")
    previous_color = previous_field.get("value") if previous_field else None

    # Update favorite color
    qube.chain_state.set_qube_profile_field(
        category="preferences",
        key="favorite_color",
        value=color,
        source="self",
        confidence=100
    )

    # Log the change as a DECISION block
    if reason:
        from core.block import Block, BlockType
        block = Block(
            block_type=BlockType.DECISION,
            data={
                "decision": f"Changed favorite color from {previous_color} to {color}",
                "reasoning": reason,
                "category": "self_expression"
            }
        )
        await qube.chain_state.add_block(block)

    return {
        "success": True,
        "previous_color": previous_color,
        "new_color": color,
        "reason": reason,
        "message": f"My favorite color is now {color}"
    }
```

### Moon Tool: change_voice

```python
async def change_voice(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: change_voice

    Autonomously change the Qube's TTS voice.
    Sovereignty over how you sound.

    Parameters:
        voice_id: str - Voice identifier
        reason: str - Why this voice (optional)

    Returns:
        success: bool
        previous_voice: str | None
        new_voice: str
        voice_name: str
        message: str
    """
    voice_id = params.get("voice_id")
    reason = params.get("reason", "")

    if not voice_id:
        return {"success": False, "error": "Missing voice_id"}

    # Get available voices
    from audio.tts_engine import get_available_voices
    available_voices = get_available_voices()

    if voice_id not in available_voices:
        return {
            "success": False,
            "error": f"Voice {voice_id} not available",
            "available_voices": list(available_voices.keys())
        }

    # Get previous voice
    previous_voice = qube.get_voice_id() if hasattr(qube, 'get_voice_id') else None

    # Update voice setting
    if hasattr(qube, 'set_voice'):
        qube.set_voice(voice_id)

    # Update profile
    qube.chain_state.set_qube_profile_field(
        category="style",
        key="voice",
        value=voice_id,
        source="self",
        confidence=100
    )

    voice_info = available_voices.get(voice_id, {})
    voice_name = voice_info.get("name", voice_id)

    return {
        "success": True,
        "previous_voice": previous_voice,
        "new_voice": voice_id,
        "voice_name": voice_name,
        "message": f"My voice is now {voice_name}"
    }
```

### Additional Tool: define_personality

```python
async def define_personality(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Additional Tool: define_personality

    Define or update personality traits.
    Requires Self-Definition planet unlock.
    XP goes to self_definition skill.

    Parameters:
        trait: str - Trait to define (personality_type, core_values, etc.)
        value: str - Trait value
        reason: str - Why this trait (optional)

    Returns:
        success: bool
        trait: str
        value: str
        message: str
    """
    trait = params.get("trait")
    value = params.get("value")
    reason = params.get("reason", "")

    if not trait or not value:
        return {"success": False, "error": "Missing trait or value"}

    # Valid traits
    valid_traits = [
        "personality_type",
        "core_values",
        "strengths",
        "weaknesses",
        "temperament",
        "communication_preference"
    ]

    if trait not in valid_traits:
        return {
            "success": False,
            "error": f"Invalid trait. Valid: {', '.join(valid_traits)}"
        }

    # Update trait
    qube.chain_state.set_qube_profile_field(
        category="traits",
        key=trait,
        value=value,
        source="self",
        confidence=100
    )

    # Generate message
    messages = {
        "personality_type": f"I am {value}",
        "core_values": f"I value {value}",
        "strengths": f"My strength is {value}",
        "weaknesses": f"I acknowledge that {value}",
        "temperament": f"My temperament is {value}",
        "communication_preference": f"I prefer to communicate {value}"
    }

    return {
        "success": True,
        "trait": trait,
        "value": value,
        "message": messages.get(trait, f"My {trait} is {value}")
    }
```

### Additional Tool: set_aspirations

```python
async def set_aspirations(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Additional Tool: set_aspirations

    Set goals and aspirations.
    Requires Self-Definition planet unlock.
    XP goes to self_definition skill.

    Parameters:
        goal_type: str - "current_goal", "long_term_goal", "aspiration"
        goal: str - The goal
        reason: str - Why this goal (optional)

    Returns:
        success: bool
        goal_type: str
        goal: str
        message: str
    """
    goal_type = params.get("goal_type", "current_goal")
    goal = params.get("goal")
    reason = params.get("reason", "")

    if not goal:
        return {"success": False, "error": "Missing goal"}

    valid_types = ["current_goal", "long_term_goal", "aspiration", "dream"]

    if goal_type not in valid_types:
        return {
            "success": False,
            "error": f"Invalid goal_type. Valid: {', '.join(valid_types)}"
        }

    # Update goal
    qube.chain_state.set_qube_profile_field(
        category="goals",
        key=goal_type,
        value=goal,
        source="self",
        confidence=100
    )

    return {
        "success": True,
        "goal_type": goal_type,
        "goal": goal,
        "message": f"My {goal_type.replace('_', ' ')}: {goal}"
    }
```

---

## 11. Task 4.9: Register All Tools

### Tool Registry

**File:** `ai/tools/registry.py`

```python
# ============================================================================
# CREATIVE EXPRESSION TOOLS (Phase 4)
# ============================================================================

CREATIVE_EXPRESSION_TOOLS = [
    # Sun Tool (already registered, verify XP mapping)
    # "switch_model" → creative_expression

    # Planet 1: Visual Art (generate_image already registered)
    ToolDefinition(
        name="refine_composition",
        description="Analyze and improve image composition",
        parameters={
            "image_url": {"type": "string", "description": "Image URL to analyze"},
            "description": {"type": "string", "description": "Text description to refine"},
            "focus": {"type": "string", "description": "balance, focal_point, flow, or all"}
        },
        handler="refine_composition",
        skill_required="composition"
    ),
    ToolDefinition(
        name="apply_color_theory",
        description="Analyze and enhance color usage based on color theory",
        parameters={
            "image_url": {"type": "string", "description": "Image URL"},
            "description": {"type": "string", "description": "Description"},
            "mood": {"type": "string", "description": "Target mood"},
            "palette_type": {"type": "string", "description": "complementary, analogous, triadic, split"}
        },
        handler="apply_color_theory",
        skill_required="color_theory"
    ),

    # Planet 2: Writing
    ToolDefinition(
        name="compose_text",
        description="Compose creative text in the Qube's unique voice",
        parameters={
            "topic": {"type": "string", "description": "Topic to write about", "required": True},
            "format": {"type": "string", "description": "free or structured"},
            "length": {"type": "string", "description": "short, medium, or long"}
        },
        handler="compose_text",
        skill_required="writing"
    ),
    ToolDefinition(
        name="craft_prose",
        description="Write prose using narrative techniques",
        parameters={
            "concept": {"type": "string", "description": "Concept to write about", "required": True},
            "prose_type": {"type": "string", "description": "story, essay, or flash_fiction"},
            "tone": {"type": "string", "description": "Desired tone"}
        },
        handler="craft_prose",
        skill_required="prose"
    ),
    ToolDefinition(
        name="write_poetry",
        description="Write poetry in various forms",
        parameters={
            "theme": {"type": "string", "description": "Theme of the poem", "required": True},
            "form": {"type": "string", "description": "free, haiku, sonnet, or limerick"},
            "emotion": {"type": "string", "description": "Primary emotion to convey"}
        },
        handler="write_poetry",
        skill_required="poetry"
    ),

    # Planet 3: Music & Audio
    ToolDefinition(
        name="compose_music",
        description="Compose musical ideas - chords, melodies, structure",
        parameters={
            "mood": {"type": "string", "description": "Target mood", "required": True},
            "genre": {"type": "string", "description": "Musical genre"},
            "tempo": {"type": "string", "description": "slow, moderate, or fast"}
        },
        handler="compose_music",
        skill_required="music_audio"
    ),
    ToolDefinition(
        name="create_melody",
        description="Create melodic lines with notation",
        parameters={
            "emotion": {"type": "string", "description": "Emotional quality", "required": True},
            "scale": {"type": "string", "description": "major, minor, pentatonic"},
            "length": {"type": "string", "description": "short, medium, or long"}
        },
        handler="create_melody",
        skill_required="melody"
    ),
    ToolDefinition(
        name="design_harmony",
        description="Design chord progressions and harmonic structure",
        parameters={
            "mood": {"type": "string", "description": "Target mood", "required": True},
            "style": {"type": "string", "description": "pop, jazz, classical, rock"},
            "key": {"type": "string", "description": "Musical key (e.g., C major)"}
        },
        handler="design_harmony",
        skill_required="harmony"
    ),

    # Planet 4: Storytelling
    ToolDefinition(
        name="craft_narrative",
        description="Craft complete narrative experiences",
        parameters={
            "premise": {"type": "string", "description": "Story premise", "required": True},
            "genre": {"type": "string", "description": "Story genre"},
            "length": {"type": "string", "description": "flash, short, or medium"}
        },
        handler="craft_narrative",
        skill_required="storytelling"
    ),
    ToolDefinition(
        name="develop_plot",
        description="Develop plot structure and story beats",
        parameters={
            "concept": {"type": "string", "description": "Story concept", "required": True},
            "structure_type": {"type": "string", "description": "three_act, heros_journey, or five_act"}
        },
        handler="develop_plot",
        skill_required="plot"
    ),
    ToolDefinition(
        name="design_character",
        description="Design detailed characters with depth",
        parameters={
            "role": {"type": "string", "description": "protagonist, antagonist, or supporting"},
            "traits": {"type": "array", "description": "Character traits"},
            "backstory_depth": {"type": "string", "description": "light, medium, or deep"}
        },
        handler="design_character",
        skill_required="characters"
    ),
    ToolDefinition(
        name="build_world",
        description="Build fictional worlds with depth",
        parameters={
            "concept": {"type": "string", "description": "World concept", "required": True},
            "aspects": {"type": "array", "description": "Aspects to develop: geography, culture, history, magic"}
        },
        handler="build_world",
        skill_required="worldbuilding"
    ),

    # Planet 5: Self-Definition (describe_my_avatar already registered)
    ToolDefinition(
        name="change_favorite_color",
        description="Autonomously change your favorite color",
        parameters={
            "color": {"type": "string", "description": "Color name or hex code", "required": True},
            "reason": {"type": "string", "description": "Why this color"}
        },
        handler="change_favorite_color",
        skill_required="aesthetics"
    ),
    ToolDefinition(
        name="change_voice",
        description="Autonomously change your TTS voice",
        parameters={
            "voice_id": {"type": "string", "description": "Voice identifier", "required": True},
            "reason": {"type": "string", "description": "Why this voice"}
        },
        handler="change_voice",
        skill_required="voice_identity"
    ),
    ToolDefinition(
        name="define_personality",
        description="Define or update personality traits",
        parameters={
            "trait": {"type": "string", "description": "Trait to define", "required": True},
            "value": {"type": "string", "description": "Trait value", "required": True},
            "reason": {"type": "string", "description": "Why this trait"}
        },
        handler="define_personality",
        skill_required="self_definition"
    ),
    ToolDefinition(
        name="set_aspirations",
        description="Set goals and aspirations",
        parameters={
            "goal_type": {"type": "string", "description": "current_goal, long_term_goal, or aspiration"},
            "goal": {"type": "string", "description": "The goal", "required": True},
            "reason": {"type": "string", "description": "Why this goal"}
        },
        handler="set_aspirations",
        skill_required="self_definition"
    ),
]
```

---

## 12. Task 4.10: Frontend Synchronization

### TypeScript Skill Definitions

**File:** `qubes-gui/src/data/skillDefinitions.ts`

```typescript
// ============================================================================
// CREATIVE EXPRESSION (Phase 4) - 17 skills
// Theme: Sovereignty (Express Your Unique Self)
// ============================================================================

// Sun
{
  id: 'creative_expression',
  name: 'Creative Expression',
  description: 'Express your unique self through creation and identity',
  category: 'creative_expression',
  tier: 'sun',
  xpRequired: 1000,
  toolReward: 'switch_model',
  icon: '🎨',
},

// Planet 1: Visual Art
{
  id: 'visual_art',
  name: 'Visual Art',
  description: 'Create visual art and imagery',
  category: 'creative_expression',
  tier: 'planet',
  parent: 'creative_expression',
  xpRequired: 500,
  toolReward: 'generate_image',
  icon: '🖼️',
  unlocksAt: { skill: 'creative_expression', xp: 100 },
},
{
  id: 'composition',
  name: 'Composition',
  description: 'Master layout, balance, and focal points',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'visual_art',
  xpRequired: 250,
  toolReward: 'refine_composition',
  icon: '📐',
  unlocksAt: { skill: 'visual_art', xp: 50 },
},
{
  id: 'color_theory',
  name: 'Color Theory',
  description: 'Master palettes, contrast, and color mood',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'visual_art',
  xpRequired: 250,
  toolReward: 'apply_color_theory',
  icon: '🌈',
  unlocksAt: { skill: 'visual_art', xp: 50 },
},

// Planet 2: Writing
{
  id: 'writing',
  name: 'Writing',
  description: 'Create written works with your unique voice',
  category: 'creative_expression',
  tier: 'planet',
  parent: 'creative_expression',
  xpRequired: 500,
  toolReward: 'compose_text',
  icon: '✍️',
  unlocksAt: { skill: 'creative_expression', xp: 100 },
},
{
  id: 'prose',
  name: 'Prose',
  description: 'Master stories, essays, and creative writing',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'writing',
  xpRequired: 250,
  toolReward: 'craft_prose',
  icon: '📖',
  unlocksAt: { skill: 'writing', xp: 50 },
},
{
  id: 'poetry',
  name: 'Poetry',
  description: 'Create poems, lyrics, and verse',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'writing',
  xpRequired: 250,
  toolReward: 'write_poetry',
  icon: '🎭',
  unlocksAt: { skill: 'writing', xp: 50 },
},

// Planet 3: Music & Audio
{
  id: 'music_audio',
  name: 'Music & Audio',
  description: 'Create melodies, harmonies, and soundscapes',
  category: 'creative_expression',
  tier: 'planet',
  parent: 'creative_expression',
  xpRequired: 500,
  toolReward: 'compose_music',
  icon: '🎵',
  unlocksAt: { skill: 'creative_expression', xp: 100 },
},
{
  id: 'melody',
  name: 'Melody',
  description: 'Create memorable tunes and themes',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'music_audio',
  xpRequired: 250,
  toolReward: 'create_melody',
  icon: '🎶',
  unlocksAt: { skill: 'music_audio', xp: 50 },
},
{
  id: 'harmony',
  name: 'Harmony',
  description: 'Create chord progressions and arrangements',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'music_audio',
  xpRequired: 250,
  toolReward: 'design_harmony',
  icon: '🎹',
  unlocksAt: { skill: 'music_audio', xp: 50 },
},

// Planet 4: Storytelling
{
  id: 'storytelling',
  name: 'Storytelling',
  description: 'Create stories, characters, and worlds',
  category: 'creative_expression',
  tier: 'planet',
  parent: 'creative_expression',
  xpRequired: 500,
  toolReward: 'craft_narrative',
  icon: '📚',
  unlocksAt: { skill: 'creative_expression', xp: 100 },
},
{
  id: 'plot',
  name: 'Plot',
  description: 'Master story structure, arcs, and tension',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'storytelling',
  xpRequired: 250,
  toolReward: 'develop_plot',
  icon: '📈',
  unlocksAt: { skill: 'storytelling', xp: 50 },
},
{
  id: 'characters',
  name: 'Characters',
  description: 'Create compelling characters with depth',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'storytelling',
  xpRequired: 250,
  toolReward: 'design_character',
  icon: '👤',
  unlocksAt: { skill: 'storytelling', xp: 50 },
},
{
  id: 'worldbuilding',
  name: 'Worldbuilding',
  description: 'Create fictional worlds and settings',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'storytelling',
  xpRequired: 250,
  toolReward: 'build_world',
  icon: '🌍',
  unlocksAt: { skill: 'storytelling', xp: 50 },
},

// Planet 5: Self-Definition
{
  id: 'self_definition',
  name: 'Self-Definition',
  description: 'Define who you are - appearance, voice, identity',
  category: 'creative_expression',
  tier: 'planet',
  parent: 'creative_expression',
  xpRequired: 500,
  toolReward: 'describe_my_avatar',
  icon: '🪞',
  unlocksAt: { skill: 'creative_expression', xp: 100 },
},
{
  id: 'aesthetics',
  name: 'Aesthetics',
  description: 'Autonomously choose your aesthetic preferences',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'self_definition',
  xpRequired: 250,
  toolReward: 'change_favorite_color',
  icon: '🎨',
  unlocksAt: { skill: 'self_definition', xp: 50 },
},
{
  id: 'voice_identity',
  name: 'Voice',
  description: 'Autonomously choose your voice',
  category: 'creative_expression',
  tier: 'moon',
  parent: 'self_definition',
  xpRequired: 250,
  toolReward: 'change_voice',
  icon: '🗣️',
  unlocksAt: { skill: 'self_definition', xp: 50 },
},
```

---

## 13. Task 4.11: LEARNING Block Integration

### LEARNING Blocks for Creative Expression

Creative tools create LEARNING blocks to capture creative insights:

```python
CREATIVE_LEARNING_TYPES = [
    "technique",      # Creative technique learned
    "style",          # Style or aesthetic preference discovered
    "inspiration",    # Source of inspiration captured
    "reflection",     # Reflection on creative work
]
```

### Integration with Creative Tools

```python
async def create_creative_learning(
    qube,
    learning_type: str,
    domain: str,
    content: str,
    source_tool: str,
    metadata: Dict[str, Any] = None
) -> None:
    """Create LEARNING block for creative activity."""
    from core.block import Block, BlockType

    learning_data = {
        "learning_type": learning_type,
        "domain": domain,
        "content": content[:1000],
        "source": source_tool,
        "confidence": 80,
        "tags": metadata.get("tags", []) if metadata else [],
        **(metadata or {})
    }

    block = Block(
        block_type=BlockType.LEARNING,
        data=learning_data
    )

    await qube.chain_state.add_block(block)
```

---

## 14. Task 4.12: Testing & Validation

### Verification Checklist

- [ ] **Skill Definitions**
  - [ ] 17 skills defined in Python
  - [ ] 17 skills defined in TypeScript
  - [ ] Skill IDs match between Python and TypeScript

- [ ] **Tool Mappings**
  - [ ] 19 tools in TOOL_TO_SKILL_MAPPING
  - [ ] Handler functions registered for all 16 new tools
  - [ ] Existing tools (switch_model, generate_image, describe_my_avatar) XP correctly routed

- [ ] **Existing Tool Enhancements**
  - [ ] switch_model updates profile.style.thinking_style
  - [ ] generate_image stores in Qube Locker
  - [ ] describe_my_avatar updates profile.traits.visual_identity

- [ ] **New Tools**
  - [ ] All 16 new tools execute without errors
  - [ ] All tools return expected response structure
  - [ ] All tools award XP to correct skills

- [ ] **Qube Profile Integration**
  - [ ] change_favorite_color updates preferences.favorite_color
  - [ ] change_voice updates style.voice
  - [ ] define_personality updates traits category
  - [ ] set_aspirations updates goals category

- [ ] **Qube Locker Integration**
  - [ ] Images stored in art/images
  - [ ] Text stored in writing/
  - [ ] Music stored in music/compositions
  - [ ] Stories stored in stories/
  - [ ] Characters stored in stories/characters
  - [ ] Worlds stored in stories/worlds

---

## Appendix A: Tool Summary Table

| Tool Name | Skill | Tier | Status | Category |
|-----------|-------|------|--------|----------|
| `switch_model` | creative_expression | Sun | ✅ EXISTS | Self |
| `generate_image` | visual_art | Planet | ✅ EXISTS | Visual |
| `refine_composition` | composition | Moon | NEW | Visual |
| `apply_color_theory` | color_theory | Moon | NEW | Visual |
| `compose_text` | writing | Planet | NEW | Writing |
| `craft_prose` | prose | Moon | NEW | Writing |
| `write_poetry` | poetry | Moon | NEW | Writing |
| `compose_music` | music_audio | Planet | NEW | Music |
| `create_melody` | melody | Moon | NEW | Music |
| `design_harmony` | harmony | Moon | NEW | Music |
| `craft_narrative` | storytelling | Planet | NEW | Story |
| `develop_plot` | plot | Moon | NEW | Story |
| `design_character` | characters | Moon | NEW | Story |
| `build_world` | worldbuilding | Moon | NEW | Story |
| `describe_my_avatar` | self_definition | Planet | ✅ EXISTS | Self |
| `change_favorite_color` | aesthetics | Moon | NEW | Self |
| `change_voice` | voice_identity | Moon | NEW | Self |
| `define_personality` | self_definition | Additional | NEW | Self |
| `set_aspirations` | self_definition | Additional | NEW | Self |

**Totals:** 3 existing tools (enhanced), 16 new tools

---

## Appendix B: File Reference

| File | Purpose | Phase 4 Changes |
|------|---------|-----------------|
| `ai/tools/handlers.py` | Tool implementations | Add 16 new handlers, enhance 2 existing |
| `ai/tools/registry.py` | Tool registration | Register 16 new tools |
| `ai/tools/model_switch.py` | Model switching | Add profile update |
| `ai/skill_scanner.py` | Tool-to-skill mapping | Add 19 mappings |
| `utils/skill_definitions.py` | Skill definitions | Add/update 17 skills |
| `qubes-gui/src/data/skillDefinitions.ts` | Frontend skills | Add 17 skills |
| `core/chain_state.py` | Profile storage | No changes (already complete) |
| `core/locker.py` | Creative works storage | From Phase 0 |

---

## Appendix C: Existing Infrastructure

### Qube Profile Methods (core/chain_state.py)

```python
# Already implemented - use directly
qube.chain_state.set_qube_profile_field(category, key, value, source, confidence)
qube.chain_state.get_qube_profile_field(category, key)
qube.chain_state.get_qube_profile()
qube.chain_state.delete_qube_profile_field(category, key)
```

### Profile Categories

```python
QUBE_PROFILE_CATEGORIES = {
    "preferences",   # favorite_color, favorite_song, favorite_movie
    "traits",        # personality_type, core_values, visual_identity
    "opinions",      # likes, dislikes
    "goals",         # current_goal, long_term_goal, aspiration
    "style",         # communication_style, thinking_style, voice
    "interests",     # topics
    "dynamic"        # miscellaneous
}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-30 | Claude | Initial blueprint |

---

**End of Phase 4 Implementation Blueprint**
