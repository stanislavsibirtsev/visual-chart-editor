"""
Контроллер для работы с диаграммами и базой данных

Этот модуль содержит все CRUD-операции (создание, чтение, обновление, удаление)
для работы с диаграммами, а также функции импорта/экспорта в CSV формате.

Основные функции:
- list_charts: Получение списка диаграмм определенного типа
- get_chart: Получение конкретной диаграммы по ID
- save_chart: Сохранение новой или обновление существующей диаграммы
- delete_chart: Удаление диаграммы
- export_to_csv: Экспорт диаграммы в CSV файл
- import_from_csv: Импорт диаграммы из CSV файла

Все функции работают с базой данных через SQLAlchemy ORM.
"""

from typing import List, Optional, Type, Dict, Any
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from database import SessionLocal
from models import BarChart, LineChart, PieChart, BaseChart
import csv
import re

# Сопоставление типов диаграмм с соответствующими классами моделей
_MODEL_MAP: Dict[str, Type[BaseChart]] = {
    'bar': BarChart,
    'line': LineChart,
    'pie': PieChart
}

def list_charts(chart_type: str) -> List[BaseChart]:
    """
    Возвращает список диаграмм указанного типа, отсортированных по дате создания
    
    :param chart_type: Тип диаграммы ('bar', 'line' или 'pie')
    :return: Список объектов диаграмм
    :raises ValueError: Если указан неверный тип диаграммы
    """
    Model = _MODEL_MAP.get(chart_type)
    if not Model:
        raise ValueError(f"Неизвестный тип диаграммы: {chart_type}")
    
    with SessionLocal() as session:
        return session.query(Model).order_by(Model.created_at).all()

def get_chart(chart_type: str, chart_id: int) -> Optional[BaseChart]:
    """
    Возвращает диаграмму по ее типу и ID
    
    :param chart_type: Тип диаграммы ('bar', 'line' или 'pie')
    :param chart_id: Идентификатор диаграммы в базе данных
    :return: Объект диаграммы или None, если не найдена
    :raises ValueError: Если указан неверный тип диаграммы
    """
    Model = _MODEL_MAP.get(chart_type)
    if not Model:
        raise ValueError(f"Неизвестный тип диаграммы: {chart_type}")
    
    with SessionLocal() as session:
        return session.get(Model, chart_id)

def save_chart(
    chart_type: str, 
    name: str, 
    data: List[Dict[str, Any]], 
    chart_id: Optional[int] = None
) -> BaseChart:
    """
    Сохраняет или обновляет диаграмму в базе данных
    
    Выполняет проверки:
    1. Уникальность имени для данного типа диаграммы
    2. Корректность типа диаграммы
    
    :param chart_type: Тип диаграммы ('bar', 'line' или 'pie')
    :param name: Название диаграммы (должно быть уникальным для типа)
    :param data: Данные диаграммы в формате списка словарей
    :param chart_id: ID существующей диаграммы (None для создания новой)
    :return: Сохраненный объект диаграммы
    :raises ValueError: При нарушении уникальности имени или других ошибках валидации
    """
    # Получаем класс модели по типу диаграммы
    Model = _MODEL_MAP.get(chart_type)
    if not Model:
        raise ValueError(f"Неизвестный тип диаграммы: {chart_type}")
    
    with SessionLocal() as session:
        try:
            if chart_id:
                # Режим обновления существующей диаграммы
                chart = session.get(Model, chart_id)
                if not chart:
                    raise ValueError("Диаграмма не найдена")
                
                # Проверяем, изменилось ли имя
                if chart.name != name:
                    # Проверяем уникальность нового имени
                    if session.query(Model).filter(Model.name == name).first():
                        raise ValueError(
                            f"Диаграмма с именем '{name}' уже существует для этого типа"
                        )
                # Обновляем данные
                chart.name = name
                chart.data = data
            else:
                # Режим создания новой диаграммы
                # Проверяем уникальность имени
                if session.query(Model).filter(Model.name == name).first():
                    raise ValueError(
                        f"Диаграмма с именем '{name}' уже существует для этого типа"
                    )
                # Создаем новый объект
                chart = Model(name=name, data=data)
                session.add(chart)
            
            # Сохраняем изменения
            session.commit()
            session.refresh(chart)
            return chart
        
        except IntegrityError as exc:
            # Обработка ошибок уникальности из PostgreSQL
            session.rollback()
            if "duplicate key value violates unique constraint" in str(exc):
                raise ValueError(
                    f"Диаграмма с именем '{name}' уже существует для типа '{chart_type}'"
                ) from exc
            raise ValueError(f"Ошибка целостности базы данных: {str(exc)}") from exc
        
        except SQLAlchemyError as exc:
            # Общая обработка ошибок SQLAlchemy
            session.rollback()
            raise ValueError(f"Ошибка базы данных: {str(exc)}") from exc

