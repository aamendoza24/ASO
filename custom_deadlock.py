import math
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from PySide6.QtCore import (QEasingCurve, QObject, QPointF, Property, QSequentialAnimationGroup,
                            QParallelAnimationGroup, QPropertyAnimation, QTimer, Qt, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGraphicsDropShadowEffect, QGraphicsEllipseItem,
    QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QSlider, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QLineEdit, QSpinBox,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout, QCheckBox,
    QProgressBar, QTextEdit, QFrame, QScrollArea, QTextBrowser, QHeaderView
)


# -----------------------------
# Enums y estructuras de datos
# -----------------------------

class ProcessState(Enum):
    NEW = "Nuevo"
    READY = "Listo"
    EXECUTING = "En ejecución"
    BLOCKED = "Bloqueado"
    FINISHED = "Terminado"

class Priority(Enum):
    LOW = "Bajo"
    MEDIUM = "Medio"
    HIGH = "Alto"
    CRITICAL = "Crítico"

class ResourceState(Enum):
    AVAILABLE = "Disponible"
    IN_USE = "En uso"

@dataclass
class CustomResource:
    name: str
    total_instances: int
    available_instances: int
    assigned_to: Dict[str, int] = None  # proceso -> cantidad asignada

    def __post_init__(self):
        if self.assigned_to is None:
            self.assigned_to = {}

@dataclass
class CustomProcess:
    name: str
    priority: Priority
    needed_resources: Dict[str, int] = None  # recurso -> cantidad necesaria
    assigned_resources: Dict[str, int] = None  # recurso -> cantidad asignada
    waiting_for: Dict[str, int] = None  # recurso -> cantidad que está esperando
    state: ProcessState = ProcessState.NEW

    def __post_init__(self):
        if self.needed_resources is None:
            self.needed_resources = {}
        if self.assigned_resources is None:
            self.assigned_resources = {}
        if self.waiting_for is None:
            self.waiting_for = {}

@dataclass
class EventLog:
    timestamp: str
    action: str
    process: str
    resource: str
    result: str
    details: str = ""


# -----------------------------
# Widgets de configuración personalizada
# -----------------------------

