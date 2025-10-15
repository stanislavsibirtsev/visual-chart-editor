"""
Окно просмотра диаграммы

Этот модуль реализует диалоговое окно для просмотра и настройки отображения диаграмм.
Обеспечивает:
- Визуализацию диаграмм различных типов (столбчатые, линейные, круговые)
- Настройку цветовых схем, шрифтов и размеров
- Drag&Drop для изменения порядка столбцов (для столбчатых диаграмм)
- Сохранение диаграммы в PNG
- Сохранение измененного порядка элементов (для столбчатых диаграмм)

Основные компоненты:
- Matplotlib Figure и Canvas для отрисовки диаграмм
- Панель управления параметрами отображения
- Механизм обработки событий для Drag&Drop
"""

import matplotlib
matplotlib.use('QtAgg')  # Используем Qt-бэкенд для Matplotlib
from typing import List, Dict, Any, Optional, Tuple, DefaultDict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QSpinBox, QPushButton, QFileDialog,
    QSplitter, QWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.artist import Artist
from matplotlib.backend_bases import PickEvent, MouseEvent
from collections import defaultdict
import matplotlib.font_manager as fm
from controllers.diagram_controller import save_chart


class PlotWindow(QDialog):
    """
    Диалоговое окно для просмотра и настройки диаграмм
    
    Параметры:
    - chart_type: Тип диаграммы ('bar', 'line', 'pie')
    - name: Название диаграммы
    - data: Данные диаграммы
    - parent: Родительское окно
    """
    
    # Предопределенные цветовые палитры
    COLOR_PALETTES: Dict[str, Optional[List[str]]] = {
        'По умолчанию': None,
        'Пастельные': ['#AEC6CF', '#FFB347', '#77DD77', '#FF6961', '#FDFD96'],
        'Яркие': ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231'],
        'Монохромные': ['#4B4B4B', '#7F7F7F', '#B2B2B2', '#DCDCDC', '#FFFFFF'],
    }

    def __init__(
        self, 
        chart_type: str, 
        name: str, 
        data: List[Dict[str, Any]], 
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.chart_type = chart_type
        self.name = name
        self.data = data
        
        # Состояние для Drag&Drop
        self._picked_bar: Optional[Artist] = None
        self._orig_index: Optional[int] = None
        self.order_changed: bool = False

        # Настройка окна
        self.setWindowTitle(f"Просмотр диаграммы: {name}")
        self.resize(900, 600)

        # Основной разделитель интерфейса
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Панель настроек отображения
        ctrl_panel = self._create_control_panel()
        splitter.addWidget(ctrl_panel)

        # Область графика и кнопок
        plot_area = self._create_plot_area()
        splitter.addWidget(plot_area)

        # Основной лейаут окна
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(splitter)

        # Инициализация графика
        self._init_plot()

    def _create_control_panel(self) -> QGroupBox:
        """Создает панель управления параметрами отображения"""
        panel = QGroupBox("Параметры отображения")
        form = QFormLayout(panel)
        
        # Выбор цветовой схемы
        self.palette_cb = QComboBox()
        self.palette_cb.addItems(self.COLOR_PALETTES.keys())
        form.addRow(QLabel("Цветовая схема:"), self.palette_cb)
        
        # Выбор шрифта
        self.font_cb = QComboBox()
        # Получаем список доступных шрифтов
        fonts = sorted({f.name for f in fm.fontManager.ttflist})
        self.font_cb.addItems(fonts)
        self.font_cb.setCurrentText('DejaVu Sans')  # Устанавливаем шрифт по умолчанию
        form.addRow(QLabel("Шрифт:"), self.font_cb)
        
        # Выбор размера шрифта
        self.size_sb = QSpinBox()
        self.size_sb.setRange(6, 36)  # Диапазон размеров
        self.size_sb.setValue(10)      # Размер по умолчанию
        form.addRow(QLabel("Размер шрифта:"), self.size_sb)
        
        return panel

    def _create_plot_area(self) -> QWidget:
        """Создает область для отображения диаграммы и кнопок управления"""
        area = QWidget()
        layout = QVBoxLayout(area)
        
        # Создаем фигуру и холст Matplotlib
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # Кнопка сохранения порядка (только для столбчатых диаграмм)
        self.save_order_btn = QPushButton("Сохранить порядок")
        self.save_order_btn.setToolTip("Сохранить измененный порядок элементов")
        self.save_order_btn.setEnabled(False)
        self.save_order_btn.setVisible(self.chart_type == 'bar')  # Только для столбчатых
        layout.addWidget(self.save_order_btn)
        
        # Кнопка сохранения в PNG
        self.save_png_btn = QPushButton("Сохранить в PNG")
        self.save_png_btn.setToolTip("Сохранить диаграмму как изображение PNG")
        layout.addWidget(self.save_png_btn)
        
        return area

    def _init_plot(self) -> None:
        """Инициализирует график и обработчики событий"""
        # Подключаем сигналы
        self.palette_cb.currentIndexChanged.connect(self.update_chart)
        self.font_cb.currentIndexChanged.connect(self.update_chart)
        self.size_sb.valueChanged.connect(self.update_chart)
        self.save_png_btn.clicked.connect(self.save_png)
        self.save_order_btn.clicked.connect(self.on_save_order)

        # Обработчики событий для Drag&Drop (только для столбчатых диаграмм)
        if self.chart_type == 'bar':
            self.canvas.mpl_connect('pick_event', self.on_pick)
            self.canvas.mpl_connect('button_release_event', self.on_release)

        # Первоначальная отрисовка диаграммы
        self.update_chart()

    def update_chart(self) -> None:
        """Обновляет отображение диаграммы с текущими параметрами"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Получаем текущие настройки
        font_family: str = self.font_cb.currentText()
        font_size: int = self.size_sb.value()
        palette: Optional[List[str]] = self.COLOR_PALETTES[self.palette_cb.currentText()]

        # Обработка разных типов диаграмм
        if self.chart_type == 'bar':
            self._plot_bar_chart(ax, font_family, font_size, palette)
        elif self.chart_type == 'pie':
            self._plot_pie_chart(ax, font_family, font_size, palette)
        elif self.chart_type == 'line':
            self._plot_line_chart(ax, font_family, font_size, palette)
        
        # Обновляем холст
        self.canvas.draw()

    def _plot_bar_chart(
        self, 
        ax: Any, 
        font_family: str, 
        font_size: int, 
        palette: Optional[List[str]]
    ) -> None:
        """Отрисовывает столбчатую диаграмму"""
        labels = [item['label'] for item in self.data]
        values = [item['value'] for item in self.data]
        
        # Создаем столбцы
        bars = ax.bar(labels, values, color=palette, picker=True)
        self._bars = bars  # Сохраняем для обработки событий

        # Настраиваем заголовки и подписи
        ax.set_title(self.name, fontfamily=font_family, fontsize=font_size)
        ax.set_ylabel('Значение', fontfamily=font_family, fontsize=font_size)
        
        # Применяем шрифт к подписям осей
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontfamily(font_family)
            label.set_fontsize(font_size)

    def _plot_pie_chart(
        self, 
        ax: Any, 
        font_family: str, 
        font_size: int, 
        palette: Optional[List[str]]
    ) -> None:
        """Отрисовывает круговую диаграмму"""
        labels = [item['label'] for item in self.data]
        values = [item['value'] for item in self.data]
        
        # Создаем круговую диаграмму
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels, 
            autopct='%1.1f%%', 
            colors=palette
        )
        
        # Настраиваем заголовок
        ax.set_title(self.name, fontfamily=font_family, fontsize=font_size)
        
        # Применяем шрифт к подписям
        for text in texts + autotexts:
            text.set_fontfamily(font_family)
            text.set_fontsize(font_size)

    def _plot_line_chart(
        self, 
        ax: Any, 
        font_family: str, 
        font_size: int, 
        palette: Optional[List[str]]
    ) -> None:
        """Отрисовывает линейную диаграмму"""
        # Группируем точки по сериям
        series: DefaultDict[str, Dict[str, List[float]]] = defaultdict(
            lambda: {'x': [], 'y': []}
        )
        
        for point in self.data:
            series[point['series']]['x'].append(point['x'])
            series[point['series']]['y'].append(point['y'])
        
        # Рисуем каждую серию
        for idx, (series_name, coords) in enumerate(series.items()):
            color = palette[idx % len(palette)] if palette else None
            ax.plot(
                coords['x'], 
                coords['y'], 
                marker='o', 
                label=series_name, 
                color=color
            )
        
        # Настраиваем заголовки и подписи
        ax.set_title(self.name, fontfamily=font_family, fontsize=font_size)
        ax.set_xlabel('X', fontfamily=font_family, fontsize=font_size)
        ax.set_ylabel('Y', fontfamily=font_family, fontsize=font_size)
        
        # Добавляем легенду
        legend = ax.legend()
        for text in legend.get_texts():
            text.set_fontfamily(font_family)
            text.set_fontsize(font_size)
        
        # Применяем шрифт к подписям осей
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontfamily(font_family)
            label.set_fontsize(font_size)

    def on_pick(self, event: PickEvent) -> None:
        """Обрабатывает выбор столбца для перемещения"""
        if self.chart_type == 'bar' and hasattr(self, '_bars'):
            artist = event.artist
            if artist in self._bars:
                self._picked_bar = artist
                self._orig_index = list(self._bars).index(artist)

    def on_release(self, event: MouseEvent) -> None:
        """Обрабатывает отпускание кнопки мыши после перемещения столбца"""
        if self.chart_type == 'bar' and self._picked_bar:
            # Рассчитываем позиции центров столбцов
            centers = [bar.get_x() + bar.get_width() / 2 for bar in self._bars]
            
            if event.xdata is not None:
                # Находим ближайший столбец к позиции курсора
                distances = [abs(event.xdata - center) for center in centers]
                new_index = distances.index(min(distances))
                
                # Если позиция изменилась, обновляем данные
                if new_index != self._orig_index:
                    self.data[self._orig_index], self.data[new_index] = (
                        self.data[new_index], self.data[self._orig_index]
                    )
                    self.order_changed = True
                    self.save_order_btn.setEnabled(True)
            
            # Сбрасываем состояние
            self._picked_bar = None
            self._orig_index = None
            self.update_chart()

    def on_save_order(self) -> None:
        """Сохраняет измененный порядок элементов в родительском диалоге"""
        parent = self.parent()
        if hasattr(parent, 'table') and self.order_changed:
            try:
                # Обновляем таблицу в диалоге редактирования
                parent.table.setRowCount(len(self.data) + 1)
                for row, item in enumerate(self.data):
                    parent.table.setItem(row, 0, QTableWidgetItem(item['label']))
                    parent.table.setItem(row, 1, QTableWidgetItem(str(item['value'])))
                
                # Сохраняем изменения в базе данных
                save_chart(
                    parent.chart_type,
                    parent.name_edit.text().strip(),
                    self.data,
                    parent.chart_id
                )
                
                # Сбрасываем флаг изменений
                self.order_changed = False
                self.save_order_btn.setEnabled(False)
                
                # Уведомляем пользователя
                QMessageBox.information(
                    self, 
                    "Порядок сохранен", 
                    "Измененный порядок элементов сохранен"
                )
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка сохранения", str(e))

    def save_png(self) -> None:
        """Сохраняет диаграмму как PNG изображение"""
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить диаграмму как PNG", 
            "", 
            "PNG Files (*.png)"
        )
        if path:
            # Сохраняем с высоким DPI для качества
            self.figure.savefig(path, dpi=300)