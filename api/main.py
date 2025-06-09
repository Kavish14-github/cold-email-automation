from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from main import run_cold_emails, generate_email, send_email
from followup import run_followups
from pathlib import Path

from . import models, schemas, crud
from datetime import datetime

from .database import SessionLocal, engine

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
    background_tasks.add_task(run_cold_emails)
    return {"message": "Cold email job started"}

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