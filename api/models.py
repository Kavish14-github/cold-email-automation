from sqlalchemy import Column, Integer, String, Text, DateTime
from .database import Base
from datetime import datetime

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(Text, nullable=False)
    job_title = Column(Text, nullable=False)
    job_description = Column(Text, nullable=False)
    recipient_email = Column(Text, nullable=False)
    email_body = Column(Text, nullable=True)
    status = Column(Text, nullable=True, default="pending")
    sent_at = Column(DateTime, nullable=True)
    followed_up_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
