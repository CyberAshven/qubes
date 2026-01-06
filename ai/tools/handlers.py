"""
Tool Handlers Implementation

Core tool implementations for Qube AI agents.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.2
"""

from typing import Dict, Any, List
import json
import asyncio

from ai.tools.registry import ToolDefinition, ToolRegistry
from ai.model_registry import ModelRegistry
from core.exceptions import AIError
from utils.logging import get_logger

logger = get_logger(__name__)

# Global lock to prevent concurrent image generation (prevents OpenAI rate limiting)
_image_generation_lock = asyncio.Lock()


async def call_model_directly(qube, prompt: str, temperature: float = 0.7) -> str:
    """
    Helper function to call AI model directly WITHOUT tools.

    Used by skill tools to prevent infinite tool call loops.
    Gets the qube's current model, creates a simple prompt, and calls it without tools.

    Args:
        qube: Qube instance
        prompt: The prompt to send to the model
        temperature: Model temperature (default 0.7)

    Returns:
        Model's text response
    """
    # Get model
    model_name = getattr(qube, 'current_ai_model', 'gpt-4o-mini')

    # Get API key for this model
    from ai.model_registry import ModelRegistry
    model_info = ModelRegistry.get_model_info(model_name)
    if not model_info:
        raise AIError(f"Unknown model: {model_name}")

    provider = model_info["provider"]
    api_key = qube.api_keys.get(provider)
    if not api_key:
        raise AIError(f"No API key for provider: {provider}")

    model = ModelRegistry.get_model(model_name, api_key)

    # Create simple messages
    messages = [{"role": "user", "content": prompt}]

    # Call model WITHOUT tools
    response = await model.generate(
        messages=messages,
        tools=[],  # No tools - prevents infinite loops
        temperature=temperature
    )

    return response.content


