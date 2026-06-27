# db.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./urlshortener.db")
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    alias = Column(String(10), unique=True, index=True)
    long_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    clicks = Column(Integer, default=0)

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key = Column(String(36), primary_key=True, index=True)
    request_hash = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
