from typing import Literal
from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class TicketClassification(BaseModel):
    category: Literal[
        "leave",
        "payroll",
        "reimbursement",
        "benefits",
        "workplace",
        "other",
    ]

    priority: Literal[
        "low",
        "medium",
        "high",
        "urgent",
    ]

    summary: str

    requires_human: bool
