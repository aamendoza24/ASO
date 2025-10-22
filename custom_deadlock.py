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
    QMessageBox, QPushButton, QSlider, QSplitter, QVBoxLayout, QWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QLineEdit, QSpinBox,
    QListWidget, QListWidgetItem, QGroupBox, QFormLayout, QCheckBox,
    QProgressBar, QTextEdit, QFrame, QScrollArea, QTextBrowser
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
    state: ProcessState = ProcessState.NEW

    def __post_init__(self):
        if self.needed_resources is None:
            self.needed_resources = {}
        if self.assigned_resources is None:
            self.assigned_resources = {}

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
            node = self.create_process_node(name, i, len(processes))
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

    def create_process_node(self, name: str, index: int, total: int) -> QGraphicsRectItem:
        node = QGraphicsRectItem(-30, -15, 60, 30)
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
        
        # Estado con color
        state_item = QTableWidgetItem(event.result)
        state_colors = {
            "ÉXITO": QColor(46, 204, 113),      # Verde
            "BLOQUEADO": QColor(255, 193, 7),   # Amarillo
            "FALLO": QColor(231, 76, 60),       # Rojo
            "ALERTA": QColor(155, 89, 182),     # Púrpura
            "ERROR": QColor(231, 76, 60)        # Rojo
        }
        
        state_color = state_colors.get(event.result, QColor(200, 200, 200))
        state_item.setBackground(state_color)
        
        # Ajustar color del texto para mejor contraste
        if event.result in ["ÉXITO", "BLOQUEADO", "FALLO", "ALERTA", "ERROR"]:
            state_item.setForeground(QColor(255, 255, 255))
        
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
        
        # Variables para asignación automática
        self.cpu_cycle = 0
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.auto_assignment_step)
        self.is_auto_running = False
        
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
        
        # Visualización del grafo
        center_layout.addWidget(self.graph_visualization)
        
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
        
        if resource.available_instances >= quantity:
            # Asignar recurso
            resource.available_instances -= quantity
            resource.assigned_to[process_name] = resource.assigned_to.get(process_name, 0) + quantity
            process.assigned_resources[resource_name] = process.assigned_resources.get(resource_name, 0) + quantity
            
            self.log_event("ASIGNAR", process_name, resource_name, "ÉXITO", f"Cantidad: {quantity}")
            self.update_visualization()
            self.check_deadlock()
        else:
            self.log_event("ASIGNAR", process_name, resource_name, "BLOQUEADO", f"Solo {resource.available_instances} disponibles")

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
            self.update_visualization()
        else:
            self.log_event("LIBERAR", process_name, resource_name, "FALLO", f"Solo {current_assigned} asignados")

    def update_visualization(self):
        self.graph_visualization.update_graph(
            self.process_config.processes,
            self.resource_config.resources
        )
        
        # Actualizar listas de selección
        self.assignment_panel.update_processes(self.process_config.processes)
        self.assignment_panel.update_resources(self.resource_config.resources)

    def check_deadlock(self):
        """Detecta deadlock usando algoritmo de detección de ciclos"""
        # Construir grafo de espera
        wait_graph = {}
        
        for process_name, process in self.process_config.processes.items():
            waiting_for = []
            for resource_name, needed in process.needed_resources.items():
                assigned = process.assigned_resources.get(resource_name, 0)
                if needed > assigned:
                    # El proceso necesita más de este recurso
                    # Buscar qué proceso tiene este recurso
                    for other_process, assigned_qty in self.resource_config.resources[resource_name].assigned_to.items():
                        if assigned_qty > 0 and other_process != process_name:
                            waiting_for.append(other_process)
            wait_graph[process_name] = waiting_for
        
        # Detectar ciclo con DFS
        visited = {p: 0 for p in wait_graph}  # 0=blanco, 1=gris, 2=negro
        
        def dfs(node):
            visited[node] = 1  # Gris
            for neighbor in wait_graph.get(node, []):
                if neighbor in wait_graph:
                    if visited[neighbor] == 0:
                        if dfs(neighbor):
                            return True
                    elif visited[neighbor] == 1:  # Ciclo detectado
                        return True
            visited[node] = 2  # Negro
            return False
        
        # Verificar si hay ciclo
        has_cycle = False
        for process in wait_graph:
            if visited[process] == 0:
                if dfs(process):
                    has_cycle = True
                    break
        
        if has_cycle:
            self.log_event("SISTEMA", "DEADLOCK", "DETECTADO", "ALERTA", "Ciclo de espera circular detectado")
            self.show_deadlock_alert()

    def show_deadlock_alert(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Deadlock Detectado")
        msg.setText("¡Se ha detectado un interbloqueo en el sistema!")
        msg.setInformativeText("Los procesos están esperando recursos mutuamente, creando un ciclo de espera circular.")
        msg.setDetailedText("Esto ocurre cuando:\n• P1 tiene R1 y necesita R2\n• P2 tiene R2 y necesita R1\n• Ningún proceso puede avanzar")
        msg.exec()

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
