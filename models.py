import uuid
import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    username = Column(String(50), unique=True, index=True)
    phone_number = Column(String(20))
    email = Column(String(100), unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    hashed_password = Column(String)

class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True)

    videos = relationship("Video", back_populates="category") 
class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    vimeo_url = Column(String) 
    vimeo_id = Column(String)   

    category = relationship("Category", back_populates="videos")