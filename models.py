"""
ORM-модели для трех типов диаграмм с JSONB-полем.
"""

from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


class BaseChart(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)  # Список точек/значений
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    @property
    def type(self) -> str:
        """Возвращает тип диаграммы на основе класса"""
        if isinstance(self, BarChart):
            return 'bar'
        elif isinstance(self, LineChart):
            return 'line'
        elif isinstance(self, PieChart):
            return 'pie'
        else:
            raise ValueError("Unknown chart type")


class BarChart(BaseChart):
    __tablename__ = 'bar_charts'
    # JSONB-структура: [{"label": str, "value": number}, ...]


class LineChart(BaseChart):
    __tablename__ = 'line_charts'
    # JSONB-структура: [{"series": str, "x": number, "y": number}, ...]


class PieChart(BaseChart):
    __tablename__ = 'pie_charts'
    # JSONB-структура: [{"label": str, "value": number}, ...]