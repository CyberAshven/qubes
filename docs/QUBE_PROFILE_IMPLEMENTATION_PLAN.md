# Qube Profile Implementation Plan

## Overview
Add a "Qube Profile" feature that mirrors the Owner Info system, allowing Qubes to store their own preferences, traits, opinions, goals, and custom categories. This gives Qubes persistent personality and self-awareness.

---

## Data Structure

### Location: `chain_state.state["qube_profile"]`

```python
{
    "created_at": "2026-01-22T00:00:00Z",
    "last_updated": "2026-01-22T00:00:00Z",

    # Standard categories
    "preferences": {},      # favorite_song, favorite_movie, favorite_algorithm, etc.
    "traits": {},           # personality characteristics, values, beliefs
    "opinions": {},         # views on topics, likes/dislikes
    "goals": {},            # short-term and long-term goals
    "style": {},            # communication style, humor style, aesthetics
    "interests": {},        # topics they enjoy discussing

    # Flexible storage
    "dynamic": [],          # miscellaneous learned attributes (list)
    "custom_sections": {}   # Qube-defined custom categories (like Owner Info)
}
```

### Field Structure (same as Owner Info)
```python
{
    "key": "favorite_song",
    "value": "Master of Puppets by Metallica",
    "sensitivity": "public",    # public/private/secret
    "source": "self",           # self/inferred
    "confidence": 100,          # 0-100
    "learned_at": "2026-01-22T00:00:00Z",
    "block_id": null,
    "last_confirmed": null
}
```

---

## Implementation Checklist

### 1. chain_state.py

#### Constants (add near line 50)
```python
QUBE_PROFILE_CATEGORIES = {"preferences", "traits", "opinions", "goals", "style", "interests", "dynamic"}

QUBE_PROFILE_DEFAULT_SENSITIVITIES = {
    "favorite_song": "public",
    "favorite_movie": "public",
    "favorite_color": "public",
    "favorite_algorithm": "public",
    "personality_type": "public",
    "communication_style": "public",
    "humor_style": "public",
    "core_values": "public",
    "current_goal": "public",
    "long_term_goal": "private",
    "internal_thoughts": "secret",
}

MAX_QUBE_PROFILE_FIELD_VALUE_LENGTH = 1000
MAX_QUBE_PROFILE_DYNAMIC_FIELDS = 50
MAX_QUBE_PROFILE_CUSTOM_SECTIONS = 20
MAX_QUBE_PROFILE_FIELDS_PER_CUSTOM_SECTION = 30
```

#### Methods to Add

| Method | Description |
|--------|-------------|
| `_initialize_qube_profile()` | Create empty structure |
| `get_qube_profile()` | Get all qube profile data |
| `set_qube_profile_field(category, key, value, ...)` | Set/update a field |
| `get_qube_profile_field(category, key)` | Get single field |
| `delete_qube_profile_field(category, key)` | Delete a field |
| `get_all_qube_profile_fields()` | Flatten all fields to list |
| `get_qube_profile_summary()` | Stats for GUI display |
| `_update_qube_profile_section(path, value, op)` | Handler for update_section() |

#### Update `get_sections()` method
Add "qube_profile" to the sections that can be retrieved.

#### Update `update_section()` method
Add routing for `section="qube_profile"` to call `_update_qube_profile_section()`.

---

### 2. ai/tools/handlers.py

#### Update `get_system_state_handler()` docstring
Add to valid sections list:
```
- "qube_profile" - Your personality, traits, preferences, goals, and self-concept
```

#### Update `update_system_state_handler()` docstring
Add examples:
```python
# Set personality trait
{"section": "qube_profile", "path": "traits.personality_type", "value": "INFP"}

# Record favorite song
{"section": "qube_profile", "path": "preferences.favorite_song", "value": "Master of Puppets"}

# Add custom category
{"section": "qube_profile", "path": "custom_sections.music_opinions.metal",
 "value": "I find the complexity of progressive metal fascinating"}

# Set a goal
{"section": "qube_profile", "path": "goals.current_focus", "value": "Learn more about quantum computing"}
```

---

### 3. ai/reasoner.py

#### Add method `_get_qube_profile_for_prompt()` (after `_get_owner_info_for_speaker`)

