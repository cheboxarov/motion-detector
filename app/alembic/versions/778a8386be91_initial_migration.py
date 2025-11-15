"""Initial migration

Revision ID: 778a8386be91
Revises: 
Create Date: 2025-11-15 18:31:30.194506

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '778a8386be91'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создание enum типа для PostgreSQL (с проверкой существования)
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'videostatus'")
    ).fetchone()
    
    if not result:
        # Создаем enum тип напрямую через SQL
        connection.execute(sa.text("CREATE TYPE videostatus AS ENUM ('pending', 'processing', 'completed', 'failed')"))
        connection.commit()
    
    # Используем существующий тип для создания таблицы
    videostatus_enum = postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='videostatus', create_type=False)
    
    # Создание таблицы video_analysis
    op.create_table('video_analysis',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
    sa.Column('filename', sa.String(), nullable=False),
    sa.Column('upload_time', sa.DateTime(), nullable=False),
    sa.Column('analysis_time', sa.DateTime(), nullable=True),
    sa.Column('has_motion', sa.Boolean(), nullable=True),
    sa.Column('processing_duration_ms', sa.Integer(), nullable=True),
    sa.Column('status', videostatus_enum, nullable=False, server_default='pending'),
    sa.Column('error_message', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Создание индексов
    op.create_index('ix_video_analysis_upload_time', 'video_analysis', ['upload_time'])
    op.create_index('ix_video_analysis_status', 'video_analysis', ['status'])


def downgrade() -> None:
    # Удаление индексов
    op.drop_index('ix_video_analysis_status', table_name='video_analysis')
    op.drop_index('ix_video_analysis_upload_time', table_name='video_analysis')
    
    # Удаление таблицы
    op.drop_table('video_analysis')
    
    # Удаление enum типа
    videostatus_enum = postgresql.ENUM('pending', 'processing', 'completed', 'failed', name='videostatus')
    videostatus_enum.drop(op.get_bind(), checkfirst=True)

