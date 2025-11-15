import pytest
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import VideoAnalysis, VideoStatus
from app.database import Base


# Тестовая БД в памяти
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Создает тестовую сессию БД"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


def test_create_video_record(db_session: Session):
    """Тест создания записи в БД"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    
    # Проверяем, что запись создана
    assert video.id is not None
    assert video.filename == "test.mp4"
    assert video.status == VideoStatus.PENDING
    
    # Проверяем, что запись доступна после коммита
    video_from_db = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video.id).first()
    assert video_from_db is not None
    assert video_from_db.filename == "test.mp4"


def test_update_status(db_session: Session):
    """Тест обновления статуса в БД"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Обновляем статус
    video.status = VideoStatus.PROCESSING
    db_session.commit()
    
    # Проверяем, что статус обновлен
    video_from_db = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
    assert video_from_db.status == VideoStatus.PROCESSING
    
    # Еще раз обновляем
    video_from_db.status = VideoStatus.COMPLETED
    video_from_db.has_motion = True
    db_session.commit()
    
    # Проверяем финальный статус
    video_final = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
    assert video_final.status == VideoStatus.COMPLETED
    assert video_final.has_motion is True


def test_transaction_rollback_on_error(db_session: Session):
    """Тест rollback транзакции при ошибке"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Начинаем транзакцию
    video.status = VideoStatus.PROCESSING
    video.has_motion = True
    
    # Симулируем ошибку - делаем rollback
    db_session.rollback()
    
    # Проверяем, что изменения откатились
    video_from_db = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
    assert video_from_db.status == VideoStatus.PENDING
    assert video_from_db.has_motion is None


def test_query_by_status(db_session: Session):
    """Тест запроса записей по статусу"""
    # Создаем несколько записей с разными статусами
    videos = [
        VideoAnalysis(filename="test1.mp4", status=VideoStatus.PENDING),
        VideoAnalysis(filename="test2.mp4", status=VideoStatus.PROCESSING),
        VideoAnalysis(filename="test3.mp4", status=VideoStatus.COMPLETED),
        VideoAnalysis(filename="test4.mp4", status=VideoStatus.PENDING),
        VideoAnalysis(filename="test5.mp4", status=VideoStatus.COMPLETED),
    ]
    
    db_session.add_all(videos)
    db_session.commit()
    
    # Запрашиваем записи со статусом PENDING
    pending_videos = db_session.query(VideoAnalysis).filter(
        VideoAnalysis.status == VideoStatus.PENDING
    ).all()
    
    assert len(pending_videos) == 2
    assert all(v.status == VideoStatus.PENDING for v in pending_videos)
    
    # Запрашиваем записи со статусом COMPLETED
    completed_videos = db_session.query(VideoAnalysis).filter(
        VideoAnalysis.status == VideoStatus.COMPLETED
    ).all()
    
    assert len(completed_videos) == 2
    assert all(v.status == VideoStatus.COMPLETED for v in completed_videos)


def test_query_by_id(db_session: Session):
    """Тест запроса записи по ID"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Запрашиваем по ID
    video_from_db = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
    
    assert video_from_db is not None
    assert video_from_db.id == video_id
    assert video_from_db.filename == "test.mp4"


def test_query_nonexistent_id(db_session: Session):
    """Тест запроса несуществующей записи"""
    fake_id = uuid.uuid4()
    
    video_from_db = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == fake_id).first()
    
    assert video_from_db is None


def test_query_with_filters(db_session: Session):
    """Тест запроса с несколькими фильтрами"""
    videos = [
        VideoAnalysis(filename="test1.mp4", status=VideoStatus.COMPLETED, has_motion=True),
        VideoAnalysis(filename="test2.mp4", status=VideoStatus.COMPLETED, has_motion=False),
        VideoAnalysis(filename="test3.mp4", status=VideoStatus.COMPLETED, has_motion=True),
        VideoAnalysis(filename="test4.mp4", status=VideoStatus.PENDING, has_motion=None),
    ]
    
    db_session.add_all(videos)
    db_session.commit()
    
    # Запрашиваем записи со статусом COMPLETED и has_motion=True
    completed_with_motion = db_session.query(VideoAnalysis).filter(
        VideoAnalysis.status == VideoStatus.COMPLETED,
        VideoAnalysis.has_motion == True
    ).all()
    
    assert len(completed_with_motion) == 2
    assert all(v.has_motion is True for v in completed_with_motion)


