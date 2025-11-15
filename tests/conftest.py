import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, String, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import VideoAnalysis
import os
import uuid


# Тестовая БД в памяти
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Для SQLite нужно адаптировать UUID и ENUM
@event.listens_for(engine, "connect", insert=True)
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Адаптер UUID для SQLite
class GUID(TypeDecorator):
    """Адаптер UUID для SQLite"""
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID as PGUUID
            return dialect.type_descriptor(PGUUID())
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


# Адаптируем типы для SQLite
def adapt_types_for_sqlite():
    """Адаптирует типы PostgreSQL для SQLite"""
    if 'video_analysis' in Base.metadata.tables:
        table = Base.metadata.tables['video_analysis']
        # Заменяем UUID на GUID
        if 'id' in table.columns:
            table.columns['id'].type = GUID()
        # Заменяем ENUM на String
        if 'status' in table.columns:
            table.columns['status'].type = String(20)


# Создаем таблицу с адаптацией для SQLite
def create_test_tables():
    """Создает таблицы для тестов с адаптацией для SQLite"""
    # Адаптируем типы для SQLite
    adapt_types_for_sqlite()
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Создает новую сессию БД для каждого теста"""
    # Удаляем все таблицы перед созданием
    Base.metadata.drop_all(bind=engine)
    # Создаем таблицы
    create_test_tables()
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Очищаем после теста
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Создает тестовый клиент FastAPI"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

