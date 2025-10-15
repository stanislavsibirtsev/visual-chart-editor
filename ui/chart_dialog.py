"""
Диалог создания и редактирования диаграмм

Этот модуль реализует диалоговое окно для:
- Создания новых диаграмм
- Редактирования существующих диаграмм
- Ввода данных в табличном формате
- Просмотра визуализации диаграммы

Особенности:
- Динамическая адаптация интерфейса под тип диаграммы
- Автоматическое добавление строк при вводе данных
- Контекстное меню для удаления строк
- Валидация данных перед сохранением
- Обновление заголовка окна при изменении имени диаграммы
"""

from typing import List, Dict, Any, Optional, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout,
    QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from controllers.diagram_controller import get_chart, save_chart
from ui.plot_window import PlotWindow


class ChartDialog(QDialog):
    """
    Диалоговое окно для создания и редактирования диаграмм
    
    Сигналы:
    - saved: Излучается при успешном сохранении диаграммы
    - closed: Излучается при закрытии диалога
    """
    
    saved = pyqtSignal()
    closed = pyqtSignal(object)

    def __init__(
        self, 
        parent: Optional[QDialog] = None, 
        chart_type: Optional[str] = None, 
        chart_id: Optional[int] = None
    ):
        """
        Инициализация диалога
        
        :param parent: Родительское окно
        :param chart_type: Тип диаграммы ('bar', 'line', 'pie') для создания
        :param chart_id: ID существующей диаграммы для редактирования
        """
        super().__init__(parent)
        self.chart_type = chart_type or 'bar'  # Тип по умолчанию
        self.chart_id = chart_id
        
        # Настройка размеров и заголовка окна
        self.resize(600, 500)
        
        # Создание элементов интерфейса (ПЕРЕД вызовом _update_window_title)
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        
        # Устанавливаем заголовок окна (после создания виджетов)
        self._update_window_title()
        
        # Загрузка данных, если редактируем существующую диаграмму
        if chart_id:
            self._load_existing_chart()
        else:
            # Инициализация таблицы для новой диаграммы
            self.build_table()

    def _create_widgets(self) -> None:
        """Создает виджеты диалога"""
        # Поле ввода имени диаграммы
        self.name_label = QLabel("Имя диаграммы:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите уникальное имя")
        
        # Выпадающий список для выбора типа диаграммы
        self.type_label = QLabel("Тип диаграммы:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Столбчатая", "Линейная", "Круговая"])
        
        # Таблица для ввода данных
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)  # Чередование цветов строк
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Кнопки управления
        self.save_button = QPushButton("Сохранить")
        self.save_button.setToolTip("Сохранить диаграмму в базе данных")
        
        self.view_button = QPushButton("Просмотреть диаграмму")
        self.view_button.setToolTip("Предпросмотр текущей диаграммы")
        
        self.cancel_button = QPushButton("Отменить")
        self.cancel_button.setToolTip("Закрыть диалог без сохранения")

    def _setup_layout(self) -> None:
        """Настраивает компоновку элементов интерфейса"""
        layout = QVBoxLayout(self)
        
        # Добавляем элементы управления
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_combo)
        
        # Добавляем таблицу (с отступами)
        layout.addWidget(QLabel("Данные:"), alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.table)
        
        # Компоновка кнопок
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.view_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Подключает сигналы к обработчикам"""
        # Сигналы изменения типа и имени
        self.type_combo.currentIndexChanged.connect(self.build_table)
        self.name_edit.textChanged.connect(self._update_window_title)
        
        # Сигналы таблицы
        self.table.cellChanged.connect(self._handle_cell_change)
        self.table.customContextMenuRequested.connect(self._open_context_menu)
        
        # Сигналы кнопок
        self.save_button.clicked.connect(self._on_save)
        self.view_button.clicked.connect(self._on_view)
        self.cancel_button.clicked.connect(self._on_cancel)

    def _update_window_title(self) -> None:
        """Обновляет заголовок окна в зависимости от режима"""
        # Проверяем, создано ли поле ввода имени
        if not hasattr(self, 'name_edit'):
            return
            
        if self.chart_id:
            # Режим редактирования: используем текущее имя из поля ввода
            name = self.name_edit.text().strip() or "Без имени"
            type_names = {
                'bar': 'столбчатой',
                'line': 'линейной',
                'pie': 'круговой'
            }
            self.setWindowTitle(
                f'Редактирование {type_names[self.chart_type]} диаграммы "{name}"'
            )
        else:
            # Режим создания
            self.setWindowTitle("Создание новой диаграммы")

    def _load_existing_chart(self) -> None:
        """Загружает данные существующей диаграммы для редактирования"""
        chart = get_chart(self.chart_type, self.chart_id)
        if not chart:
            QMessageBox.warning(self, "Ошибка", "Диаграмма не найдена")
            self.close()
            return
        
        # Устанавливаем имя диаграммы
        self.name_edit.setText(chart.name)
        
        # Устанавливаем тип диаграммы (только для отображения)
        type_index = {'bar': 0, 'line': 1, 'pie': 2}[self.chart_type]
        self.type_combo.setCurrentIndex(type_index)
        self.type_combo.setEnabled(False)  # Тип нельзя менять при редактировании
        
        # Настраиваем таблицу и загружаем данные
        self.build_table()
        self.load_data(chart.data)

    def build_table(self) -> None:
        """
        Настраивает таблицу данных в соответствии с выбранным типом диаграммы
        
        Определяет:
        - Количество столбцов
        - Заголовки столбцов
        - Начальное количество строк
        """
        # Определяем текущий тип диаграммы по выбранному индексу
        mapping = {0: 'bar', 1: 'line', 2: 'pie'}
        self.chart_type = mapping[self.type_combo.currentIndex()]
        
        # Настраиваем столбцы в зависимости от типа
        if self.chart_type in ('bar', 'pie'):
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["Наименование", "Значение"])
        else:  # Линейная диаграмма
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Серия", "X", "Y"])
        
        # Устанавливаем начальное количество строк + пустая строка для ввода
        self.table.setRowCount(5)
        
        # Разрешаем контекстное меню для удаления строк
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def load_data(self, data: List[Dict[str, Any]]) -> None:
        """
        Загружает данные в таблицу
        
        :param data: Список словарей с данными диаграммы
        """
        # Блокируем сигналы для предотвращения рекурсивных обновлений
        self.table.blockSignals(True)
        
        # Устанавливаем количество строк (данные + пустая строка для новых вводов)
        self.table.setRowCount(len(data) + 1)
        
        # Заполняем таблицу данными
        for row, item in enumerate(data):
            if self.chart_type in ('bar', 'pie'):
                self.table.setItem(row, 0, QTableWidgetItem(item['label']))
                self.table.setItem(row, 1, QTableWidgetItem(str(item['value'])))
            else:  # Линейная диаграмма
                self.table.setItem(row, 0, QTableWidgetItem(item['series']))
                self.table.setItem(row, 1, QTableWidgetItem(str(item['x'])))
                self.table.setItem(row, 2, QTableWidgetItem(str(item['y'])))
        
        # Включаем сигналы обратно
        self.table.blockSignals(False)

    def _handle_cell_change(self, row: int, column: int) -> None:
        """
        Обрабатывает изменение ячейки таблицы
        
        Автоматически добавляет новую строку, если заполнена последняя строка
        """
        # Проверяем, является ли измененная ячейка последней в таблице
        if row == self.table.rowCount() - 1:
            # Проверяем, есть ли данные в строке
            has_data = any(
                self.table.item(row, col) and 
                self.table.item(row, col).text().strip()
                for col in range(self.table.columnCount())
            )
            
            # Если есть данные, добавляем новую пустую строку
            if has_data:
                self.table.insertRow(self.table.rowCount())

    def _open_context_menu(self, pos: QPoint) -> None:
        """Открывает контекстное меню для удаления строк"""
        menu = QMenu()
        delete_action = menu.addAction("Удалить строку")
        
        # Показываем меню и обрабатываем выбор
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        
        if action == delete_action:
            # Получаем выделенные строки
            selected_rows = {index.row() for index in self.table.selectedIndexes()}
            
            # Удаляем строки в обратном порядке, чтобы не нарушить индексы
            for row in sorted(selected_rows, reverse=True):
                self.table.removeRow(row)

    def get_data(self) -> List[Dict[str, Any]]:
        """
        Извлекает данные из таблицы
        
        :return: Список словарей с данными в формате, соответствующем типу диаграммы
        """
        result = []
        cols = self.table.columnCount()
        
        for row in range(self.table.rowCount()):
            # Получаем элементы строки
            items = [self.table.item(row, col) for col in range(cols)]
            
            # Пропускаем пустые строки (где первый столбец пуст)
            if not items or not items[0] or not items[0].text().strip():
                continue
            
            # Обработка данных для столбчатых и круговых диаграмм
            if self.chart_type in ('bar', 'pie'):
                label = items[0].text().strip()
                
                # Пытаемся преобразовать значение в число
                try:
                    value = float(items[1].text()) if items[1] and items[1].text().strip() else 0.0
                except ValueError:
                    value = 0.0
                
                result.append({'label': label, 'value': value})
            
            # Обработка данных для линейных диаграмм
            else:
                series = items[0].text().strip()
                
                # Пытаемся преобразовать координаты в числа
                try:
                    x = float(items[1].text()) if items[1] and items[1].text().strip() else 0.0
                except ValueError:
                    x = 0.0
                
                try:
                    y = float(items[2].text()) if items[2] and items[2].text().strip() else 0.0
                except ValueError:
                    y = 0.0
                
                result.append({'series': series, 'x': x, 'y': y})
        
        return result

    def _on_save(self) -> None:
        """Обрабатывает сохранение диаграммы"""
        name = self.name_edit.text().strip()
        
        # Проверка наличия имени
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя диаграммы")
            return
        
        # Получение данных из таблицы
        data = self.get_data()
        
        # Дополнительная валидация для столбчатых и круговых диаграмм
        if self.chart_type in ['bar', 'pie']:
            labels = [item['label'] for item in data]
            
            # Проверка на уникальность меток
            if len(labels) != len(set(labels)):
                # Находим дубликаты
                duplicates = {label for label in labels if labels.count(label) > 1}
                
                QMessageBox.warning(
                    self, 
                    "Ошибка уникальности",
                    f"Найдены дубликаты меток: {', '.join(duplicates)}\n"
                    "Названия должны быть уникальны для каждого значения!"
                )
                return
        
        try:
            # Сохраняем диаграмму
            save_chart(self.chart_type, name, data, self.chart_id)
            
            # Отправляем сигнал об успешном сохранении
            self.saved.emit()
            
            # Закрываем диалог после успешного сохранения
            if not self.chart_id:
                self.close()
                
        except ValueError as e:
            # Обработка ошибок сохранения (например, неуникальное имя)
            QMessageBox.warning(self, "Ошибка сохранения", str(e))

    def _on_view(self) -> None:
        """Открывает окно предпросмотра диаграммы"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя диаграммы")
            return
        
        # Получаем текущие данные
        data = self.get_data()
        
        # Проверяем наличие данных
        if not data:
            QMessageBox.warning(self, "Ошибка", "Добавьте данные для диаграммы")
            return
        
        # Для столбчатых и круговых диаграмм проверяем уникальность меток
        if self.chart_type in ['bar', 'pie']:
            labels = [item['label'] for item in data]
            
            # Проверка на уникальность меток
            if len(labels) != len(set(labels)):
                # Находим дубликаты
                duplicates = {label for label in labels if labels.count(label) > 1}
                
                QMessageBox.warning(
                    self, 
                    "Ошибка уникальности",
                    f"Найдены дубликаты меток: {', '.join(duplicates)}\n"
                    "Названия должны быть уникальны для каждого значения!\n\n"
                    "Исправьте дубликаты перед просмотром диаграммы."
                )
                return
        
        # Создаем и показываем окно предпросмотра
        preview = PlotWindow(
            chart_type=self.chart_type, 
            name=name, 
            data=data, 
            parent=self
        )
        preview.show()

    def _on_cancel(self) -> None:
        """Обрабатывает отмену редактирования"""
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Обрабатывает закрытие окна"""
        # Отправляем сигнал о закрытии
        self.closed.emit(self)
        super().closeEvent(event)