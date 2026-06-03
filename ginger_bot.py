"""
GingerAI - Telegram Bot with Long-Term Memory via Ollama

Polls Telegram for messages, injects memory context into prompts sent to Ollama,
and persists memory updates back to memory.json.

Usage:
  pip install python-telegram-bot requests
  python ginger_bot.py
"""

import asyncio
import json
import logging
import requests
import subprocess
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import config
from memory_manager import (
    load_memory,
    save_memory,
    get_memory_context,
    get_full_memory_context,
    detect_and_update_memory,
    add_conversation,
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class OllamaError(Exception):
    pass


class OllamaTimeoutError(OllamaError):
    pass


def load_retry_queue() -> list:
    queue_file = config.RETRY_QUEUE_FILE
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    if not queue_file.exists():
        return []
    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load retry queue: {e}")
        return []


def save_retry_queue(queue: list) -> None:
    queue_file = config.RETRY_QUEUE_FILE
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_file, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def enqueue_retry_item(chat_id: int, user_message: str) -> None:
    queue = load_retry_queue()
    queue.append({
        "chat_id": chat_id,
        "user_message": user_message,
        "attempts": 0,
        "created_at": datetime.utcnow().isoformat() + "Z"
    })
    save_retry_queue(queue)


def should_retry(item: dict) -> bool:
    return item.get("attempts", 0) < config.MAX_RETRY_ATTEMPTS


def ask_ollama(prompt: str, model: str = config.DEFAULT_MODEL) -> str:
    """Send prompt to Ollama via HTTP API or CLI."""
    # Try HTTP first
    try:
        url = f"{config.OLLAMA_HOST}/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": False}
        resp = requests.post(url, json=payload, timeout=config.OLLAMA_HTTP_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "response" in data:
            return data["response"].strip()
    except requests.exceptions.ReadTimeout as e:
        logger.warning(f"HTTP request timed out: {e}. Trying CLI...")
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"HTTP connection failed: {e}. Trying CLI...")
    except Exception as e:
        logger.warning(f"HTTP request failed: {e}. Trying CLI...")
    
    # Fallback to CLI
    try:
        cmd = ["ollama", "run", model, prompt, "--format", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=config.OLLAMA_CLI_TIMEOUT)
        out = result.stdout.strip()
        if not out:
            raise OllamaError("No output returned from Ollama CLI.")
        data = json.loads(out)
        return (data.get("response") or data.get("text") or data.get("content") or "").strip()
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Ollama CLI timeout: {e}")
        raise OllamaTimeoutError("Ollama CLI request timed out")
    except Exception as e:
        logger.error(f"Ollama CLI error: {e}")
        raise OllamaError("Ollama CLI request failed")


def build_prompt(user_input: str, memory: dict) -> str:
    """Build prompt by injecting memory context + recent conversation history."""
    # Include both facts and conversation history
    memory_context = get_full_memory_context(memory, include_history=True, history_limit=5)
    
    prompt = config.SYSTEM_PROMPT + "\n\n"
    if memory_context:
        prompt += "=== Your Memory and Context ===\n" + memory_context + "\n\n"
    
    prompt += f"User: {user_input}\n\nAssistant:"
    return prompt


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Welcome to GingerAI! I'm a Telegram bot with long-term memory.\n\n"
        "Just send me a message and I'll remember facts about you like your name, projects, and preferences.\n\n"
        "Commands:\n"
        "/memory - Show what I remember about you\n"
        "/clear - Clear my memory\n"
        "/help - Show help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "🤖 GingerAI Help\n\n"
        "I learn from our conversations! Try:\n"
        "• 'My name is [Name]'\n"
        "• 'I'm working on [Project]'\n"
        "• 'I prefer [Preference]'\n"
        "• 'Remember: [Fact]'\n\n"
        "Commands:\n"
        "/memory - Show what I remember\n"
        "/clear - Clear my memory\n"
        "/start - Welcome message"
    )


