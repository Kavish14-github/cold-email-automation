from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from cold_email import run_cold_emails

from . import models, schemas, crud
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

@app.post("/applications/", response_model=schemas.ApplicationCreate)
def create_application(application: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    return crud.create_application(db, application)

# ✅ Use List[] instead of list[] here
@app.get("/applications/", response_model=List[schemas.ApplicationCreate])
def read_applications(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_items(db, skip=skip, limit=limit)

@app.get("/applications/{application_id}", response_model=schemas.ApplicationCreate)
def read_application(application_id: int, db: Session = Depends(get_db)):
    db_app = crud.get_item(db, application_id)
    if db_app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return db_app

@app.put("/applications/{application_id}", response_model=schemas.ApplicationCreate)
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
