from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from main import run_cold_emails, generate_email, send_email
from followup import run_followups, run_followups_by_ids
from pathlib import Path
from . import models, schemas, crud
from datetime import datetime
from .database import SessionLocal, engine
import shutil
from pathlib import Path

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/applications/", response_model=schemas.ApplicationResponse)
def create_application(application: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    return crud.create_application(db, application)

# ✅ Use List[] instead of list[] here
@app.get("/applications/", response_model=List[schemas.ApplicationResponse])
def read_applications(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_items(db, skip=skip, limit=limit)

@app.get("/applications/{application_id}", response_model=schemas.ApplicationResponse)
def read_application(application_id: int, db: Session = Depends(get_db)):
    db_app = crud.get_item(db, application_id)
    if db_app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return db_app

@app.get("/applications/status/{status}", response_model=List[schemas.ApplicationResponse])
def get_applications_by_status(status: str, db: Session = Depends(get_db)):
    valid_statuses = {"sent", "pending", "followed_up"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status value")
    
    return db.query(models.Application).filter(models.Application.status == status).all()

@app.put("/applications/{application_id}", response_model=schemas.ApplicationResponse)
def update_application(application_id: int, application: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    return crud.update_application(db, application_id, application)

@app.delete("/applications/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    db_app = crud.delete_item(db, application_id)
    if db_app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"ok": True}

@app.post("/trigger-cold-emails")
def trigger_cold_emails(background_tasks: BackgroundTasks):
    try:
        print("Starting cold email background task...")
        background_tasks.add_task(run_cold_emails)
        return {
            "status": "started",
            "message": "Cold email job started in the background",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        error_msg = f"Failed to start cold email job: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/trigger-followups")
def trigger_followups(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_followups)
    return {"message": "Follow-up job started in the background"}

@app.post("/send-selected-emails")
def send_selected_emails(payload: schemas.IDList, db: Session = Depends(get_db)):
    resume_path = Path("resume.txt")
    if not resume_path.exists():
        raise HTTPException(status_code=500, detail="Resume file missing")

    with open(resume_path, "r", encoding="utf-8") as file:
        resume_text = file.read()

    sent = []
    errors = []

    for app_id in payload.application_ids:
        app = db.query(models.Application).filter(models.Application.id == app_id).first()
        if not app:
            errors.append({"id": app_id, "error": "Not found"})
            continue

        if app.status == "sent":
            errors.append({"id": app_id, "error": "Already sent"})
            continue

        try:
            email_body = generate_email(app.company_name, app.job_title, app.job_description, resume_text)
            subject = f"Excited by {app.company_name}'s Mission—Interested in the {app.job_title} Role"
            send_email(app.recipient_email, subject, email_body)

            app.status = "sent"
            app.sent_at = datetime.utcnow()
            app.email_body = email_body
            db.commit()
            sent.append(app_id)
        except Exception as e:
            errors.append({"id": app_id, "error": str(e)})

    return {"sent": sent, "errors": errors}

@app.post("/send-selected-followups")
def send_selected_followups(payload: schemas.IDList):
    return run_followups_by_ids(payload.application_ids)

@app.post("/upload-resume")
def upload_resume(file: UploadFile = File(...)):
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    # Optional: restrict to only .pdf or .txt
    if file.content_type not in ["application/pdf", "text/plain"]:
        raise HTTPException(status_code=400, detail="Only .pdf or .txt files allowed")

    # Determine the final path based on file type
    if file.filename.endswith(".pdf"):
        final_path = uploads_dir / "resume.pdf"
    else:
        final_path = uploads_dir / "resume.txt"

    # If file exists, remove it first
    if final_path.exists():
        final_path.unlink()

    # Save the file directly to the final path
    with open(final_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": final_path.name, "message": "Resume uploaded successfully"}