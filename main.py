# main.py

import os
from dotenv import load_dotenv
from fastapi import HTTPException
from pathlib import Path
from datetime import datetime
from api import models, crud
from email_utils import generate_email, send_email
import openai
import PyPDF2

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Load environment variables
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_PASS")

def get_resume_text(user_id: str) -> str:
    """Get resume text from either PDF or TXT file."""
    pdf_path = Path(f"uploads/{user_id}/resume.pdf")
    if pdf_path.exists():
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
    else:
        raise HTTPException(status_code=500, detail="Resume PDF file missing")

def generate_email(company_name: str, position: str, job_description: str, resume_text: str) -> str:
    """Generate a personalized cold email using OpenAI."""
    prompt = f"""Based on the following resume and job details, write a personalized cold email (should be less than 150 words) that:
1. Shows genuine interest in the company and role
2. Highlights relevant experience from the resume
3. Maintains a professional yet conversational tone
4. Is concise and impactful
5. Ends with a clear call to action

Resume:
{resume_text}

Job Details:
Company: {company_name}
Position: {position}
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

def send_email(to_email, subject, body, resume_path=None):
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))


    if resume_path and resume_path.exists():
        with open(resume_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename="resume.pdf")
            msg.attach(part)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        print(f"[✔] Email successfully sent to {to_email}")
    except Exception as e:
        print(f"[✘] Failed to send email to {to_email}: {e}")

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