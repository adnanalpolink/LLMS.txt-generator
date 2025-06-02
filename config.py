"""Configuration settings for the LLMS.txt Generator."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Default LLM models available on OpenRouter
DEFAULT_LLM_MODELS = [
    "anthropic/claude-3-haiku",
    "anthropic/claude-3-sonnet", 
    "openai/gpt-3.5-turbo",
    "openai/gpt-4",
    "openai/gpt-4-turbo",
    "meta-llama/llama-2-70b-chat",
    "google/gemini-pro",
    "mistralai/mistral-7b-instruct"
]

# Default model for content processing
DEFAULT_MODEL = "anthropic/claude-3-haiku"

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
