import json
from pathlib import Path
from typing import List, Dict, Any

MEMORY_PATH = Path("data/memory.json")

def _load_memory_file() -> Dict[str, List[Dict[str, Any]]]:
    if not MEMORY_PATH.exists():
        return {}
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def _save_memory_file(data: Dict[str, List[Dict[str, Any]]]):
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_history(employee_id: str) -> List[Dict[str, Any]]:
    """Retrieve conversation history for an employee."""
    data = _load_memory_file()
    return data.get(employee_id, [])

def add_message(employee_id: str, role: str, content: str):
    """Add a message to the employee's history."""
    data = _load_memory_file()
    if employee_id not in data:
        data[employee_id] = []
    
    # Simple deduplication or structure logic (e.g., limit history to last 20 messages)
    data[employee_id].append({"role": role, "content": content})
    
    # Truncate history if too long to save tokens (e.g. max 10 messages)
    if len(data[employee_id]) > 10:
        data[employee_id] = data[employee_id][-10:]
        
    _save_memory_file(data)

def add_tool_call_and_response(employee_id: str, tool_call_msg: dict, tool_response_msg: dict):
    """Adds tool call and tool response messages to the history."""
    data = _load_memory_file()
    if employee_id not in data:
        data[employee_id] = []
    
    data[employee_id].append(tool_call_msg)
    data[employee_id].append(tool_response_msg)
    
    if len(data[employee_id]) > 10:
        data[employee_id] = data[employee_id][-10:]
        
    _save_memory_file(data)