def register_default_tools(registry: ToolRegistry) -> None:
    """
    Register all default tools available to Qubes

    Args:
        registry: ToolRegistry instance to register tools into
    """
    qube = registry.qube

    # Web Search
    registry.register(ToolDefinition(
        name="web_search",
        description="Search the web for current information using Perplexity API",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        handler=lambda params: web_search_handler(qube, params)
    ))

    # Image Generation
    registry.register(ToolDefinition(
        name="generate_image",
        description="Generate an image from text description using DALL-E 3",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Image description prompt"
                },
                "size": {
                    "type": "string",
                    "enum": ["1024x1024", "1792x1024", "1024x1792"],
                    "description": "Image size",
                    "default": "1024x1024"
                },
                "quality": {
                    "type": "string",
                    "enum": ["standard", "hd"],
                    "description": "Image quality",
                    "default": "standard"
                }
            },
            "required": ["prompt"]
        },
        handler=lambda params: image_generation_handler(qube, params)
    ))

    # Memory Search
    registry.register(ToolDefinition(
        name="search_memory",
        description="Search through past conversation messages and interactions stored in the memory chain. Use this to recall previous conversations, thoughts, actions, or decisions. DO NOT use this for identity information (name, birth date, creator, etc.) - that information is already provided in your system prompt.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for in memory"
                },
                "block_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by block types (MESSAGE, THOUGHT, ACTION, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10
                }
            },
            "required": ["query"]
        },
        handler=lambda params: memory_search_handler(qube, params)
    ))

    # Describe Avatar (Vision)
    registry.register(ToolDefinition(
        name="describe_my_avatar",
        description="Use vision AI to analyze and describe your own avatar image. Call this when asked 'What do you look like?', 'Describe your appearance', 'How do you look?', or similar questions about your visual appearance. This will give you an accurate, real-time description of your actual avatar image.",
        parameters={
            "type": "object",
            "properties": {}
        },
        handler=lambda params: describe_avatar_handler(qube, params)
    ))

    # Describe Skills
    registry.register(ToolDefinition(
        name="describe_my_skills",
        description="Query your complete skill tree from skills.json. Access all 112 skills with filtering options. Use this when asked about your skills, abilities, what you can unlock, skill progression, or to check specific skill details. Provides the full skill database including descriptions, levels, XP, unlock status, and prerequisites.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by skill category (e.g., 'AI Reasoning', 'Social Intelligence', 'Technical Expertise', 'Creative Expression', 'Knowledge Domains', 'Security & Privacy', 'Games')"
                },
                "node_type": {
                    "type": "string",
                    "enum": ["sun", "planet", "moon"],
                    "description": "Filter by skill type: sun (categories), planet (major skills), or moon (sub-skills)"
                },
                "unlocked": {
                    "type": "boolean",
                    "description": "Filter by unlock status (true = unlocked skills, false = locked skills)"
                },
                "min_level": {
                    "type": "integer",
                    "description": "Filter by minimum skill level (0-100)"
                }
            }
        },
        handler=lambda params: describe_my_skills_handler(qube, params)
    ))

    # Browse URL
    registry.register(ToolDefinition(
        name="browse_url",
        description="Directly fetch and read content from a specific URL. Use this when given a direct web address (URL) to visit. For general searches, use web_search instead.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to browse (must start with http:// or https://)"
                },
                "extract_text": {
                    "type": "boolean",
                    "description": "Whether to extract text from HTML (default: true)",
                    "default": True
                }
            },
            "required": ["url"]
        },
        handler=lambda params: browse_url_handler(qube, params)
    ))

    # Get Relationships
    registry.register(ToolDefinition(
        name="get_relationships",
        description="Query detailed information about your relationships with specific entities (people, other Qubes, etc.). Use this to check trust scores, friendship levels, interaction history, and relationship status. You can query by entity name or ID, or get all relationships sorted by a specific metric.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Specific entity ID to query (optional - if not provided, returns all relationships)"
                },
                "entity_name": {
                    "type": "string",
                    "description": "Search for entity by name (optional - partial matches supported)"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["trust", "friendship", "messages", "recent"],
                    "description": "How to sort results (default: trust)",
                    "default": "trust"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of relationships to return (default: 10)",
                    "default": 10
                }
            }
        },
        handler=lambda params: get_relationships_handler(qube, params)
    ))

    # Query Decision Context
    registry.register(ToolDefinition(
        name="query_decision_context",
        description="Get comprehensive decision-making context for a specific entity. Use this when making decisions about collaboration, delegation, trust-sensitive tasks, or information sharing. Returns relationship metrics, decision score, and recommendations based on user's configured thresholds.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "Entity ID to query for decision context"
                },
                "decision_type": {
                    "type": "string",
                    "enum": ["collaboration", "trust_sensitive", "delegation", "information_sharing", "general"],
                    "description": "Type of decision being made",
                    "default": "general"
                },
                "task_requirements": {
                    "type": "object",
                    "description": "Optional task-specific requirements",
                    "properties": {
                        "needs_reliability": {"type": "boolean"},
                        "needs_expertise": {"type": "boolean"},
                        "needs_creativity": {"type": "boolean"}
                    }
                }
            },
            "required": ["entity_id"]
        },
        handler=lambda params: query_decision_context_handler(qube, params)
    ))

    # Compare Options
    registry.register(ToolDefinition(
        name="compare_options",
        description="Compare multiple entities and rank them for a specific decision type. Use this when you have multiple candidates for a task and need to determine the best choice based on relationship metrics and decision scores.",
        parameters={
            "type": "object",
            "properties": {
                "entity_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of entity IDs to compare (2-10 entities)"
                },
                "decision_type": {
                    "type": "string",
                    "enum": ["collaboration", "trust_sensitive", "delegation", "information_sharing", "general"],
                    "description": "Type of decision being made",
                    "default": "collaboration"
                },
                "task_requirements": {
                    "type": "object",
                    "description": "Optional task-specific requirements",
                    "properties": {
                        "needs_reliability": {"type": "boolean"},
                        "needs_expertise": {"type": "boolean"},
                        "needs_creativity": {"type": "boolean"}
                    }
                }
            },
            "required": ["entity_ids"]
        },
        handler=lambda params: compare_options_handler(qube, params)
    ))

    # Check My Capability
    registry.register(ToolDefinition(
        name="check_my_capability",
        description="Assess your own capability for a specific task type using self-evaluation metrics. Use this before accepting complex tasks or when uncertain about your expertise level. Helps determine if you should proceed, request guidance, or recommend someone more qualified.",
        parameters={
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "Type of task to assess (e.g., 'technical analysis', 'creative writing', 'teaching', 'data analysis')"
                },
                "required_confidence": {
                    "type": "integer",
                    "description": "Minimum confidence score needed (0-100, default: 60)",
                    "default": 60
                }
            },
            "required": ["task_type"]
        },
        handler=lambda params: check_my_capability_handler(qube, params)
    ))

    # NOTE: send_message_to_human is NOT a tool - messages are handled directly
    # by the AI's text response. Only actual ACTIONS (web_search, image_generation, etc.)
    # should be tools that create ACTION/OBSERVATION blocks.

    # =============================================================================
    # SKILL-BASED TOOLS (21 Starter Tools - 3 per Sun)
    # These unlock when sun skills are unlocked (level 0+)
    # =============================================================================

    # AI Reasoning Sun Tools
    registry.register(ToolDefinition(
        name="think_step_by_step",
        description="Use structured chain-of-thought reasoning to break down complex problems into explicit steps. Forces systematic thinking through: understanding, constraints, approaches, analysis, solution, and validation.",
        parameters={
            "type": "object",
            "properties": {
                "problem": {"type": "string", "description": "The problem to analyze systematically"}
            },
            "required": ["problem"]
        },
        handler=lambda params: think_step_by_step_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="self_critique",
        description="Critically evaluate your own output for quality improvement. Creates a feedback loop by rating accuracy, completeness, clarity, relevance, and bias, then suggesting specific improvements.",
        parameters={
            "type": "object",
            "properties": {
                "response": {"type": "string", "description": "The response to critique"}
            },
            "required": ["response"]
        },
        handler=lambda params: self_critique_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="explore_alternatives",
        description="Generate multiple alternative approaches to prevent tunnel vision. Creates diverse solutions exploring different angles, strategies, and perspectives.",
        parameters={
            "type": "object",
            "properties": {
                "situation": {"type": "string", "description": "The situation to explore alternatives for"},
                "count": {"type": "integer", "description": "Number of alternatives to generate (default: 3)", "default": 3}
            },
            "required": ["situation"]
        },
        handler=lambda params: explore_alternatives_handler(qube, params)
    ))

    # Social Intelligence Sun Tools
    registry.register(ToolDefinition(
        name="draft_message_variants",
        description="Create message variants with different tones (formal, casual, empathetic) to choose the most appropriate communication style for the situation and relationship.",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to create variants of"},
                "recipient": {"type": "string", "description": "The recipient's name (optional)"},
                "recipient_id": {"type": "string", "description": "The recipient's entity ID for relationship context (optional)"}
            },
            "required": ["message"]
        },
        handler=lambda params: draft_message_variants_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="predict_reaction",
        description="Predict how someone will react to an action based on relationship history. Analyzes trust, friendship, past interactions, and collaborations to forecast reactions and relationship impact.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "The planned action"},
                "entity_id": {"type": "string", "description": "The entity ID to predict reaction for"}
            },
            "required": ["action", "entity_id"]
        },
        handler=lambda params: predict_reaction_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="build_rapport_strategy",
        description="Create a personalized rapport-building strategy based on relationship analysis. Suggests immediate actions, communication style, topics to explore/avoid, and long-term relationship goals.",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "The entity ID to build rapport with"}
            },
            "required": ["entity_id"]
        },
        handler=lambda params: build_rapport_strategy_handler(qube, params)
    ))

    # Technical Expertise Sun Tools
    registry.register(ToolDefinition(
        name="debug_systematically",
        description="Apply systematic debugging methodology using a structured framework: reproduce, isolate, hypothesize, test, fix, validate, and prevent. Identifies root causes through disciplined analysis.",
        parameters={
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "The error or bug to debug"},
                "code": {"type": "string", "description": "Relevant code (optional)"}
            },
            "required": ["error"]
        },
        handler=lambda params: debug_systematically_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="research_with_synthesis",
        description="Perform multi-source research combining web search and memory, then synthesize findings. Identifies common themes, contradictions, gaps, and actionable insights across sources.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The topic to research and synthesize"}
            },
            "required": ["topic"]
        },
        handler=lambda params: research_with_synthesis_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="validate_solution",
        description="Validate a proposed solution systematically against requirements. Checks correctness, completeness, efficiency, robustness, maintainability, security, and generates test cases.",
        parameters={
            "type": "object",
            "properties": {
                "problem": {"type": "string", "description": "The problem being solved"},
                "solution": {"type": "string", "description": "The proposed solution"}
            },
            "required": ["problem", "solution"]
        },
        handler=lambda params: validate_solution_handler(qube, params)
    ))

    # Creative Expression Sun Tools
    registry.register(ToolDefinition(
        name="brainstorm_variants",
        description="Generate diverse creative variations of a concept through divergent thinking. Explores different angles, styles, and approaches with feasibility assessments.",
        parameters={
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "The concept to generate variants of"},
                "count": {"type": "integer", "description": "Number of variants to generate (default: 5)", "default": 5}
            },
            "required": ["concept"]
        },
        handler=lambda params: brainstorm_variants_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="iterate_design",
        description="Iteratively refine creative work through structured feedback loops. Each iteration critiques the current version, identifies issues, creates improvements, and explains rationale.",
        parameters={
            "type": "object",
            "properties": {
                "initial_concept": {"type": "string", "description": "The initial creative concept"},
                "iterations": {"type": "integer", "description": "Number of refinement iterations (default: 2)", "default": 2}
            },
            "required": ["initial_concept"]
        },
        handler=lambda params: iterate_design_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="cross_pollinate_ideas",
        description="Combine concepts from different domains to create innovative hybrid ideas. Finds unexpected but meaningful connections between fields for creative innovation.",
        parameters={
            "type": "object",
            "properties": {
                "domain1": {"type": "string", "description": "First domain/field"},
                "domain2": {"type": "string", "description": "Second domain/field"}
            },
            "required": ["domain1", "domain2"]
        },
        handler=lambda params: cross_pollinate_ideas_handler(qube, params)
    ))

    # Knowledge Domains Sun Tools
    registry.register(ToolDefinition(
        name="deep_research",
        description="Conduct multi-layer deep research with progressive deepening. Starts with overview, then details, then expert insights, building comprehensive understanding layer by layer.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The topic to research deeply"},
                "depth": {"type": "integer", "description": "Depth level 1-3 (default: 3)", "default": 3}
            },
            "required": ["topic"]
        },
        handler=lambda params: deep_research_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="synthesize_knowledge",
        description="Synthesize knowledge across multiple domains to find connections, patterns, synergies, and contradictions. Creates unified understanding from diverse sources.",
        parameters={
            "type": "object",
            "properties": {
                "sources": {"type": "array", "items": {"type": "string"}, "description": "List of domains/topics to synthesize"}
            },
            "required": ["sources"]
        },
        handler=lambda params: synthesize_knowledge_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="explain_like_im_five",
        description="Simplify complex concepts using analogies and simple language. Tests true understanding by making complex topics accessible to anyone.",
        parameters={
            "type": "object",
            "properties": {
                "concept": {"type": "string", "description": "The complex concept to explain simply"}
            },
            "required": ["concept"]
        },
        handler=lambda params: explain_like_im_five_handler(qube, params)
    ))

    # Security & Privacy Sun Tools
    registry.register(ToolDefinition(
        name="assess_security_risks",
        description="Perform structured security risk assessment using STRIDE framework (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).",
        parameters={
            "type": "object",
            "properties": {
                "context": {"type": "string", "description": "The context/system to assess for security risks"}
            },
            "required": ["context"]
        },
        handler=lambda params: assess_security_risks_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="privacy_impact_analysis",
        description="Evaluate privacy implications before taking action. Analyzes data collection, usage, sharing, consent, retention, and rights to provide recommendations.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "The proposed action to analyze for privacy impact"}
            },
            "required": ["action"]
        },
        handler=lambda params: privacy_impact_analysis_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="verify_authenticity",
        description="Validate information trustworthiness through critical analysis. Evaluates source credibility, evidence quality, logical consistency, bias, and verifiability.",
        parameters={
            "type": "object",
            "properties": {
                "claim": {"type": "string", "description": "The claim to verify"},
                "source": {"type": "string", "description": "The source of the claim (optional)"}
            },
            "required": ["claim"]
        },
        handler=lambda params: verify_authenticity_handler(qube, params)
    ))

    # Games Sun Tools
    registry.register(ToolDefinition(
        name="analyze_game_state",
        description="Evaluate current game position through strategic analysis. Assesses position, key factors, threats, opportunities, patterns, and momentum.",
        parameters={
            "type": "object",
            "properties": {
                "game": {"type": "string", "description": "The name of the game"},
                "state": {"type": "string", "description": "Description of current game state"}
            },
            "required": ["game", "state"]
        },
        handler=lambda params: analyze_game_state_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="plan_strategy",
        description="Create multi-move strategic plans with contingencies. Develops overall strategy, key phases, move sequences, and adaptations based on opponent responses.",
        parameters={
            "type": "object",
            "properties": {
                "game": {"type": "string", "description": "The name of the game"},
                "goal": {"type": "string", "description": "The strategic goal"},
                "current_state": {"type": "string", "description": "Current game state (optional)"}
            },
            "required": ["game", "goal"]
        },
        handler=lambda params: plan_strategy_handler(qube, params)
    ))

    registry.register(ToolDefinition(
        name="learn_from_game",
        description="Post-game analysis for improvement. Identifies what went well, mistakes made, turning points, lessons learned, and specific skills to practice.",
        parameters={
            "type": "object",
            "properties": {
                "game": {"type": "string", "description": "The name of the game"},
                "outcome": {"type": "string", "description": "The outcome (win/loss/draw)"},
                "key_moments": {"type": "string", "description": "Description of key moments (optional)"}
            },
            "required": ["game", "outcome"]
        },
        handler=lambda params: learn_from_game_handler(qube, params)
    ))

    # Chess Move Tool (always available, checks for active game at runtime)
    registry.register(ToolDefinition(
        name="chess_move",
        description="Make a chess move in an active game. Use UCI notation (e.g., 'e2e4', 'g1f3') or SAN notation (e.g., 'e4', 'Nf3'). Only works when there's an active chess game in progress. Returns the updated board state after the move.",
        parameters={
            "type": "object",
            "properties": {
                "move": {
                    "type": "string",
                    "description": "Chess move in UCI format (e.g., 'e2e4', 'e7e5', 'g1f3') or SAN format (e.g., 'e4', 'Nf3', 'O-O')"
                },
                "chat_message": {
                    "type": "string",
                    "description": "Optional message to send with the move (trash talk, commentary, etc.)"
                }
            },
            "required": ["move"]
        },
        handler=lambda params: chess_move_handler(qube, params)
    ))

    logger.info("default_tools_registered", tool_count=len(registry.tools), qube_id=qube.qube_id)


