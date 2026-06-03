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
import re
import requests
import subprocess
import sys
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
from scraper import PageFetcher, MediaFinder, MediaDownloader
from scraper.url_utils import URLUtils

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
        "/download <formats> [limit] <url> - Download media from a webpage\n"
        "/start - Welcome message"
    )


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /download command."""
    await update.message.chat.send_action("typing")
    args = context.args
    parsed = _parse_download_args(args)
    if not parsed:
        await update.message.reply_text(
            "Usage: /download <formats> [limit] <url>\n"
            "Example: /download gif 3 https://example.com/gallery"
        )
        return

    formats, max_files, url = parsed
    await update.message.reply_text(
        f"Downloading up to {max_files or 'all'} {', '.join(formats)} file(s) from {url}..."
    )

    try:
        output_dir, downloaded, failed = await asyncio.to_thread(_download_media_from_url, url, formats, max_files)
        summary = _format_download_summary(output_dir, downloaded, failed)
        await update.message.reply_text(summary)
        if downloaded:
            await _send_downloaded_files(update, context, downloaded)
    except Exception as e:
        error_msg = str(e)
        if '403' in error_msg:
            await update.message.reply_text(
                f"⚠️ Access Denied (403)\n\n"
                f"The website blocks media downloads. This is common on:\n"
                f"• Sites with strong anti-scraping measures\n"
                f"• Protected image galleries\n"
                f"• Paid content sites\n\n"
                f"Try a different website or URL."
            )
        else:
            logger.error(f"Download command error: {error_msg}")
            await update.message.reply_text(f"⚠️ Failed to download media: {error_msg}")


def _create_output_directory(url: str) -> Path:
    """Create a unique numbered output directory for each URL request."""
    domain = URLUtils.get_domain_name(url)
    base_dir = Path(__file__).resolve().parent / "downloads"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Find next available numbered folder
    counter = 1
    while True:
        if counter == 1:
            output_dir = base_dir / domain
        else:
            output_dir = base_dir / f"{domain}_{counter}"
        
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created download folder: {output_dir.name}")
            return output_dir
        
        counter += 1


def _parse_download_args(args: list[str]) -> tuple[list[str], int, str] | None:
    """Parse /download command arguments."""
    if len(args) < 2:
        return None

    url = args[-1].strip()
    if not URLUtils.validate_url(url):
        return None

    formats = []
    max_files = 0
    for token in args[:-1]:
        normalized = token.lower().strip(',')
        if normalized.isdigit():
            max_files = int(normalized)
            continue
        if normalized.endswith('s'):
            normalized = normalized[:-1]
        if normalized in URLUtils.SUPPORTED_FORMATS:
            formats.append(normalized)

    if not formats:
        formats = ['gif']

    return formats, max_files, url


def _extract_download_request(text: str) -> tuple[list[str], int, str] | None:
    """Detect a natural-language download request and extract arguments."""
    text_lower = text.lower()
    if 'download' not in text_lower and 'grab' not in text_lower and 'fetch' not in text_lower:
        return None

    url_match = re.search(r"(https?://[^\s'\"]+)", text)
    if not url_match:
        return None

    url = url_match.group(1).rstrip('.,!')
    if not URLUtils.validate_url(url):
        return None

    formats = []
    for fmt in URLUtils.SUPPORTED_FORMATS:
        if re.search(rf"\b{fmt}s?\b", text_lower):
            formats.append(fmt)

    if not formats:
        if 'gif' in text_lower:
            formats = ['gif']
        elif 'jpg' in text_lower or 'jpeg' in text_lower:
            formats = ['jpg']
        elif 'png' in text_lower:
            formats = ['png']
        elif 'mp4' in text_lower:
            formats = ['mp4']
        elif 'webm' in text_lower:
            formats = ['webm']
        else:
            return None

    max_files = 0
    limit_match = re.search(r"limit\s+(\d+)", text_lower)
    if limit_match:
        max_files = int(limit_match.group(1))

    return formats, max_files, url


def _download_media_from_url(url: str, formats: list[str], max_files: int = 0) -> tuple[Path, list[Path], list[str]]:
    """Download media from a URL and return the saved file paths."""
    fetcher = PageFetcher()
    downloader = MediaDownloader()
    try:
        logger.info(f"Starting download from {url} for formats: {formats}, max_files: {max_files}")
        
        html, message = fetcher.fetch_page(url)
        if not html:
            raise ValueError(message)
        
        logger.info(f"Page fetched: {message}")

        media_urls = MediaFinder.find_media_urls(html, url, formats)
        logger.info(f"Found {len(media_urls)} media URLs")
        
        if not media_urls:
            raise ValueError("No media files found matching the selected formats.")

        if max_files > 0:
            media_urls = media_urls[:max_files]
            logger.info(f"Limited to {len(media_urls)} files (requested {max_files})")

        output_dir = _create_output_directory(url)
        downloader.download_media(media_urls, str(output_dir), show_progress=False)

        downloaded = []
        failed = downloader.download_stats.get('failed_urls', [])
        for path in output_dir.iterdir():
            if path.is_file():
                downloaded.append(path)

        logger.info(f"Download complete: {len(downloaded)} successful, {len(failed)} failed")
        
        if not downloaded and failed:
            # All downloads failed
            error_reason = "Access forbidden (403) - website blocks this scraper"
            if any('403' in str(err) for err in failed):
                error_reason = "Access forbidden (403) - website blocks this scraper"
            raise ValueError(f"Could not download any files. Reason: {error_reason}")

        return output_dir, downloaded, failed
    finally:
        fetcher.close()
        downloader.close()


def _format_download_summary(output_dir: Path, downloaded: list[Path], failed: list[str]) -> str:
    """Return a simple status summary for the bot."""
    lines = [
        f"Downloaded {len(downloaded)} file(s) to {output_dir.name}."
    ]
    if failed:
        lines.append(f"Failed downloads: {len(failed)}")
    return "\n".join(lines)


def _get_media_sender_method(file_path: Path):
    suffix = file_path.suffix.lower()
    if suffix == '.gif':
        return 'animation'
    if suffix in ['.jpg', '.jpeg', '.png']:
        return 'photo'
    if suffix in ['.mp4', '.webm']:
        return 'video'
    return 'document'


def _generate_file_caption(file_path: Path) -> str:
    return f"Downloaded file: {file_path.name}"


async def _send_downloaded_files(update: Update, context: ContextTypes.DEFAULT_TYPE, files: list[Path]) -> int:
    """Send downloaded files to the Telegram chat."""
    sent_count = 0
    for file_path in sorted(files):
        try:
            if _get_media_sender_method(file_path) == 'animation':
                with open(file_path, 'rb') as f:
                    await update.message.reply_animation(animation=f, caption=_generate_file_caption(file_path))
            elif _get_media_sender_method(file_path) == 'photo':
                with open(file_path, 'rb') as f:
                    await update.message.reply_photo(photo=f, caption=_generate_file_caption(file_path))
            elif _get_media_sender_method(file_path) == 'video':
                with open(file_path, 'rb') as f:
                    await update.message.reply_video(video=f, caption=_generate_file_caption(file_path))
            else:
                with open(file_path, 'rb') as f:
                    await update.message.reply_document(document=f, caption=_generate_file_caption(file_path))
            sent_count += 1
        except Exception as e:
            logger.warning(f"Failed to send {file_path.name}: {e}")
    return sent_count


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

    # Check for natural download request in text
    download_request = _extract_download_request(user_message)
    if download_request:
        formats, max_files, url = download_request
        await update.message.reply_text(
            f"Sure! Downloading up to {max_files or 'all'} {', '.join(formats)} file(s) from {url}..."
        )
        try:
            output_dir, downloaded, failed = await asyncio.to_thread(_download_media_from_url, url, formats, max_files)
            summary = _format_download_summary(output_dir, downloaded, failed)
            await update.message.reply_text(summary)
            if downloaded:
                await _send_downloaded_files(update, context, downloaded)
            return
        except Exception as e:
            error_msg = str(e)
            if '403' in error_msg:
                await update.message.reply_text(
                    "⚠️ Access Denied (403)\n\n"
                    "The website blocks media downloads from scrapers.\n"
                    "Try a different website or URL."
                )
            else:
                logger.error(f"Natural download error: {error_msg}")
                await update.message.reply_text(f"⚠️ I couldn't download media: {error_msg}")
            return
    
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
    try:
        logger.info("Starting GingerAI Telegram Bot...")
        logger.info(f"Using model: {config.DEFAULT_MODEL}")
        logger.info(f"Ollama host: {config.OLLAMA_HOST}")
        
        # Explicitly create and set event loop for Windows Python 3.14
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create application
        app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(on_app_init).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("memory", memory_command))
        app.add_handler(CommandHandler("clear", clear_command))
        app.add_handler(CommandHandler("download", download_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start polling - let python-telegram-bot use the event loop
        logger.info("Bot is polling for messages...")
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
