import pytest
from datetime import datetime
import uuid

from app.models import VideoAnalysis, VideoStatus
from app.database import Base
from sqlalchemy import create_engine, event, String, TypeDecorator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# Адаптер UUID для SQLite
class GUID(TypeDecorator):
    """Адаптер UUID для SQLite"""
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
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


# Тестовая БД в памяти
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Для SQLite нужно использовать String вместо ENUM
@event.listens_for(engine, "connect", insert=True)
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Адаптируем типы для SQLite перед созданием таблиц
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

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Создает тестовую сессию БД"""
    # Адаптируем типы для SQLite
    adapt_types_for_sqlite()
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


def test_video_analysis_create_with_pending_status(db_session):
    """Тест создания VideoAnalysis со статусом pending"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.id is not None
    assert video.filename == "test.mp4"
    assert video.status == VideoStatus.PENDING
    assert video.has_motion is None
    assert video.processing_duration_ms is None
    assert video.error_message is None
    assert video.upload_time is not None
    assert video.analysis_time is None


def test_video_analysis_create_with_completed_status(db_session):
    """Тест создания VideoAnalysis со статусом completed"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.COMPLETED,
        has_motion=True,
        processing_duration_ms=1000
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.status == VideoStatus.COMPLETED
    assert video.has_motion is True
    assert video.processing_duration_ms == 1000


def test_video_analysis_create_with_failed_status(db_session):
    """Тест создания VideoAnalysis со статусом failed"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.FAILED,
        error_message="Ошибка обработки"
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.status == VideoStatus.FAILED
    assert video.error_message == "Ошибка обработки"


def test_video_analysis_create_with_processing_status(db_session):
    """Тест создания VideoAnalysis со статусом processing"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PROCESSING
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.status == VideoStatus.PROCESSING


def test_video_analysis_default_status(db_session):
    """Тест default значения статуса"""
    video = VideoAnalysis(
        filename="test.mp4"
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.status == VideoStatus.PENDING


def test_video_analysis_default_upload_time(db_session):
    """Тест default значения upload_time"""
    before_create = datetime.utcnow()
    
    video = VideoAnalysis(
        filename="test.mp4"
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    after_create = datetime.utcnow()
    
    assert video.upload_time is not None
    assert before_create <= video.upload_time <= after_create


def test_video_analysis_default_id(db_session):
    """Тест default значения id (UUID)"""
    video = VideoAnalysis(
        filename="test.mp4"
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.id is not None
    assert isinstance(video.id, uuid.UUID)


def test_video_analysis_custom_id(db_session):
    """Тест создания VideoAnalysis с кастомным ID"""
    custom_id = uuid.uuid4()
    video = VideoAnalysis(
        id=custom_id,
        filename="test.mp4"
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.id == custom_id


def test_video_analysis_analysis_time(db_session):
    """Тест установки analysis_time"""
    analysis_time = datetime.utcnow()
    
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.COMPLETED,
        analysis_time=analysis_time
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.analysis_time == analysis_time


def test_video_analysis_all_fields(db_session):
    """Тест создания VideoAnalysis со всеми полями"""
    video_id = uuid.uuid4()
    upload_time = datetime.utcnow()
    analysis_time = datetime.utcnow()
    
    video = VideoAnalysis(
        id=video_id,
        filename="test_video.mp4",
        upload_time=upload_time,
        analysis_time=analysis_time,
        has_motion=True,
        processing_duration_ms=1500,
        status=VideoStatus.COMPLETED,
        error_message=None
    )
    
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    
    assert video.id == video_id
    assert video.filename == "test_video.mp4"
    assert video.upload_time == upload_time
    assert video.analysis_time == analysis_time
    assert video.has_motion is True
    assert video.processing_duration_ms == 1500
    assert video.status == VideoStatus.COMPLETED
    assert video.error_message is None


def test_video_status_enum_values():
    """Тест значений enum VideoStatus"""
    assert VideoStatus.PENDING.value == "pending"
    assert VideoStatus.PROCESSING.value == "processing"
    assert VideoStatus.COMPLETED.value == "completed"
    assert VideoStatus.FAILED.value == "failed"


def test_video_status_enum_comparison():
    """Тест сравнения enum VideoStatus"""
    assert VideoStatus.PENDING == VideoStatus.PENDING
    assert VideoStatus.PENDING != VideoStatus.COMPLETED
    
    # Проверка сравнения со строкой
    assert VideoStatus.PENDING.value == "pending"
    assert str(VideoStatus.PENDING.value) == "pending"


def test_video_analysis_update_status(db_session):
    """Тест обновления статуса VideoAnalysis"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    
    # Обновляем статус
    video.status = VideoStatus.PROCESSING
    db_session.commit()
    db_session.refresh(video)
    
    assert video.status == VideoStatus.PROCESSING
    
    # Еще раз обновляем
    video.status = VideoStatus.COMPLETED
    db_session.commit()
    db_session.refresh(video)
    
    assert video.status == VideoStatus.COMPLETED


def test_video_analysis_update_has_motion(db_session):
    """Тест обновления has_motion"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PROCESSING
    )
    
    db_session.add(video)
    db_session.commit()
    
    video.has_motion = True
    db_session.commit()
    db_session.refresh(video)
    
    assert video.has_motion is True


def test_video_analysis_query_by_status(db_session):
    """Тест запроса VideoAnalysis по статусу"""
    # Создаем несколько записей с разными статусами
    video1 = VideoAnalysis(filename="test1.mp4", status=VideoStatus.PENDING)
    video2 = VideoAnalysis(filename="test2.mp4", status=VideoStatus.COMPLETED)
    video3 = VideoAnalysis(filename="test3.mp4", status=VideoStatus.PENDING)
    
    db_session.add_all([video1, video2, video3])
    db_session.commit()
    
    # Запрашиваем записи со статусом PENDING
    pending_videos = db_session.query(VideoAnalysis).filter(
        VideoAnalysis.status == VideoStatus.PENDING
    ).all()
    
    assert len(pending_videos) == 2
    assert all(v.status == VideoStatus.PENDING for v in pending_videos)

