from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from typing import Optional
from . import schemas
from sqlalchemy.orm import Session
from . import crud
from .database import get_db
from . import models

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class AuthHandler:
    async def get_current_user(self, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        try:
            # Decode the JWT using Supabase client
            user_info = supabase.auth.get_user(token)
            if not user_info or not user_info.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user_id = user_info.user.id  # This is the Supabase UID (sub)
            # Fetch user from your database
            db_user = crud.get_user(db, user_id)
            if not db_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return db_user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def signup(self, email: str, password: str):
        try:
            # Sign up with Supabase
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "email": email
                    },
                    "email_redirect_to": "http://localhost:8000/login"  # Redirect after email confirmation
                }
            })
            
            if not response or not response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user"
                )
            
            # Return a success message with instructions
            return {
                "message": "Registration successful! Please check your email to confirm your account.",
                "user": response.user
            }
            
        except Exception as e:
            error_message = str(e)
            if "User already registered" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered. Please try logging in instead."
                )
            elif "Email not confirmed" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please check your email to confirm your account before logging in."
                )
            else:
                print(f"Signup error: {error_message}")  # Add logging
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Registration failed: {error_message}"
                )

    async def login(self, email: str, password: str):
        try:
            # Sign in with Supabase
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not response or not response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return {
                "user": response.user,
                "session": response.session,
                "email": email
            }
            
        except Exception as e:
            error_message = str(e)
            if "Email not confirmed" in error_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please check your email to confirm your account before logging in."
                )
            else:
                print(f"Login error: {error_message}")  # Add logging
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

auth_handler = AuthHandler()

def create_application(db: Session, application: schemas.ApplicationCreate, user_id: str):
    db_application = models.Application(
        **application.dict(),
        user_id=user_id
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application 

def get_user_applications(db: Session, user_id: str, skip: int = 0, limit: int = 10):
    return db.query(models.Application).filter(models.Application.user_id == user_id).offset(skip).limit(limit).all() 
