# main.py

import openai
import smtplib
import os
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from pathlib import Path
import PyPDF2

# Load environment variables
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_PASS")

def generate_email(company, job, description, resume_text):
    prompt = f"""
You are a helpful assistant that writes professional, personalized cold emails for job applications.

Company: {company}  
Role: {job}  
Job Description: {description}

Based on the following resume, write a personalized cold email:
{resume_text}

Guidelines:
1. Start with a personalized hook showing excitement about {company}'s mission or product.
2. Briefly introduce the candidate using relevant information from their resume.
3. Highlight 3-4 most relevant experiences from their resume that match the job requirements in bullet points.
4. Include their contact information and professional links from the resume.
5. Keep the tone professional but conversational.
6. End with a clear call to action.

IMPORTANT:
- The email should be concise (under 150 words) and focus on how the candidate's specific experiences align with the role.
- DO NOT include the subject line in the email body.
- Start directly with the greeting (e.g., "Dear Hiring Manager,").
- The subject line will be handled separately, so don't reference it in the body.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500
    )
    return response['choices'][0]['message']['content']

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

def run_cold_emails():
    try:
        print("Starting cold email process...")
        
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

        # DB connection
        print("Connecting to database...")
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                port=os.getenv("DB_PORT"),
                sslmode='require'
            )
            cursor = conn.cursor()
            print("Database connection successful")
        except Exception as db_error:
            error_msg = f"Database connection failed: {str(db_error)}"
            print(error_msg)
            return {"status": "error", "message": error_msg}

        print("Fetching pending applications...")
        cursor.execute("SELECT id, company_name, job_title, job_description, recipient_email FROM applications WHERE status = 'pending'")
        rows = cursor.fetchall()
        print(f"Found {len(rows)} pending applications")

        if not rows:
            return {"status": "done", "message": "No pending applications"}

        sent_count = 0
        error_count = 0
        errors = []

        for row in rows:
            app_id, company, job, description, recipient = row
            print(f"\nProcessing application {app_id} for {company}...")
            
            try:
                print("Generating email content...")
                email_body = generate_email(company, job, description, resume_text)
                subject = f"Excited by {company}'s Mission—Interested in the {job} Role"
                
                print(f"Sending email to {recipient}...")
                send_email(recipient, subject, email_body)

                print("Updating database status...")
                cursor.execute(
                    "UPDATE applications SET status = 'sent', sent_at = NOW(), email_body = %s WHERE id = %s",
                    (email_body, app_id)
                )
                conn.commit()
                print(f"Successfully sent email to {recipient}")
                sent_count += 1

            except Exception as e:
                error_msg = f"Failed to send to {recipient}: {str(e)}"
                print(error_msg)
                errors.append({"recipient": recipient, "error": str(e)})
                error_count += 1
                # Continue with next application even if one fails
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
        error_msg = f"Unexpected error in run_cold_emails: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}
