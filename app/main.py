import re
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llm import ask_llm_stream, classify_ticket, policy_answer
from logger import log_event

app = FastAPI(title="HR Helpdesk Assistant")

class ChatRequest(BaseModel):
    message: str

def get_employee_id(x_employee_id: str = Header(..., description="Employee ID for authentication")):
    if not x_employee_id:
        raise HTTPException(status_code=401, detail="X-Employee-ID header missing")
    return x_employee_id

# Catastrophic action guardrails
CATASTROPHIC_PATTERNS = [
    r"(?i)\bupdate\s+salary\b",
    r"(?i)\bchange\s+salary\b",
    r"(?i)\bmodify\s+leave\b",
    r"(?i)\badd\s+leave\b",
    r"(?i)\bdelete\s+record\b",
    r"(?i)\bfire\s+employee\b"
]

def check_guardrails(message: str):
    for pattern in CATASTROPHIC_PATTERNS:
        if re.search(pattern, message):
            log_event("Guardrail triggered", pattern=pattern, message=message)
            return True
    return False

@app.get("/")
def root():
    return {"message": "HR Helpdesk API is running"}

@app.post("/chat")
def chat(request: ChatRequest, employee_id: str = Depends(get_employee_id)):
    if check_guardrails(request.message):
        return {"response": "ERROR: Requested action is not permitted due to security guardrails."}
    
    return StreamingResponse(
        ask_llm_stream(employee_id, request.message),
        media_type="text/plain"
    )

@app.post("/classify-ticket")
def classify_hr_ticket(request: ChatRequest):
    ticket = classify_ticket(request.message)
    return ticket

@app.post("/policy-answer")
def answer_policy_question(request: ChatRequest):
    answer = policy_answer(request.message)
    return {"response": answer}
