"""
Configuration for GingerAI Telegram Bot with Ollama Memory
"""

from pathlib import Path

# File paths
BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "memory.json"

# Telegram settings
TELEGRAM_BOT_TOKEN = "enter_bot_token_here"
POLLING_INTERVAL = 1  # seconds

# Ollama settings
OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "dolphin-llama3:8b"
OLLAMA_HTTP_TIMEOUT = 86400  # 24 hours in seconds
OLLAMA_CLI_TIMEOUT = 86400  # 24 hours in seconds

# Retry queue settings
RETRY_QUEUE_FILE = BASE_DIR / "retry_queue.json"
MAX_RETRY_ATTEMPTS = 3
RETRY_INTERVAL_SECONDS = 30

# Memory settings
MEMORY_AUTO_UPDATE = True
CONVERSATION_HISTORY_LIMIT = 10
MAX_MEMORY_STRING_LENGTH = 200

# Chat settings
SYSTEM_PROMPT = """You are GingerAI, a helpful Telegram bot with long-term memory. You remember facts about the user and use them in your responses. Keep responses concise for Telegram (under 2000 chars). You are friendly and conversational."""

# Feature flags
USE_MEMORY_INJECTION = True
AUTO_DETECT_MEMORY = True
