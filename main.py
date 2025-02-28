from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import SessionLocal, Like, Comment

# Load environment variables
load_dotenv()

VIDEOS_URL = os.getenv("VIDEOS_URL")
SEARCH_URL = os.getenv("SEARCH_URL")
CHANNEL_URL = os.getenv("CHANNEL_URL")
SHOWCASE_URL = os.getenv("SHOWCASE_URL")

app = FastAPI()

# Allow CORS for React Native app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message": "FastAPI Vimeo API is running!"}

@app.get("/videos")
def get_vimeo_videos():
    try:
        response = requests.get(VIDEOS_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_vimeo_videos(q: str = Query(..., title="Search Query")):
    try:
        response = requests.get(SEARCH_URL, params={"q": q})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/channel")
def get_channel_videos(channel_id: str = Query(..., title="Vimeo Channel ID")):
    try:
        response = requests.get(CHANNEL_URL, params={"channel_id": channel_id})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/showcase")
def get_showcase_videos(album_id: str = Query(..., title="Vimeo Album ID")):
    try:
        response = requests.get(SHOWCASE_URL, params={"album_id": album_id})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Add Like
@app.post("/likes/")
def add_like(user_id: int, video_id: str, db: Session = Depends(get_db)):
    new_like = Like(user_id=user_id, video_id=video_id)
    db.add(new_like)
    db.commit()
    return {"message": "Like added"}

# ✅ Add Comment
@app.post("/comments/")
def add_comment(user_id: int, video_id: str, text: str, db: Session = Depends(get_db)):
    new_comment = Comment(user_id=user_id, video_id=video_id, text=text)
    db.add(new_comment)
    db.commit()
    return {"message": "Comment added"}

# ✅ Get Comments for a Video
@app.get("/comments/{video_id}")
def get_comments(video_id: str, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.video_id == video_id).all()
    return comments

# Run FastAPI
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
