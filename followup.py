# followup.py

import openai
import smtplib
import os
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
import PyPDF2
from fastapi import HTTPException
from sqlalchemy.orm import Session
from api import models, crud
from email_utils import generate_followup, send_email

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_PASS")

def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            # Create PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract text from all pages
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    resume_path = Path("uploads/resume.pdf")
    if not resume_path.exists():
        raise FileNotFoundError("Resume PDF not found in /uploads. Please upload it first.")

    try:
        with open(resume_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename="Resume.pdf")
            msg.attach(part)
    except Exception as e:
        raise Exception(f"Error attaching resume: {str(e)}")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
    except Exception as e:
        raise Exception(f"Error sending email: {str(e)}")

def get_resume_text(user_id: str) -> str:
    """Get resume text from either PDF or TXT file."""
    resume_path = Path(f"uploads/{user_id}/resume.txt")
    if not resume_path.exists():
        resume_path = Path(f"uploads/{user_id}/resume.pdf")
        if not resume_path.exists():
            raise HTTPException(status_code=500, detail="Resume file missing")
    
    with open(resume_path, "r", encoding="utf-8") as file:
        return file.read()

def generate_followup(company_name: str, job_title: str, original_email: str, resume_text: str) -> str:
    """Generate a follow-up email using OpenAI."""
    prompt = f"""Based on the following information, write a professional follow-up email that:
1. References the original email
2. Maintains interest in the position
3. Adds new value or information
4. Is concise and respectful
5. Has a clear call to action

Company: {company_name}
Position: {job_title}
Original Email:
{original_email}

Resume:
{resume_text}

Write the email body only, without subject line or signature."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional email writer specializing in follow-up communications."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate follow-up: {str(e)}")

def run_followups(user_id: str):
    """Run follow-up generation for all sent applications that haven't been followed up."""
    try:
        # Get database session
        from api.database import SessionLocal
        db = SessionLocal()
        
        # Get user's resume
        resume_text = get_resume_text(user_id)
        
        # Get sent applications that haven't been followed up
        sent_apps = crud.get_user_applications_by_status(db, user_id, "sent")
        
        for app in sent_apps:
            # Check if it's been at least 5 days since the original email
            if not app.sent_at or (datetime.utcnow() - app.sent_at) < timedelta(days=5):
                continue
                
            try:
                followup_body = generate_followup(
                    app.company_name,
                    app.job_title,
                    app.email_body,
                    resume_text
                )
                subject = f"Following up: {app.job_title} Position at {app.company_name}"
                send_email(app.recipient_email, subject, followup_body)
                
                # Update application status
                app.status = "followed_up"
                app.followup_body = followup_body
                app.followup_sent_at = datetime.utcnow()
                db.commit()
                
            except Exception as e:
                print(f"Error processing follow-up for application {app.id}: {str(e)}")
                continue
        
        db.close()
        
    except Exception as e:
        print(f"Error in run_followups: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def run_followups_by_ids(application_ids: list[int], user_id: str):
    """Run follow-up generation for specific applications."""
    try:
        # Get database session
        from api.database import SessionLocal
        db = SessionLocal()
        
        # Get user's resume
        resume_text = get_resume_text(user_id)
        
        sent = []
        errors = []
        
        for app_id in application_ids:
            app = crud.get_user_application(db, app_id, user_id)
            if not app:
                errors.append({"id": app_id, "error": "Not found"})
                continue
                
            if app.status != "sent":
                errors.append({"id": app_id, "error": "Application not in sent status"})
                continue
                
            try:
                followup_body = generate_followup(
                    app.company_name,
                    app.job_title,
                    app.email_body,
                    resume_text
                )
                subject = f"Following up: {app.job_title} Position at {app.company_name}"
                send_email(app.recipient_email, subject, followup_body)
                
                # Update application status
                app.status = "followed_up"
                app.followup_body = followup_body
                app.followup_sent_at = datetime.utcnow()
                db.commit()
                
                sent.append(app_id)
                
            except Exception as e:
                errors.append({"id": app_id, "error": str(e)})
                continue
        
        db.close()
        return {"sent": sent, "errors": errors}
        
    except Exception as e:
        print(f"Error in run_followups_by_ids: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))