"""Configuration settings for the LLMS.txt Generator."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Categorized LLM models available on OpenRouter
CATEGORIZED_LLM_MODELS = {
    "Deepseek": [
        "deepseek/deepseek-r1-0528",
        "deepseek/deepseek-prover-v2",
        "deepseek/deepseek-r1-0528:free",
        "deepseek/deepseek-prover-v2:free"
    ],
    "OpenAI": [
        "openai/gpt-4.1",
        "openai/gpt-4.1-mini",
        "openai/gpt-4.1-nano",
        "openai/chatgpt-4o-latest",
        "openai/gpt-4o-mini",
        "openai/o1-preview",
        "openai/o1-mini"
    ],
    "Claude": [
        "anthropic/claude-opus-4",
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3.7-sonnet",
        "anthropic/claude-3.7-sonnet:thinking",
        "anthropic/claude-3.5-haiku",
        "anthropic/claude-3.5-sonnet"
    ],
    "Gemini": [
        "google/gemini-2.5-flash-preview-05-20",
        "google/gemini-2.5-flash-preview-05-20:thinking",
        "google/gemini-2.5-pro-preview",
        "google/gemma-3-27b-it"
    ],
    "xAI": [
        "x-ai/grok-3-mini-beta",
        "x-ai/grok-3-beta"
    ],
    "Qwen": [
        "qwen/qwen2.5-vl-32b-instruct"
    ]
}

# Flatten the categorized models for backward compatibility
DEFAULT_LLM_MODELS = []
for provider, models in CATEGORIZED_LLM_MODELS.items():
    DEFAULT_LLM_MODELS.extend(models)

# Default model for content processing (first free option)
DEFAULT_MODEL = "deepseek/deepseek-r1-0528:free"

# Puppeteer Configuration
PUPPETEER_TIMEOUT = 30000  # 30 seconds
PUPPETEER_WAIT_UNTIL = "networkidle2"

# Content extraction settings
MAX_CONTENT_LENGTH = 8000  # Maximum characters to send to LLM
MIN_CONTENT_LENGTH = 100   # Minimum content length to process

# Request settings
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3

# User agent for web scraping
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Model validation
def validate_custom_model(model_name: str) -> bool:
    """Validate custom model name format.

    Args:
        model_name: The model name to validate

    Returns:
        True if valid, False otherwise
    """
    import re

    if not model_name or not isinstance(model_name, str):
        return False

    # Pattern: provider/model-name or provider/model-name:variant
    pattern = r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+(?::[a-zA-Z0-9._-]+)?$'
    return bool(re.match(pattern, model_name.strip()))

def get_model_display_name(model_name: str) -> str:
    """Get a user-friendly display name for a model.

    Args:
        model_name: The full model name

    Returns:
        Formatted display name
    """
    if not model_name:
        return "Unknown Model"

    # Extract just the model part after the provider
    parts = model_name.split('/')
    if len(parts) >= 2:
        model_part = parts[1]
        # Add (Free) indicator for free models
        if model_part.endswith(':free'):
            base_name = model_part.replace(':free', '')
            return f"{base_name} (Free)"
        elif ':thinking' in model_part:
            base_name = model_part.replace(':thinking', '')
            return f"{base_name} (Thinking)"
        return model_part

    return model_name
