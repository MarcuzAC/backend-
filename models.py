import uuid
import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Index

Base = declarative_base()

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
    reset_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    likes = relationship("Like", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    searches = relationship("SearchHistory", back_populates="user")

class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    videos = relationship("Video", back_populates="category")

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False, index=True)  # Added index for search
    description = Column(Text)
    thumbnail_url = Column(String)
    created_date = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    vimeo_url = Column(String)
    vimeo_id = Column(String)
    duration = Column(Integer)  # Duration in seconds
    view_count = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)

    # Relationships
    category = relationship("Category", back_populates="videos")
    likes = relationship("Like", back_populates="video")
    comments = relationship("Comment", back_populates="video")

    # Indexes for search optimization
    __table_args__ = (
        Index('ix_video_title_fts', func.to_tsvector('english', title), postgresql_using='gin'),
        Index('ix_video_description_fts', func.to_tsvector('english', description), postgresql_using='gin'),
    )

class Like(Base):
    __tablename__ = "likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="comments")
    video = relationship("Video", back_populates="comments")

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Nullable for anonymous searches
    query = Column(String(255), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    result_count = Column(Integer)

    # Relationships
    user = relationship("User", back_populates="searches")
    category = relationship("Category")

    __table_args__ = (
        Index('ix_search_history_query', 'query'),
        Index('ix_search_history_created_at', 'created_at'),
    )

class PopularSearch(Base):
    __tablename__ = "popular_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String(255), unique=True, nullable=False)
    search_count = Column(Integer, default=1)
    last_searched = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index('ix_popular_searches_search_count', 'search_count'),
    )