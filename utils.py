from jose import JWTError, jwt
from datetime import datetime, timedelta
import aiosmtplib
from email.message import EmailMessage

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