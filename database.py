"""
Инициализация подключения к PostgreSQL через SQLAlchemy

Этот модуль:
1. Создает движок (engine) для подключения к базе данных
2. Настраивает фабрику сессий (sessionmaker)
3. Определяет базовый класс для моделей SQLAlchemy
4. Предоставляет функцию для инициализации структуры БД

Основные компоненты:
- engine: Объект для управления подключениями к БД
- SessionLocal: Фабрика для создания сессий БД
- Base: Базовый класс для декларативных моделей
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm.session import Session
from typing import Type

# Импорт настроек подключения из конфигурации
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Формирование URL подключения к PostgreSQL
# Формат: postgresql+psycopg2://user:password@host:port/dbname
DATABASE_URL: str = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

def create_db_engine(url: str) -> Engine:
    """
    Создает и возвращает движок подключения к базе данных
    
    :param url: Строка подключения в формате SQLAlchemy
    :return: Объект движка SQLAlchemy Engine
    """
    return create_engine(
        url,
        echo=False,           # Включить True для отладки SQL-запросов
        future=True,           # Использовать новое API SQLAlchemy 2.0
        pool_size=10,          # Максимальное количество соединений в пуле
        max_overflow=20,       # Дополнительные соединения при перегрузке
        pool_recycle=3600      # Пересоздавать соединения каждые 60 минут
    )

# Создание основного движка приложения
engine: Engine = create_db_engine(DATABASE_URL)

def create_session_factory(engine: Engine) -> Type[Session]:
    """
    Создает фабрику сессий для работы с базой данных
    
    :param engine: Движок подключения к БД
    :return: Класс-фабрика для создания сессий
    """
    return sessionmaker(
        bind=engine,
        autoflush=False,        # Отключить автоматическую синхронизацию
        autocommit=False,       # Отключить автоматический коммит
        future=True,            # Использовать новое API SQLAlchemy 2.0
        expire_on_commit=False  # Не сбрасывать состояние объектов после коммита
    )

# Создание фабрики сессий
SessionLocal: Type[Session] = create_session_factory(engine)

# Базовый класс для декларативных моделей
Base = declarative_base()

def initialize_database() -> None:
    """
    Инициализирует структуру базы данных
    
    Эта функция:
    1. Импортирует все модели приложения
    2. Создает соответствующие таблицы в БД
    3. Выполняется при старте приложения
    
    Примечание: Для корректной работы должны быть импортированы все модели,
    использующие Base в качестве базового класса.
    """
    # Импорт моделей необходим для их регистрации в метаданных Base
    # noqa: F401 - игнорирование предупреждения о неиспользуемом импорте
    import models
    
    # Создание всех таблиц, определенных в моделях
    Base.metadata.create_all(bind=engine)
    print(f"База данных инициализирована: {DB_NAME}@{DB_HOST}:{DB_PORT}")