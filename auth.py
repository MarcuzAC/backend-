from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from crud import get_user_by_username
from schemas import Token, UserResponse, UserCreate
from security import verify_password, get_password_hash  
from jose import JWTError, jwt
from datetime import timedelta, datetime
from typing import Optional
import models
from models import User
from sqlalchemy.future import select

SECRET_KEY = "ivneWx0gdaNz9IEjeIAnhrUwFYLVYDHKQlrOoUYpi4GLxT_5YzF_KJ9d6s6XagXoMzxvMgJOZr765zoSPtglZw"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter(tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Authenticate user (for login)
async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

# Create JWT access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Get the current logged-in user
async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# 🔥 NEW: Register a new user
@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if username or email is already registered
    existing_user = await db.execute(select(User).filter(User.username == user.username))
    if existing_user.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")

    existing_email = await db.execute(select(User).filter(User.email == user.email))
    if existing_email.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = get_password_hash(user.password)

    # Create new user
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        is_admin=False
    )

    # Add and commit to DB
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create token for new user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": new_user.username, "user_id":str(new_user.id), "email":new_user.email, "phone":new_user.phone_number}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        #"user_id": new_user.id
    }
# 🔥 NEW: Get current user details
#@router.get("/me", response_model=UserResponse)
#async def read_users_me(current_user: User = Depends(get_current_user)):
    #return current_user
@router.post("/refresh")
async def refresh_token(refresh_token: str = Body(...)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        new_token = create_access_token(data={"sub": payload["sub"]})
        return {"access_token": new_token}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# User Login
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
# Add the /user-details endpoint
@router.get("/user-details", response_model=UserResponse)
async def get_user_details(current_user: User = Depends(get_current_user)):
    return current_user

# Add this endpoint to verify access tokens
@router.get("/verify-token")
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verify the access token and return basic user information.
    This endpoint is protected and requires a valid JWT token.
    """
    return {
        "message": "Token is valid",
        "username": current_user.username,
        "user_id": current_user.id,
        "is_admin": current_user.is_admin
    }