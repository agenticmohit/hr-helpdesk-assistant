import re
import time
import uuid
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from llm import ask_llm_stream, ask_llm_sync, classify_ticket, policy_answer
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

def check_guardrails(message: str, request_id: str):
    for pattern in CATASTROPHIC_PATTERNS:
        if re.search(pattern, message):
            log_event("Guardrail triggered", request_id=request_id, pattern=pattern, message=message, status="rejected")
            return True
    return False

@app.get("/")
def root():
    return {"message": "HR Helpdesk API is running"}

@app.post("/chat")
def chat(request: ChatRequest, employee_id: str = Depends(get_employee_id)):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    log_event("Incoming request", request_id=request_id, endpoint="/chat", employee_id=employee_id)
    
    if check_guardrails(request.message, request_id):
        latency = time.time() - start_time
        log_event("Request completed", request_id=request_id, status="error", latency_sec=latency)
        return {"response": "ERROR: Requested action is not permitted due to security guardrails."}
    
    # We yield the stream and calculate latency at the end inside llm.py, 
    # but we can pass request_id to llm.py
    return StreamingResponse(
        ask_llm_stream(employee_id, request.message, request_id),
        media_type="text/plain"
    )

@app.post("/chat-sync")
def chat_sync(request: ChatRequest, employee_id: str = Depends(get_employee_id)):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    log_event("Incoming request", request_id=request_id, endpoint="/chat-sync", employee_id=employee_id)
    
    if check_guardrails(request.message, request_id):
        latency = time.time() - start_time
        log_event("Request completed", request_id=request_id, status="error", latency_sec=latency)
        return {"response": "ERROR: Requested action is not permitted due to security guardrails."}
    
    response = ask_llm_sync(employee_id, request.message, request_id)
    latency = time.time() - start_time
    log_event("Request completed", request_id=request_id, status="success", latency_sec=latency)
    
    return {"response": response}

@app.post("/classify-ticket")
def classify_hr_ticket(request: ChatRequest):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    log_event("Incoming request", request_id=request_id, endpoint="/classify-ticket")
    ticket = classify_ticket(request.message)
    latency = time.time() - start_time
    log_event("Request completed", request_id=request_id, status="success", latency_sec=latency)
    return ticket

@app.post("/policy-answer")
def answer_policy_question(request: ChatRequest):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    log_event("Incoming request", request_id=request_id, endpoint="/policy-answer")
    answer = policy_answer(request.message)
    latency = time.time() - start_time
    log_event("Request completed", request_id=request_id, status="success", latency_sec=latency)
    return {"response": answer}
