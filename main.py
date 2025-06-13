# main.py

import os
from dotenv import load_dotenv
from fastapi import HTTPException
from pathlib import Path
from datetime import datetime
from api import models, crud
from email_utils import generate_email, send_email

# This file is kept for backward compatibility
# The main functionality has been moved to job_runner.py

# Load environment variables
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_PASS")

def get_resume_text(user_id: str) -> str:
    """Get resume text from either PDF or TXT file."""
    resume_path = Path(f"uploads/{user_id}/resume.txt")
    if not resume_path.exists():
        resume_path = Path(f"uploads/{user_id}/resume.pdf")
        if not resume_path.exists():
            raise HTTPException(status_code=500, detail="Resume file missing")
    
    with open(resume_path, "r", encoding="utf-8") as file:
        return file.read()

def generate_email(company_name: str, job_title: str, job_description: str, resume_text: str) -> str:
    """Generate a personalized cold email using OpenAI."""
    prompt = f"""Based on the following resume and job details, write a personalized cold email that:
1. Shows genuine interest in the company and role
2. Highlights relevant experience from the resume
3. Maintains a professional yet conversational tone
4. Is concise and impactful
5. Ends with a clear call to action

Resume:
{resume_text}

Job Details:
Company: {company_name}
Position: {job_title}
Description: {job_description}

Write the email body only, without subject line or signature."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional email writer specializing in cold outreach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email: {str(e)}")

def send_email(recipient: str, subject: str, body: str):
    """Send email using configured email service."""
    # Implement your email sending logic here
    # For now, we'll just print the email details
    print(f"Sending email to {recipient}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")

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

def run_cold_emails(user_id: str):
    """Run cold email generation for all pending applications."""
    try:
        # Get database session
        from api.database import SessionLocal
        db = SessionLocal()
        
        # Get user's resume
        resume_text = get_resume_text(user_id)
        
        # Get pending applications
        pending_apps = crud.get_user_applications_by_status(db, user_id, "pending")
        
        for app in pending_apps:
            try:
                email_body = generate_email(
                    app.company_name,
                    app.job_title,
                    app.job_description,
                    resume_text
                )
                subject = f"Excited by {app.company_name}'s Mission—Interested in the {app.job_title} Role"
                send_email(app.recipient_email, subject, email_body)
                
                # Update application status
                app.status = "sent"
                app.sent_at = datetime.utcnow()
                app.email_body = email_body
                db.commit()
                
            except Exception as e:
                print(f"Error processing application {app.id}: {str(e)}")
                continue
        
        db.close()
        
    except Exception as e:
        print(f"Error in run_cold_emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
