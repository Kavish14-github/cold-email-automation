# from fastapi import FastAPI, Depends, HTTPException
# from sqlalchemy.orm import Session
# from . import models, schemas, crud
# from .database import SessionLocal, engine

# models.Base.metadata.create_all(bind=engine)
# app = FastAPI()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# @app.post("/applications/", response_model=schemas.ApplicationCreate)
# def create_application(application: schemas.ApplicationCreate, db: Session = Depends(get_db)):
#     return crud.create_application(db, application)

# @app.get("/applications/", response_model=list[schemas.ApplicationCreate])
# def read_applications(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
#     return crud.get_items(db, skip=skip, limit=limit)  # You can rename this to get_applications

# @app.get("/applications/{application_id}", response_model=schemas.ApplicationCreate)
# def read_application(application_id: int, db: Session = Depends(get_db)):
#     db_app = crud.get_item(db, application_id)
#     if db_app is None:
#         raise HTTPException(status_code=404, detail="Application not found")
#     return db_app

# @app.put("/applications/{application_id}", response_model=schemas.ApplicationCreate)
# def update_application(application_id: int, application: schemas.ApplicationCreate, db: Session = Depends(get_db)):
#     return crud.update_application(db, application_id, application)

# @app.delete("/applications/{application_id}")
# def delete_application(application_id: int, db: Session = Depends(get_db)):
#     db_app = crud.delete_item(db, application_id)
#     if db_app is None:
#         raise HTTPException(status_code=404, detail="Application not found")
#     return {"ok": True}


from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List  # ✅ Added for compatibility

from . import models, schemas, crud
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

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
