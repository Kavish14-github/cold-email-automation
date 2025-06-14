import os
from pathlib import Path
import smtplib
import PyPDF2
import openai
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Load environment variables
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_PASS")

def get_resume_text(user_id: str) -> str:
    """Extracts text from a user's resume PDF stored at uploads/{user_id}/resume.pdf."""
    resume_path = Path(f"uploads/{user_id}/resume.pdf")
    if not resume_path.exists():
        raise FileNotFoundError(f"Resume not found at {resume_path}")
    
    try:
        with open(resume_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''.join([page.extract_text() or '' for page in pdf_reader.pages])
        return text
    except Exception as e:
        raise Exception(f"Error reading resume PDF: {str(e)}")

def generate_email(company_name: str, position: str, job_description: str, resume_text: str) -> str:
    """Uses OpenAI's GPT model to generate a personalized cold email."""
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
        raise Exception(f"OpenAI API error: {str(e)}")

def generate_followup(company: str, job: str) -> str:
    """Uses OpenAI to generate a professional follow-up email for a job application."""
    prompt = f"""
Write a concise and professional follow-up email (under 120 words) for a job application I sent over 2 days ago.
Company: {company}
Role: {job}
Do NOT repeat the subject line in body section of the email — assume it is already in the subject section of the email.

Start the email with: "Dear Hiring Manager,"

Reaffirm interest in the position politely, and ask to schedule a call at their convenience.

Best,  
Kavish Khatri  
kkhatri1411@gmail.com | 682-321-6296  
LinkedIn: https://www.linkedin.com/in/kavish-khatri/  
GitHub: https://github.com/Kavish14-github
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        raise Exception(f"OpenAI API error in follow-up: {str(e)}")

def send_email(to_email: str, subject: str, body: str, resume_path: Path = None):
    """Sends an email via Gmail SMTP with optional resume attachment."""
    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if resume_path and resume_path.exists():
        try:
            with open(resume_path, "rb") as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename="resume.pdf")
                msg.attach(part)
        except Exception as e:
            print(f"[!] Failed to attach resume: {e}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        print(f"[✔] Email sent to {to_email}")
    except Exception as e:
        print(f"[✘] Failed to send email to {to_email}: {e}")
