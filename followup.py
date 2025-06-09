# followup_email.py

import openai
import smtplib
import os
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
gmail_user = os.getenv("GMAIL_USER")
gmail_password = os.getenv("GMAIL_PASS")

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

def generate_followup(company, job):
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
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300
    )
    return response['choices'][0]['message']['content']

def run_followups():
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

        cursor.execute("""
            SELECT id, company_name, job_title, recipient_email, sent_at
            FROM applications
            WHERE status = 'sent' AND sent_at <= NOW() - INTERVAL '2 days'
        """)
        rows = cursor.fetchall()

        if not rows:
            return {"status": "done", "message": "No follow-ups needed"}

        for row in rows:
            app_id, company, job, recipient, sent_at = row
            followup_body = generate_followup(company, job)
            subject = f"Following up on {job} at {company}"

            try:
                send_email(recipient, subject, followup_body)
                print(f"Follow-up sent to {recipient}")

                cursor.execute(
                    "UPDATE applications SET status = 'followed_up' WHERE id = %s",
                    (app_id,)
                )
                conn.commit()
            except Exception as e:
                print(f"Failed to send follow-up to {recipient}: {e}")

        return {"status": "done", "message": f"{len(rows)} follow-ups sent"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
def run_followups_by_ids(application_ids):
    sent = []
    errors = []

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
                body = generate_followup(company, job)
                subject = f"Following up on {job} at {company}"
                send_email(recipient, subject, body)

                cursor.execute(
                    "UPDATE applications SET status = 'followed_up', followed_up_at = %s WHERE id = %s",
                    (datetime.utcnow(), app_id)
                )
                conn.commit()
                sent.append(app_id)

            except Exception as e:
                errors.append({"id": app_id, "error": str(e)})

        return {"followed_up": sent, "errors": errors}

    except Exception as e:
        return {"status": "error", "message": str(e)}