from fastapi import HTTPException
from pathlib import Path
from datetime import datetime
from api import models, crud
from email_utils import generate_email, send_email

def get_resume_text(user_id: str) -> str:
    """Get resume text from either PDF or TXT file."""
    resume_path = Path(f"uploads/{user_id}/resume.txt")
    if not resume_path.exists():
        resume_path = Path(f"uploads/{user_id}/resume.pdf")
        if not resume_path.exists():
            raise HTTPException(status_code=500, detail="Resume file missing")
    
    with open(resume_path, "r", encoding="utf-8") as file:
        return file.read()

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