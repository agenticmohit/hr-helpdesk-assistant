import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from models import TicketClassification
from prompts import (
    SYSTEM_PROMPT,
    TICKET_CLASSIFICATION_PROMPT,
    POLICY_PROMPT
)
from db import get_employee_record
from memory import get_history, add_message, add_tool_call_and_response
from logger import log_event

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1", 
    api_key=os.getenv("OPENROUTER_API_KEY")
)
MODEL = "google/gemini-2.5-flash"

POLICIES_PATH = Path("data/policies.md")

def load_policies():
    return POLICIES_PATH.read_text(encoding="utf-8")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_policy",
            "description": "Retrieves the company HR policies.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_employee_record",
            "description": "Retrieves the employee record for the authenticated user, including leave balances and department.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def calculate_cost(usage) -> float:
    if not usage: return 0.0
    # Approximate cost for gemini-2.5-flash via OpenRouter
    prompt_cost = (usage.prompt_tokens / 1_000_000) * 0.075
    completion_cost = (usage.completion_tokens / 1_000_000) * 0.30
    return prompt_cost + completion_cost

def ask_llm_stream(employee_id: str, message: str):
    log_event("Started ask_llm_stream", employee_id=employee_id, user_message=message)
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = get_history(employee_id)
    messages.extend(history)
    
    user_msg = {"role": "user", "content": message}
    messages.append(user_msg)
    add_message(employee_id, "user", message)
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            stream=False # We use False first to handle tool calls simply. Streaming tool calls requires more complex logic.
        )
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            log_event("Tool call requested", employee_id=employee_id, tool_calls=[tc.function.name for tc in msg.tool_calls])
            
            tool_call_dict = msg.model_dump()
            # Convert tool_calls to dict correctly
            tool_call_msg = {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": tool_call_dict["tool_calls"]
            }
            messages.append(tool_call_msg)
            
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                
                if func_name == "get_policy":
                    result = load_policies()
                elif func_name == "get_employee_record":
                    result = get_employee_record(employee_id, employee_id)
                else:
                    result = f"Error: unknown tool {func_name}"
                
                tool_response_msg = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                }
                messages.append(tool_response_msg)
                add_tool_call_and_response(employee_id, tool_call_msg, tool_response_msg)
            
            # Second call with tool responses
            stream_response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True}
            )
            
            full_content = ""
            for chunk in stream_response:
                if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield content
                
                if chunk.usage:
                    cost = calculate_cost(chunk.usage)
                    log_event("LLM Completed", employee_id=employee_id, tokens=chunk.usage.total_tokens, cost=cost)
            
            add_message(employee_id, "assistant", full_content)
        else:
            # No tool calls, standard stream response
            full_content = ""
            if msg.content:
                full_content = msg.content
                yield msg.content
                
            if response.usage:
                cost = calculate_cost(response.usage)
                log_event("LLM Completed", employee_id=employee_id, tokens=response.usage.total_tokens, cost=cost)
                
            add_message(employee_id, "assistant", full_content)
            
    except Exception as e:
        log_event("LLM Error", level=40, employee_id=employee_id, error=str(e))
        yield f"Error processing request: {e}"

def classify_ticket(message: str):
    log_event("Started classify_ticket", user_message=message)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": TICKET_CLASSIFICATION_PROMPT},
                {"role": "user", "content": message}
            ],
            response_format={"type": "json_object"}
        )
        raw_output = response.choices[0].message.content
        data = json.loads(raw_output)
        ticket = TicketClassification.model_validate(data)
        
        if response.usage:
            cost = calculate_cost(response.usage)
            log_event("Ticket Classified", tokens=response.usage.total_tokens, cost=cost, category=ticket.category)
            
        return ticket.model_dump()
    except json.JSONDecodeError:
        return {"error": "Model returned invalid JSON."}
    except ValidationError as e:
        return {"error": "Model output did not match the required schema.", "details": str(e)}
    except Exception as e:
        return {"error": f"OpenRouter Error: {e}"}

def policy_answer(message: str):
    log_event("Started policy_answer", user_message=message)
    try:
        policies = load_policies()
        user_input = f"HR POLICY DOCUMENT:\n---BEGIN POLICY---\n{policies}\n---END POLICY---\nEMPLOYEE QUESTION:\n{message}"
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": POLICY_PROMPT},
                {"role": "user", "content": user_input}
            ]
        )
        
        if response.usage:
            cost = calculate_cost(response.usage)
            log_event("Policy Answered", tokens=response.usage.total_tokens, cost=cost)
            
        return response.choices[0].message.content
    except Exception as e:
        log_event("Policy Error", level=40, error=str(e))
        return f"OpenRouter Error: {e}"