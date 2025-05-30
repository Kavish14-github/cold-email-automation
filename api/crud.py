from sqlalchemy.orm import Session
from . import models, schemas

def get_item(db: Session, item_id: int):
    return db.query(models.Application).filter(models.Application.id == item_id).first()

def get_items(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Application).offset(skip).limit(limit).all()

def create_application(db: Session, application: schemas.ApplicationCreate):
    db_application = models.Application(**application.dict())
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application    

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