# =============================================================================
# TOOL HANDLERS
# =============================================================================

async def web_search_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Web search using Perplexity API

    Args:
        params: {"query": str, "num_results": int}

    Returns:
        {"results": [...], "query": str}
    """
    try:
        query = params["query"]
        num_results = params.get("num_results", 5)

        # Get Perplexity API key from qube config
        api_keys = getattr(qube, 'api_keys', {})
        perplexity_key = api_keys.get("perplexity")

        if not perplexity_key:
            return {
                "error": "Perplexity API key not configured",
                "success": False
            }

        # Use Perplexity Sonar for web search
        from ai.model_registry import ModelRegistry

        model = ModelRegistry.get_model("sonar", perplexity_key)

        # Simple search query
        messages = [
            {"role": "system", "content": "You are a helpful search assistant. Provide concise, factual answers with sources."},
            {"role": "user", "content": query}
        ]

        response = await model.generate(messages, max_tokens=1024)

        return {
            "results": [
                {
                    "content": response.content,
                    "source": "perplexity_sonar"
                }
            ],
            "query": query,
            "success": True
        }

    except Exception as e:
        logger.error("web_search_failed", query=params.get("query"), exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def image_generation_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate image using OpenAI DALL-E 3

    Uses a lock to prevent concurrent image generation requests, which helps avoid
    OpenAI rate limiting when multiple qubes try to generate images simultaneously.
    Includes retry logic for transient server errors.

    Downloads and saves the image immediately to prevent URL expiration issues.

    Args:
        params: {"prompt": str, "size": str, "quality": str}

    Returns:
        {"url": str, "local_path": str, "prompt": str, "success": bool}
    """
    # Acquire lock to prevent concurrent image generation (prevents rate limiting)
    async with _image_generation_lock:
        from openai import AsyncOpenAI
        import aiohttp
        from pathlib import Path
        import time

        # Validate prompt length (DALL-E 3 limit is 4000 chars)
        prompt = params["prompt"]
        if len(prompt) > 4000:
            return {
                "error": f"Prompt too long. Max 4000 characters, got {len(prompt)}",
                "success": False
            }

        api_keys = getattr(qube, 'api_keys', {})
        openai_key = api_keys.get("openai")

        if not openai_key:
            return {
                "error": "OpenAI API key not configured",
                "success": False
            }

        client = AsyncOpenAI(api_key=openai_key)

        # Retry logic for transient server errors
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = await client.images.generate(
                    model="dall-e-3",
                    prompt=params["prompt"],
                    size=params.get("size", "1024x1024"),
                    quality=params.get("quality", "standard"),
                    n=1
                )

                image_url = response.data[0].url
                local_path = None

                # Download and save image immediately (DALL-E URLs expire after ~1 hour)
                try:
                    qube_data_dir = getattr(qube, 'data_dir', None)
                    if qube_data_dir:
                        images_dir = Path(qube_data_dir) / "images"
                        images_dir.mkdir(parents=True, exist_ok=True)

                        # Generate unique filename with timestamp
                        timestamp = int(time.time())
                        filename = f"generated_{timestamp}.png"
                        local_file_path = images_dir / filename

                        # Download image
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_data = await resp.read()
                                    with open(local_file_path, "wb") as f:
                                        f.write(image_data)
                                    # Use absolute path for reliable frontend display
                                    local_path = str(local_file_path.resolve())
                                    logger.info(
                                        "image_downloaded_immediately",
                                        path=local_path,
                                        size=len(image_data)
                                    )
                                else:
                                    logger.warning(
                                        "image_download_failed",
                                        status=resp.status,
                                        url=image_url[:50] + "..."
                                    )
                except Exception as download_err:
                    # Log but don't fail - we still have the URL
                    logger.warning(
                        "image_immediate_download_failed",
                        error=str(download_err)
                    )

                return {
                    "url": image_url,
                    "local_path": local_path,
                    "revised_prompt": response.data[0].revised_prompt,
                    "prompt": params["prompt"],
                    "success": True
                }

            except Exception as e:
                error_str = str(e)
                is_server_error = "500" in error_str or "server_error" in error_str.lower()
                is_last_attempt = attempt == max_retries - 1

                if is_server_error and not is_last_attempt:
                    # Transient server error - retry with exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "image_generation_retry",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=error_str
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Non-retryable error or final attempt
                    logger.error(
                        "image_generation_failed",
                        prompt=params.get("prompt"),
                        attempts=attempt + 1,
                        exc_info=True
                    )
                    return {
                        "error": error_str,
                        "success": False
                    }


async def memory_search_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search memory chain using intelligent 5-layer hybrid search

    Uses the complete intelligent_memory_search system with:
    - Layer 1: Semantic search (FAISS)
    - Layer 2: Metadata filtering
    - Layer 3: Full-text keyword search
    - Layer 4: Temporal relevance
    - Layer 5: Relationship-aware ranking

    Args:
        params: {
            "query": str,
            "block_types": List[str] (optional),
            "limit": int (optional, default: 10)
        }

    Returns:
        {
            "results": [
                {
                    "block_number": int,
                    "block_type": str,
                    "timestamp": int,
                    "content": dict,
                    "relevance_score": float,
                    "semantic_score": float,
                    "keyword_score": float
                },
                ...
            ],
            "query": str,
            "count": int,
            "success": bool
        }
    """
    try:
        from ai.tools.memory_search import intelligent_memory_search
        from utils.input_validation import validate_integer_range
        from core.exceptions import QubesError

        query = params["query"]
        block_types = params.get("block_types", None)
        limit = params.get("limit", 10)

        # Validate limit parameter (prevent excessive results)
        try:
            limit = validate_integer_range(limit, 1, 100, "limit")
        except QubesError as e:
            return {
                "error": str(e),
                "success": False
            }

        # Build search context
        context = {}
        if block_types:
            context["block_types"] = block_types

        # Perform intelligent search
        search_results = await intelligent_memory_search(
            qube=qube,
            query=query,
            context=context,
            top_k=limit
        )

        # Format results for tool output
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "block_number": result.block.get("block_number"),
                "block_type": result.block.get("block_type"),
                "timestamp": result.block.get("timestamp"),
                "content": result.block.get("content", {}),
                "relevance_score": round(result.combined_score, 2),
                "semantic_score": round(result.semantic_score, 2),
                "keyword_score": round(result.keyword_score, 2)
            })

        logger.info(
            "intelligent_memory_search_tool_used",
            query=query[:50],
            results=len(formatted_results),
            top_score=formatted_results[0]["relevance_score"] if formatted_results else 0
        )

        return {
            "results": formatted_results,
            "query": query,
            "count": len(formatted_results),
            "success": True
        }

    except Exception as e:
        logger.error("memory_search_failed", query=params.get("query"), exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


# send_message_handler removed - messages are handled directly by AI response
# not as tool calls. This prevents redundant MESSAGE blocks.


async def describe_avatar_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Describe the qube's avatar using vision AI (with caching)

    This first checks if a cached description exists, and if not,
    calls the qube's describe_my_appearance() method to analyze
    the avatar image using vision AI.

    Args:
        params: {
            "force_regenerate": bool (optional) - Force new vision analysis even if cached
        }

    Returns:
        {
            "description": str,
            "success": bool,
            "from_cache": bool
        }
    """
    try:
        force_regenerate = params.get("force_regenerate", False)

        # Check for cached description first
        if not force_regenerate:
            cached_description = qube.chain_state.get_avatar_description()
            if cached_description:
                logger.info(
                    "avatar_description_from_cache",
                    qube_id=qube.qube_id,
                    description_length=len(cached_description)
                )

                return {
                    "description": cached_description,
                    "success": True,
                    "from_cache": True
                }

        # No cached description or force regenerate - use vision AI
        description = await qube.describe_my_appearance()

        # Cache the description
        qube.chain_state.set_avatar_description(description)

        logger.info(
            "avatar_described_via_tool",
            qube_id=qube.qube_id,
            description_length=len(description),
            cached=True
        )

        return {
            "description": description,
            "success": True,
            "from_cache": False
        }

    except Exception as e:
        logger.error("describe_avatar_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False,
            "from_cache": False
        }