def delete_chart(chart_type: str, chart_id: int) -> None:
    """
    Удаляет диаграмму по ее типу и ID
    
    :param chart_type: Тип диаграммы ('bar', 'line' или 'pie')
    :param chart_id: Идентификатор диаграммы в базе данных
    :raises ValueError: Если указан неверный тип диаграммы
    """
    Model = _MODEL_MAP.get(chart_type)
    if not Model:
        raise ValueError(f"Неизвестный тип диаграммы: {chart_type}")
    
    with SessionLocal() as session:
        chart = session.get(Model, chart_id)
        if chart:
            session.delete(chart)
            session.commit()

def export_to_csv(chart: BaseChart, filename: str) -> bool:
    """
    Экспортирует данные диаграммы в CSV файл
    
    Формат файла:
    1. Секция метаданных (тип и имя диаграммы)
    2. Пустая строка-разделитель
    3. Секция данных (зависит от типа диаграммы)
    
    :param chart: Объект диаграммы для экспорта
    :param filename: Путь для сохранения файла
    :return: True если экспорт успешен, False при ошибке
    """
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Записываем метаданные
            writer.writerow(['type', 'name'])
            writer.writerow([chart.type, chart.name])
            writer.writerow([])  # Разделитель
            
            # Записываем данные в зависимости от типа диаграммы
            if chart.type in ('bar', 'pie'):
                writer.writerow(['label', 'value'])
                for item in chart.data:
                    writer.writerow([item['label'], item['value']])
            
            elif chart.type == 'line':
                writer.writerow(['series', 'x', 'y'])
                for item in chart.data:
                    writer.writerow([item['series'], item['x'], item['y']])
            
            return True
    
    except Exception as exc:
        print(f"Ошибка экспорта в CSV: {exc}")
        return False

def import_from_csv(filename: str) -> Optional[BaseChart]:
    """
    Импортирует диаграмму из CSV файла
    
    Ожидает файл в формате, созданном функцией export_to_csv
    
    :param filename: Путь к CSV файлу
    :return: Объект диаграммы или None при ошибке
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            # Чтение метаданных
            metadata_header = next(reader)
            if metadata_header != ['type', 'name']:
                print("Неверный формат заголовка метаданных")
                return None
                
            chart_type, name = next(reader)
            next(reader)  # Пропускаем разделитель
            
            # Чтение заголовка данных
            data_header = next(reader)
            data = []
            
            # Обработка данных для столбчатых и круговых диаграмм
            if chart_type in ('bar', 'pie'):
                if data_header != ['label', 'value']:
                    print("Неверный формат заголовка данных для bar/pie")
                    return None
                
                for row in reader:
                    # Пропускаем пустые строки
                    if not row or len(row) < 2:
                        continue
                    try:
                        data.append({
                            'label': row[0].strip(),
                            'value': float(row[1])
                        })
                    except ValueError:
                        print(f"Ошибка преобразования значения: {row}")
                        continue
            
            # Обработка данных для линейных диаграмм
            elif chart_type == 'line':
                if data_header != ['series', 'x', 'y']:
                    print("Неверный формат заголовка данных для line")
                    return None
                
                for row in reader:
                    # Пропускаем пустые строки
                    if not row or len(row) < 3:
                        continue
                    try:
                        data.append({
                            'series': row[0].strip(),
                            'x': float(row[1]),
                            'y': float(row[2])
                        })
                    except ValueError:
                        print(f"Ошибка преобразования значения: {row}")
                        continue
            
            else:
                print(f"Неизвестный тип диаграммы: {chart_type}")
                return None
            
            print(f"Успешно импортировано {len(data)} записей")
            
            # Создаем объект соответствующего типа
            if chart_type == 'bar':
                return BarChart(name=name, data=data)
            elif chart_type == 'line':
                return LineChart(name=name, data=data)
            elif chart_type == 'pie':
                return PieChart(name=name, data=data)
            return None
    
    except Exception as exc:
        print(f"Ошибка импорта из CSV: {exc}")
        return None