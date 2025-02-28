from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Database connection URL
DATABASE_URL = "sqlite:///./database.db"

# Creating database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Creating a session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Creating a base class for models
Base = declarative_base()

# Like model
class Like(Base):
    __tablename__ = "likes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    video_id = Column(String, nullable=False)

# Comment model
class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    video_id = Column(String, nullable=False)
    text = Column(String, nullable=False)

# Function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
