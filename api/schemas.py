from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApplicationCreate(BaseModel):
    company_name: str
    job_title: str
    job_description: str
    recipient_email: str
    email_body: Optional[str] = None
    status: Optional[str] = "pending"
    sent_at: Optional[datetime] = None
    followed_up_at: Optional[datetime] = None
