"""
Главное окно приложения "Визуальный редактор диаграмм"

Этот модуль реализует главное окно приложения, которое:
1. Отображает иерархическое дерево диаграмм (сгруппированных по типам)
2. Предоставляет кнопки для управления диаграммами
3. Обрабатывает создание, открытие, удаление, импорт и экспорт диаграмм

Основные компоненты:
- Дерево диаграмм (QTreeWidget)
- Кнопки управления (QPushButton)
- Диалоги для импорта/экспорта (QFileDialog, QInputDialog)
- Взаимодействие с контроллером диаграмм (diagram_controller)
"""

from typing import List, Tuple, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QPushButton, QSplitter, QHBoxLayout, 
    QFileDialog, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtGui import QCloseEvent
from controllers.diagram_controller import (
    list_charts, delete_chart, 
    get_chart, export_to_csv, import_from_csv, save_chart
)
from ui.chart_dialog import ChartDialog
import re 


class MainWindow(QMainWindow):
    """Главное окно приложения для управления диаграммами"""
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """
        Инициализация главного окна
        
        Создает:
        - Разделенный интерфейс с деревом диаграмм слева
        - Панель кнопок управления
        - Список для отслеживания открытых окон редактирования
        """
        super().__init__(parent)
        self.setWindowTitle("Визуальный редактор диаграмм")
        self.resize(1000, 700)  # Начальный размер окна

        # Список открытых окон редактирования диаграмм
        self.open_dialogs: List[ChartDialog] = []

        # Создаем разделитель для основного интерфейса
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        
        # Левая панель: дерево диаграмм
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Виджет дерева для отображения диаграмм по типам
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)  # Скрываем заголовки столбцов
        left_layout.addWidget(self.tree)
        
        # Кнопка обновления списка диаграмм
        self.refresh_button = QPushButton("Обновить список")
        self.refresh_button.setToolTip("Обновить список диаграмм из базы данных")
        left_layout.addWidget(self.refresh_button)
        
        splitter.addWidget(left_widget)

        # Правая панель (пока пустая, может использоваться для предпросмотра)
        self.right_widget = QWidget()
        splitter.addWidget(self.right_widget)

        # Основной контейнер для всего интерфейса
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.addWidget(splitter)
        
        # Панель кнопок управления
        btn_layout = QHBoxLayout()
        
        # Кнопки управления диаграммами
        self.create_button = QPushButton("Создать диаграмму")
        self.create_button.setToolTip("Создать новую диаграмму")
        
        self.open_button = QPushButton("Открыть")
        self.open_button.setToolTip("Открыть выбранную диаграмму для редактирования")
        self.open_button.setEnabled(False)  # По умолчанию неактивна
        
        self.delete_button = QPushButton("Удалить диаграмму")
        self.delete_button.setToolTip("Удалить выбранную диаграмму")
        self.delete_button.setEnabled(False)  # По умолчанию неактивна
        
        self.export_btn = QPushButton("Экспорт в CSV")
        self.export_btn.setToolTip("Экспортировать выбранную диаграмму в CSV файл")
        self.export_btn.setEnabled(False)  # По умолчанию неактивна
        
        self.import_btn = QPushButton("Импорт из CSV")
        self.import_btn.setToolTip("Импортировать диаграмму из CSV файла")
        
        # Размещаем кнопки на панели
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.create_button)
        btn_layout.addWidget(self.open_button)
        btn_layout.addWidget(self.delete_button)
        
        main_layout.addLayout(btn_layout)
        self.setCentralWidget(container)

        # Подключаем обработчики событий
        self._connect_signals()
        
        # Первоначальная загрузка данных
        self.load_tree()

    def _connect_signals(self) -> None:
        """Подключает сигналы кнопок и виджетов к обработчикам"""
        self.refresh_button.clicked.connect(self.load_tree)
        self.create_button.clicked.connect(self.on_create)
        self.open_button.clicked.connect(self.on_open)
        self.delete_button.clicked.connect(self.on_delete)
        self.tree.itemSelectionChanged.connect(self.on_selection)
        self.export_btn.clicked.connect(self.on_export)
        self.import_btn.clicked.connect(self.on_import)

    def load_tree(self) -> None:
        """
        Загружает и отображает диаграммы из базы данных в древовидной структуре
        
        Структура:
        - Корневые элементы: типы диаграмм (Столбчатые, Линейные, Круговые)
        - Дочерние элементы: конкретные диаграммы каждого типа
        """
        self.tree.clear()
        
        # Определяем типы диаграмм для отображения
        types: List[Tuple[str, str]] = [
            ("Столбчатые", 'bar'), 
            ("Линейные", 'line'), 
            ("Круговые", 'pie')
        ]
        
        for title, key in types:
            # Создаем корневой элемент для типа диаграмм
            parent = QTreeWidgetItem(self.tree, [title])
            
            # Получаем все диаграммы этого типа из базы данных
            charts = list_charts(key)
            
            # Добавляем каждую диаграмму как дочерний элемент
            for chart in charts:
                item = QTreeWidgetItem(parent, [chart.name])
                # Сохраняем в данных тип и ID диаграммы
                item.setData(0, Qt.ItemDataRole.UserRole, (key, chart.id))
            
            # Раскрываем корневой элемент для показа дочерних
            parent.setExpanded(True)

    def on_selection(self) -> None:
        """
        Обрабатывает изменение выбора в дереве диаграмм
        
        Активирует/деактивирует кнопки в зависимости от выбора:
        - Кнопки "Открыть", "Удалить", "Экспорт" активны только при выборе конкретной диаграммы
        - При выборе типа диаграммы или ничего кнопки деактивируются
        """
        selected_items = self.tree.selectedItems()
        
        # Определяем, выбран ли конкретный элемент диаграммы (не тип)
        is_diagram_selected = bool(
            selected_items and 
            selected_items[0].parent() is not None
        )
        
        # Устанавливаем состояние кнопок
        self.open_button.setEnabled(is_diagram_selected)
        self.delete_button.setEnabled(is_diagram_selected)
        self.export_btn.setEnabled(is_diagram_selected)

    def on_create(self) -> None:
        """Обрабатывает создание новой диаграммы"""
        dialog = ChartDialog(parent=self)
        self.open_dialogs.append(dialog)
        
        # Подключаем сигналы диалога
        dialog.saved.connect(self.load_tree)  # Обновляем дерево после сохранения
        dialog.closed.connect(lambda d=dialog: self._remove_dialog(d))
        
        dialog.show()

    def on_open(self) -> None:
        """Открывает выбранную диаграмму для редактирования"""
        selected_item = self.tree.selectedItems()[0]
        
        # Извлекаем тип и ID диаграммы из данных элемента
        chart_type, chart_id = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        # Создаем диалог редактирования
        dialog = ChartDialog(parent=self, chart_type=chart_type, chart_id=chart_id)
        self.open_dialogs.append(dialog)
        
        # Подключаем сигналы диалога
        dialog.saved.connect(self.load_tree)
        dialog.closed.connect(lambda d=dialog: self._remove_dialog(d))
        
        dialog.show()

    def _remove_dialog(self, dialog: ChartDialog) -> None:
        """Удаляет закрытый диалог из списка открытых"""
        if dialog in self.open_dialogs:
            self.open_dialogs.remove(dialog)

    def on_delete(self) -> None:
        """Удаляет выбранную диаграмму"""
        selected_item = self.tree.selectedItems()[0]
        chart_type, chart_id = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        # Подтверждение удаления
        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить эту диаграмму?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            delete_chart(chart_type, chart_id)
            self.load_tree()  # Обновляем список диаграмм
    
    def on_export(self) -> None:
        """Экспортирует выбранную диаграмму в CSV файл"""
        selected_item = self.tree.selectedItems()[0]
        chart_type, chart_id = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        # Получаем диаграмму из базы данных
        chart = get_chart(chart_type, chart_id)
        
        if not chart:
            QMessageBox.warning(self, "Ошибка", "Диаграмма не найдена")
            return
        
        # Формируем предложение для имени файла
        # 1. Удаляем запрещенные символы из имени диаграммы
        clean_name = re.sub(r'[<>:"/\\|?*]', '_', chart.name)
        
        # 2. Создаем удобочитаемое название типа
        type_names = {'bar': 'столбчатая', 'line': 'линейная', 'pie': 'круговая'}
        suggested_name = f"{clean_name} ({type_names[chart_type]}).csv"
        
        # Запрашиваем у пользователя место сохранения
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Экспорт диаграммы в CSV", 
            suggested_name,
            "CSV Files (*.csv)"
        )
        
        if filename:
            # Пытаемся экспортировать
            if export_to_csv(chart, filename):
                QMessageBox.information(
                    self, 
                    "Экспорт завершен", 
                    f"Диаграмма '{chart.name}' успешно экспортирована"
                )
            else:
                QMessageBox.warning(
                    self, 
                    "Ошибка экспорта", 
                    "Не удалось экспортировать диаграмму"
                )

    def on_import(self) -> None:
        """Импортирует диаграмму из CSV файла"""
        # Запрашиваем файл для импорта
        filename, _ = QFileDialog.getOpenFileName(
            self, 
            "Импорт диаграммы из CSV", 
            "", 
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return  # Пользователь отменил выбор
            
        # Пытаемся импортировать диаграмму из файла
        chart = import_from_csv(filename)
        if not chart:
            QMessageBox.warning(
                self, 
                "Ошибка импорта", 
                "Невозможно импортировать файл. Проверьте формат."
            )
            return
            
        # Запрашиваем подтверждение имени для импортируемой диаграммы
        name, ok = QInputDialog.getText(
            self, 
            "Имя диаграммы", 
            "Введите имя для импортируемой диаграммы:",
            text=chart.name
        )
        
        # Проверяем, ввел ли пользователь имя
        if not ok or not name.strip():
            return
            
        try:
            # Сохраняем диаграмму в базе данных
            saved_chart = save_chart(chart.type, name, chart.data)
            
            # Обновляем дерево диаграмм
            self.load_tree()
            
            # Уведомляем об успехе
            QMessageBox.information(
                self, 
                "Импорт завершен", 
                f"Диаграмма '{saved_chart.name}' успешно импортирована"
            )
        except ValueError as e:
            # Обрабатываем ошибки (например, неуникальное имя)
            QMessageBox.warning(self, "Ошибка импорта", str(e))
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Обрабатывает закрытие главного окна"""
        # Закрываем все открытые диалоги редактирования
        for dialog in self.open_dialogs[:]:
            dialog.close()
        
        super().closeEvent(event)