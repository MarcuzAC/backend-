import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from database import engine
import models
from auth import router as auth_router
from routers import users, videos, categories, likes, comments,news

app = FastAPI(
    title="Video API",
    description="A Video streaming application for managing videos based on subscription.",
    version="1.0.0",
    redoc_url="/redoc",  # This will set the URL for the ReDoc documentation
    docs_url="/docs",  # This will set the URL for the Swagger UI documentation
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://dashboard-tau-mocha.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)