class CustomProcessConfig(QWidget):
    def __init__(self, on_data_changed=None):
        super().__init__()
        self.on_data_changed = on_data_changed
        self.processes: Dict[str, CustomProcess] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("CONFIGURACIÓN DE PROCESOS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Formulario para agregar procesos
        form_group = QGroupBox("Agregar Proceso")
        form_layout = QFormLayout(form_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: P1, P2, P3...")
        form_layout.addRow("Nombre:", self.name_input)
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems([p.value for p in Priority])
        form_layout.addRow("Prioridad:", self.priority_combo)
        
        self.add_btn = QPushButton("Agregar")
        self.add_btn.clicked.connect(self.add_process)
        form_layout.addRow(self.add_btn)
        
        layout.addWidget(form_group)
        
        # Lista de procesos
        processes_group = QGroupBox("PROCESOS CONFIGURADOS")
        processes_layout = QVBoxLayout(processes_group)
        
        self.processes_list = QListWidget()
        self.processes_list.setMaximumHeight(200)
        processes_layout.addWidget(self.processes_list)
        
        # Botón para eliminar proceso seleccionado
        self.remove_btn = QPushButton("Eliminar Seleccionado")
        self.remove_btn.clicked.connect(self.remove_selected_process)
        processes_layout.addWidget(self.remove_btn)
        
        layout.addWidget(processes_group)

    def add_process(self):
        name = self.name_input.text().strip()
        if not name:
            return
        
        if name in self.processes:
            QMessageBox.warning(self, "Error", f"El proceso {name} ya existe")
            return
        
        priority = Priority(self.priority_combo.currentText())
        process = CustomProcess(name=name, priority=priority)
        self.processes[name] = process
        self.update_list()
        
        self.name_input.clear()
        
        if self.on_data_changed:
            self.on_data_changed()

    def remove_selected_process(self):
        current_item = self.processes_list.currentItem()
        if current_item:
            process_name = current_item.data(Qt.UserRole)
            if process_name in self.processes:
                del self.processes[process_name]
                self.update_list()
                if self.on_data_changed:
                    self.on_data_changed()

    def update_list(self):
        self.processes_list.clear()
        
        for name, process in self.processes.items():
            item_text = f"{name} - {process.priority.value}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.processes_list.addItem(item)


class CustomResourceConfig(QWidget):
    def __init__(self, on_data_changed=None):
        super().__init__()
        self.on_data_changed = on_data_changed
        self.resources: Dict[str, CustomResource] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("CONFIGURACIÓN DE RECURSOS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Formulario para agregar recursos
        form_group = QGroupBox("Agregar Recurso")
        form_layout = QFormLayout(form_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: R1, R2, R3...")
        form_layout.addRow("Nombre:", self.name_input)
        
        self.instances_input = QSpinBox()
        self.instances_input.setRange(1, 10)
        self.instances_input.setValue(1)
        form_layout.addRow("Instancias totales:", self.instances_input)
        
        self.add_btn = QPushButton("Agregar")
        self.add_btn.clicked.connect(self.add_resource)
        form_layout.addRow(self.add_btn)
        
        layout.addWidget(form_group)
        
        # Lista de recursos
        resources_group = QGroupBox("RECURSOS CONFIGURADOS")
        resources_layout = QVBoxLayout(resources_group)
        
        self.resources_list = QListWidget()
        self.resources_list.setMaximumHeight(200)
        resources_layout.addWidget(self.resources_list)
        
        # Botón para eliminar recurso seleccionado
        self.remove_btn = QPushButton("Eliminar Seleccionado")
        self.remove_btn.clicked.connect(self.remove_selected_resource)
        resources_layout.addWidget(self.remove_btn)
        
        layout.addWidget(resources_group)

    def add_resource(self):
        name = self.name_input.text().strip()
        if not name:
            return
        
        if name in self.resources:
            QMessageBox.warning(self, "Error", f"El recurso {name} ya existe")
            return
        
        instances = self.instances_input.value()
        resource = CustomResource(
            name=name, 
            total_instances=instances, 
            available_instances=instances
        )
        self.resources[name] = resource
        self.update_list()
        
        self.name_input.clear()
        self.instances_input.setValue(1)
        
        if self.on_data_changed:
            self.on_data_changed()

    def remove_selected_resource(self):
        current_item = self.resources_list.currentItem()
        if current_item:
            resource_name = current_item.data(Qt.UserRole)
            if resource_name in self.resources:
                del self.resources[resource_name]
                self.update_list()
                if self.on_data_changed:
                    self.on_data_changed()

    def update_list(self):
        self.resources_list.clear()
        
        for name, resource in self.resources.items():
            item_text = f"{name} - {resource.available_instances}/{resource.total_instances} disponibles"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.resources_list.addItem(item)


class ResourceAssignmentPanel(QWidget):
    def __init__(self, on_assignment_changed=None):
        super().__init__()
        self.on_assignment_changed = on_assignment_changed
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("ASIGNACIÓN DE RECURSOS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Selector de proceso
        process_layout = QHBoxLayout()
        process_layout.addWidget(QLabel("Proceso:"))
        self.process_combo = QComboBox()
        process_layout.addWidget(self.process_combo)
        layout.addLayout(process_layout)
        
        # Selector de recurso
        resource_layout = QHBoxLayout()
        resource_layout.addWidget(QLabel("Recurso:"))
        self.resource_combo = QComboBox()
        resource_layout.addWidget(self.resource_combo)
        layout.addLayout(resource_layout)
        
        # Cantidad
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel("Cantidad:"))
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 10)
        self.quantity_input.setValue(1)
        quantity_layout.addWidget(self.quantity_input)
        layout.addLayout(quantity_layout)
        
        # Botones de acción
        button_layout = QHBoxLayout()
        
        self.assign_btn = QPushButton("Asignar")
        self.assign_btn.clicked.connect(self.assign_resource)
        button_layout.addWidget(self.assign_btn)
        
        self.release_btn = QPushButton("Liberar")
        self.release_btn.clicked.connect(self.release_resource)
        button_layout.addWidget(self.release_btn)
        
        layout.addLayout(button_layout)
        
        # Estado actual
        self.status_label = QLabel("Selecciona proceso y recurso")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

    def update_processes(self, processes: Dict[str, CustomProcess]):
        self.process_combo.clear()
        for name in processes.keys():
            self.process_combo.addItem(name)

    def update_resources(self, resources: Dict[str, CustomResource]):
        self.resource_combo.clear()
        for name in resources.keys():
            self.resource_combo.addItem(name)

    def assign_resource(self):
        process_name = self.process_combo.currentText()
        resource_name = self.resource_combo.currentText()
        quantity = self.quantity_input.value()
        
        if self.on_assignment_changed:
            self.on_assignment_changed("assign", process_name, resource_name, quantity)

    def release_resource(self):
        process_name = self.process_combo.currentText()
        resource_name = self.resource_combo.currentText()
        quantity = self.quantity_input.value()
        
        if self.on_assignment_changed:
            self.on_assignment_changed("release", process_name, resource_name, quantity)

    def update_status(self, text: str):
        self.status_label.setText(text)


class GraphVisualization(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.setDragMode(QGraphicsView.NoDrag)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.process_nodes: Dict[str, QGraphicsRectItem] = {}
        self.resource_nodes: Dict[str, QGraphicsEllipseItem] = {}
        self.arrows: List[QGraphicsPathItem] = []
        
    def update_graph(self, processes: Dict[str, CustomProcess], resources: Dict[str, CustomResource]):
        self.scene.clear()
        self.process_nodes.clear()
        self.resource_nodes.clear()
        self.arrows.clear()
        
        # Crear nodos de procesos
        for i, (name, process) in enumerate(processes.items()):
            node = self.create_process_node(name, i, len(processes), process)
            self.scene.addItem(node)
            self.process_nodes[name] = node
        
        # Crear nodos de recursos
        for i, (name, resource) in enumerate(resources.items()):
            node = self.create_resource_node(name, i, len(resources))
            self.scene.addItem(node)
            self.resource_nodes[name] = node
        
        # Crear flechas de asignación
        for process_name, process in processes.items():
            for resource_name, quantity in process.assigned_resources.items():
                if quantity > 0 and resource_name in self.resource_nodes:
                    self.create_assignment_arrow(process_name, resource_name, quantity)
        
        # Crear flechas de solicitud (recursos necesarios pero no asignados)
        for process_name, process in processes.items():
            for resource_name, needed in process.needed_resources.items():
                assigned = process.assigned_resources.get(resource_name, 0)
                if needed > assigned and resource_name in self.resource_nodes:
                    self.create_request_arrow(process_name, resource_name, needed - assigned)

    def create_process_node(self, name: str, index: int, total: int, process: CustomProcess = None) -> QGraphicsRectItem:
        node = QGraphicsRectItem(-30, -15, 60, 30)
        
        # Cambiar color según el estado del proceso
        if process and process.state == ProcessState.BLOCKED:
            # Proceso bloqueado - color rojo/naranja
            node.setBrush(QColor(231, 76, 60))
            node.setPen(QPen(QColor(192, 57, 43), 2))
        else:
            # Proceso normal - color azul
            node.setBrush(QColor(99, 179, 237))
            node.setPen(QPen(QColor(35, 110, 170), 2))
        
        # Posicionar en círculo
        angle = 2 * math.pi * index / total - math.pi / 2
        radius = 150
        x = 200 + radius * math.cos(angle)
        y = 200 + radius * math.sin(angle)
        node.setPos(x, y)
        
        # Agregar etiqueta
        label = QGraphicsSimpleTextItem(name, node)
        label.setPos(-15, -5)
        label.setBrush(QColor(255, 255, 255))
        
        return node

    def create_resource_node(self, name: str, index: int, total: int) -> QGraphicsEllipseItem:
        node = QGraphicsEllipseItem(-25, -25, 50, 50)
        node.setBrush(QColor(255, 204, 112))
        node.setPen(QPen(QColor(190, 140, 60), 2))
        
        # Posicionar en círculo interior
        angle = 2 * math.pi * index / total - math.pi / 2
        radius = 100
        x = 200 + radius * math.cos(angle)
        y = 200 + radius * math.sin(angle)
        node.setPos(x, y)
        
        # Agregar etiqueta
        label = QGraphicsSimpleTextItem(name, node)
        label.setPos(-10, -5)
        label.setBrush(QColor(0, 0, 0))
        
        return node

    def create_assignment_arrow(self, process_name: str, resource_name: str, quantity: int):
        if process_name not in self.process_nodes or resource_name not in self.resource_nodes:
            return
        
        start = self.process_nodes[process_name].sceneBoundingRect().center()
        end = self.resource_nodes[resource_name].sceneBoundingRect().center()
        
        arrow = self.create_arrow(start, end, QColor(46, 204, 113), f"{quantity}")
        self.scene.addItem(arrow)
        self.arrows.append(arrow)

    def create_request_arrow(self, process_name: str, resource_name: str, quantity: int):
        if process_name not in self.process_nodes or resource_name not in self.resource_nodes:
            return
        
        start = self.process_nodes[process_name].sceneBoundingRect().center()
        end = self.resource_nodes[resource_name].sceneBoundingRect().center()
        
        arrow = self.create_arrow(start, end, QColor(231, 76, 60), f"?{quantity}")
        self.scene.addItem(arrow)
        self.arrows.append(arrow)

    def create_arrow(self, start: QPointF, end: QPointF, color: QColor, label: str) -> QGraphicsPathItem:
        path = QPainterPath(start)
        path.lineTo(end)
        
        # Crear cabeza de flecha
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.hypot(dx, dy)
        if length > 0:
            angle = math.atan2(dy, dx)
            head_length = 10
            left = QPointF(
                end.x() - head_length * math.cos(angle - math.pi / 6),
                end.y() - head_length * math.sin(angle - math.pi / 6)
            )
            right = QPointF(
                end.x() - head_length * math.cos(angle + math.pi / 6),
                end.y() - head_length * math.sin(angle + math.pi / 6)
            )
            path.moveTo(end)
            path.lineTo(left)
            path.moveTo(end)
            path.lineTo(right)
        
        arrow = QGraphicsPathItem(path)
        arrow.setPen(QPen(color, 3))
        
        # Agregar etiqueta de cantidad
        mid_x = (start.x() + end.x()) / 2
        mid_y = (start.y() + end.y()) / 2
        label_item = QGraphicsSimpleTextItem(label, arrow)
        label_item.setPos(mid_x - 10, mid_y - 10)
        label_item.setBrush(color)
        
        return arrow


class EventLogWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("REGISTRO DE EVENTOS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Tabla de eventos
        self.event_table = QTableWidget()
        self.event_table.setColumnCount(4)
        self.event_table.setHorizontalHeaderLabels([
            "Ciclo CPU", "Acción", "Proceso → Recurso", "Estado"
        ])
        
        # Configurar tabla
        self.event_table.setMaximumHeight(300)
        self.event_table.setAlternatingRowColors(True)
        self.event_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.setColumnWidth(0, 80)  # Ciclo CPU
        self.event_table.setColumnWidth(1, 100)  # Acción
        self.event_table.setColumnWidth(2, 150)  # Proceso → Recurso
        
        layout.addWidget(self.event_table)
        
        # Botones de control
        button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Limpiar Registro")
        self.clear_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_btn)
        
        self.auto_btn = QPushButton("Asignación Automática")
        self.auto_btn.setCheckable(True)
        self.auto_btn.clicked.connect(self.toggle_auto_assignment)
        button_layout.addWidget(self.auto_btn)
        
        layout.addLayout(button_layout)
        
        # Botón para limpiar todo el sistema (se conectará desde la ventana principal)
        self.clear_system_btn = QPushButton("Limpiar Sistema")
        self.clear_system_btn.setStyleSheet("background: #e74c3c; color: white; font-weight: bold;")
        layout.addWidget(self.clear_system_btn)

    def add_event(self, event: EventLog):
        row = self.event_table.rowCount()
        self.event_table.insertRow(row)
        
        # Ciclo CPU
        cycle_item = QTableWidgetItem(str(event.timestamp))
        self.event_table.setItem(row, 0, cycle_item)
        
        # Acción
        action_item = QTableWidgetItem(event.action)
        self.event_table.setItem(row, 1, action_item)
        
        # Proceso → Recurso
        process_resource_item = QTableWidgetItem(f"{event.process} → {event.resource}")
        self.event_table.setItem(row, 2, process_resource_item)
        
        # Estado con color de fuente
        state_item = QTableWidgetItem(event.result)
        state_colors = {
            "ÉXITO": QColor(46, 204, 113),      # Verde
            "BLOQUEADO": QColor(255, 193, 7),   # Amarillo/Naranja
            "FALLO": QColor(231, 76, 60),       # Rojo
            "ALERTA": QColor(155, 89, 182),     # Púrpura
            "ERROR": QColor(231, 76, 60),       # Rojo
            "INICIADO": QColor(52, 152, 219),   # Azul
            "DETENIDO": QColor(149, 165, 166)   # Gris
        }
        
        # Aplicar color de fuente según el estado
        state_color = state_colors.get(event.result, QColor(0, 0, 0))  # Negro por defecto
        state_item.setForeground(state_color)
        
        self.event_table.setItem(row, 3, state_item)
        
        # Scroll al final
        self.event_table.scrollToBottom()

    def clear_log(self):
        self.event_table.setRowCount(0)

    def toggle_auto_assignment(self, checked):
        if checked:
            self.auto_btn.setText("Auto ON")
            self.auto_btn.setStyleSheet("background: #10b981; color: white;")
        else:
            self.auto_btn.setText("Asignación Automática")
            self.auto_btn.setStyleSheet("")


class DeadlockAnimationWidget(QWidget):
    """Widget animado que muestra una alerta visual cuando se detecta un deadlock"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.animation_group = None
        self._stack_widget = None  # Referencia al QStackedWidget
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignCenter)
        
        # Etiqueta de error
        self.error_label = QLabel("⚠️ DEADLOCK DETECTADO ⚠️")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                background-color: #e74c3c;
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                border-radius: 10px;
                border: 3px solid #c0392b;
            }
        """)
        layout.addWidget(self.error_label)
        
        # Mensaje descriptivo
        self.message_label = QLabel("Los procesos están bloqueados mutuamente")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        layout.addWidget(self.message_label)
        
    def show_animation(self):
        """Muestra la animación de error"""
        # Detener cualquier animación anterior si existe
        if self.animation_group:
            self.animation_group.stop()
            self.animation_group = None
        
        self.setVisible(True)
        # Cambiar a la capa de animación usando la referencia guardada
        if self._stack_widget:
            self._stack_widget.setCurrentIndex(1)
        
        # Crear animación de parpadeo y escala
        normal_style = """
            QLabel {
                background-color: #e74c3c;
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                border-radius: 10px;
                border: 3px solid #c0392b;
            }
        """
        bright_style = """
            QLabel {
                background-color: #ff6b6b;
                color: white;
                font-size: 24px;
                font-weight: bold;
                padding: 20px;
                border-radius: 10px;
                border: 3px solid #ff4757;
            }
        """
        
        self.error_label.setStyleSheet(normal_style)
        
        # Animación de parpadeo repetido
        blink_group = QParallelAnimationGroup()
        for _ in range(5):
            blink_anim = QPropertyAnimation(self.error_label, b"styleSheet")
            blink_anim.setDuration(300)
            blink_anim.setStartValue(normal_style)
            blink_anim.setKeyValueAt(0.5, bright_style)
            blink_anim.setEndValue(normal_style)
            blink_group.addAnimation(blink_anim)
        
        self.animation_group = blink_group
        self.animation_group.start()
        
        # Volver al grafo después de 3 segundos
        QTimer.singleShot(3000, self.hide_animation)
        
    def hide_animation(self):
        """Oculta la animación"""
        if self.animation_group:
            self.animation_group.stop()
        self.setVisible(False)
        # Volver a la capa del grafo
        if self._stack_widget:
            self._stack_widget.setCurrentIndex(0)


class CustomDeadlockWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador de Deadlock Personalizado")
        self.resize(1400, 900)
        
        # Inicializar componentes
        self.process_config = CustomProcessConfig(self.on_data_changed)
        self.resource_config = CustomResourceConfig(self.on_data_changed)
        self.assignment_panel = ResourceAssignmentPanel(self.on_assignment_changed)
        self.graph_visualization = GraphVisualization()
        self.event_log = EventLogWidget()
        self.deadlock_animation = DeadlockAnimationWidget()
        
        # Variables para asignación automática
        self.cpu_cycle = 0
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.auto_assignment_step)
        self.is_auto_running = False
        
        # Estado de deadlock
        self.deadlock_detected = False
        self.deadlock_alert_shown = False  # Flag para evitar mostrar alerta múltiples veces
        self.deadlock_alert_timer = QTimer()
        self.deadlock_alert_timer.setSingleShot(True)
        self.deadlock_alert_timer.timeout.connect(self.reset_deadlock_alert_flag)
        
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Layout principal con splitter horizontal
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo - Configuración
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Pestañas para configuración
        config_tabs = QTabWidget()
        config_tabs.addTab(self.process_config, "Procesos")
        config_tabs.addTab(self.resource_config, "Recursos")
        config_tabs.addTab(self.assignment_panel, "Asignación")
        
        left_layout.addWidget(config_tabs)
        
        # Panel central - Visualización
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título del grafo
        graph_title = QLabel("GRAFO DE RECURSOS Y PROCESOS")
        graph_title.setObjectName("mainTitle")
        graph_title.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(graph_title)
        
        # Contenedor para grafo con animación overlay
        graph_stack = QStackedWidget()
        
        # Capa 1: Visualización del grafo
        graph_stack.addWidget(self.graph_visualization)
        
        # Capa 2: Widget de animación (inicialmente oculto)
        animation_container = QWidget()
        animation_layout = QVBoxLayout(animation_container)
        animation_layout.setContentsMargins(0, 0, 0, 0)
        animation_layout.setAlignment(Qt.AlignCenter)
        animation_layout.addWidget(self.deadlock_animation)
        graph_stack.addWidget(animation_container)
        
        # Guardar referencia al stack para acceso desde el widget de animación
        self.deadlock_animation._stack_widget = graph_stack
        
        # Mostrar siempre la capa del grafo
        graph_stack.setCurrentIndex(0)
        self.graph_stack = graph_stack
        
        center_layout.addWidget(graph_stack)
        
        # Panel derecho - Log de eventos
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(self.event_log)
        
        # Agregar paneles al splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(center_panel)
        main_splitter.addWidget(right_panel)
        
        # Configurar proporciones
        main_splitter.setStretchFactor(0, 1)  # Panel izquierdo
        main_splitter.setStretchFactor(1, 2)  # Panel central
        main_splitter.setStretchFactor(2, 1)  # Panel derecho
        
        main_layout.addWidget(main_splitter)

    def setup_connections(self):
        self.event_log.auto_btn.toggled.connect(self.toggle_auto_assignment)
        self.event_log.clear_system_btn.clicked.connect(self.clear_system)

    def on_data_changed(self):
        self.update_visualization()

    def on_assignment_changed(self, action: str, process_name: str, resource_name: str, quantity: int):
        if action == "assign":
            self.assign_resource(process_name, resource_name, quantity)
        elif action == "release":
            self.release_resource(process_name, resource_name, quantity)

    def assign_resource(self, process_name: str, resource_name: str, quantity: int):
        if process_name not in self.process_config.processes:
            self.log_event("ERROR", process_name, resource_name, "FALLO", "Proceso no existe")
            return
        
        if resource_name not in self.resource_config.resources:
            self.log_event("ERROR", process_name, resource_name, "FALLO", "Recurso no existe")
            return
        
        process = self.process_config.processes[process_name]
        resource = self.resource_config.resources[resource_name]
        
        # Registrar la necesidad del recurso
        process.needed_resources[resource_name] = process.needed_resources.get(resource_name, 0) + quantity
        
        if resource.available_instances >= quantity:
            # Asignar recurso inmediatamente
            resource.available_instances -= quantity
            resource.assigned_to[process_name] = resource.assigned_to.get(process_name, 0) + quantity
            process.assigned_resources[resource_name] = process.assigned_resources.get(resource_name, 0) + quantity
            
            # Actualizar necesidad
            process.needed_resources[resource_name] = max(0, process.needed_resources[resource_name] - quantity)
            
            # Limpiar espera si existía
            if resource_name in process.waiting_for:
                del process.waiting_for[resource_name]
            
            # Cambiar estado a READY si no está esperando nada
            if not process.waiting_for:
                process.state = ProcessState.READY
            
            self.log_event("ASIGNAR", process_name, resource_name, "ÉXITO", f"Cantidad: {quantity}")
            self.update_visualization()
            self.check_deadlock()
        else:
            # Recurso no disponible - proceso queda en espera
            process.waiting_for[resource_name] = process.waiting_for.get(resource_name, 0) + quantity
            process.state = ProcessState.BLOCKED
            
            # Verificar si el recurso está siendo usado por otro proceso
            blocking_processes = []
            for other_process_name, assigned_qty in resource.assigned_to.items():
                if assigned_qty > 0 and other_process_name != process_name:
                    blocking_processes.append(other_process_name)
            
            details = f"Solo {resource.available_instances} disponibles"
            if blocking_processes:
                details += f" (usado por: {', '.join(blocking_processes)})"
            
            self.log_event("ASIGNAR", process_name, resource_name, "BLOQUEADO", details)
            self.update_visualization()
            self.check_deadlock()

    def release_resource(self, process_name: str, resource_name: str, quantity: int):
        if process_name not in self.process_config.processes:
            self.log_event("ERROR", process_name, resource_name, "FALLO", "Proceso no existe")
            return
        
        if resource_name not in self.resource_config.resources:
            self.log_event("ERROR", process_name, resource_name, "FALLO", "Recurso no existe")
            return
        
        process = self.process_config.processes[process_name]
        resource = self.resource_config.resources[resource_name]
        
        current_assigned = process.assigned_resources.get(resource_name, 0)
        if current_assigned >= quantity:
            # Liberar recurso
            resource.available_instances += quantity
            resource.assigned_to[process_name] = max(0, resource.assigned_to.get(process_name, 0) - quantity)
            process.assigned_resources[resource_name] = max(0, current_assigned - quantity)
            
            self.log_event("LIBERAR", process_name, resource_name, "ÉXITO", f"Cantidad: {quantity}")
            
            # Intentar satisfacer procesos en espera de este recurso
            self.satisfy_waiting_processes(resource_name)
            
            self.update_visualization()
            self.check_deadlock()
        else:
            self.log_event("LIBERAR", process_name, resource_name, "FALLO", f"Solo {current_assigned} asignados")
    
    def satisfy_waiting_processes(self, resource_name: str):
        """Intenta satisfacer las solicitudes pendientes de procesos en espera"""
        resource = self.resource_config.resources[resource_name]
        
        # Buscar procesos que están esperando este recurso
        for process_name, process in self.process_config.processes.items():
            if resource_name in process.waiting_for:
                waiting_qty = process.waiting_for[resource_name]
                
                # Si hay suficientes recursos disponibles, asignarlos
                if resource.available_instances >= waiting_qty:
                    resource.available_instances -= waiting_qty
                    resource.assigned_to[process_name] = resource.assigned_to.get(process_name, 0) + waiting_qty
                    process.assigned_resources[resource_name] = process.assigned_resources.get(resource_name, 0) + waiting_qty
                    
                    # Actualizar necesidad
                    process.needed_resources[resource_name] = max(0, process.needed_resources.get(resource_name, 0) - waiting_qty)
                    
                    # Limpiar espera
                    del process.waiting_for[resource_name]
                    
                    # Cambiar estado si no está esperando nada más
                    if not process.waiting_for:
                        process.state = ProcessState.READY
                    
                    self.log_event("ASIGNAR", process_name, resource_name, "ÉXITO", 
                                 f"Recurso liberado - Cantidad: {waiting_qty}")

    def update_visualization(self):
        self.graph_visualization.update_graph(
            self.process_config.processes,
            self.resource_config.resources
        )
        
        # Actualizar listas de selección
        self.assignment_panel.update_processes(self.process_config.processes)
        self.assignment_panel.update_resources(self.resource_config.resources)

    def check_deadlock(self):
        """Detecta deadlock usando algoritmo mejorado de detección de ciclos"""
        # Construir grafo de espera: proceso -> lista de procesos de los que depende
        wait_graph = {}
        
        for process_name, process in self.process_config.processes.items():
            waiting_for = set()
            
            # Si el proceso está bloqueado esperando recursos
            if process.waiting_for:
                for resource_name, waiting_qty in process.waiting_for.items():
                    if resource_name in self.resource_config.resources:
                        resource = self.resource_config.resources[resource_name]
                        # Buscar qué procesos tienen este recurso asignado
                        for other_process_name, assigned_qty in resource.assigned_to.items():
                            if assigned_qty > 0 and other_process_name != process_name:
                                waiting_for.add(other_process_name)
            
            # También verificar recursos necesarios pero no asignados
            for resource_name, needed in process.needed_resources.items():
                assigned = process.assigned_resources.get(resource_name, 0)
                if needed > assigned and resource_name in self.resource_config.resources:
                    resource = self.resource_config.resources[resource_name]
                    # Si no hay suficientes instancias disponibles, depende de otros procesos
                    if resource.available_instances < (needed - assigned):
                        for other_process_name, assigned_qty in resource.assigned_to.items():
                            if assigned_qty > 0 and other_process_name != process_name:
                                waiting_for.add(other_process_name)
            
            wait_graph[process_name] = list(waiting_for)
        
        # Detectar ciclo usando DFS (algoritmo de colores)
        visited = {p: 0 for p in wait_graph}  # 0=blanco (no visitado), 1=gris (en proceso), 2=negro (completado)
        cycle_path = []
        
        def dfs(node, path):
            visited[node] = 1  # Marcar como gris (en proceso)
            path.append(node)
            
            for neighbor in wait_graph.get(node, []):
                if neighbor not in wait_graph:
                    continue
                    
                if visited[neighbor] == 0:  # No visitado
                    if dfs(neighbor, path):
                        return True
                elif visited[neighbor] == 1:  # Ciclo detectado (back edge)
                    # Encontrar el ciclo completo
                    cycle_start = path.index(neighbor)
                    cycle_path.extend(path[cycle_start:] + [neighbor])
                    return True
            
            visited[node] = 2  # Marcar como negro (completado)
            path.pop()
            return False
        
        # Verificar si hay ciclo en el grafo
        has_cycle = False
        for process in wait_graph:
            if visited[process] == 0:
                if dfs(process, []):
                    has_cycle = True
                    break
        
        # Si se detecta deadlock y no estaba detectado antes
        if has_cycle and not self.deadlock_detected:
            self.deadlock_detected = True
            cycle_str = " → ".join(cycle_path) if cycle_path else "ciclo detectado"
            self.log_event("SISTEMA", "DEADLOCK", "DETECTADO", "ALERTA", 
                         f"Ciclo de espera circular: {cycle_str}")
            
            # Solo mostrar alerta y animación si no se ha mostrado recientemente
            if not self.deadlock_alert_shown:
                self.deadlock_alert_shown = True
                self.show_deadlock_alert(cycle_path, wait_graph)
                # Mostrar animación
                self.deadlock_animation.show_animation()
                # Resetear el flag después de 5 segundos para permitir mostrar de nuevo si persiste
                self.deadlock_alert_timer.start(5000)
        elif not has_cycle:
            # Si no hay deadlock, resetear los flags
            self.deadlock_detected = False
            self.deadlock_alert_shown = False
            self.deadlock_alert_timer.stop()

    def show_deadlock_alert(self, cycle_path: List[str], wait_graph: Dict[str, List[str]]):
        """Muestra un mensaje de alerta cuando se detecta deadlock con explicación detallada"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Deadlock Detectado")
        msg.setText("¡Se ha detectado un interbloqueo en el sistema!")
        msg.setInformativeText("Los procesos están esperando recursos mutuamente, creando un ciclo de espera circular.")
        
        # Construir explicación detallada del deadlock
        detailed_text = self.generate_deadlock_explanation(cycle_path, wait_graph)
        msg.setDetailedText(detailed_text)
        
        # Agregar botón personalizado para detener ejecución
        stop_button = msg.addButton("Detener Ejecución", QMessageBox.ActionRole)
        ok_button = msg.addButton(QMessageBox.Ok)
        
        # Establecer el botón OK como predeterminado
        msg.setDefaultButton(ok_button)
        
        # Mostrar el mensaje
        result = msg.exec()
        clicked_button = msg.clickedButton()
        
        # Si se presiona "Detener Ejecución" o "OK", detener la asignación automática
        if clicked_button == stop_button or result == QMessageBox.Ok:
            if self.is_auto_running:
                self.toggle_auto_assignment(False)
                self.log_event("SISTEMA", "EJECUCIÓN", "DETENIDA", "ALERTA", 
                             "Ejecución detenida por detección de deadlock")
    
    def generate_deadlock_explanation(self, cycle_path: List[str], wait_graph: Dict[str, List[str]]) -> str:
        """Genera una explicación detallada de por qué se generó el deadlock"""
        explanation = "═══════════════════════════════════════════════════════\n"
        explanation += "    EXPLICACIÓN DEL DEADLOCK DETECTADO EN ESTE ESCENARIO\n"
        explanation += "═══════════════════════════════════════════════════════\n\n"
        
        if not cycle_path:
            explanation += "Se detectó un ciclo en el grafo de espera, pero no se pudo identificar el camino exacto.\n"
            return explanation
        
        # Mostrar el ciclo detectado
        cycle_str = " → ".join(cycle_path)
        explanation += f"🔴 CICLO DE ESPERA CIRCULAR DETECTADO:\n"
        explanation += f"   {cycle_str}\n\n"
        explanation += "Este ciclo significa que cada proceso está esperando un recurso\n"
        explanation += "que está siendo retenido por otro proceso en el ciclo.\n\n"
        
        # Explicar cada paso del ciclo
        explanation += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        explanation += "ANÁLISIS DETALLADO DEL CICLO:\n"
        explanation += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        for i, process_name in enumerate(cycle_path):
            if i < len(cycle_path) - 1:
                next_process = cycle_path[i + 1]
            else:
                next_process = cycle_path[0]  # El último apunta al primero
            
            process = self.process_config.processes.get(process_name)
            if not process:
                continue
            
            # Obtener recursos asignados y recursos necesarios
            assigned_resources = [r for r, q in process.assigned_resources.items() if q > 0]
            needed_resources = [r for r, q in process.needed_resources.items() if q > 0]
            
            # Buscar qué recurso está esperando que libere el siguiente proceso
            waiting_for_resource = None
            waiting_for_process = None
            
            # Primero verificar si el siguiente proceso tiene algún recurso que este proceso necesita
            next_process_obj = self.process_config.processes.get(next_process)
            if next_process_obj:
                # Buscar recursos que el siguiente proceso tiene asignados
                for res_name, res_qty in next_process_obj.assigned_resources.items():
                    if res_qty > 0 and res_name in needed_resources:
                        waiting_for_resource = res_name
                        waiting_for_process = next_process
                        break
            
            # Si no se encontró, buscar en los recursos directamente
            if not waiting_for_resource:
                for resource_name in needed_resources:
                    if resource_name in self.resource_config.resources:
                        resource = self.resource_config.resources[resource_name]
                        # Verificar si el siguiente proceso tiene este recurso asignado
                        if resource.assigned_to and next_process in resource.assigned_to:
                            if resource.assigned_to[next_process] > 0:
                                waiting_for_resource = resource_name
                                waiting_for_process = next_process
                                break
                        # También verificar si el recurso está asignado al siguiente proceso
                        elif next_process_obj and resource_name in next_process_obj.assigned_resources:
                            if next_process_obj.assigned_resources[resource_name] > 0:
                                waiting_for_resource = resource_name
                                waiting_for_process = next_process
                                break
            
            explanation += f"\n{process_name}:\n"
            if assigned_resources:
                assigned_str = ', '.join([f'{r}({process.assigned_resources[r]})' for r in assigned_resources])
                explanation += f"  • Posee: {assigned_str}\n"
            else:
                explanation += f"  • Posee: Ninguno\n"
            
            if waiting_for_resource and waiting_for_process:
                explanation += f"  • Espera: {waiting_for_resource} (retenido por {waiting_for_process})\n"
            elif needed_resources:
                needed_str = ', '.join(needed_resources)
                # Intentar identificar quién tiene estos recursos
                holders = []
                for res_name in needed_resources:
                    if res_name in self.resource_config.resources:
                        resource = self.resource_config.resources[res_name]
                        if resource.assigned_to:
                            for holder, qty in resource.assigned_to.items():
                                if qty > 0 and holder != process_name:
                                    holders.append(f"{res_name}→{holder}")
                if holders:
                    explanation += f"  • Necesita: {needed_str} (retenidos por: {', '.join(set(holders))})\n"
                else:
                    explanation += f"  • Necesita: {needed_str}\n"
            else:
                explanation += f"  • Necesita: Ninguno\n"
            
            explanation += f"  • Estado: {process.state.value}\n"
        
        explanation += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        explanation += "POR QUÉ SE GENERÓ EL DEADLOCK EN ESTE ESCENARIO:\n"
        explanation += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        explanation += "El deadlock se generó en este escenario específico porque se cumplen\n"
        explanation += "simultáneamente las 4 condiciones necesarias para un deadlock:\n\n"
        
        # Verificar condiciones
        has_exclusive = any(r.total_instances == 1 for r in self.resource_config.resources.values())
        has_hold_wait = any(
            any(q > 0 for q in p.assigned_resources.values()) and 
            any(q > 0 for q in p.needed_resources.values())
            for p in self.process_config.processes.values()
        )
        
        explanation += f"1. EXCLUSIÓN MUTUA: {'✅ Cumplida' if has_exclusive else '❌ No cumplida'}\n"
        explanation += "   Algunos recursos tienen capacidad 1, por lo que solo un proceso puede poseerlos.\n\n"
        
        explanation += f"2. RETENCIÓN Y ESPERA: {'✅ Cumplida' if has_hold_wait else '❌ No cumplida'}\n"
        explanation += "   Los procesos poseen recursos mientras solicitan otros recursos adicionales.\n\n"
        
        explanation += "3. NO EXPROPIACIÓN: ✅ Cumplida\n"
        explanation += "   Los recursos no pueden ser arrebatados; solo se liberan cuando el proceso termina.\n\n"
        
        explanation += "4. ESPERA CIRCULAR: ✅ Cumplida\n"
        explanation += f"   Existe un ciclo donde cada proceso espera un recurso retenido por otro:\n"
        explanation += f"   {cycle_str}\n\n"
        
        explanation += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        explanation += "SOLUCIÓN SUGERIDA PARA ESTE ESCENARIO:\n"
        explanation += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        explanation += "Para resolver el deadlock en este escenario específico, puedes:\n\n"
        explanation += "1. Liberar recursos manualmente:\n"
        first_process = cycle_path[0] if cycle_path else "un proceso"
        explanation += f"   • Selecciona uno de los procesos del ciclo ({first_process})\n"
        explanation += "   • Libera los recursos que tiene asignados\n"
        explanation += "   • Esto romperá el ciclo de espera\n\n"
        explanation += "2. Agregar más instancias:\n"
        explanation += "   • Aumenta la cantidad de instancias de los recursos en conflicto\n"
        explanation += "   • Esto permitirá que más procesos accedan simultáneamente\n\n"
        explanation += "3. Reordenar solicitudes:\n"
        explanation += "   • Cambia el orden en que los procesos solicitan recursos\n"
        explanation += "   • Esto puede prevenir la formación del ciclo\n\n"
        explanation += "═══════════════════════════════════════════════════════\n"
        
        return explanation
    
    def reset_deadlock_alert_flag(self):
        """Resetea el flag de alerta mostrada para permitir mostrar de nuevo si persiste"""
        self.deadlock_alert_shown = False

    def log_event(self, action: str, process: str, resource: str, result: str, details: str = ""):
        event = EventLog(self.cpu_cycle, action, process, resource, result, details)
        self.event_log.add_event(event)

    def toggle_auto_assignment(self, checked):
        self.is_auto_running = checked
        if checked:
            self.cpu_cycle = 0
            self.auto_timer.start(1000)  # 1 segundo por ciclo
            self.log_event("SISTEMA", "AUTO", "MODO", "INICIADO", "Asignación automática activada")
        else:
            self.auto_timer.stop()
            self.log_event("SISTEMA", "AUTO", "MODO", "DETENIDO", "Asignación automática desactivada")

    def clear_system(self):
        """Limpia todo el sistema: procesos, recursos, asignaciones, registro de eventos y visualización"""
        # Detener asignación automática si está activa
        if self.is_auto_running:
            self.toggle_auto_assignment(False)
        
        # Limpiar procesos
        self.process_config.processes.clear()
        self.process_config.update_list()
        
        # Limpiar recursos
        self.resource_config.resources.clear()
        self.resource_config.update_list()
        
        # Limpiar registro de eventos
        self.event_log.clear_log()
        
        # Resetear ciclo CPU
        self.cpu_cycle = 0
        
        # Resetear estado de deadlock
        self.deadlock_detected = False
        self.deadlock_alert_shown = False
        self.deadlock_alert_timer.stop()
        
        # Limpiar visualización del grafo (dibujo)
        self.graph_visualization.scene.clear()
        self.graph_visualization.process_nodes.clear()
        self.graph_visualization.resource_nodes.clear()
        self.graph_visualization.arrows.clear()
        
        # Ocultar animación de deadlock si está visible
        if self.deadlock_animation.isVisible():
            self.deadlock_animation.hide_animation()
        
        # Actualizar visualización (esto limpiará el grafo visualmente)
        self.update_visualization()
        
        # Limpiar estado del panel de asignación
        self.assignment_panel.update_processes({})
        self.assignment_panel.update_resources({})
        self.assignment_panel.update_status("Sistema limpiado")
        
        QMessageBox.information(self, "Sistema Limpiado", "Todo el sistema ha sido limpiado correctamente, incluyendo la visualización del grafo.")
    
    def auto_assignment_step(self):
        if not self.is_auto_running:
            return
        
        self.cpu_cycle += 1
        
        # Lógica de asignación automática simple
        import random
        
        # Intentar asignar recursos aleatoriamente
        processes = list(self.process_config.processes.keys())
        resources = list(self.resource_config.resources.keys())
        
        if processes and resources:
            # Seleccionar proceso y recurso aleatorios
            process_name = random.choice(processes)
            resource_name = random.choice(resources)
            quantity = random.randint(1, 3)
            
            # Intentar asignación
            if resource_name in self.resource_config.resources:
                resource = self.resource_config.resources[resource_name]
                if resource.available_instances >= quantity:
                    self.assign_resource(process_name, resource_name, quantity)
                else:
                    self.log_event("AUTO-ASIGNAR", process_name, resource_name, "BLOQUEADO", f"Solo {resource.available_instances} disponibles")
            
            # Ocasionalmente liberar recursos
            if random.random() < 0.3:  # 30% de probabilidad
                process_name = random.choice(processes)
                if process_name in self.process_config.processes:
                    process = self.process_config.processes[process_name]
                    assigned_resources = [r for r, q in process.assigned_resources.items() if q > 0]
                    if assigned_resources:
                        resource_name = random.choice(assigned_resources)
                        quantity = random.randint(1, min(2, process.assigned_resources[resource_name]))
                        self.release_resource(process_name, resource_name, quantity)


def main():
    app = QApplication(sys.argv)
    
    # Cargar estilos
    try:
        with open("styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass
    
    window = CustomDeadlockWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