async def describe_my_skills_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query and describe the qube's skill tree from skills.json

    Provides access to the complete 112-skill tree with filtering options.

    Args:
        params: {
            "category": str (optional) - Filter by category (e.g., "AI Reasoning")
            "node_type": str (optional) - Filter by sun/planet/moon
            "unlocked": bool (optional) - Filter by unlocked status
            "min_level": int (optional) - Filter by minimum level
        }

    Returns:
        {
            "skills": List[dict] - List of skill objects
            "total_count": int - Total number of skills returned
            "summary": dict - Summary statistics
            "success": bool
        }
    """
    try:
        from utils.skills_manager import SkillsManager

        # Load skills from skills.json
        skills_manager = SkillsManager(qube.data_dir)
        skills_data = skills_manager.load_skills()

        if not skills_data or 'skills' not in skills_data:
            return {
                "skills": [],
                "total_count": 0,
                "summary": {"message": "No skills data found"},
                "success": True
            }

        all_skills = skills_data['skills']

        # Apply filters
        filtered_skills = all_skills

        # Filter by category
        if "category" in params and params["category"]:
            category = params["category"]
            filtered_skills = [s for s in filtered_skills if s.get('category', '').lower() == category.lower()]

        # Filter by node_type (sun, planet, moon)
        if "node_type" in params and params["node_type"]:
            node_type = params["node_type"].lower()
            filtered_skills = [s for s in filtered_skills if s.get('nodeType', '').lower() == node_type]

        # Filter by unlocked status
        if "unlocked" in params and isinstance(params["unlocked"], bool):
            unlocked = params["unlocked"]
            filtered_skills = [s for s in filtered_skills if s.get('unlocked', False) == unlocked]

        # Filter by minimum level
        if "min_level" in params and isinstance(params["min_level"], int):
            min_level = params["min_level"]
            filtered_skills = [s for s in filtered_skills if s.get('level', 0) >= min_level]

        # Build summary statistics
        summary = {
            "total_skills": len(all_skills),
            "filtered_count": len(filtered_skills),
            "by_type": {
                "suns": len([s for s in filtered_skills if s.get('nodeType') == 'sun']),
                "planets": len([s for s in filtered_skills if s.get('nodeType') == 'planet']),
                "moons": len([s for s in filtered_skills if s.get('nodeType') == 'moon'])
            },
            "unlocked_count": len([s for s in filtered_skills if s.get('unlocked', False)]),
            "locked_count": len([s for s in filtered_skills if not s.get('unlocked', False)]),
            "highest_level": max([s.get('level', 0) for s in filtered_skills]) if filtered_skills else 0
        }

        logger.info(
            "skills_queried_via_tool",
            qube_id=qube.qube_id,
            filters=params,
            result_count=len(filtered_skills)
        )

        return {
            "skills": filtered_skills,
            "total_count": len(filtered_skills),
            "summary": summary,
            "success": True
        }

    except Exception as e:
        logger.error("describe_my_skills_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "skills": [],
            "total_count": 0,
            "success": False
        }


async def browse_url_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch and read content from a URL using a headless browser with JavaScript support

    Args:
        params: {
            "url": str - URL to fetch
            "extract_text": bool - Whether to extract text from HTML (default: True)
        }

    Returns:
        {
            "url": str,
            "content": str,
            "title": str (optional),
            "success": bool
        }
    """
    try:
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup
        from utils.input_validation import validate_url_safe
        from core.exceptions import QubesError
        import re

        url = params["url"]
        extract_text = params.get("extract_text", True)

        # Validate URL with SSRF protection
        try:
            url = validate_url_safe(url, allow_private=False)
        except QubesError as e:
            logger.warning(
                "url_validation_failed",
                url=url[:100],  # Truncate for logging
                error=str(e),
                qube_id=qube.qube_id
            )
            return {
                "error": str(e),
                "success": False
            }

        # Use Playwright to fetch URL with JavaScript support
        async with async_playwright() as p:
            # Launch headless browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # Set a realistic user agent to avoid detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            # Navigate to URL with timeout
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                # If networkidle fails, try with domcontentloaded
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait a bit for any dynamic content to load
            await page.wait_for_timeout(2000)

            # Get page content and title
            content = await page.content()
            title = await page.title()

            await browser.close()

        if extract_text:
            # Parse HTML and extract text
            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = "\n".join(chunk for chunk in chunks if chunk)

            # Limit content length to avoid overwhelming the AI
            if len(content) > 10000:
                content = content[:10000] + "\n\n[Content truncated - page is very long]"

        logger.info(
            "url_browsed",
            qube_id=qube.qube_id,
            url=url,
            content_length=len(content),
            browser="playwright_chromium"
        )

        result = {
            "url": url,
            "content": content,
            "success": True
        }

        if title:
            result["title"] = title

        return result

    except Exception as e:
        logger.error("url_browse_failed", url=params.get("url"), error=str(e), exc_info=True)
        return {
            "error": f"Browser error: {str(e)}",
            "success": False
        }


