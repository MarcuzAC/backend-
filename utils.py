from jose import JWTError, jwt
from datetime import datetime, timedelta
import aiosmtplib
from email.message import EmailMessage
import os
import uuid
from fastapi import HTTPException, status
from config import supabase, settings
from typing import Optional
from fastapi import UploadFile

# JWT Configuration
SECRET_KEY = "your-secret-key"  
ALGORITHM = "HS256"
RESET_TOKEN_EXPIRE_MINUTES = 30

# Email Configuration
SMTP_SERVER = "aspmx.l.google.com"  
SMTP_PORT = 25
SMTP_USERNAME = "MarcuzAC"  
SMTP_PASSWORD = "Fizosat2010"  

def create_reset_token(email: str) -> str:
    expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expires}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def send_reset_email(email: str, token: str):
    message = EmailMessage()
    message["From"] = SMTP_USERNAME
    message["To"] = email
    message["Subject"] = "Password Reset Request"
    message.set_content(f"Use this token to reset your password: {token}")

    await aiosmtplib.send(
        message,
        hostname=SMTP_SERVER,
        port=SMTP_PORT,
        username=SMTP_USERNAME,
        password=SMTP_PASSWORD,
        use_tls=True,
    )


async def upload_to_supabase(file: UploadFile, file_name: str) -> str:
    try:
        contents = await file.read()
        res = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            file=contents,
            path=file_name,
            file_options={"content-type": file.content_type}
        )
        return supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(file_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

async def delete_from_supabase(file_url: str) -> bool:
    try:
        file_name = file_url.split('/')[-1].split('?')[0]
        res = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([file_name])
        return True
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )
async def save_upload_file(file: UploadFile) -> str:
    """
    Saves an uploaded file to Supabase Storage with a unique filename.
    Returns the public URL of the uploaded file.
    """
    file_ext = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_ext}"
    return await upload_to_supabase(file, unique_filename)
