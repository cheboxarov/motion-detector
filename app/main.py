from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import os
import tempfile
import logging
from datetime import datetime

from app.database import get_db
from app.models import VideoAnalysis, VideoStatus
from app.schemas import VideoAnalysisResponse, AnalyzeResponse
from app.dependencies import get_video_analyzer
from app.services.video_analyzer import VideoAnalyzer
from app.metrics import (
    get_metrics,
    increment_video_processed,
    observe_processing_duration,
    increment_video_errors,
    set_videos_in_queue
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Analysis Service",
    description="Микросервис для анализа видео и детекции движения",
    version="1.0.0"
)

ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}


def is_video_file(filename: str) -> bool:
    """Проверяет, является ли файл видео"""
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_VIDEO_EXTENSIONS


def process_video_analysis(
    video_id: uuid.UUID,
    video_path: str,
    filename: str,
    db_url: str,
    analyzer: VideoAnalyzer,
    db_session: Optional[Session] = None
):
    """Фоновая задача для обработки видео"""
    from app.database import SessionLocal
    
    # Используем переданную сессию или создаем новую
    if db_session is not None:
        db = db_session
        should_close = False
    else:
        db = SessionLocal()
        should_close = True
    
    try:
        # Обновляем статус на processing
        video_record = db.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
        if not video_record:
            logger.error(f"Видео запись не найдена: {video_id}")
            return
        
        video_record.status = VideoStatus.PROCESSING
        db.commit()
        
        # Анализируем видео
        has_motion, processing_duration_ms = analyzer.detect_motion(video_path)
        
        # Обновляем результат
        video_record.has_motion = has_motion
        video_record.processing_duration_ms = processing_duration_ms
        video_record.analysis_time = datetime.utcnow()
        video_record.status = VideoStatus.COMPLETED
        db.commit()
        
        # Обновляем метрики
        increment_video_processed(VideoStatus.COMPLETED.value)
        observe_processing_duration(processing_duration_ms / 1000.0)
        
        logger.info(f"Видео {video_id} успешно обработано: движение={has_motion}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке видео {video_id}: {str(e)}")
        
        # Обновляем статус на failed
        try:
            video_record = db.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
            if video_record:
                video_record.status = VideoStatus.FAILED
                video_record.error_message = str(e)
                db.commit()
        except Exception as db_error:
            logger.error(f"Ошибка при обновлении статуса: {str(db_error)}")
        
        increment_video_processed(VideoStatus.FAILED.value)
        increment_video_errors()
    
    finally:
        # Удаляем временный файл
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception as e:
            logger.error(f"Ошибка при удалении временного файла: {str(e)}")
        
        # Обновляем метрику очереди
        try:
            pending_count = db.query(VideoAnalysis).filter(
                VideoAnalysis.status.in_([VideoStatus.PENDING, VideoStatus.PROCESSING])
            ).count()
            set_videos_in_queue(pending_count)
        except Exception as e:
            logger.error(f"Ошибка при обновлении метрики очереди: {str(e)}")
        finally:
            if should_close:
                db.close()


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    analyzer: VideoAnalyzer = Depends(get_video_analyzer)
):
    """Принимает видео файл и запускает анализ"""
    
    if not is_video_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Разрешенные форматы: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
    
    # Создаем запись в БД
    video_record = VideoAnalysis(
        filename=file.filename,
        status=VideoStatus.PENDING
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)
    
    # Сохраняем файл во временную директорию
    temp_dir = tempfile.gettempdir()
    video_path = os.path.join(temp_dir, f"{video_record.id}_{file.filename}")
    
    try:
        with open(video_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Получаем URL БД для фоновой задачи
        from app.database import settings
        db_url = settings.database_url
        
        # Запускаем обработку в фоне
        background_tasks.add_task(
            process_video_analysis,
            video_record.id,
            video_path,
            file.filename,
            db_url,
            analyzer
        )
        
        # Обновляем метрику очереди
        pending_count = db.query(VideoAnalysis).filter(
            VideoAnalysis.status.in_([VideoStatus.PENDING, VideoStatus.PROCESSING])
        ).count()
        set_videos_in_queue(pending_count)
        
        return AnalyzeResponse(
            video_id=video_record.id,
            status=VideoStatus.PENDING.value,
            message="Видео принято в обработку"
        )
    
    except Exception as e:
        # Удаляем запись из БД при ошибке
        db.delete(video_record)
        db.commit()
        
        # Удаляем файл если он был создан
        if os.path.exists(video_path):
            os.remove(video_path)
        
        logger.error(f"Ошибка при сохранении видео: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {str(e)}")


@app.get("/results/{video_id}", response_model=VideoAnalysisResponse)
async def get_result(video_id: uuid.UUID, db: Session = Depends(get_db)):
    """Получить результат анализа по ID"""
    
    video_record = db.query(VideoAnalysis).filter(VideoAnalysis.id == video_id).first()
    
    if not video_record:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    
    return VideoAnalysisResponse.model_validate(video_record)


@app.get("/metrics")
async def metrics():
    """Эндпоинт для Prometheus метрик"""
    from prometheus_client import CONTENT_TYPE_LATEST
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Проверяем подключение к БД
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

