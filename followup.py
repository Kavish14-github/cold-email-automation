# followup.py

import openai
import smtplib
import os
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import PyPDF2

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

def generate_followup(company, job, resume_text):
    prompt = f"""
Write a concise and professional follow-up email (under 100 words) for a job application I sent over 2 days ago.

Company: {company}
Role: {job}

Based on the following resume:
{resume_text}

Guidelines:
1. Start with "Dear Hiring Manager,"
2. Reaffirm interest in the position politely
3. Reference specific qualifications from the resume that match the role
4. Ask to schedule a call at their convenience
5. Keep it brief and professional
6. Include contact information from the resume

IMPORTANT:
- DO NOT include the subject line in the email body.
- Start directly with the greeting.
- The subject line will be handled separately, so don't reference it in the body.
- Keep the tone professional and concise.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300
    )
    return response['choices'][0]['message']['content']

def run_followups():
    try:
        # Load uploaded resume PDF and extract text
        resume_pdf_path = Path("uploads/resume.pdf")
        if not resume_pdf_path.exists():
            error_msg = "Uploaded resume.pdf not found in /uploads"
            print(error_msg)
            return {"status": "error", "message": error_msg}

        print("Extracting text from resume PDF...")
        try:
            resume_text = extract_text_from_pdf(resume_pdf_path)
            if not resume_text.strip():
                error_msg = "No text could be extracted from the PDF. Please ensure the PDF is not scanned or image-based."
                print(error_msg)
                return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Error processing resume PDF: {str(e)}"
            print(error_msg)
            return {"status": "error", "message": error_msg}

        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT"),
            sslmode='require'
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, company_name, job_title, recipient_email, sent_at
            FROM applications
            WHERE status = 'sent' AND sent_at <= NOW() - INTERVAL '2 days'
        """)
        rows = cursor.fetchall()

        if not rows:
            return {"status": "done", "message": "No follow-ups needed"}

        sent_count = 0
        error_count = 0
        errors = []

        for row in rows:
            app_id, company, job, recipient, sent_at = row
            print(f"\nProcessing follow-up for {company}...")
            
            try:
                print("Generating follow-up content...")
                followup_body = generate_followup(company, job, resume_text)
                subject = f"Following up on {job} at {company}"

                print(f"Sending follow-up to {recipient}...")
                send_email(recipient, subject, followup_body)

                print("Updating database status...")
                cursor.execute(
                    "UPDATE applications SET status = 'followed_up' WHERE id = %s",
                    (app_id,)
                )
                conn.commit()
                print(f"Successfully sent follow-up to {recipient}")
                sent_count += 1

            except Exception as e:
                error_msg = f"Failed to send follow-up to {recipient}: {str(e)}"
                print(error_msg)
                errors.append({"recipient": recipient, "error": str(e)})
                error_count += 1
                continue

        summary = {
            "status": "done",
            "message": f"Process completed. Sent: {sent_count}, Errors: {error_count}",
            "details": {
                "sent_count": sent_count,
                "error_count": error_count,
                "errors": errors
            }
        }
        print(f"\nProcess summary: {summary['message']}")
        return summary

    except Exception as e:
        error_msg = f"Unexpected error in run_followups: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

def run_followups_by_ids(application_ids):
    sent = []
    errors = []

    try:
        # Load uploaded resume PDF and extract text
        resume_pdf_path = Path("uploads/resume.pdf")
        if not resume_pdf_path.exists():
            error_msg = "Uploaded resume.pdf not found in /uploads"
            print(error_msg)
            return {"status": "error", "message": error_msg}

        print("Extracting text from resume PDF...")
        try:
            resume_text = extract_text_from_pdf(resume_pdf_path)
            if not resume_text.strip():
                error_msg = "No text could be extracted from the PDF. Please ensure the PDF is not scanned or image-based."
                print(error_msg)
                return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Error processing resume PDF: {str(e)}"
            print(error_msg)
            return {"status": "error", "message": error_msg}

        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT"),
            sslmode='require'
        )
        cursor = conn.cursor()

        for app_id in application_ids:
            cursor.execute("SELECT company_name, job_title, recipient_email, status FROM applications WHERE id = %s", (app_id,))
            row = cursor.fetchone()

            if not row:
                errors.append({"id": app_id, "error": "Not found"})
                continue

            company, job, recipient, status = row

            if status == 'followed_up':
                errors.append({"id": app_id, "error": "Already followed up"})
                continue

            try:
                print(f"\nProcessing follow-up for {company}...")
                print("Generating follow-up content...")
                body = generate_followup(company, job, resume_text)
                subject = f"Following up on {job} at {company}"
                
                print(f"Sending follow-up to {recipient}...")
                send_email(recipient, subject, body)

                print("Updating database status...")
                cursor.execute(
                    "UPDATE applications SET status = 'followed_up', followed_up_at = %s WHERE id = %s",
                    (datetime.utcnow(), app_id)
                )
                conn.commit()
                print(f"Successfully sent follow-up to {recipient}")
                sent.append(app_id)

            except Exception as e:
                error_msg = f"Failed to send follow-up to {recipient}: {str(e)}"
                print(error_msg)
                errors.append({"id": app_id, "error": str(e)})

        return {"followed_up": sent, "errors": errors}

    except Exception as e:
        error_msg = f"Unexpected error in run_followups_by_ids: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}