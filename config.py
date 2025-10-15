"""
Конфигурация приложения для работы с PostgreSQL

Этот модуль загружает настройки подключения к базе данных из переменных окружения,
которые хранятся в файле .env в корне проекта. Используется библиотека python-dotenv.

Переменные окружения:
- DB_HOST: Хост базы данных (по умолчанию: localhost)
- DB_PORT: Порт подключения (по умолчанию: 5432)
- DB_USER: Имя пользователя PostgreSQL
- DB_PASSWORD: Пароль пользователя
- DB_NAME: Название базы данных

Для работы приложения необходимо создать файл .env с этими переменными.
"""

from pathlib import Path
from dotenv import load_dotenv
import os
from typing import Optional

# Загрузка переменных окружения из файла .env
# Файл должен находиться в корневой директории проекта
load_dotenv(Path(__file__).parent / '.env')

def get_env_variable(name: str, default: Optional[str] = None) -> str:
    """
    Получает значение переменной окружения с проверкой
    
    :param name: Имя переменной окружения
    :param default: Значение по умолчанию, если переменная не найдена
    :return: Значение переменной окружения
    :raises EnvironmentError: Если переменная не найдена и не указано значение по умолчанию
    """
    value = os.getenv(name, default)
    if value is None:
        raise EnvironmentError(f"Переменная окружения {name} не определена")
    return value

# Чтение конфигурационных переменных
DB_HOST: str = get_env_variable("DB_HOST", "localhost")  # Хост БД
DB_PORT: int = int(get_env_variable("DB_PORT", "5432"))  # Порт подключения
DB_USER: str = get_env_variable("DB_USER")               # Пользователь БД
DB_PASSWORD: str = get_env_variable("DB_PASSWORD")       # Пароль пользователя
DB_NAME: str = get_env_variable("DB_NAME")               # Имя базы данных

# Дополнительная проверка для критических параметров
if not DB_USER or not DB_PASSWORD or not DB_NAME:
    raise EnvironmentError("Не заданы обязательные параметры подключения к БД")