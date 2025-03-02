from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from database import get_db
from auth import router as auth_router
from routers import users, videos, categories

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get database instance
db = get_db()

# Include routers with MongoDB dependency
app.include_router(auth_router)
app.include_router(users.router)
app.include_router(videos.router)
app.include_router(categories.router)

# Redirect from / to /redoc
@app.get("/")
def read_root():
    return RedirectResponse(url="/redoc")

# Example route to test MongoDB connection
@app.get("/test-db")
async def test_db():
    collections = await db.list_collection_names()
    return {"collections": collections}
