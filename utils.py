from jose import JWTError, jwt
from datetime import datetime, timedelta
import aiosmtplib
from email.message import EmailMessage
import os
import uuid
from fastapi import UploadFile, HTTPException, status

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


async def save_upload_file(file: UploadFile):
    """Save uploaded file to static folder and return URL"""
    try:
        # Create uploads directory if it doesn't exist
        os.makedirs("static/uploads", exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = file.filename.split(".")[-1]
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.{file_ext}"
        filepath = f"static/uploads/{filename}"
        
        # Save file
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return f"/static/uploads/{filename}"
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )