from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from email_utils import generate_email, send_email

def get_item(db: Session, item_id: int):
    return db.query(models.Application).filter(models.Application.id == item_id).first()

def get_items(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Application).offset(skip).limit(limit).all()

def create_application(db: Session, application: schemas.ApplicationCreate, user_id: str):
    db_app = models.Application(
        **application.dict(),
        user_id=user_id
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app

def delete_item(db: Session, item_id: int):
    item = get_item(db, item_id)
    if item:
        db.delete(item)
        db.commit()
    return item

def update_application(db: Session, application_id: int, new_data: schemas.ApplicationCreate):
    application = db.query(models.Application).filter(models.Application.id == application_id).first()
    if application:
        for key, value in new_data.dict(exclude_unset=True).items():
            setattr(application, key, value)
        db.commit()
        db.refresh(application)
    return application

def get_user_applications(db: Session, user_id: str, skip: int = 0, limit: int = 10):
    return db.query(models.Application)\
        .filter(models.Application.user_id == user_id)\
        .offset(skip)\
        .limit(limit)\
        .all()

def get_user_application(db: Session, application_id: int, user_id: str):
    return db.query(models.Application)\
        .filter(models.Application.id == application_id)\
        .filter(models.Application.user_id == user_id)\
        .first()

def get_user_applications_by_status(db: Session, user_id: str, status: str):
    return db.query(models.Application)\
        .filter(models.Application.user_id == user_id)\
        .filter(models.Application.status == status)\
        .all()

def update_user_application(db: Session, application_id: int, application: schemas.ApplicationCreate, user_id: str):
    db_app = get_user_application(db, application_id, user_id)
    if db_app is None:
        return None
    
    for key, value in application.dict().items():
        setattr(db_app, key, value)
    
    db.commit()
    db.refresh(db_app)
    return db_app

def delete_user_application(db: Session, application_id: int, user_id: str):
    db_app = get_user_application(db, application_id, user_id)
    if db_app is None:
        return None
    
    db.delete(db_app)
    db.commit()
    return db_app

def send_selected_emails(db: Session, application_ids: list[int], user_id: str):
    resume_path = Path(f"uploads/{user_id}/resume.txt")
    if not resume_path.exists():
        resume_path = Path(f"uploads/{user_id}/resume.pdf")
        if not resume_path.exists():
            raise HTTPException(status_code=500, detail="Resume file missing")

    with open(resume_path, "r", encoding="utf-8") as file:
        resume_text = file.read()

    sent = []
    errors = []

    for app_id in application_ids:
        app = get_user_application(db, app_id, user_id)
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

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, supabase_user_id: str):
    db_user = models.User(
        id=supabase_user_id,
        email=user.email
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_application(db: Session, application_id: int, user_id: str):
    return db.query(models.Application).filter(
        models.Application.id == application_id,
        models.Application.user_id == user_id
    ).first()

def get_applications(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.Application).filter(
        models.Application.user_id == user_id
    ).offset(skip).limit(limit).all()

def update_application(db: Session, application_id: int, application: schemas.ApplicationUpdate, user_id: str):
    db_application = get_application(db, application_id, user_id)
    if not db_application:
        return None
    
    for key, value in application.dict(exclude_unset=True).items():
        setattr(db_application, key, value)
    
    db.commit()
    db.refresh(db_application)
    return db_application

def delete_application(db: Session, application_id: int, user_id: str):
    db_application = get_application(db, application_id, user_id)
    if not db_application:
        return None
    
    db.delete(db_application)
    db.commit()
    return db_application

def get_pending_applications(db: Session, user_id: str):
    return db.query(models.Application).filter(
        models.Application.user_id == user_id,
        models.Application.status == "pending"
    ).all()

def update_application_status(db: Session, application_id: int, status: str, user_id: str):
    db_application = get_application(db, application_id, user_id)
    if not db_application:
        return None
    
    db_application.status = status
    db_application.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_application)
    return db_application
