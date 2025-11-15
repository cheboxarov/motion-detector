"""
Утилиты для тестов, адаптирующие PostgreSQL типы для SQLite
"""
from sqlalchemy import TypeDecorator, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid


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

