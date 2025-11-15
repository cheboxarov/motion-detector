from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings

import os


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://video_user:video_password@localhost:5432/video_db")
    
    class Config:
        env_file = ".env"


settings = Settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

