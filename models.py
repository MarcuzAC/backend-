import uuid
import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    username = Column(String(50), unique=True, index=True)
    phone_number = Column(String(20), nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    is_admin = Column(Boolean, default=False)
    hashed_password = Column(String(255), nullable=False)
    reset_token = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    # Relationships
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    videos = relationship("Video", back_populates="category", cascade="all, delete-orphan")

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    vimeo_url = Column(String(255), nullable=True)
    vimeo_id = Column(String(50), unique=True, nullable=True)
    view_count = Column(Integer, default=0)

    # Relationships
    category = relationship("Category", back_populates="videos")
    likes = relationship("Like", back_populates="video", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")

    def like_count(self):
        return len(self.likes)
    
    def comment_count(self):
        return len(self.comments)

class Like(Base):
    __tablename__ = "likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="likes")
    video = relationship("Video", back_populates="likes")

    # Ensure a user can like a video only once
    __table_args__ = (
        UniqueConstraint('user_id', 'video_id', name='unique_user_video_like'),
    )

class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)  # Changed from 'text' to 'content' for consistency
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="comments")
    video = relationship("Video", back_populates="comments")