async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /memory command."""
    memory = load_memory()
    lines = ["📚 My Memory About You:\n"]
    
    if memory.get("user_name"):
        lines.append(f"👤 Name: {memory['user_name']}")
    
    if memory.get("projects"):
        lines.append(f"💼 Projects: {', '.join(memory['projects'])}")
    
    if memory.get("preferences"):
        lines.append(f"⚙️ Preferences: {', '.join(memory['preferences'])}")
    
    if memory.get("notes"):
        lines.append(f"📝 Notes: {', '.join(memory['notes'])}")
    
    conv_count = len(memory.get("conversation_history", []))
    lines.append(f"💬 Recent conversations: {conv_count}")
    
    text = "\n".join(lines) if len(lines) > 1 else "📚 I haven't learned anything about you yet!"
    await update.message.reply_text(text)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command."""
    from memory_manager import initialize_memory
    initialize_memory()
    await update.message.reply_text("🧹 My memory has been cleared!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages."""
    user_message = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or f"User{user_id}"
    
    logger.info(f"[{user_name}] {user_message}")
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    # Load memory
    memory = load_memory()
    
    # Build prompt with memory injection
    prompt = build_prompt(user_message, memory)
    
    # Get response from Ollama
    try:
        response = ask_ollama(prompt)
    except OllamaTimeoutError:
        enqueue_retry_item(update.effective_chat.id, user_message)
        await update.message.reply_text(
            "⚠️ Ollama timed out while processing your request. I've queued it and will retry shortly."
        )
        return
    except OllamaError:
        enqueue_retry_item(update.effective_chat.id, user_message)
        await update.message.reply_text(
            "⚠️ I couldn't reach Ollama right now. Your message has been queued and I'll retry again soon."
        )
        return
    
    # Truncate for Telegram (max 4096 chars)
    if len(response) > 4000:
        response = response[:4000] + "..."
    
    # Detect and update memory from user input
    if config.AUTO_DETECT_MEMORY:
        try:
            memory = detect_and_update_memory(memory, user_message)
        except Exception as e:
            logger.warning(f"Memory detection error: {e}")
    
    # Add conversation to history
    try:
        memory = add_conversation(memory, user_message, response)
    except Exception as e:
        logger.warning(f"Conversation append error: {e}")
        memory.setdefault("conversation_history", []).append({
            "user": user_message,
            "assistant": response
        })
    
    # Save updated memory
    try:
        save_memory(memory)
    except Exception as e:
        logger.error(f"Memory save error: {e}")
    
    # Send response
    await update.message.reply_text(response)


async def process_retry_queue(app: Application) -> None:
    """Retry any queued messages that previously failed due to Ollama issues."""
    queue = load_retry_queue()
    if not queue:
        return

    pending = []
    for item in queue:
        chat_id = item.get("chat_id")
        user_message = item.get("user_message")
        attempts = item.get("attempts", 0)

        if attempts >= config.MAX_RETRY_ATTEMPTS:
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "⚠️ I couldn't process a previous message after several retries. "
                        "Please try again later."
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to notify chat {chat_id} about dropped retry: {e}")
            continue

        memory = load_memory()
        prompt = build_prompt(user_message, memory)

        try:
            response = ask_ollama(prompt)
        except OllamaTimeoutError as e:
            item["attempts"] = attempts + 1
            logger.warning(f"Retry attempt {attempts + 1} timed out for chat {chat_id}: {e}")
            pending.append(item)
            continue
        except OllamaError as e:
            item["attempts"] = attempts + 1
            logger.warning(f"Retry attempt {attempts + 1} failed for chat {chat_id}: {e}")
            pending.append(item)
            continue

        # Update memory and save conversation
        if config.AUTO_DETECT_MEMORY:
            try:
                memory = detect_and_update_memory(memory, user_message)
            except Exception as e:
                logger.warning(f"Memory detection error during retry: {e}")

        try:
            memory = add_conversation(memory, user_message, response)
        except Exception as e:
            logger.warning(f"Conversation append error during retry: {e}")
            memory.setdefault("conversation_history", []).append({
                "user": user_message,
                "assistant": response
            })

        try:
            save_memory(memory)
        except Exception as e:
            logger.error(f"Memory save error during retry: {e}")

        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text=(
                    "✅ I was able to retry your earlier message successfully.\n\n"
                    f"{response}"
                )
            )
        except Exception as e:
            logger.warning(f"Failed to send retry response to chat {chat_id}: {e}")

    save_retry_queue(pending)


async def retry_loop(app: Application) -> None:
    while True:
        await process_retry_queue(app)
        await asyncio.sleep(config.RETRY_INTERVAL_SECONDS)


async def on_app_init(app: Application) -> None:
    """Start the retry loop after the application initializes."""
    app.create_task(retry_loop(app))


def main():
    """Start the bot."""
    logger.info("Starting GingerAI Telegram Bot...")
    logger.info(f"Using model: {config.DEFAULT_MODEL}")
    logger.info(f"Ollama host: {config.OLLAMA_HOST}")
    
    # Create application
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(on_app_init).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    logger.info("Bot is polling for messages...")
    app.run_polling()


if __name__ == "__main__":
    main()