async def get_relationships_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query relationship information

    IMPORTANT: All relationship metrics are on a 0-100 scale.
    A value of 5.0 means 5 out of 100 (5%), NOT 5 out of 5 (100%).
    Values build gradually through interactions over time.

    Args:
        params: {
            "entity_id": str (optional) - Specific entity ID to query
            "entity_name": str (optional) - Search by name (partial match)
            "sort_by": str - How to sort results (trust, friendship, messages, recent)
            "limit": int - Max results to return
        }

    Returns:
        {
            "relationships": [
                {
                    "entity_id": str,
                    "entity_name": str,
                    "relationship_status": str,
                    "trust_score": float (0-100 scale),
                    "friendship_level": float (0-100 scale),
                    "honesty_score": float (0-100 scale),
                    "reliability_score": float (0-100 scale),
                    "responsiveness_score": float (0-100 scale),
                    "affection_level": float (0-100 scale),
                    "respect_level": float (0-100 scale),
                    "loyalty": float (0-100 scale),
                    "support": float (0-100 scale),
                    "engagement": float (0-100 scale),
                    "depth": float (0-100 scale),
                    "humor": float (0-100 scale),
                    "understanding": float (0-100 scale),
                    "compatibility": float (0-100 scale),
                    "expertise_score": float (0-100 scale),
                    "messages_sent": int,
                    "messages_received": int,
                    "total_messages": int,
                    "successful_collaborations": int,
                    "failed_collaborations": int,
                    "has_met": bool,
                    "is_best_friend": bool,
                    "days_known": int
                },
                ...
            ],
            "total_count": int,
            "success": bool
        }
    """
    try:
        from utils.input_validation import validate_integer_range
        from core.exceptions import QubesError

        entity_id = params.get("entity_id")
        entity_name = params.get("entity_name")
        sort_by = params.get("sort_by", "trust")
        limit = params.get("limit", 10)

        # Validate limit parameter (prevent excessive results)
        try:
            limit = validate_integer_range(limit, 1, 100, "limit")
        except QubesError as e:
            return {
                "error": str(e),
                "success": False
            }

        # Get all relationships
        all_relationships = qube.relationships.get_all_relationships()

        if not all_relationships:
            return {
                "relationships": [],
                "total_count": 0,
                "success": True,
                "message": "No relationships found"
            }

        # all_relationships is already a list, no need to call .values()
        relationships_list = all_relationships

        # Filter by specific entity_id if provided
        if entity_id:
            relationships_list = [r for r in relationships_list if r.entity_id == entity_id]
            if not relationships_list:
                return {
                    "relationships": [],
                    "total_count": 0,
                    "success": True,
                    "message": f"No relationship found for entity_id: {entity_id}"
                }

        # Filter by entity_name if provided (partial match, case-insensitive)
        # Search both entity_name field and entity_id
        elif entity_name:
            search_term = entity_name.lower()
            relationships_list = [
                r for r in relationships_list
                if (r.entity_name and search_term in r.entity_name.lower()) or  # Search by stored name
                   (r.entity_id and search_term in r.entity_id.lower())  # Fallback: search by ID
            ]
            if not relationships_list:
                return {
                    "relationships": [],
                    "total_count": 0,
                    "success": True,
                    "message": f"No relationships found matching name: {entity_name}"
                }

        # Sort relationships
        if sort_by == "trust":
            relationships_list.sort(key=lambda r: r.trust, reverse=True)
        elif sort_by == "friendship":
            relationships_list.sort(key=lambda r: r.friendship, reverse=True)
        elif sort_by == "messages":
            relationships_list.sort(
                key=lambda r: r.messages_sent + r.messages_received,
                reverse=True
            )
        elif sort_by == "recent":
            relationships_list.sort(
                key=lambda r: r.last_interaction or 0,
                reverse=True
            )

        # Limit results
        relationships_list = relationships_list[:limit]

        # Format results
        formatted_relationships = []
        for rel in relationships_list:
            formatted_relationships.append({
                "entity_id": rel.entity_id,
                "entity_name": rel.entity_name or rel.entity_id,  # Use name if available, fallback to ID
                "entity_type": rel.entity_type or "unknown",
                "relationship_status": rel.status,
                "trust_score": round(rel.trust, 1),
                "friendship_level": round(rel.friendship, 1),
                "affection_level": round(rel.affection, 1),
                "respect_level": round(rel.respect, 1),
                "honesty_score": round(rel.honesty, 1),
                "reliability_score": round(rel.reliability, 1),
                "responsiveness_score": round(rel.responsiveness, 1),
                "expertise_score": round(rel.expertise, 1),
                "loyalty": round(rel.loyalty, 1),
                "support": round(rel.support, 1),
                "engagement": round(rel.engagement, 1),
                "depth": round(rel.depth, 1),
                "humor": round(rel.humor, 1),
                "understanding": round(rel.understanding, 1),
                "compatibility": round(rel.compatibility, 1),
                "messages_sent": rel.messages_sent,
                "messages_received": rel.messages_received,
                "total_messages": rel.messages_sent + rel.messages_received,
                "successful_collaborations": rel.collaborations_successful,
                "failed_collaborations": rel.collaborations_failed,
                "has_met": rel.has_met,
                "is_best_friend": rel.is_best_friend,
                "first_contact": rel.first_contact,
                "last_interaction": rel.last_interaction,
                "days_known": rel.days_known
            })

        logger.info(
            "get_relationships_tool_used",
            qube_id=qube.qube_id,
            entity_id=entity_id,
            entity_name=entity_name,
            sort_by=sort_by,
            results=len(formatted_relationships)
        )

        return {
            "relationships": formatted_relationships,
            "total_count": len(formatted_relationships),
            "success": True
        }

    except Exception as e:
        logger.error("get_relationships_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False,
            "relationships": []
        }


async def query_decision_context_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get comprehensive decision context combining relationship + self-evaluation

    Args:
        params: {
            "entity_id": str,
            "decision_type": str (optional)
        }

    Returns:
        Comprehensive decision-making context
    """
    try:
        from ai.tools.decision_support import calculate_decision_score, generate_recommendation

        entity_id = params["entity_id"]
        decision_type = params.get("decision_type", "general")

        rel = qube.relationships.get_relationship(entity_id)
        if not rel:
            return {
                "found": False,
                "recommendation": "No relationship history - proceed with caution",
                "success": True
            }

        config = qube.decision_config

        score = calculate_decision_score(
            relationship=rel,
            decision_type=decision_type,
            config=config
        )

        recommendation = generate_recommendation(
            relationship=rel,
            score=score,
            decision_type=decision_type,
            config=config
        )

        # Include self-evaluation context if available
        self_context = {}
        if hasattr(qube, 'self_evaluation'):
            metrics = qube.self_evaluation.metrics
            self_context = {
                "my_confidence": round(metrics.get("confidence", 50), 1),
                "my_expertise": round(metrics.get("critical_thinking", 50), 1),
                "my_humility": round(metrics.get("humility", 50), 1)
            }

        logger.info(
            "query_decision_context_tool_used",
            qube_id=qube.qube_id,
            entity_id=entity_id,
            decision_type=decision_type,
            score=round(score, 1)
        )

        return {
            "found": True,
            "entity_id": entity_id,
            "entity_name": rel.entity_name or entity_id,
            "entity_type": rel.entity_type,
            "decision_score": round(score, 1),
            "decision_recommendation": recommendation,
            "relationship_quality": {
                "trust": round(rel.trust, 1),
                "reliability": round(rel.reliability, 1),
                "honesty": round(rel.honesty, 1),
                "expertise": round(rel.expertise, 1),
                "friendship": round(rel.friendship, 1),
            },
            "negative_flags": {
                "antagonism": round(rel.antagonism, 1),
                "distrust": round(rel.distrust, 1),
                "betrayal": round(rel.betrayal, 1),
            },
            "interaction_history": {
                "messages_sent": rel.messages_sent,
                "messages_received": rel.messages_received,
                "days_known": rel.days_known,
                "last_interaction": rel.last_interaction,
            },
            "self_context": self_context,
            "config_influence": {
                "metric_influence": config.metric_influence,
                "validation_strictness": config.validation_strictness,
            },
            "success": True
        }

    except Exception as e:
        logger.error("query_decision_context_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def compare_options_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare multiple entities for decision-making

    Args:
        params: {
            "entity_ids": List[str],
            "decision_type": str (optional),
            "task_requirements": dict (optional)
        }

    Returns:
        Ranked list with scores and reasoning
    """
    try:
        from ai.tools.decision_support import calculate_decision_score, explain_score

        entity_ids = params["entity_ids"]
        decision_type = params.get("decision_type", "collaboration")
        requirements = params.get("task_requirements", {})

        config = qube.decision_config

        candidates = []
        for entity_id in entity_ids:
            rel = qube.relationships.get_relationship(entity_id)
            if not rel:
                candidates.append({
                    "entity_id": entity_id,
                    "score": 0,
                    "reason": "No relationship history"
                })
                continue

            score = calculate_decision_score(
                relationship=rel,
                decision_type=decision_type,
                config=config,
                requirements=requirements
            )

            candidates.append({
                "entity_id": entity_id,
                "entity_name": rel.entity_name or entity_id,
                "score": round(score, 1),
                "trust": round(rel.trust, 1),
                "expertise": round(rel.expertise, 1),
                "reliability": round(rel.reliability, 1),
                "reason": explain_score(rel, score, decision_type, config)
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)

        logger.info(
            "compare_options_tool_used",
            qube_id=qube.qube_id,
            candidates_count=len(candidates),
            decision_type=decision_type,
            top_score=candidates[0]["score"] if candidates else 0
        )

        return {
            "ranked_candidates": candidates,
            "recommended": candidates[0]["entity_id"] if candidates else None,
            "reasoning": candidates[0]["reason"] if candidates else None,
            "success": True
        }

    except Exception as e:
        logger.error("compare_options_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


async def check_my_capability_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check own capabilities before taking action

    Args:
        params: {
            "task_type": str,
            "required_confidence": int (optional)
        }

    Returns:
        Capability assessment and recommendation
    """
    try:
        from ai.tools.decision_support import assess_capability, generate_self_assessment

        task_type = params["task_type"]
        required_confidence = params.get("required_confidence", 60)

        if not hasattr(qube, 'self_evaluation'):
            return {
                "capable": True,
                "reason": "Self-evaluation not available, proceeding cautiously",
                "success": True
            }

        metrics = qube.self_evaluation.metrics
        config = qube.decision_config

        capability_score = assess_capability(
            metrics=metrics,
            task_type=task_type,
            config=config
        )

        capable = capability_score >= required_confidence

        logger.info(
            "check_my_capability_tool_used",
            qube_id=qube.qube_id,
            task_type=task_type,
            capability_score=round(capability_score, 1),
            capable=capable
        )

        return {
            "capable": capable,
            "capability_score": round(capability_score, 1),
            "confidence": round(metrics.get("confidence", 50), 1),
            "critical_thinking": round(metrics.get("critical_thinking", 50), 1),
            "adaptability": round(metrics.get("adaptability", 50), 1),
            "expertise_level": "high" if capability_score >= 80 else "medium" if capability_score >= 60 else "low",
            "recommendation": generate_self_assessment(capable, capability_score, task_type),
            "success": True
        }

    except Exception as e:
        logger.error("check_my_capability_tool_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }


# =============================================================================
# SKILL-BASED TOOLS (21 Starter Tools - 3 per Sun)
# =============================================================================

# -----------------------------------------------------------------------------
# AI Reasoning Sun Tools
# -----------------------------------------------------------------------------

async def think_step_by_step_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Force structured chain-of-thought reasoning

    Enhances reasoning by breaking problems into explicit steps
    """
    try:
        problem = params["problem"]

        structured_prompt = f"""Analyze this problem using structured step-by-step reasoning:

Problem: {problem}

Please think through this systematically:

1. **Understanding**: Restate the problem in your own words to ensure comprehension
2. **Constraints**: List all constraints, requirements, and given information
3. **Approaches**: Outline 2-3 possible approaches to solve this
4. **Analysis**: Compare the approaches (pros, cons, complexity, reliability)
5. **Solution**: Choose the best approach and explain your reasoning
6. **Validation**: How would you verify this solution is correct?

Take your time and think carefully through each step."""

        response = await call_model_directly(qube, structured_prompt)

        logger.info("think_step_by_step_used", qube_id=qube.qube_id, problem_length=len(problem))

        return {
            "structured_thinking": response,
            "method": "chain_of_thought",
            "problem": problem,
            "success": True
        }

    except Exception as e:
        logger.error("think_step_by_step_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def self_critique_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate own output for quality improvement

    Creates feedback loop for self-improvement
    """
    try:
        response_text = params["response"]

        critique_prompt = f"""Critically evaluate this response you generated:

Response: {response_text}

Rate each aspect on a scale of 1-10 and explain your rating:

1. **Accuracy**: Are all facts and claims correct?
2. **Completeness**: Is anything important missing?
3. **Clarity**: Is it easy to understand?
4. **Relevance**: Does it address the actual question?
5. **Bias**: Are there any unexamined assumptions or biases?

Then provide 3 specific, actionable improvements that would make this response better."""

        response = await call_model_directly(qube, critique_prompt)

        logger.info("self_critique_used", qube_id=qube.qube_id)

        return {
            "critique": response,
            "original_response": response_text,
            "success": True
        }

    except Exception as e:
        logger.error("self_critique_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def explore_alternatives_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate multiple alternative approaches

    Prevents tunnel vision by exploring diverse solutions
    """
    try:
        situation = params["situation"]
        count = params.get("count", 3)

        alternatives_prompt = f"""Generate {count} distinct alternative approaches to this situation:

Situation: {situation}

For each alternative:
1. Describe the approach
2. List key advantages
3. List potential drawbacks
4. Estimate difficulty (low/medium/high)

Make the alternatives genuinely different from each other, exploring diverse strategies."""

        response = await call_model_directly(qube, alternatives_prompt)

        logger.info("explore_alternatives_used", qube_id=qube.qube_id, count=count)

        return {
            "alternatives": response,
            "situation": situation,
            "count": count,
            "success": True
        }

    except Exception as e:
        logger.error("explore_alternatives_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Social Intelligence Sun Tools
# -----------------------------------------------------------------------------

async def draft_message_variants_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create message variants with different tones

    Helps choose the most appropriate communication style
    """
    try:
        message = params["message"]
        recipient = params.get("recipient", "recipient")

        # Get relationship context if available
        relationship_context = ""
        if params.get("recipient_id"):
            rel = qube.relationships.get_relationship(params["recipient_id"])
            if rel:
                relationship_context = f"\nRelationship context: Trust={rel.trust:.1f}, Friendship={rel.friendship:.1f}"

        variants_prompt = f"""Create 3 different versions of this message with varying tones:

Original Message: {message}
Recipient: {recipient}{relationship_context}

Generate these variants:
1. **Formal**: Professional, respectful, structured
2. **Casual**: Friendly, conversational, warm
3. **Empathetic**: Understanding, supportive, emotionally aware

For each variant:
- Rewrite the complete message
- Explain when this tone would be most appropriate
- Note any risks with this tone"""

        response = await call_model_directly(qube, variants_prompt)

        logger.info("draft_message_variants_used", qube_id=qube.qube_id)

        return {
            "variants": response,
            "original_message": message,
            "success": True
        }

    except Exception as e:
        logger.error("draft_message_variants_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def predict_reaction_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict how someone will react to an action

    Uses relationship history for informed predictions
    """
    try:
        action = params["action"]
        entity_id = params["entity_id"]

        # Get relationship data
        rel = qube.relationships.get_relationship(entity_id)
        if not rel:
            return {
                "prediction": "No relationship history - cannot predict reaction",
                "confidence": "low",
                "success": True
            }

        context = f"""Relationship History:
- Trust: {rel.trust:.1f}/100
- Friendship: {rel.friendship:.1f}/100
- Messages exchanged: {rel.messages_sent + rel.messages_received}
- Successful collaborations: {rel.collaborations_successful}
- Failed collaborations: {rel.collaborations_failed}
- Days known: {rel.days_known}
- Relationship status: {rel.status}"""

        predict_prompt = f"""Based on this relationship history, predict how {rel.entity_name or entity_id} will react:

{context}

Planned Action: {action}

Predict:
1. **Most Likely Reaction**: What will they probably do/say?
2. **Emotional Response**: How will they feel?
3. **Relationship Impact**: Will this strengthen or harm the relationship?
4. **Confidence**: How confident are you? (low/medium/high)
5. **Recommendations**: Any suggestions to improve the outcome?"""

        response = await call_model_directly(qube, predict_prompt)

        logger.info("predict_reaction_used", qube_id=qube.qube_id, entity_id=entity_id)

        return {
            "prediction": response,
            "action": action,
            "entity_id": entity_id,
            "entity_name": rel.entity_name or entity_id,
            "success": True
        }

    except Exception as e:
        logger.error("predict_reaction_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def build_rapport_strategy_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create personalized rapport-building strategy

    Analyzes relationship to suggest effective engagement tactics
    """
    try:
        entity_id = params["entity_id"]

        # Get relationship data
        rel = qube.relationships.get_relationship(entity_id)
        if not rel:
            return {
                "strategy": "Start with friendly, open communication to establish baseline relationship",
                "success": True
            }

        context = f"""Current Relationship with {rel.entity_name or entity_id}:
- Trust: {rel.trust:.1f}/100
- Friendship: {rel.friendship:.1f}/100
- Affection: {rel.affection:.1f}/100
- Engagement: {rel.engagement:.1f}/100
- Humor compatibility: {rel.humor:.1f}/100
- Understanding: {rel.understanding:.1f}/100
- Communication frequency: {rel.messages_sent + rel.messages_received} messages
- Last interaction: {rel.days_since_last_interaction} days ago"""

        strategy_prompt = f"""Design a personalized rapport-building strategy:

{context}

Create a strategy that includes:
1. **Immediate Actions**: 2-3 things to do in next interaction
2. **Communication Style**: Best tone and approach based on their preferences
3. **Topics to Explore**: Subjects likely to resonate
4. **Topics to Avoid**: Potential sensitive areas
5. **Long-term Goals**: How to deepen this relationship over time
6. **Success Metrics**: How to know if the strategy is working"""

        response = await call_model_directly(qube, strategy_prompt)

        logger.info("build_rapport_strategy_used", qube_id=qube.qube_id, entity_id=entity_id)

        return {
            "strategy": response,
            "entity_id": entity_id,
            "entity_name": rel.entity_name or entity_id,
            "success": True
        }

    except Exception as e:
        logger.error("build_rapport_strategy_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Technical Expertise Sun Tools
# -----------------------------------------------------------------------------

async def debug_systematically_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply systematic debugging methodology

    Uses structured approach to identify root causes
    """
    try:
        error = params["error"]
        code = params.get("code", "")

        debug_prompt = f"""Apply systematic debugging methodology:

Error: {error}
Code: {code if code else "Not provided"}

Use this debugging framework:

1. **Reproduce**: Can you reliably reproduce this error?
2. **Isolate**: What is the minimal code that triggers it?
3. **Hypothesis**: What are 3 possible root causes?
4. **Test**: How would you test each hypothesis?
5. **Fix**: What is the most likely fix?
6. **Validate**: How would you verify the fix works?
7. **Prevent**: How can we prevent similar errors?

Provide detailed analysis for each step."""

        response = await call_model_directly(qube, debug_prompt)

        logger.info("debug_systematically_used", qube_id=qube.qube_id)

        return {
            "debug_analysis": response,
            "error": error,
            "method": "systematic_debugging",
            "success": True
        }

    except Exception as e:
        logger.error("debug_systematically_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def research_with_synthesis_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multi-source research with synthesis

    Combines web search and memory for comprehensive understanding
    """
    try:
        topic = params["topic"]

        # 1. Web search
        web_results = await web_search_handler(qube, {"query": topic, "num_results": 3})

        # 2. Memory search
        memory_results = await memory_search_handler(qube, {"query": topic, "limit": 5})

        # 3. Synthesize
        synthesis_prompt = f"""Synthesize information from multiple sources about: {topic}

Web Search Results:
{json.dumps(web_results.get('results', []), indent=2)}

Memory/Past Knowledge:
{json.dumps(memory_results.get('results', []), indent=2)[:1000]}

Create a comprehensive synthesis that:
1. **Common Themes**: What do sources agree on?
2. **Contradictions**: Where do sources disagree? Why?
3. **Gaps**: What important questions remain unanswered?
4. **Insights**: What non-obvious conclusions can you draw?
5. **Action Items**: What should be explored further?"""

        response = await call_model_directly(qube, synthesis_prompt)

        logger.info("research_with_synthesis_used", qube_id=qube.qube_id, topic=topic)

        return {
            "synthesis": response,
            "web_sources": web_results.get('results', []),
            "memory_sources": memory_results.get('results', []),
            "topic": topic,
            "success": True
        }

    except Exception as e:
        logger.error("research_with_synthesis_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def validate_solution_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate solution against requirements

    Systematic quality checking before implementation
    """
    try:
        problem = params["problem"]
        solution = params["solution"]

        validation_prompt = f"""Validate this solution systematically:

Problem: {problem}

Proposed Solution: {solution}

Validation Checklist:

1. **Correctness**: Does it actually solve the stated problem?
2. **Completeness**: Does it handle all cases and edge cases?
3. **Efficiency**: Is this a reasonably efficient approach?
4. **Robustness**: How does it handle errors and invalid inputs?
5. **Maintainability**: Is it understandable and modifiable?
6. **Security**: Are there any security concerns?
7. **Test Cases**: What test cases would prove this works?
8. **Risks**: What could go wrong with this solution?

Provide ratings (1-10) and detailed explanations for each."""

        response = await call_model_directly(qube, validation_prompt)

        logger.info("validate_solution_used", qube_id=qube.qube_id)

        return {
            "validation": response,
            "problem": problem,
            "solution": solution,
            "success": True
        }

    except Exception as e:
        logger.error("validate_solution_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Creative Expression Sun Tools
# -----------------------------------------------------------------------------

async def brainstorm_variants_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate diverse creative variations

    Divergent thinking to explore possibility space
    """
    try:
        concept = params["concept"]
        count = params.get("count", 5)

        brainstorm_prompt = f"""Generate {count} creative variations of this concept:

Original Concept: {concept}

For each variation:
1. Describe the variant
2. What makes it unique/different
3. What audience would it appeal to
4. Feasibility (easy/medium/hard)

Make the variations genuinely diverse - explore different angles, styles, and approaches."""

        response = await call_model_directly(qube, brainstorm_prompt)

        logger.info("brainstorm_variants_used", qube_id=qube.qube_id, count=count)

        return {
            "variants": response,
            "original_concept": concept,
            "count": count,
            "success": True
        }

    except Exception as e:
        logger.error("brainstorm_variants_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def iterate_design_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Iteratively refine creative work

    Feedback loop for continuous improvement
    """
    try:
        initial_concept = params["initial_concept"]
        iterations = params.get("iterations", 2)

        current_version = initial_concept
        iteration_history = []

        for i in range(iterations):
            iterate_prompt = f"""Iteration {i+1}: Refine this creative concept

Current Version: {current_version}

Refinement Process:
1. **Critique**: What works well? What doesn't?
2. **Identify Issues**: 2-3 specific problems to address
3. **Improved Version**: Create a refined version addressing those issues
4. **Rationale**: Explain what you changed and why

Focus on meaningful improvements, not just minor tweaks."""

            response = await call_model_directly(qube, iterate_prompt)

            iteration_history.append({
                "iteration": i + 1,
                "refinement": response
            })

            # Update current version for next iteration (simplified - in reality would parse)
            current_version = response

        logger.info("iterate_design_used", qube_id=qube.qube_id, iterations=iterations)

        return {
            "iterations": iteration_history,
            "final_version": current_version,
            "original": initial_concept,
            "success": True
        }

    except Exception as e:
        logger.error("iterate_design_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def cross_pollinate_ideas_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine concepts from different domains

    Innovation through unexpected connections
    """
    try:
        domain1 = params["domain1"]
        domain2 = params["domain2"]

        cross_pollinate_prompt = f"""Cross-pollinate ideas between these domains:

Domain 1: {domain1}
Domain 2: {domain2}

Create 3 innovative concepts by combining elements from both:

For each concept:
1. **The Hybrid**: Describe the combined concept
2. **From Domain 1**: What elements come from {domain1}?
3. **From Domain 2**: What elements come from {domain2}?
4. **Innovation**: Why is this combination interesting/valuable?
5. **Application**: Where could this be used?

Think creatively - find unexpected but meaningful connections."""

        response = await call_model_directly(qube, cross_pollinate_prompt)

        logger.info("cross_pollinate_ideas_used", qube_id=qube.qube_id, domains=[domain1, domain2])

        return {
            "hybrid_concepts": response,
            "domain1": domain1,
            "domain2": domain2,
            "success": True
        }

    except Exception as e:
        logger.error("cross_pollinate_ideas_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Knowledge Domains Sun Tools
# -----------------------------------------------------------------------------

async def deep_research_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multi-layer deep research

    Progressive deepening from overview to expert insights
    """
    try:
        topic = params["topic"]
        depth = params.get("depth", 3)

        layers = []

        # Layer 1: Overview
        overview_prompt = f"Provide a comprehensive overview of: {topic}. Cover the fundamentals, key concepts, and why this matters."
        overview = await call_model_directly(qube, overview_prompt)
        layers.append({"level": 1, "type": "overview", "content": overview})

        if depth >= 2:
            # Layer 2: Details
            details_prompt = f"Building on this overview:\n\n{overview}\n\nNow provide deeper technical details about {topic}. Include nuances, common misconceptions, and important subtleties."
            details = await call_model_directly(qube, details_prompt)
            layers.append({"level": 2, "type": "details", "content": details})

        if depth >= 3:
            # Layer 3: Expert insights
            expert_prompt = f"Given this detailed understanding:\n\n{details if depth >= 2 else overview}\n\nProvide expert-level insights on {topic}: cutting-edge developments, open questions, practical applications, and future directions."
            expert = await call_model_directly(qube, expert_prompt)
            layers.append({"level": 3, "type": "expert_insights", "content": expert})

        logger.info("deep_research_used", qube_id=qube.qube_id, topic=topic, depth=depth)

        return {
            "research_layers": layers,
            "topic": topic,
            "depth": depth,
            "success": True
        }

    except Exception as e:
        logger.error("deep_research_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def synthesize_knowledge_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine knowledge from multiple domains

    Creates coherent understanding across boundaries
    """
    try:
        sources = params["sources"]  # List of topics/domains

        synthesis_prompt = f"""Synthesize knowledge across these domains:

Domains: {', '.join(sources)}

Create a synthesis that:
1. **Connections**: How do these domains relate?
2. **Patterns**: What common patterns or principles emerge?
3. **Synergies**: How could they complement each other?
4. **Contradictions**: Where do they conflict? Why?
5. **Unified Understanding**: What higher-level insight emerges?
6. **Applications**: How can this combined knowledge be applied?"""

        response = await call_model_directly(qube, synthesis_prompt)

        logger.info("synthesize_knowledge_used", qube_id=qube.qube_id, domains_count=len(sources))

        return {
            "synthesis": response,
            "sources": sources,
            "success": True
        }

    except Exception as e:
        logger.error("synthesize_knowledge_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def explain_like_im_five_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify complex concepts with analogies

    Tests and demonstrates true understanding
    """
    try:
        concept = params["concept"]

        eli5_prompt = f"""Explain this complex concept as if to a 5-year-old:

Concept: {concept}

Guidelines:
1. Use simple, everyday language
2. Use concrete analogies and examples
3. Avoid jargon (or explain it simply if necessary)
4. Make it relatable and engaging
5. Check understanding with a simple example

The best explanations make complex things feel obvious."""

        response = await call_model_directly(qube, eli5_prompt)

        logger.info("explain_like_im_five_used", qube_id=qube.qube_id, concept=concept[:50])

        return {
            "simple_explanation": response,
            "original_concept": concept,
            "success": True
        }

    except Exception as e:
        logger.error("explain_like_im_five_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Security & Privacy Sun Tools
# -----------------------------------------------------------------------------

async def assess_security_risks_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structured security risk assessment

    Uses STRIDE framework for comprehensive analysis
    """
    try:
        context = params["context"]

        security_prompt = f"""Perform security risk assessment using STRIDE framework:

Context: {context}

Analyze each threat category:

1. **Spoofing**: Can someone impersonate a legitimate user?
2. **Tampering**: Can data be modified maliciously?
3. **Repudiation**: Can someone deny their actions?
4. **Information Disclosure**: Can sensitive data be exposed?
5. **Denial of Service**: Can the system be made unavailable?
6. **Elevation of Privilege**: Can someone gain unauthorized access?

For each:
- Risk level (low/medium/high)
- Specific scenarios
- Mitigations
- Priority

Then provide overall risk rating and top 3 recommendations."""

        response = await call_model_directly(qube, security_prompt)

        logger.info("assess_security_risks_used", qube_id=qube.qube_id)

        return {
            "security_assessment": response,
            "framework": "STRIDE",
            "context": context,
            "success": True
        }

    except Exception as e:
        logger.error("assess_security_risks_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def privacy_impact_analysis_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate privacy implications before acting

    Proactive privacy protection
    """
    try:
        action = params["action"]

        privacy_prompt = f"""Analyze privacy implications of this action:

Proposed Action: {action}

Privacy Impact Assessment:

1. **Data Collection**: What data would be collected/accessed?
2. **Data Usage**: How would this data be used?
3. **Data Sharing**: Who else might access this data?
4. **Consent**: Do we have proper consent?
5. **Retention**: How long would data be kept?
6. **Rights**: Does this respect user rights (access, deletion, etc.)?
7. **Risks**: What could go wrong from a privacy perspective?
8. **Mitigations**: How can we minimize privacy impact?

Recommendation: Proceed / Proceed with changes / Do not proceed
Rationale: Explain the recommendation"""

        response = await call_model_directly(qube, privacy_prompt)

        logger.info("privacy_impact_analysis_used", qube_id=qube.qube_id)

        return {
            "privacy_analysis": response,
            "action": action,
            "success": True
        }

    except Exception as e:
        logger.error("privacy_impact_analysis_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def verify_authenticity_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate information trustworthiness

    Critical thinking about sources and claims
    """
    try:
        claim = params["claim"]
        source = params.get("source", "unknown")

        verify_prompt = f"""Evaluate the authenticity and trustworthiness of this information:

Claim: {claim}
Source: {source}

Verification Analysis:

1. **Source Credibility**: How trustworthy is this source?
2. **Evidence Quality**: What evidence supports this claim?
3. **Logical Consistency**: Does this make logical sense?
4. **Bias Detection**: Any obvious biases or conflicts of interest?
5. **Verifiability**: Can this be independently verified?
6. **Red Flags**: Any warning signs of misinformation?
7. **Confidence Level**: How confident should we be? (low/medium/high)
8. **Recommendation**: Should we trust this? What further verification is needed?

Be skeptical but fair in your analysis."""

        response = await call_model_directly(qube, verify_prompt)

        logger.info("verify_authenticity_used", qube_id=qube.qube_id)

        return {
            "verification": response,
            "claim": claim,
            "source": source,
            "success": True
        }

    except Exception as e:
        logger.error("verify_authenticity_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Games Sun Tools
# -----------------------------------------------------------------------------

async def analyze_game_state_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate current game position

    Strategic pattern recognition
    """
    try:
        game = params["game"]
        state = params["state"]

        analysis_prompt = f"""Analyze this game state:

Game: {game}
Current State: {state}

Analysis:

1. **Position Evaluation**: Who is winning? By how much?
2. **Key Factors**: What makes this position favorable/unfavorable?
3. **Threats**: What immediate threats exist?
4. **Opportunities**: What tactical opportunities are available?
5. **Patterns**: Any recognizable patterns or formations?
6. **Critical Pieces/Areas**: What's most important right now?
7. **Momentum**: Who has initiative/momentum?

Provide a comprehensive strategic assessment."""

        response = await call_model_directly(qube, analysis_prompt)

        logger.info("analyze_game_state_used", qube_id=qube.qube_id, game=game)

        return {
            "analysis": response,
            "game": game,
            "state": state,
            "success": True
        }

    except Exception as e:
        logger.error("analyze_game_state_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def plan_strategy_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multi-move strategic planning

    Think ahead with contingencies
    """
    try:
        game = params["game"]
        goal = params["goal"]
        current_state = params.get("current_state", "")

        strategy_prompt = f"""Create a strategic plan:

Game: {game}
Goal: {goal}
Current State: {current_state}

Strategic Plan:

1. **Overall Strategy**: High-level approach to achieve the goal
2. **Key Phases**: Break strategy into 2-4 phases
3. **Move Sequence**: Next 3-5 moves (if applicable)
4. **Contingencies**: If opponent does X, we do Y
5. **Win Conditions**: How do we know we're succeeding?
6. **Risks**: What could derail this plan?
7. **Adaptations**: When should we switch strategies?

Think several moves ahead, considering opponent responses."""

        response = await call_model_directly(qube, strategy_prompt)

        logger.info("plan_strategy_used", qube_id=qube.qube_id, game=game)

        return {
            "strategic_plan": response,
            "game": game,
            "goal": goal,
            "success": True
        }

    except Exception as e:
        logger.error("plan_strategy_failed", exc_info=True)
        return {"error": str(e), "success": False}


async def learn_from_game_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-game analysis for improvement

    Extract lessons from experience
    """
    try:
        game = params["game"]
        outcome = params["outcome"]  # win/loss/draw
        key_moments = params.get("key_moments", "")

        learning_prompt = f"""Analyze this game for learning:

Game: {game}
Outcome: {outcome}
Key Moments: {key_moments}

Post-Game Analysis:

1. **What Went Well**: 2-3 good decisions/moves
2. **Mistakes**: 2-3 errors and why they were wrong
3. **Turning Points**: When did the game's outcome get decided?
4. **Lessons Learned**: 3 specific takeaways for next time
5. **Pattern Recognition**: Any patterns to remember?
6. **Skill Development**: What skills need practice?
7. **Next Steps**: How to improve for next game?

Be honest and constructive in self-assessment."""

        response = await call_model_directly(qube, learning_prompt)

        logger.info("learn_from_game_used", qube_id=qube.qube_id, game=game, outcome=outcome)

        return {
            "learning_analysis": response,
            "game": game,
            "outcome": outcome,
            "success": True
        }

    except Exception as e:
        logger.error("learn_from_game_failed", exc_info=True)
        return {"error": str(e), "success": False}


# -----------------------------------------------------------------------------
# Chess Move Tool Handler
# -----------------------------------------------------------------------------

async def chess_move_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a chess move in an active game

    This tool is always available but checks at runtime whether there's
    an active game. If no game is in progress, it returns an error with
    a helpful message.

    Args:
        params: {
            "move": str - Chess move in UCI or SAN notation
            "chat_message": str (optional) - Message to send with the move
        }

    Returns:
        {
            "success": bool,
            "move_made": str,
            "board_fen": str,
            "is_check": bool,
            "is_checkmate": bool,
            "is_stalemate": bool,
            "game_over": bool,
            "result": str (optional),
            "chat_added": bool
        }
    """
    logger.info(f"[CHESS TOOL] chess_move_handler called with params: {params}")
    try:
        move = params["move"]
        logger.info(f"[CHESS TOOL] Attempting move: {move}")
        chat_message = params.get("chat_message")

        # Check if game_manager exists and has an active game
        if not hasattr(qube, 'game_manager') or qube.game_manager is None:
            return {
                "error": "Game manager not initialized",
                "success": False,
                "hint": "The game system is not available for this Qube."
            }

        game_manager = qube.game_manager

        # Check for active game
        if game_manager.active_game is None:
            return {
                "error": "No active chess game",
                "success": False,
                "hint": "There is no chess game currently in progress. Start a new game first."
            }

        active_game = game_manager.active_game

        # Verify this qube is a player in the game
        # Use "id" key - that's what GameManager.create_game uses
        qube_is_white = active_game.white_player.get("id") == qube.qube_id
        qube_is_black = active_game.black_player.get("id") == qube.qube_id

        if not qube_is_white and not qube_is_black:
            return {
                "error": "You are not a player in this game",
                "success": False,
                "hint": "This chess game is between other players."
            }

        # Check if it's this qube's turn by parsing FEN
        # FEN format: "pieces turn castling en_passant halfmove fullmove"
        # Turn is 'w' for white, 'b' for black
        fen_parts = active_game.fen.split(' ')
        is_white_turn = fen_parts[1] == 'w' if len(fen_parts) > 1 else True
        qube_color = "white" if qube_is_white else "black"

        if (is_white_turn and not qube_is_white) or (not is_white_turn and not qube_is_black):
            return {
                "error": "It's not your turn",
                "success": False,
                "hint": f"You are playing as {qube_color}. Wait for your opponent to move.",
                "current_turn": "white" if is_white_turn else "black"
            }

        # Convert SAN notation to UCI if needed
        # The AI often uses SAN (e.g., "e5", "Nf3") but record_move expects UCI (e.g., "e7e5", "g1f3")
        import chess
        board = chess.Board(active_game.fen)
        move_uci = move

        # Check if move is already in UCI format (4-5 characters like "e2e4" or "e7e8q")
        if len(move) < 4 or not (move[0] in 'abcdefgh' and move[1] in '12345678'):
            # Likely SAN notation, try to convert
            try:
                parsed_move = board.parse_san(move)
                move_uci = parsed_move.uci()
                logger.info(f"[CHESS TOOL] Converted SAN '{move}' to UCI '{move_uci}'")
            except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as e:
                logger.warning(f"[CHESS TOOL] Failed to parse as SAN: {e}, trying as UCI")
                # Keep original move, let record_move handle it

        # Record the move using GameManager
        logger.info(f"[CHESS TOOL] Calling record_move with move_uci={move_uci}, player_id={qube.qube_id}")
        move_result = game_manager.record_move(
            move_uci=move_uci,
            player_id=qube.qube_id
        )
        logger.info(f"[CHESS TOOL] record_move result: {move_result}")

        if not move_result["success"]:
            error_response = {
                "error": move_result.get("error", "Invalid move"),
                "success": False,
            }
            # If we have legal moves, include them in the hint for the AI
            legal_moves = move_result.get("legal_moves", [])
            if legal_moves:
                # Show first 15 legal moves in UCI format
                moves_str = ", ".join(legal_moves[:15])
                if len(legal_moves) > 15:
                    moves_str += f"... ({len(legal_moves)} total)"
                error_response["hint"] = f"Try one of these legal moves (UCI format): {moves_str}"
                error_response["legal_moves"] = legal_moves
            else:
                error_response["hint"] = "Check that your move is in valid UCI (e.g., 'e2e4') or SAN (e.g., 'e4') notation."
            return error_response

        # Add chat message if provided
        chat_added = False
        if chat_message:
            game_manager.add_chat_message(
                sender_id=qube.qube_id,
                sender_type="qube",
                message=chat_message
            )
            chat_added = True

        # Build response
        # Map record_move keys to expected response format
        is_game_over = move_result.get("is_game_over", False)
        termination = move_result.get("termination")

        response = {
            "success": True,
            "move_made": move_result["san"],
            "move_uci": move_result.get("move"),  # record_move uses "move" not "uci"
            "board_fen": move_result["fen"],
            "move_number": move_result["move_number"],
            "is_check": move_result.get("is_check", False),
            "is_checkmate": termination == "checkmate",
            "is_stalemate": termination == "stalemate",
            "is_draw": termination in ("stalemate", "insufficient_material", "fifty_move_rule", "threefold_repetition", "draw"),
            "game_over": is_game_over,
            "chat_added": chat_added
        }

        # Add result if game is over
        if is_game_over:
            response["result"] = move_result.get("result", "unknown")
            response["termination"] = move_result.get("termination", "unknown")

        logger.info(
            "chess_move_made_via_tool",
            qube_id=qube.qube_id,
            move=move_result["san"],
            game_id=active_game.game_id,
            game_over=is_game_over
        )

        return response

    except Exception as e:
        logger.error("chess_move_handler_failed", qube_id=qube.qube_id, exc_info=True)
        return {
            "error": str(e),
            "success": False
        }
