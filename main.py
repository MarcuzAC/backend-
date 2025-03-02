from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from database import engine
import models
from auth import router as auth_router
from routers import users, videos, categories
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI(
    title="Video API",
    description="A Video streaming application for managing videos based on subcription.",
    version="1.0.0",
    redoc_url="/redoc", 
    docs_url="/docs",  
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users.router)
app.include_router(videos.router)
app.include_router(categories.router)

# Redirect from / to /redoc
@app.get("/")
def read_root():
    return RedirectResponse(url="/redoc")
