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

1. Start with a personalized hook showing excitement about {company}'s mission or product.
2. Briefly introduce me: I'm Kavish Khatri, a backend-focused software engineer with 3+ years of experience in building data pipelines and ML model serving systems.
3. Highlight relevant experiences in 3–4 bullet points:
    - Built Python/Node microservices and ML inference APIs on GCP and AWS
    - Integrated Redis/RabbitMQ for async workflows and analytics
    - Worked directly with founders on early-stage product direction and infra
4. Include:
    LinkedIn: https://www.linkedin.com/in/kavish-khatri/
    GitHub: https://github.com/Kavish14-github
5. End with this signature:

Best,  
Kavish Khatri  
kkhatri1411@gmail.com | 682-321-6296
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

    with open("KavishKhatri.pdf", "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header('Content-Disposition', 'attachment', filename="KavishKhatri.pdf")
        msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)

def run_cold_emails():
    try:
        # Load uploaded resume
        resume_path = Path("uploads/resume.txt")
        if not resume_path.exists():
            return {"status": "error", "message": "Uploaded resume.txt not found in /uploads"}

        with open(resume_path, "r", encoding="utf-8") as file:
            resume_text = file.read()

        # DB connection
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT"),
            sslmode='require'
        )
        cursor = conn.cursor()

        cursor.execute("SELECT id, company_name, job_title, job_description, recipient_email FROM applications WHERE status = 'pending'")
        rows = cursor.fetchall()

        if not rows:
            return {"status": "done", "message": "No pending applications"}

        for row in rows:
            app_id, company, job, description, recipient = row
            try:
                email_body = generate_email(company, job, description, resume_text)
                subject = f"Excited by {company}'s Mission—Interested in the {job} Role"
                send_email(recipient, subject, email_body)

                cursor.execute(
                    "UPDATE applications SET status = 'sent', sent_at = NOW(), email_body = %s WHERE id = %s",
                    (email_body, app_id)
                )
                conn.commit()
                print(f"Email sent to {recipient}")

            except Exception as e:
                print(f"Failed to send to {recipient}: {e}")

        return {"status": "done", "message": f"{len(rows)} cold emails sent"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
