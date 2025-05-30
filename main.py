import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from database import engine, Base  # Import Base from database
import models
from auth import router as auth_router
from routers import users, videos, categories, likes, comments, news
import asyncio  # Add this import

app = FastAPI(
    title="Video API",
    description="A Video streaming application for managing videos based on subscription.",
    version="1.0.0",
    redoc_url="/redoc",
    docs_url="/docs",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://dashboard-tau-mocha.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add this startup event handler
@app.on_event("startup")
async def startup_db():
    async with engine.begin() as conn:
        # This will create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully!")

# Include routers
app.include_router(auth_router)
app.include_router(users.router)
app.include_router(videos.router)
app.include_router(categories.router)
app.include_router(likes.router)
app.include_router(comments.router)
app.include_router(news.router)

# Redirect from / to /redoc
@app.get("/")
def read_root():
    return RedirectResponse(url="/redoc")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)