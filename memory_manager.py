"""
Memory Manager for Ollama Long-Term Memory System (V1)

Responsibilities:
- Load Memory
- Save Memory
- Add New Memories
- Retrieve Memories
- Update Memories
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMORY_FILE = Path(__file__).resolve().parent / "memory.json"


def load_memory() -> Dict[str, Any]:
    """Load memory from memory.json file."""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Memory file not found: {MEMORY_FILE}. Creating new one...")
        return initialize_memory()
    except json.JSONDecodeError:
        print(f"Memory file corrupted: {MEMORY_FILE}. Creating new one...")
        return initialize_memory()


def save_memory(memory: Dict[str, Any]) -> None:
    """Save memory to memory.json file."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=4, ensure_ascii=False)


def initialize_memory() -> Dict[str, Any]:
    """Initialize empty memory structure."""
    memory = {
        "user_name": "",
        "assistant_name": "GingerAI",
        "projects": [],
        "preferences": [],
        "notes": [],
        "conversation_history": []
    }
    save_memory(memory)
    return memory


def get_user_name(memory: Dict[str, Any]) -> str:
    """Retrieve user's name from memory."""
    return memory.get("user_name", "")


def set_user_name(memory: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Store user's name in memory."""
    memory["user_name"] = name
    return memory


def get_assistant_name(memory: Dict[str, Any]) -> str:
    """Retrieve assistant's name from memory."""
    return memory.get("assistant_name", "GingerAI")


def set_assistant_name(memory: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Set assistant's name in memory."""
    memory["assistant_name"] = name
    return memory


def add_project(memory: Dict[str, Any], project: str) -> Dict[str, Any]:
    """Add a new project to memory."""
    if project not in memory["projects"]:
        memory["projects"].append(project)
    return memory


def get_projects(memory: Dict[str, Any]) -> List[str]:
    """Retrieve all projects from memory."""
    return memory.get("projects", [])


def add_preference(memory: Dict[str, Any], preference: str) -> Dict[str, Any]:
    """Add a new preference to memory."""
    if preference not in memory["preferences"]:
        memory["preferences"].append(preference)
    return memory


def get_preferences(memory: Dict[str, Any]) -> List[str]:
    """Retrieve all preferences from memory."""
    return memory.get("preferences", [])


def add_note(memory: Dict[str, Any], note: str) -> Dict[str, Any]:
    """Add a general note to memory."""
    if note not in memory["notes"]:
        memory["notes"].append(note)
    return memory


def get_notes(memory: Dict[str, Any]) -> List[str]:
    """Retrieve all notes from memory."""
    return memory.get("notes", [])


def add_conversation(memory: Dict[str, Any], user_msg: str, assistant_msg: str) -> Dict[str, Any]:
    """Add conversation to history (optional, for keeping recent context)."""
    memory["conversation_history"].append({
        "user": user_msg,
        "assistant": assistant_msg
    })
    # Keep only last 10 conversations to avoid memory bloat
    if len(memory["conversation_history"]) > 10:
        memory["conversation_history"] = memory["conversation_history"][-10:]
    return memory


def get_memory_context(memory: Dict[str, Any]) -> str:
    """Build a text representation of memory for prompt injection."""
    context_parts = []
    
    # User information
    if memory.get("user_name"):
        context_parts.append(f"User Name: {memory['user_name']}")
    
    # Assistant information
    if memory.get("assistant_name"):
        context_parts.append(f"Assistant Name: {memory['assistant_name']}")
    
    # Projects
    projects = memory.get("projects", [])
    if projects:
        context_parts.append(f"User's Projects: {', '.join(projects)}")
    
    # Preferences
    preferences = memory.get("preferences", [])
    if preferences:
        context_parts.append(f"User's Preferences: {', '.join(preferences)}")
    
    # Notes
    notes = memory.get("notes", [])
    if notes:
        context_parts.append(f"Important Notes: {', '.join(notes)}")
    
    return "\n".join(context_parts)


def get_conversation_history_text(memory: Dict[str, Any], limit: int = 5) -> str:
    """Build a text representation of recent conversations for context."""
    conversations = memory.get("conversation_history", [])
    if not conversations:
        return ""
    
    # Get the last N conversations
    recent = conversations[-limit:] if len(conversations) > limit else conversations
    
    lines = ["Recent Conversation History:"]
    for conv in recent:
        user_msg = conv.get("user", "").strip()
        asst_msg = conv.get("assistant", "").strip()
        if user_msg:
            lines.append(f"User: {user_msg}")
        if asst_msg:
            lines.append(f"Assistant: {asst_msg}")
    
    return "\n".join(lines)


def get_full_memory_context(memory: Dict[str, Any], include_history: bool = True, history_limit: int = 5) -> str:
    """Build full memory context including facts and conversation history."""
    context_parts = [get_memory_context(memory)]
    
    if include_history:
        history_text = get_conversation_history_text(memory, history_limit)
        if history_text:
            context_parts.append(history_text)
    
    return "\n\n".join(filter(None, context_parts))


def detect_and_update_memory(memory: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    """
    Automatically detect and update memory based on user input.
    
    Detects patterns like:
    - "my name is X"
    - "I am working on X" or "I'm building X"
    - "I prefer X"
    - "Remember: X" or "Remember this: X"
    """
    user_lower = user_input.lower()
    
    # Detect name
    if "my name is" in user_lower:
        try:
            name = user_input.split("is")[-1].strip().rstrip(".")
            if name and len(name) < 50:
                memory = set_user_name(memory, name)
        except Exception:
            pass
    
    # Detect projects (working on, building, developing)
    if any(phrase in user_lower for phrase in ["working on", "building", "developing", "creating"]):
        try:
            if "working on" in user_lower:
                project = user_input.split("working on")[-1].strip().rstrip(".")
            elif "building" in user_lower:
                project = user_input.split("building")[-1].strip().rstrip(".")
            elif "developing" in user_lower:
                project = user_input.split("developing")[-1].strip().rstrip(".")
            elif "creating" in user_lower:
                project = user_input.split("creating")[-1].strip().rstrip(".")
            else:
                project = ""
            
            if project and len(project) < 200:
                memory = add_project(memory, project)
        except Exception:
            pass
    
    # Detect preferences
    if "prefer" in user_lower:
        try:
            preference = user_input.split("prefer")[-1].strip().rstrip(".")
            if preference and len(preference) < 150:
                memory = add_preference(memory, preference)
        except Exception:
            pass
    
    # Detect notes (explicit remember command)
    if "remember" in user_lower and ":" in user_input:
        try:
            note = user_input.split(":")[-1].strip().rstrip(".")
            if note and len(note) < 200:
                memory = add_note(memory, note)
        except Exception:
            pass
    
    return memory
