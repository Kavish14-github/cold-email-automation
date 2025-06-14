from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class User(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ApplicationBase(BaseModel):
    company_name: str
    position: str
    job_description: str
    recipient_email: str
    email_body: Optional[str] = None
    status: str = "pending"
    sent_at: Optional[datetime] = None
    followed_up_at: Optional[datetime] = None

    class Config:
        schema_extra = {
            "example": {
                "company_name": "string",
                "position": "string",
                "job_description": "string",
                "recipient_email": "string",
                "email_body": "string",
                "status": "pending"
            }
        }

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: int
    user_id: str
    class Config:
        from_attributes = True

class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = None
    position: Optional[str] = None
    job_description: Optional[str] = None
    recipient_email: Optional[str] = None
    email_body: Optional[str] = None
    status: Optional[str] = None
    sent_at: Optional[datetime] = None
    followed_up_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class IDList(BaseModel):
    ids: List[int]

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    email: str