def test_indexes_performance(db_session: Session):
    """Тест производительности индексов"""
    # Создаем много записей для тестирования индексов
    videos = [
        VideoAnalysis(
            filename=f"test{i}.mp4",
            status=VideoStatus.PENDING if i % 2 == 0 else VideoStatus.COMPLETED,
            upload_time=datetime.utcnow()
        )
        for i in range(100)
    ]
    
    db_session.add_all(videos)
    db_session.commit()
    
    # Тестируем запрос по статусу (должен использовать индекс)
    import time
    start_time = time.time()
    pending_videos = db_session.query(VideoAnalysis).filter(
        VideoAnalysis.status == VideoStatus.PENDING
    ).all()
    elapsed_time = time.time() - start_time
    
    assert len(pending_videos) == 50
    # Запрос должен быть быстрым (менее 1 секунды для 100 записей)
    assert elapsed_time < 1.0, "Запрос по статусу должен быть быстрым благодаря индексу"


def test_concurrent_access(db_session: Session):
    """Тест конкурентного доступа (симуляция)"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Симулируем конкурентный доступ - открываем новую сессию
    db_session2 = TestingSessionLocal()
    
    try:
        video1 = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        video2 = db_session2.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        
        # Обновляем в первой сессии
        video1.status = VideoStatus.PROCESSING
        db_session.commit()
        
        # Обновляем во второй сессии
        video2.status = VideoStatus.COMPLETED
        db_session2.commit()
        
        # Проверяем финальное состояние
        video_final = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        assert video_final.status == VideoStatus.COMPLETED
        
    finally:
        db_session2.close()


def test_delete_video_record(db_session: Session):
    """Тест удаления записи из БД"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Проверяем, что запись существует
    video_from_db = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
    assert video_from_db is not None
    
    # Удаляем запись
    db_session.delete(video_from_db)
    db_session.commit()
    
    # Проверяем, что запись удалена
    deleted_video = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
    assert deleted_video is None


def test_multiple_status_updates(db_session: Session):
    """Тест множественных обновлений статуса"""
    video = VideoAnalysis(
        filename="test.mp4",
        status=VideoStatus.PENDING
    )
    
    db_session.add(video)
    db_session.commit()
    video_id = video.id
    
    # Последовательность обновлений статуса
    statuses = [
        VideoStatus.PENDING,
        VideoStatus.PROCESSING,
        VideoStatus.COMPLETED
    ]
    
    for i, status in enumerate(statuses):
        video = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        video.status = status
        if status == VideoStatus.COMPLETED:
            video.has_motion = True
            video.processing_duration_ms = 1000
        db_session.commit()
        
        # Проверяем статус после каждого обновления
        video_updated = db_session.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        assert video_updated.status == status


def test_query_by_time_range(db_session: Session):
    """Тест запроса записей по временному диапазону"""
    now = datetime.utcnow()
    
    videos = [
        VideoAnalysis(filename="test1.mp4", upload_time=now, status=VideoStatus.PENDING),
        VideoAnalysis(filename="test2.mp4", upload_time=now, status=VideoStatus.PROCESSING),
        VideoAnalysis(filename="test3.mp4", upload_time=now, status=VideoStatus.COMPLETED),
    ]
    
    db_session.add_all(videos)
    db_session.commit()
    
    # Запрашиваем записи, созданные сегодня
    today_videos = db_session.query(VideoAnalysis).filter(
        VideoAnalysis.upload_time >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    ).all()
    
    assert len(today_videos) >= 3


def test_bulk_insert(db_session: Session):
    """Тест массовой вставки записей"""
    videos = [
        VideoAnalysis(
            filename=f"test{i}.mp4",
            status=VideoStatus.PENDING
        )
        for i in range(50)
    ]
    
    db_session.add_all(videos)
    db_session.commit()
    
    # Проверяем, что все записи созданы
    count = db_session.query(VideoAnalysis).count()
    assert count == 50

