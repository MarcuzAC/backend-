import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    VIMEO_CLIENT_ID = os.getenv("VIMEO_CLIENT_ID")
    VIMEO_CLIENT_SECRET = os.getenv("VIMEO_CLIENT_SECRET")
    VIMEO_ACCESS_TOKEN = os.getenv("VIMEO_ACCESS_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")

settings = Settings()