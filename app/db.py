import json
from pathlib import Path
from typing import Optional, Dict, Any

DB_PATH = Path("data/db.json")

def load_db() -> Dict[str, Any]:
    if not DB_PATH.exists():
        return {}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_employee_record(requested_employee_id: str, authenticated_employee_id: str) -> str:
    """
    Securely fetches an employee record.
    Only allows an employee to fetch their own record.
    """
    if requested_employee_id != authenticated_employee_id:
        return "ERROR: Unauthorized. You can only request your own employee records."
    
    db = load_db()
    record = db.get(requested_employee_id)
    
    if not record:
        return f"ERROR: Employee record for {requested_employee_id} not found."
    
    return json.dumps(record, indent=2)
