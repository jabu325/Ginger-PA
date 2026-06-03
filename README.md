# 🤖 GingerAI - Telegram Bot with Long-Term Memory

A Telegram bot powered by **Ollama** (local LLM) with persistent long-term memory via `memory.json`. The bot learns facts about you and remembers them across conversations.

## ✨ Features

- 🧠 **Long-term Memory**: Automatically remembers your name, projects, preferences, and notes
- 🔄 **Persistent**: Memory survives across bot restarts
- 🚀 **Local LLM**: Uses Ollama (dolphin-llama3:8b by default) — no API costs
- ⚡ **Real-time Polling**: Instant responses via Telegram polling
- 📝 **Auto-Learning**: Detects facts from natural language (e.g., "My name is Alex")

## 📋 Requirements

- Python 3.8+
- [Ollama](https://ollama.ai) installed and running
- Telegram bot token (from [@BotFather](https://t.me/BotFather))

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd "C:\Users\HP\Documents\Telegram Bots\GingerAI"
pip install -r requirements.txt
```

### 2. Start Ollama Server (in a separate terminal)

```bash
ollama serve
```

Or pull the model if not already present:

```bash
ollama pull dolphin-llama3:8b
```

### 3. Run the Bot

```bash
python ginger_bot.py
```

The bot will start polling Telegram and is ready to chat!

## 💬 Usage

1. Open Telegram and find your bot (token endpoint)
2. Send messages naturally:
   - `"My name is Techknight"`
   - `"I'm working on a Telegram bot"`
   - `"I prefer Python"`
   - `"Remember: My server is Ubuntu"`
3. Use commands:
   - `/memory` - See what I remember
   - `/clear` - Clear my memory
   - `/help` - Show help

## 📁 File Structure

```
GingerAI/
├── ginger_bot.py           # Main bot script
├── memory_manager.py       # Memory CRUD operations
├── config.py               # Configuration (token, model, paths)
├── memory.json             # Persistent memory store
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## ⚙️ Configuration

Edit `config.py` to customize:

```python
TELEGRAM_BOT_TOKEN = "your-token-here"
OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "dolphin-llama3:8b"
SYSTEM_PROMPT = "..."  # Bot personality
```

## 🧠 Memory System

Memory is stored in `memory.json`:

```json
{
  "user_name": "Techknight",
  "assistant_name": "GingerAI",
  "projects": ["Telegram bot", "AI voice assistant"],
  "preferences": ["Python", "Unix"],
  "notes": ["My server runs Ubuntu"],
  "conversation_history": [...]
}
```

The bot auto-detects and updates memory from patterns:
- "My name is X" → Updates `user_name`
- "I'm working on X" → Adds to `projects`
- "I prefer X" → Adds to `preferences`
- "Remember: X" → Adds to `notes`

## 🔧 Troubleshooting

**Bot doesn't respond:**
- Ensure Ollama is running: `ollama serve`
- Check token in `config.py`
- Verify Ollama model is installed: `ollama list`

**Memory not updating:**
- Check `memory.json` permissions
- Ensure `AUTO_DETECT_MEMORY = True` in `config.py`
- Check logs for errors

**Slow responses:**
- Larger models (8B) are slower; try smaller ones: `ollama pull neural-chat:7b`
- Increase `timeout` in `ask_ollama()` if needed

## 📝 Notes

- Conversations older than 10 are pruned from memory to avoid bloat
- Responses are truncated to 4000 chars for Telegram limits
- The bot uses HTTP polling (not webhooks) for simplicity

## 🎯 Future Ideas

- Voice message transcription
- Integration with vector DB for semantic memory
- Multi-user support with separate memory stores
- Scheduled reminders based on memory
