from datetime import datetime
from api import crud
from api.database import SessionLocal
from email_utils import get_resume_text, generate_email, send_email
from pathlib import Path

async def run_cold_emails(user_id: str):
    try:
        print(f"[DEBUG] run_cold_emails started for user_id: {user_id}", flush=True)
        ...
    except Exception as e:
        print(f"[ERROR] run_cold_emails failed: {e}", flush=True)

    db = SessionLocal()
    try:
        resume_path = Path(f"uploads/{user_id}/resume.pdf")
        resume_text = get_resume_text(user_id)
        pending_apps = crud.get_user_applications_by_status(db, user_id, "pending")

        for app in pending_apps:
            try:
                email_body = generate_email(app.company_name, app.position, app.job_description, resume_text)
                subject = f"Excited by {app.company_name}'s Mission—Interested in the {app.position} Role"
                send_email(app.recipient_email, subject, email_body, resume_path)

                app.status = "sent"
                app.sent_at = datetime.utcnow()
                app.email_body = email_body
                db.commit()
            except Exception as e:
                print(f"[✘] Error processing application {app.id}: {e}")
    except Exception as e:
        print(f"[✘] Cold email job failed: {e}")
    finally:
        db.close()