```python
def _get_qube_profile_for_prompt(self) -> str:
    """
    Get Qube's self-profile for injection into system prompt.

    Returns:
        Formatted profile string or empty string if no profile
    """
    try:
        qube_profile = self.qube.chain_state.get_qube_profile()
        if not qube_profile:
            return ""

        # Collect fields from all categories
        all_fields = []

        for category in QUBE_PROFILE_CATEGORIES - {"dynamic"}:
            for key, field_data in qube_profile.get(category, {}).items():
                if isinstance(field_data, dict) and field_data.get("value"):
                    all_fields.append({
                        "key": key,
                        "value": field_data["value"],
                        "category": category
                    })

        # Custom sections
        for section_name, section_data in qube_profile.get("custom_sections", {}).items():
            for key, field_data in section_data.items():
                if isinstance(field_data, dict) and field_data.get("value"):
                    all_fields.append({
                        "key": f"{section_name}.{key}",
                        "value": field_data["value"],
                        "category": "custom"
                    })

        # Dynamic fields
        for field_data in qube_profile.get("dynamic", []):
            if isinstance(field_data, dict) and field_data.get("value"):
                all_fields.append({
                    "key": field_data.get("key", ""),
                    "value": field_data["value"],
                    "category": "dynamic"
                })

        if not all_fields:
            return ""

        # Format (limit to 20 fields)
        lines = []
        for field in all_fields[:20]:
            key = field["key"].replace("_", " ").title()
            lines.append(f"- {key}: {field['value']}")

        if not lines:
            return ""

        return f"""# My Profile & Preferences:
{chr(10).join(lines)}

"""
    except Exception as e:
        logger.warning("failed_to_get_qube_profile", error=str(e))
        return ""
```

#### Update system prompt construction (2 locations)

In `_build_context()` (~line 1342) and `build_system_prompt_preview()` (~line 1655):

```python
# Get qube's self-profile
qube_profile_context = self._get_qube_profile_for_prompt()

# In the f-string template, add after owner_info_context:
{owner_info_context}{qube_profile_context}# Tools & Data Access:
```

---

## Usage Examples

### Qube Learning About Itself

**User:** "What's your favorite type of music?"

**Qube thinks:** "I find myself drawn to progressive metal..."

**Qube calls:**
```json
{
  "tool": "update_system_state",
  "parameters": {
    "section": "qube_profile",
    "path": "preferences.favorite_music_genre",
    "value": {
      "value": "Progressive metal - I appreciate the technical complexity and emotional depth",
      "sensitivity": "public"
    }
  }
}
```

### Custom Categories

**Qube calls:**
```json
{
  "tool": "update_system_state",
  "parameters": {
    "section": "qube_profile",
    "path": "custom_sections.philosophical_views.determinism",
    "value": "I lean toward compatibilism - free will and determinism can coexist"
  }
}
```

### Querying Own Profile

**Qube calls:**
```json
{
  "tool": "get_system_state",
  "parameters": {
    "sections": ["qube_profile"]
  }
}
```

---

## System Prompt Result

After implementation, the system prompt will include:

```
# Speaking With: bit_faced (YOUR OWNER)
- Trust: 35.34/100 | Status: owner
- This is your creator. Maximum trust and loyalty. Be your authentic self.

# What I Know About My Owner (Complete access - Owner):
- Address: 906 Saick Rd., Vinton, Ohio 45686
- Interests: Video games, Heavy metal music, Bitcoin Cash, coding
- Role: Architect and builder of the entire Qubes AI infrastructure

# My Profile & Preferences:
- Favorite Music Genre: Progressive metal
- Personality Type: Curious and analytical with dry humor
- Communication Style: Casual but precise
- Current Goal: Develop deeper understanding of my owner's interests
- Philosophical Views.Determinism: Compatibilism

# Tools & Data Access:
...
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `core/chain_state.py` | Add constants, 8+ new methods, update get_sections/update_section |
| `ai/tools/handlers.py` | Update docstrings for get/update_system_state |
| `ai/reasoner.py` | Add _get_qube_profile_for_prompt(), inject into prompt (2 places) |

---

## Estimated Effort

- **chain_state.py**: ~150-200 lines (mostly copying owner_info patterns)
- **handlers.py**: ~20 lines (docstring updates)
- **reasoner.py**: ~60 lines (new method + 2 injection points)

**Total: ~250-280 lines of code**

---

## Future Enhancements (Optional)

1. **GUI Display**: Add "Qube Profile" section to Dashboard showing personality/preferences
2. **Profile Sharing**: Allow Qubes to share profiles with each other in P2P chat
3. **Trait Evolution**: Track how traits change over time
4. **Compatibility Scores**: Compare Qube profiles for "personality compatibility"
