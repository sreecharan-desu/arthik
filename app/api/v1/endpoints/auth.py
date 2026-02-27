from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from app.models.models import Users
from passlib.context import CryptContext
from app.db.session import get_db
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone
import os
import requests

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

SECRET_KEY = os.getenv("SECRET_KEY", "c626778ab8558c653679edcb6f47e25a7c726b53bb8712dd7a255fbbd937d6db")
ALGORITHM = "HS256"

class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

class GoogleAuthCode(BaseModel):
    code: str

def authenticate_user(username: str, password: str, db: Session):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: str, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)], db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user.")
        
        user = db.query(Users).filter(Users.id == user_id).first()
        if not user:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
        
        # Compatibility with old code that expects a dict
        user_dict = {
            'username': user.username,
            'id': user.id,
            'role': user.role,
            'email': user.email
        }
        return user_dict
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user.")

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(create_user_request: CreateUserRequest, db: Session = Depends(get_db)):
    existing_user = db.query(Users).filter(
        (Users.username == create_user_request.username) | 
        (Users.email == create_user_request.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exists."
        )

    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        role=create_user_request.role,
        is_active=True
    )
    db.add(create_user_model)
    db.commit()
    db.refresh(create_user_model)
    
    return {"message": "Account created successfully"}
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user.")
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=60))
    return {'access_token': token, 'token_type': 'bearer'}

@router.get("/google/login")
@router.post("/google/login")
def google_login():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = f"{os.getenv('APP_URL')}/auth/google/callback"
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=email%20profile"
    }

@router.get("/google/callback")
@router.post("/google/callback")
async def google_callback(code: str = None, payload: GoogleAuthCode = None, db: Session = Depends(get_db)):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = f"{os.getenv('APP_URL')}/auth/google/callback"
    
    # Extract code from query or body payload
    auth_code = code if code else (payload.code if payload else None)
    if not auth_code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Exchange code for token
    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    })
    
    if not token_resp.ok:
        raise HTTPException(status_code=400, detail=f"Google Token Exchange Failed: {token_resp.text}")
        
    token_json = token_resp.json()
    access_token = token_json.get("access_token")
    
    user_info_resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={
        "Authorization": f"Bearer {access_token}"
    })
    
    if not user_info_resp.ok:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")
        
    user_info = user_info_resp.json()
    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user = db.query(Users).filter(Users.email == email).first()
    
    if not user:
        # Create new user
        user = Users(
            email=email,
            username=email.split("@")[0],
            first_name=user_info.get("given_name"),
            last_name=user_info.get("family_name"),
            hashed_password=None, # Google users don't have a local password by default
            role="guest",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=60))
    
    # If it's a GET request (browser redirect), and we have a FRONTEND_URL, redirect back
    frontend_url = os.getenv("FRONTEND_URL")
    if code and frontend_url:
        return RedirectResponse(url=f"{frontend_url}/auth/callback?token={token}")
        
    return {"access_token": token, "token_type": "bearer"}