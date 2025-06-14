from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from job_runner import run_cold_emails
from followup import run_followups, run_followups_by_ids
from pathlib import Path
from . import models, schemas, crud
from datetime import datetime
from .database import SessionLocal, engine, get_db
from .auth import auth_handler
import shutil
from fastapi.security import OAuth2PasswordRequestForm

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Auth endpoints
@app.post("/signup")
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    auth_response = await auth_handler.signup(user.email, user.password)
    db_user = crud.create_user(db, user, auth_response["user"].id)
    return {
        "message": auth_response["message"],
        "user": {
            "id": db_user.id,
            "email": db_user.email
        }
    }

@app.post("/token", response_model=schemas.LoginResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    auth_response = await auth_handler.login(form_data.username, form_data.password)
    return schemas.LoginResponse(
        access_token=auth_response["session"].access_token,
        token_type="bearer",
        email=form_data.username
    )

@app.post("/login", response_model=schemas.LoginResponse)
async def login(user: schemas.UserLogin):
    auth_response = await auth_handler.login(user.email, user.password)
    return schemas.LoginResponse(
        access_token=auth_response["session"].access_token,
        token_type="bearer",
        email=user.email
    )

# Application endpoints (now user-specific)
@app.post("/applications/", response_model=schemas.ApplicationResponse)
async def create_application(
    application: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth_handler.get_current_user)
):
    return crud.create_application(db, application, current_user.id)

@app.get("/applications/", response_model=List[schemas.ApplicationResponse])
async def read_applications(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(auth_handler.get_current_user)
):
    return crud.get_user_applications(db, current_user.id, skip=skip, limit=limit)

@app.get("/applications/{application_id}", response_model=schemas.ApplicationResponse)
async def read_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth_handler.get_current_user)
):
    db_app = crud.get_user_application(db, application_id, current_user.id)
    if db_app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return db_app

@app.get("/applications/status/{status}", response_model=List[schemas.ApplicationResponse])
async def get_applications_by_status(
    status: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth_handler.get_current_user)
):
    valid_statuses = {"sent", "pending", "followed_up"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status value")
    return crud.get_user_applications_by_status(db, current_user.id, status)

@app.put("/applications/{application_id}", response_model=schemas.ApplicationResponse)
async def update_application(
    application_id: int,
    application: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth_handler.get_current_user)
):
    return crud.update_user_application(db, application_id, application, current_user.id)

@app.delete("/applications/{application_id}")
async def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(auth_handler.get_current_user)
):
    db_app = crud.delete_user_application(db, application_id, current_user.id)
    if db_app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"ok": True}

@app.post("/trigger-cold-emails")
async def trigger_cold_emails(
    background_tasks: BackgroundTasks,
    current_user=Depends(auth_handler.get_current_user)
):
    try:
        print("Starting cold email background task...")
        background_tasks.add_task(run_cold_emails, current_user.id)
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
async def trigger_followups(
    background_tasks: BackgroundTasks,
    current_user=Depends(auth_handler.get_current_user)
):
    background_tasks.add_task(run_followups, current_user.id)
    return {"message": "Follow-up job started in the background"}

@app.post("/send-selected-emails")
async def send_selected_emails(
    payload: schemas.IDList,
    db: Session = Depends(get_db),
    current_user=Depends(auth_handler.get_current_user)
):
    return crud.send_selected_emails(db, payload.application_ids, current_user.id)

@app.post("/send-selected-followups")
async def send_selected_followups(
    payload: schemas.IDList,
    current_user=Depends(auth_handler.get_current_user)
):
    return run_followups_by_ids(payload.application_ids, current_user.id)

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user=Depends(auth_handler.get_current_user)
):
    uploads_dir = Path(f"uploads/{current_user.id}")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    if file.content_type not in ["application/pdf", "text/plain"]:
        raise HTTPException(status_code=400, detail="Only .pdf or .txt files allowed")

    if file.filename.endswith(".pdf"):
        final_path = uploads_dir / "resume.pdf"
    else:
        final_path = uploads_dir / "resume.txt"

    if final_path.exists():
        final_path.unlink()

    with open(final_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": final_path.name, "message": "Resume uploaded successfully"}