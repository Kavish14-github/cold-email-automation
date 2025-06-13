from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    position = Column(String, nullable=False)
    job_description = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    email_body = Column(Text)
    status = Column(String, default="pending")
    sent_at = Column(DateTime)
    followed_up_at = Column(DateTime)
    created_at = Column(DateTime)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="applications")

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime)

    applications = relationship("Application", back_populates="user")
