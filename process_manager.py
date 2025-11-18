import math
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

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
class Resource:
    name: str
    state: ResourceState = ResourceState.AVAILABLE
    assigned_to: Optional[str] = None  # proceso que lo tiene
    size: int = 1

@dataclass
class Process:
    name: str
    state: ProcessState = ProcessState.NEW
    priority: Priority = Priority.MEDIUM
    resources: Dict[str, int] = field(default_factory=dict)  # recurso -> cantidad
    needed_resources: Dict[str, int] = field(default_factory=dict)  # recurso -> cantidad necesaria
    assigned_resources: Dict[str, int] = field(default_factory=dict)  # recurso -> cantidad asignada
    processor: Optional[str] = None
    execution_time: int = 0
    total_time: int = 10

@dataclass
class Processor:
    name: str
    threads: int = 1
    current_processes: List[str] = field(default_factory=list)  # procesos ejecutándose

@dataclass
class SimulationStep:
    cycle: int
    process: str
    action: str  # "start", "assign_resource", "release_resource", "finish"
    resource: Optional[str] = None
    processor: Optional[str] = None


# -----------------------------
# Widgets de gestión
# -----------------------------

class ResourceManager(QWidget):
    def __init__(self, on_resource_changed=None):
        super().__init__()
        self.on_resource_changed = on_resource_changed
        self.resources: Dict[str, Resource] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("GESTIÓN DE RECURSOS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Formulario para agregar recursos
        form_group = QGroupBox("Agregar Recurso")
        form_layout = QFormLayout(form_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: R1, R2, R3...")
        form_layout.addRow("Nombre:", self.name_input)
        
        self.size_input = QSpinBox()
        self.size_input.setRange(1, 100)
        self.size_input.setValue(1)
        form_layout.addRow("Tamaño:", self.size_input)
        
        self.add_btn = QPushButton("Agregar")
        self.add_btn.clicked.connect(self.add_resource)
        form_layout.addRow(self.add_btn)
        
        layout.addWidget(form_group)
        
        # Lista de recursos disponibles
        available_group = QGroupBox("DISPONIBLE")
        available_layout = QVBoxLayout(available_group)
        
        self.available_list = QListWidget()
        self.available_list.setMaximumHeight(150)
        available_layout.addWidget(QLabel("Nombre"))
        available_layout.addWidget(self.available_list)
        
        layout.addWidget(available_group)
        
        # Lista de recursos en uso
        in_use_group = QGroupBox("REC EN USO")
        in_use_layout = QVBoxLayout(in_use_group)
        
        self.in_use_list = QListWidget()
        self.in_use_list.setMaximumHeight(150)
        in_use_layout.addWidget(QLabel("Nombre"))
        in_use_layout.addWidget(self.in_use_list)
        
        layout.addWidget(in_use_group)

    def add_resource(self):
        name = self.name_input.text().strip()
        if not name:
            return
        
        if name in self.resources:
            QMessageBox.warning(self, "Error", f"El recurso {name} ya existe")
            return
        
        resource = Resource(name=name, size=self.size_input.value())
        self.resources[name] = resource
        self.update_lists()
        
        self.name_input.clear()
        self.size_input.setValue(1)
        
        if self.on_resource_changed:
            self.on_resource_changed()

    def update_lists(self):
        self.available_list.clear()
        self.in_use_list.clear()
        
        for name, resource in self.resources.items():
            item = QListWidgetItem(f"{name} (Tamaño: {resource.size})")
            if resource.state == ResourceState.AVAILABLE:
                self.available_list.addItem(item)
            else:
                self.in_use_list.addItem(item)

    def get_available_resources(self) -> List[str]:
        return [name for name, res in self.resources.items() if res.state == ResourceState.AVAILABLE]

    def assign_resource(self, resource_name: str, process_name: str) -> bool:
        if resource_name in self.resources and self.resources[resource_name].state == ResourceState.AVAILABLE:
            self.resources[resource_name].state = ResourceState.IN_USE
            self.resources[resource_name].assigned_to = process_name
            self.update_lists()
            return True
        return False

    def release_resource(self, resource_name: str):
        if resource_name in self.resources:
            self.resources[resource_name].state = ResourceState.AVAILABLE
            self.resources[resource_name].assigned_to = None
            self.update_lists()


class ProcessManager(QWidget):
    def __init__(self, on_process_changed=None):
        super().__init__()
        self.on_process_changed = on_process_changed
        self.processes: Dict[str, Process] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("GESTIÓN DE PROCESOS")
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
        
        self.execution_time_input = QSpinBox()
        self.execution_time_input.setRange(1, 100)
        self.execution_time_input.setValue(10)
        form_layout.addRow("Tiempo ejecución:", self.execution_time_input)
        
        self.add_btn = QPushButton("Agregar")
        self.add_btn.clicked.connect(self.add_process)
        form_layout.addRow(self.add_btn)
        
        layout.addWidget(form_group)
        
        # Lista de procesos
        processes_group = QGroupBox("PROCESOS")
        processes_layout = QVBoxLayout(processes_group)
        
        self.processes_list = QListWidget()
        self.processes_list.setMaximumHeight(200)
        processes_layout.addWidget(self.processes_list)
        
        layout.addWidget(processes_group)

    def add_process(self):
        name = self.name_input.text().strip()
        if not name:
            return
        
        if name in self.processes:
            QMessageBox.warning(self, "Error", f"El proceso {name} ya existe")
            return
        
        priority = Priority(self.priority_combo.currentText())
        execution_time = self.execution_time_input.value()
        
        process = Process(
            name=name,
            priority=priority,
            total_time=execution_time
        )
        self.processes[name] = process
        self.update_list()
        
        self.name_input.clear()
        self.execution_time_input.setValue(10)
        
        if self.on_process_changed:
            self.on_process_changed()

    def update_list(self):
        self.processes_list.clear()
        
        for name, process in self.processes.items():
            state_color = {
                ProcessState.NEW: "gray",
                ProcessState.READY: "blue", 
                ProcessState.EXECUTING: "green",
                ProcessState.BLOCKED: "orange",
                ProcessState.FINISHED: "red"
            }.get(process.state, "gray")
            
            item_text = f"{name} - {process.priority.value} - {process.state.value}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.processes_list.addItem(item)

    def get_processes_by_state(self, state: ProcessState) -> List[str]:
        return [name for name, proc in self.processes.items() if proc.state == state]

    def update_process_state(self, process_name: str, new_state: ProcessState):
        if process_name in self.processes:
            self.processes[process_name].state = new_state
            self.update_list()


class ProcessorManager(QWidget):
    def __init__(self, on_processor_changed=None):
        super().__init__()
        self.on_processor_changed = on_processor_changed
        self.processors: Dict[str, Processor] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("GESTIÓN DE PROCESADORES")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Formulario para agregar procesadores
        form_group = QGroupBox("Agregar Procesador")
        form_layout = QFormLayout(form_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: CPU1, CPU2...")
        form_layout.addRow("Nombre:", self.name_input)
        
        self.threads_input = QSpinBox()
        self.threads_input.setRange(1, 16)
        self.threads_input.setValue(1)
        form_layout.addRow("Hilos:", self.threads_input)
        
        self.add_btn = QPushButton("Agregar")
        self.add_btn.clicked.connect(self.add_processor)
        form_layout.addRow(self.add_btn)
        
        layout.addWidget(form_group)
        
        # Lista de procesadores
        processors_group = QGroupBox("PROCESADORES")
        processors_layout = QVBoxLayout(processors_group)
        
        self.processors_list = QListWidget()
        self.processors_list.setMaximumHeight(200)
        processors_layout.addWidget(self.processors_list)
        
        layout.addWidget(processors_group)

    def add_processor(self):
        name = self.name_input.text().strip()
        if not name:
            return
        
        if name in self.processors:
            QMessageBox.warning(self, "Error", f"El procesador {name} ya existe")
            return
        
        threads = self.threads_input.value()
        processor = Processor(name=name, threads=threads)
        self.processors[name] = processor
        self.update_list()
        
        self.name_input.clear()
        self.threads_input.setValue(1)
        
        if self.on_processor_changed:
            self.on_processor_changed()

    def update_list(self):
        self.processors_list.clear()
        
        for name, processor in self.processors.items():
            item_text = f"{name} - {processor.threads} hilos - {len(processor.current_processes)} procesos"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, name)
            self.processors_list.addItem(item)

    def get_available_processors(self) -> List[str]:
        return [name for name, proc in self.processors.items() 
                if len(proc.current_processes) < proc.threads]

    def assign_process(self, processor_name: str, process_name: str) -> bool:
        if (processor_name in self.processors and 
            len(self.processors[processor_name].current_processes) < self.processors[processor_name].threads):
            self.processors[processor_name].current_processes.append(process_name)
            self.update_list()
            return True
        return False

    def release_process(self, processor_name: str, process_name: str):
        if processor_name in self.processors:
            try:
                self.processors[processor_name].current_processes.remove(process_name)
                self.update_list()
            except ValueError:
                pass


class SimulationTable(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("CALENDARIZADOR")
        title.setObjectName("mainTitle")
        layout.addWidget(title)
        
        # Tabla principal
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Proceso", "Prioridad", "Estado", "Procesador", "Recurso"
        ])
        
        # Configurar tabla
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.table)

    def update_table(self, processes: Dict[str, Process], resources: Dict[str, Resource]):
        if not processes:
            self.table.setRowCount(0)
            return
            
        self.table.setRowCount(len(processes))
        
        # Definir colores para cada estado
        state_colors = {
            ProcessState.NEW: QColor(128, 128, 128),      # Gris
            ProcessState.READY: QColor(52, 152, 219),     # Azul
            ProcessState.EXECUTING: QColor(46, 204, 113), # Verde
            ProcessState.BLOCKED: QColor(255, 193, 7),    # Amarillo
            ProcessState.FINISHED: QColor(231, 76, 60)    # Rojo
        }
        
        for row, (proc_name, process) in enumerate(processes.items()):
            # Proceso
            process_item = QTableWidgetItem(str(proc_name))
            process_item.setForeground(state_colors.get(process.state, QColor(0, 0, 0)))
            self.table.setItem(row, 0, process_item)
            
            # Prioridad
            priority_item = QTableWidgetItem(str(process.priority.value))
            priority_item.setForeground(state_colors.get(process.state, QColor(0, 0, 0)))
            self.table.setItem(row, 1, priority_item)
            
            # Estado
            state_item = QTableWidgetItem(str(process.state.value))
            state_item.setForeground(state_colors.get(process.state, QColor(0, 0, 0)))
            # Hacer el estado más visible con fondo sutil
            state_bg = state_colors.get(process.state, QColor(255, 255, 255))
            state_item.setBackground(QColor(state_bg.red(), state_bg.green(), state_bg.blue(), 50))  # Fondo semi-transparente
            self.table.setItem(row, 2, state_item)
            
            # Procesador - mostrar CPU en ejecución
            processor_text = str(process.processor) if process.processor else "-"
            processor_item = QTableWidgetItem(processor_text)
            processor_item.setForeground(state_colors.get(process.state, QColor(0, 0, 0)))
            self.table.setItem(row, 3, processor_item)
            
            # Recurso utilizado
            assigned_resources = [name for name, res in resources.items() 
                                if res.assigned_to == proc_name]
            resource_text = assigned_resources[0] if assigned_resources else "-"
            resource_item = QTableWidgetItem(resource_text)
            resource_item.setForeground(state_colors.get(process.state, QColor(0, 0, 0)))
            self.table.setItem(row, 4, resource_item)
            


class SimulationControls(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Controles de velocidad
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidad:"))
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5X", "1X", "2X", "4X", "8X"])
        self.speed_combo.setCurrentText("1X")
        speed_layout.addWidget(self.speed_combo)
        
        self.time_label = QLabel("00 Segundos")
        speed_layout.addWidget(self.time_label)
        
        layout.addLayout(speed_layout)
        
        # Contador de ciclos
        self.cycles_label = QLabel("0 Ciclos")
        layout.addWidget(self.cycles_label)
        
        # Botones de control
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Iniciar")
        self.start_btn.setObjectName("startButton")
        button_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("Pausar")
        self.pause_btn.setObjectName("pauseButton")
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)
        
        layout.addLayout(button_layout)
        
        # Botones adicionales
        additional_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Limpiar Sistema")
        self.clear_btn.setObjectName("clearButton")
        additional_layout.addWidget(self.clear_btn)
        
        self.random_btn = QPushButton("Escenario Aleatorio")
        self.random_btn.setObjectName("randomButton")
        additional_layout.addWidget(self.random_btn)
        
        self.deadlock_btn = QPushButton("Escenario Deadlock")
        self.deadlock_btn.setObjectName("deadlockButton")
        additional_layout.addWidget(self.deadlock_btn)
        
        layout.addLayout(additional_layout)
        
        # Estadísticas finales
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("statsLabel")
        self.stats_label.setVisible(False)
        layout.addWidget(self.stats_label)


class MemoryNomenclature(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("Nomenclatura de Memoria Virtual")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Indicadores de estado
        states_layout = QVBoxLayout()
        
        # Ejecutando
        exec_layout = QHBoxLayout()
        exec_square = QLabel("■")
        exec_square.setStyleSheet("color: #2ECC71; font-size: 16px;")
        exec_layout.addWidget(exec_square)
        exec_layout.addWidget(QLabel("Ejecutando"))
        exec_layout.addStretch()
        states_layout.addLayout(exec_layout)
        
        # Terminado
        fin_layout = QHBoxLayout()
        fin_square = QLabel("■")
        fin_square.setStyleSheet("color: #E74C3C; font-size: 16px;")
        fin_layout.addWidget(fin_square)
        fin_layout.addWidget(QLabel("Terminado"))
        fin_layout.addStretch()
        states_layout.addLayout(fin_layout)
        
        # Nuevo
        new_layout = QHBoxLayout()
        new_square = QLabel("■")
        new_square.setStyleSheet("color: #95A5A6; font-size: 16px;")
        new_layout.addWidget(new_square)
        new_layout.addWidget(QLabel("Nuevo"))
        new_layout.addStretch()
        states_layout.addLayout(new_layout)
        
        layout.addLayout(states_layout)


class ProcessCollector(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("COLECTOR DE PROCESOS")
        title.setObjectName("collectorTitle")
        layout.addWidget(title)
        
        # Lista de procesos terminados
        self.finished_list = QListWidget()
        self.finished_list.setMaximumHeight(150)
        layout.addWidget(self.finished_list)

    def add_finished_process(self, process_name: str):
        item = QListWidgetItem(f"✓ {process_name}")
        item.setBackground(QColor(231, 76, 60, 50))
        self.finished_list.addItem(item)


class DeadlockAnalysisWidget(QWidget):
    """Widget que muestra el análisis completo de deadlock"""
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título
        title = QLabel("ANÁLISIS DE DEADLOCK")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Área de texto con scroll para el análisis
        self.analysis_text = QTextBrowser()
        self.analysis_text.setMaximumHeight(400)
        self.analysis_text.setStyleSheet("""
            QTextBrowser {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.analysis_text)
        
        # Botón para cerrar
        self.close_btn = QPushButton("Cerrar Análisis")
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)
    
    def show_analysis(self, analysis_text: str):
        """Muestra el análisis formateado"""
        self.analysis_text.setHtml(analysis_text)
        self.show()


class StatusBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.current_size_label = QLabel("Tamaño de Proceso Actual: -")
        layout.addWidget(self.current_size_label)
        
        layout.addWidget(QLabel("→"))
        
        self.processor_label = QLabel("Procesador en Uso: -")
        layout.addWidget(self.processor_label)
        
        layout.addWidget(QLabel("→"))
        
        self.speed_label = QLabel("Velocidad 1X")
        self.speed_label.setObjectName("speedLabel")
        layout.addWidget(self.speed_label)
        
        layout.addWidget(QLabel("→"))
        
        self.time_label = QLabel("Tiempo Estimado: -")
        self.time_label.setObjectName("timeLabel")
        layout.addWidget(self.time_label)
        
        layout.addStretch()


class ProcessSimulationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador de Gestión de Procesos - Sistemas Operativos")
        self.resize(1400, 900)
        
        # Inicializar componentes
        self.resource_manager = ResourceManager(self.on_data_changed)
        self.process_manager = ProcessManager(self.on_data_changed)
        self.processor_manager = ProcessorManager(self.on_data_changed)
        self.simulation_table = SimulationTable()
        self.simulation_controls = SimulationControls()
        self.memory_nomenclature = MemoryNomenclature()
        self.process_collector = ProcessCollector()
        self.status_bar = StatusBar()
        self.deadlock_analysis = DeadlockAnalysisWidget()
        
        # Timer de simulación
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.simulation_step)
        self.current_cycle = 0
        self.is_running = False
        self.start_time = None
        self.finished_processes_count = 0
        
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Layout principal con splitter horizontal
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo - Gestión
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Pestañas para gestión
        management_tabs = QTabWidget()
        management_tabs.addTab(self.resource_manager, "Recursos")
        management_tabs.addTab(self.process_manager, "Procesos")
        management_tabs.addTab(self.processor_manager, "Procesadores")
        
        left_layout.addWidget(management_tabs)
        
        # Panel central - Simulación
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabla de simulación
        center_layout.addWidget(self.simulation_table)
        
        # Controles de simulación
        center_layout.addWidget(self.simulation_controls)
        
        # Panel derecho - Estado y colector
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(self.memory_nomenclature)
        right_layout.addWidget(self.process_collector)
        right_layout.addWidget(self.deadlock_analysis)
        self.deadlock_analysis.hide()
        
        # Agregar paneles al splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(center_panel)
        main_splitter.addWidget(right_panel)
        
        # Configurar proporciones
        main_splitter.setStretchFactor(0, 1)  # Panel izquierdo
        main_splitter.setStretchFactor(1, 2)  # Panel central
        main_splitter.setStretchFactor(2, 1)  # Panel derecho
        
        main_layout.addWidget(main_splitter)
        
        # Barra de estado
        main_layout.addWidget(self.status_bar)

    def setup_connections(self):
        self.simulation_controls.start_btn.clicked.connect(self.start_simulation)
        self.simulation_controls.pause_btn.clicked.connect(self.pause_simulation)
        self.simulation_controls.speed_combo.currentTextChanged.connect(self.update_speed)
        self.simulation_controls.clear_btn.clicked.connect(self.clear_system)
        self.simulation_controls.random_btn.clicked.connect(self.generate_random_scenario)
        self.simulation_controls.deadlock_btn.clicked.connect(self.generate_deadlock_scenario)

    def on_data_changed(self):
        self.update_simulation_table()

    def update_simulation_table(self):
        self.simulation_table.update_table(
            self.process_manager.processes,
            self.resource_manager.resources
        )

    def start_simulation(self):
        if not self.process_manager.processes:
            QMessageBox.warning(self, "Error", "No hay procesos configurados")
            return
        
        self.is_running = True
        self.current_cycle = 0
        self.start_time = QTimer()
        self.finished_processes_count = 0
        self.simulation_controls.start_btn.setEnabled(False)
        self.simulation_controls.pause_btn.setEnabled(True)
        self.simulation_controls.stats_label.setVisible(False)
        
        # Iniciar timer
        speed_text = self.simulation_controls.speed_combo.currentText()
        speed_multiplier = float(speed_text.replace('X', ''))
        interval = int(1000 / speed_multiplier)  # 1000ms base
        self.simulation_timer.start(interval)

    def pause_simulation(self):
        self.is_running = False
        self.simulation_timer.stop()
        self.simulation_controls.start_btn.setEnabled(True)
        self.simulation_controls.pause_btn.setEnabled(False)

    def update_speed(self, speed_text: str):
        if self.is_running:
            speed_multiplier = float(speed_text.replace('X', ''))
            interval = int(1000 / speed_multiplier)
            self.simulation_timer.start(interval)

    def simulation_step(self):
        if not self.is_running:
            return
        
        self.current_cycle += 1
        self.simulation_controls.cycles_label.setText(f"{self.current_cycle} Ciclos")
        
        # Lógica de simulación básica
        self.execute_processes()
        self.update_simulation_table()
        self.update_status_bar()

    def execute_processes(self):
        # Mover procesos nuevos a listos
        new_processes = self.process_manager.get_processes_by_state(ProcessState.NEW)
        for process_name in new_processes:
            self.process_manager.update_process_state(process_name, ProcessState.READY)
        
        # Asignar procesos listos a procesadores disponibles
        ready_processes = self.process_manager.get_processes_by_state(ProcessState.READY)
        available_processors = self.processor_manager.get_available_processors()
        
        # Asignar procesos a procesadores disponibles
        for i, process_name in enumerate(ready_processes):
            if i < len(available_processors):
                processor_name = available_processors[i]
                if self.processor_manager.assign_process(processor_name, process_name):
                    # Actualizar el proceso con el procesador asignado
                    process = self.process_manager.processes[process_name]
                    process.processor = processor_name
                    
                    # Asignar un recurso disponible automáticamente
                    available_resources = [name for name, res in self.resource_manager.resources.items() 
                                         if res.state == ResourceState.AVAILABLE]
                    if available_resources:
                        resource_name = available_resources[0]
                        if self.resource_manager.assign_resource(resource_name, process_name):
                            process.assigned_resources[resource_name] = 1
                            self.process_manager.update_process_state(process_name, ProcessState.EXECUTING)
                        else:
                            self.process_manager.update_process_state(process_name, ProcessState.BLOCKED)
                    else:
                        self.process_manager.update_process_state(process_name, ProcessState.BLOCKED)
        
        # Ejecutar procesos
        executing_processes = self.process_manager.get_processes_by_state(ProcessState.EXECUTING)
        for process_name in executing_processes:
            process = self.process_manager.processes[process_name]
            process.execution_time += 1
            
            if process.execution_time >= process.total_time:
                # Proceso terminado
                self.process_manager.update_process_state(process_name, ProcessState.FINISHED)
                self.process_collector.add_finished_process(process_name)
                self.finished_processes_count += 1
                
                # Liberar procesador
                if process.processor:
                    self.processor_manager.release_process(process.processor, process_name)
                    process.processor = None
        
        # Detectar deadlock
        self.check_deadlock()
        
        # Verificar si todos los procesos terminaron
        total_processes = len(self.process_manager.processes)
        if self.finished_processes_count >= total_processes and total_processes > 0:
            self.finish_simulation()

    def update_status_bar(self):
        executing_processes = self.process_manager.get_processes_by_state(ProcessState.EXECUTING)
        if executing_processes:
            process_name = executing_processes[0]
            process = self.process_manager.processes[process_name]
            self.status_bar.current_size_label.setText(f"Tamaño de Proceso Actual: {process_name}")
            self.status_bar.processor_label.setText(f"Procesador en Uso: {process.processor or '-'}")
        else:
            self.status_bar.current_size_label.setText("Tamaño de Proceso Actual: -")
            self.status_bar.processor_label.setText("Procesador en Uso: -")
        
        speed_text = self.simulation_controls.speed_combo.currentText()
        self.status_bar.speed_label.setText(f"Velocidad {speed_text}")
        self.status_bar.time_label.setText(f"Tiempo Estimado: {self.current_cycle}Seg")

    def check_deadlock(self):
        """Detecta deadlock en el sistema de procesos y recursos usando algoritmo de detección de ciclos"""
        # Construir grafo de espera
        wait_graph = {}
        for process_name, process in self.process_manager.processes.items():
            waiting_for = set()
            
            # Verificar recursos necesarios pero no asignados completamente
            for needed_resource, needed_qty in process.needed_resources.items():
                if needed_qty > 0 and needed_resource in self.resource_manager.resources:
                    resource = self.resource_manager.resources[needed_resource]
                    assigned = process.assigned_resources.get(needed_resource, 0)
                    
                    # Si el proceso necesita más de lo que tiene asignado
                    if needed_qty > assigned:
                        # Verificar si el recurso está asignado a otro proceso
                        if resource.assigned_to and resource.assigned_to != process_name:
                            waiting_for.add(resource.assigned_to)
                        # También verificar si el recurso está en uso
                        elif resource.state == ResourceState.IN_USE:
                            if resource.assigned_to and resource.assigned_to != process_name:
                                waiting_for.add(resource.assigned_to)
                        # Buscar en assigned_resources de otros procesos
                        else:
                            for other_process_name, other_process in self.process_manager.processes.items():
                                if other_process_name != process_name:
                                    if needed_resource in other_process.assigned_resources:
                                        if other_process.assigned_resources[needed_resource] > 0:
                                            waiting_for.add(other_process_name)
                                            break
            
            # Considerar procesos bloqueados
            if process.state == ProcessState.BLOCKED:
                for res_name, res in self.resource_manager.resources.items():
                    if res_name in process.needed_resources:
                        if res.state == ResourceState.IN_USE and res.assigned_to:
                            if res.assigned_to != process_name:
                                waiting_for.add(res.assigned_to)
            
            wait_graph[process_name] = list(waiting_for)
        
        # Detectar ciclo usando DFS
        visited = {p: 0 for p in wait_graph}
        cycle_path = []
        
        def dfs(node, path):
            visited[node] = 1
            path.append(node)
            
            for neighbor in wait_graph.get(node, []):
                if neighbor not in wait_graph:
                    continue
                if visited[neighbor] == 0:
                    if dfs(neighbor, path):
                        return True
                elif visited[neighbor] == 1:  # Ciclo detectado
                    cycle_start = path.index(neighbor)
                    cycle_path.extend(path[cycle_start:] + [neighbor])
                    return True
            
            visited[node] = 2
            path.pop()
            return False
        
        has_cycle = False
        for process in wait_graph:
            if visited[process] == 0:
                if dfs(process, []):
                    has_cycle = True
                    break
        
        if has_cycle:
            self.show_deadlock_alert(cycle_path, wait_graph)
            return True
        return False

    def show_deadlock_alert(self, cycle_path: List[str] = None, wait_graph: Dict[str, List[str]] = None):
        """Muestra alerta de deadlock detectado con explicación detallada"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Deadlock Detectado")
        msg.setText("¡Se ha detectado un interbloqueo en el sistema!")
        msg.setInformativeText("Los procesos están esperando recursos mutuamente, creando un ciclo de espera circular.")
        
        # Construir explicación detallada del deadlock
        if cycle_path:
            detailed_text = self.generate_deadlock_explanation(cycle_path, wait_graph)
        else:
            detailed_text = "Se detectó un deadlock, pero no se pudo identificar el ciclo exacto."
        
        msg.setDetailedText(detailed_text)
        
        # Agregar botón para detener ejecución
        stop_button = msg.addButton("Detener Ejecución", QMessageBox.ActionRole)
        ok_button = msg.addButton(QMessageBox.Ok)
        msg.setDefaultButton(ok_button)
        
        # Mostrar el mensaje
        result = msg.exec()
        clicked_button = msg.clickedButton()
        
        # Si se presiona "Detener Ejecución" o "OK", detener la simulación
        if clicked_button == stop_button or result == QMessageBox.Ok:
            if self.is_running:
                self.pause_simulation()
    
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
            
            process = self.process_manager.processes.get(process_name)
            if not process:
                continue
            
            # Obtener recursos asignados y recursos necesarios
            assigned_resources = [r for r, q in process.assigned_resources.items() if q > 0]
            needed_resources = [r for r, q in process.needed_resources.items() if q > 0]
            
            # Buscar qué recurso está esperando que libere el siguiente proceso
            waiting_for_resource = None
            next_process_obj = self.process_manager.processes.get(next_process)
            if next_process_obj:
                # Buscar recursos que el siguiente proceso tiene asignados
                for res_name, res_qty in next_process_obj.assigned_resources.items():
                    if res_qty > 0 and res_name in needed_resources:
                        waiting_for_resource = res_name
                        break
            
            # Si no se encontró, buscar en los recursos directamente
            if not waiting_for_resource:
                for resource_name in needed_resources:
                    if resource_name in self.resource_manager.resources:
                        resource = self.resource_manager.resources[resource_name]
                        if resource.assigned_to and resource.assigned_to == next_process:
                            waiting_for_resource = resource_name
                            break
                        elif next_process_obj and resource_name in next_process_obj.assigned_resources:
                            if next_process_obj.assigned_resources[resource_name] > 0:
                                waiting_for_resource = resource_name
                                break
            
            explanation += f"\n{process_name}:\n"
            if assigned_resources:
                assigned_str = ', '.join([f'{r}({process.assigned_resources[r]})' for r in assigned_resources])
                explanation += f"  • Posee: {assigned_str}\n"
            else:
                explanation += f"  • Posee: Ninguno\n"
            
            if waiting_for_resource:
                explanation += f"  • Espera: {waiting_for_resource} (retenido por {next_process})\n"
            elif needed_resources:
                needed_str = ', '.join(needed_resources)
                # Intentar identificar quién tiene estos recursos
                holders = []
                for res_name in needed_resources:
                    if res_name in self.resource_manager.resources:
                        resource = self.resource_manager.resources[res_name]
                        if resource.assigned_to and resource.assigned_to != process_name:
                            holders.append(f"{res_name}→{resource.assigned_to}")
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
        has_exclusive = any(r.size == 1 for r in self.resource_manager.resources.values())
        has_hold_wait = any(
            any(q > 0 for q in p.assigned_resources.values()) and 
            any(q > 0 for q in p.needed_resources.values())
            for p in self.process_manager.processes.values()
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
        first_process = cycle_path[0] if cycle_path else "un proceso"
        explanation += f"1. Liberar recursos manualmente:\n"
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

    def finish_simulation(self):
        """Finaliza la simulación y muestra estadísticas"""
        self.is_running = False
        self.simulation_timer.stop()
        self.simulation_controls.start_btn.setEnabled(True)
        self.simulation_controls.pause_btn.setEnabled(False)
        
        # Calcular tiempo transcurrido
        elapsed_seconds = self.current_cycle  # Aproximación basada en ciclos
        
        # Mostrar estadísticas
        stats_text = f"✅ Simulación completada!\nCiclos: {self.current_cycle} | Tiempo: {elapsed_seconds}s | Procesos: {self.finished_processes_count}"
        self.simulation_controls.stats_label.setText(stats_text)
        self.simulation_controls.stats_label.setVisible(True)
        
        # Mostrar mensaje de finalización
        QMessageBox.information(
            self, 
            "Simulación Finalizada", 
            f"Todos los procesos han terminado.\n\nCiclos ejecutados: {self.current_cycle}\nTiempo estimado: {elapsed_seconds} segundos\nProcesos completados: {self.finished_processes_count}"
        )

    def clear_system(self):
        """Limpia todo el sistema"""
        self.pause_simulation()
        
        # Limpiar datos
        self.process_manager.processes.clear()
        self.resource_manager.resources.clear()
        self.processor_manager.processors.clear()
        self.process_collector.finished_list.clear()
        
        # Resetear contadores
        self.current_cycle = 0
        self.finished_processes_count = 0
        
        # Actualizar UI
        self.process_manager.update_list()
        self.resource_manager.update_lists()
        self.processor_manager.update_list()
        self.update_simulation_table()
        self.simulation_controls.cycles_label.setText("0 Ciclos")
        self.simulation_controls.stats_label.setVisible(False)
        
        # Resetear barra de estado
        self.status_bar.current_size_label.setText("Tamaño de Proceso Actual: -")
        self.status_bar.processor_label.setText("Procesador en Uso: -")
        self.status_bar.time_label.setText("Tiempo Estimado: -")

    def generate_random_scenario(self):
        """Genera un escenario aleatorio para simulación"""
        import random
        
        self.clear_system()
        
        # Generar recursos aleatorios
        num_resources = random.randint(3, 6)
        for i in range(1, num_resources + 1):
            resource = Resource(
                name=f"R{i}",
                size=random.randint(1, 5)
            )
            self.resource_manager.resources[f"R{i}"] = resource
        
        # Generar procesos aleatorios
        num_processes = random.randint(4, 8)
        for i in range(1, num_processes + 1):
            priority = random.choice(list(Priority))
            execution_time = random.randint(5, 20)
            
            process = Process(
                name=f"P{i}",
                priority=priority,
                total_time=execution_time
            )
            self.process_manager.processes[f"P{i}"] = process
        
        # Generar procesadores aleatorios
        num_processors = random.randint(1, 3)
        for i in range(1, num_processors + 1):
            threads = random.randint(1, 4)
            processor = Processor(
                name=f"CPU{i}",
                threads=threads
            )
            self.processor_manager.processors[f"CPU{i}"] = processor
        
        # Actualizar UI
        self.process_manager.update_list()
        self.resource_manager.update_lists()
        self.processor_manager.update_list()
        self.update_simulation_table()
        
        QMessageBox.information(
            self, 
            "Escenario Aleatorio Generado", 
            f"Se generó un escenario con:\n• {num_resources} recursos\n• {num_processes} procesos\n• {num_processors} procesadores\n\n¡Listo para simular!"
        )

    def generate_deadlock_scenario(self):
        """Genera un escenario realista de deadlock con análisis completo"""
        import random
        
        self.clear_system()
        
        # Generar entre 4-8 procesos
        num_processes = random.randint(4, 8)
        process_names = [f"P{i}" for i in range(1, num_processes + 1)]
        
        # Generar entre 4-10 recursos, algunos con capacidad 1 (exclusión mutua)
        num_resources = random.randint(4, 10)
        resource_names = [f"R{i}" for i in range(1, num_resources + 1)]
        
        # Crear recursos: algunos con capacidad 1, otros con capacidad mayor
        for i, resource_name in enumerate(resource_names):
            # Al menos la mitad deben tener capacidad 1 para exclusión mutua
            if i < num_resources // 2:
                size = 1
            else:
                size = random.randint(1, 3)
            
            resource = Resource(name=resource_name, size=size)
            self.resource_manager.resources[resource_name] = resource
        
        # Crear procesos con diferentes estados iniciales
        states = [ProcessState.NEW, ProcessState.READY, ProcessState.EXECUTING, ProcessState.BLOCKED]
        for i, process_name in enumerate(process_names):
            priority = random.choice(list(Priority))
            execution_time = random.randint(5, 20)
            initial_state = random.choice(states) if i < len(process_names) - 2 else ProcessState.READY
            
            process = Process(
                name=process_name,
                priority=priority,
                total_time=execution_time,
                state=initial_state
            )
            self.process_manager.processes[process_name] = process
        
        # Asignar recursos aleatoriamente a algunos procesos (retención y espera)
        assigned_resources = {}
        for process_name in process_names[:num_processes - 1]:  # Todos menos uno
            if random.random() < 0.7:  # 70% de probabilidad de tener un recurso
                resource_name = random.choice(resource_names)
                resource = self.resource_manager.resources[resource_name]
                
                if resource.state == ResourceState.AVAILABLE:
                    if self.resource_manager.assign_resource(resource_name, process_name):
                        process = self.process_manager.processes[process_name]
                        process.assigned_resources[resource_name] = 1
                        assigned_resources[resource_name] = process_name
        
        # Generar solicitudes de recursos adicionales (intentar crear dependencias circulares)
        # Decidir si queremos crear un deadlock o no
        create_deadlock = random.random() < 0.6  # 60% de probabilidad de deadlock
        
        if create_deadlock:
            # Crear un ciclo de espera circular
            cycle_size = min(3, num_processes, num_resources)
            cycle_processes = process_names[:cycle_size]
            cycle_resources = resource_names[:cycle_size]
            
            # Crear ciclo: P1 tiene R1, necesita R2; P2 tiene R2, necesita R3; etc.
            for i in range(cycle_size):
                process_name = cycle_processes[i]
                current_resource = cycle_resources[i]
                next_resource = cycle_resources[(i + 1) % cycle_size]
                
                process = self.process_manager.processes[process_name]
                
                # Si no tiene el recurso actual, asignárselo
                if current_resource not in process.assigned_resources:
                    if current_resource in self.resource_manager.resources:
                        resource = self.resource_manager.resources[current_resource]
                        if resource.state == ResourceState.AVAILABLE:
                            if self.resource_manager.assign_resource(current_resource, process_name):
                                process.assigned_resources[current_resource] = 1
                
                # Solicitar el siguiente recurso (que está en uso por otro proceso)
                # Asegurarse de que el proceso realmente necesita este recurso
                if next_resource not in process.assigned_resources:
                    process.needed_resources[next_resource] = 1
                else:
                    # Si ya lo tiene, necesita más
                    process.needed_resources[next_resource] = process.assigned_resources.get(next_resource, 0) + 1
                process.state = ProcessState.BLOCKED
        else:
            # Generar solicitudes aleatorias sin crear deadlock
            for process_name in process_names:
                process = self.process_manager.processes[process_name]
                if random.random() < 0.5:  # 50% de probabilidad de solicitar recurso
                    resource_name = random.choice(resource_names)
                    if resource_name not in process.assigned_resources:
                        process.needed_resources[resource_name] = 1
                        if resource_name in assigned_resources:
                            process.state = ProcessState.BLOCKED
        
        # Crear procesadores
        num_processors = random.randint(1, 3)
        for i in range(1, num_processors + 1):
            threads = random.randint(1, 4)
            processor = Processor(name=f"CPU{i}", threads=threads)
            self.processor_manager.processors[f"CPU{i}"] = processor
        
        # Actualizar UI
        self.process_manager.update_list()
        self.resource_manager.update_lists()
        self.processor_manager.update_list()
        self.update_simulation_table()
        
        # Realizar análisis completo
        analysis = self.analyze_deadlock_scenario()
        self.deadlock_analysis.show_analysis(analysis)
        
        QMessageBox.information(
            self,
            "Escenario Generado",
            f"Se generó un escenario con:\n"
            f"• {num_processes} procesos\n"
            f"• {num_resources} recursos\n"
            f"• {num_processors} procesadores\n\n"
            f"Ver el panel de análisis para detalles completos."
        )
    
    def analyze_deadlock_scenario(self) -> str:
        """Analiza el escenario actual y genera un reporte completo"""
        html = "<html><body style='font-family: Arial, sans-serif;'>"
        
        # 1. Tabla de Procesos
        html += "<h2 style='color: #2c3e50;'>1️⃣ TABLA DE PROCESOS</h2>"
        html += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
        html += "<tr style='background-color: #3498db; color: white;'>"
        html += "<th>Proceso</th><th>Estado</th><th>Recursos Asignados</th><th>Recurso Solicitado</th></tr>"
        
        for process_name, process in self.process_manager.processes.items():
            assigned = ", ".join([f"{r}({q})" for r, q in process.assigned_resources.items() if q > 0]) or "Ninguno"
            needed = ", ".join([f"{r}({q})" for r, q in process.needed_resources.items() if q > 0]) or "Ninguno"
            state_color = {
                ProcessState.NEW: "#95a5a6",
                ProcessState.READY: "#3498db",
                ProcessState.EXECUTING: "#2ecc71",
                ProcessState.BLOCKED: "#f39c12",
                ProcessState.FINISHED: "#e74c3c"
            }.get(process.state, "#000000")
            
            html += f"<tr>"
            html += f"<td><b>{process_name}</b></td>"
            html += f"<td style='color: {state_color};'><b>{process.state.value}</b></td>"
            html += f"<td>{assigned}</td>"
            html += f"<td>{needed}</td>"
            html += f"</tr>"
        html += "</table><br>"
        
        # 2. Tabla de Recursos
        html += "<h2 style='color: #2c3e50;'>2️⃣ TABLA DE RECURSOS</h2>"
        html += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>"
        html += "<tr style='background-color: #e67e22; color: white;'>"
        html += "<th>Recurso</th><th>Capacidad</th><th>Estado</th><th>Proceso que lo posee</th></tr>"
        
        for resource_name, resource in self.resource_manager.resources.items():
            owner = resource.assigned_to or "Disponible"
            state_text = "En uso" if resource.state == ResourceState.IN_USE else "Disponible"
            state_color = "#e74c3c" if resource.state == ResourceState.IN_USE else "#2ecc71"
            
            html += f"<tr>"
            html += f"<td><b>{resource_name}</b></td>"
            html += f"<td>{resource.size}</td>"
            html += f"<td style='color: {state_color};'><b>{state_text}</b></td>"
            html += f"<td>{owner}</td>"
            html += f"</tr>"
        html += "</table><br>"
        
        # 3. Lista de Dependencias
        html += "<h2 style='color: #2c3e50;'>3️⃣ LISTA DE DEPENDENCIAS</h2>"
        html += "<ul style='line-height: 1.8;'>"
        dependencies = []
        for process_name, process in self.process_manager.processes.items():
            for assigned_resource, qty in process.assigned_resources.items():
                if qty > 0:
                    for needed_resource, needed_qty in process.needed_resources.items():
                        if needed_qty > 0:
                            dependencies.append(f"<li><b>{process_name}</b> posee <b>{assigned_resource}</b> → necesita <b>{needed_resource}</b></li>")
        
        if dependencies:
            html += "".join(dependencies)
        else:
            html += "<li>No hay dependencias de recursos configuradas</li>"
        html += "</ul><br>"
        
        # 4. Análisis Estructural
        html += "<h2 style='color: #2c3e50;'>4️⃣ ANÁLISIS ESTRUCTURAL DEL SISTEMA</h2>"
        
        # Verificar las 4 condiciones
        condition1 = self.check_mutual_exclusion()
        condition2 = self.check_hold_and_wait()
        condition3 = self.check_no_preemption()
        condition4 = self.check_circular_wait()
        
        html += "<h3 style='color: #34495e;'>Verificación de las 4 Condiciones de Deadlock:</h3>"
        html += "<ul style='line-height: 2;'>"
        html += f"<li><b>1. Exclusión Mutua:</b> {'✅ Cumplida' if condition1 else '❌ No cumplida'}</li>"
        html += f"<li><b>2. Retención y Espera:</b> {'✅ Cumplida' if condition2 else '❌ No cumplida'}</li>"
        html += f"<li><b>3. No Expropiación:</b> {'✅ Cumplida' if condition3 else '❌ No cumplida'}</li>"
        html += f"<li><b>4. Espera Circular:</b> {'✅ Cumplida' if condition4[0] else '❌ No cumplida'}</li>"
        html += "</ul><br>"
        
        # Búsqueda de ciclos
        html += "<h3 style='color: #34495e;'>Búsqueda de Ciclos en el Grafo de Espera:</h3>"
        if condition4[0]:
            html += f"<p style='color: #e74c3c; font-weight: bold;'>Ciclo detectado: {' → '.join(condition4[1])}</p>"
        else:
            html += "<p style='color: #2ecc71;'>No se encontraron ciclos en el grafo de espera.</p>"
        html += "<br>"
        
        # 5. Resultado Final
        html += "<h2 style='color: #2c3e50;'>5️⃣ RESULTADO FINAL</h2>"
        if condition1 and condition2 and condition3 and condition4[0]:
            html += "<div style='background-color: #e74c3c; color: white; padding: 15px; border-radius: 5px; font-size: 18px; font-weight: bold; text-align: center;'>"
            html += "⚠️ DEADLOCK DETECTADO ⚠️<br><br>"
            html += f"Ciclo exacto: {' → '.join(condition4[1])}"
            html += "</div>"
        else:
            html += "<div style='background-color: #2ecc71; color: white; padding: 15px; border-radius: 5px; font-size: 18px; font-weight: bold; text-align: center;'>"
            html += "✅ NO EXISTE DEADLOCK EN EL SISTEMA<br><br>"
            reasons = []
            if not condition1:
                reasons.append("No hay exclusión mutua")
            if not condition2:
                reasons.append("No hay retención y espera")
            if not condition3:
                reasons.append("Los recursos pueden ser expropiados")
            if not condition4[0]:
                reasons.append("No hay espera circular")
            html += f"Justificación: {'; '.join(reasons) if reasons else 'Todas las condiciones no se cumplen simultáneamente'}"
            html += "</div>"
        
        html += "</body></html>"
        return html
    
    def check_mutual_exclusion(self) -> bool:
        """Verifica exclusión mutua: algunos recursos deben ser no compartibles (capacidad 1)"""
        return any(r.size == 1 for r in self.resource_manager.resources.values())
    
    def check_hold_and_wait(self) -> bool:
        """Verifica retención y espera: procesos poseen recursos mientras solicitan otros"""
        for process in self.process_manager.processes.values():
            has_assigned = any(q > 0 for q in process.assigned_resources.values())
            has_needed = any(q > 0 for q in process.needed_resources.values())
            if has_assigned and has_needed:
                return True
        return False
    
    def check_no_preemption(self) -> bool:
        """Verifica no expropiación: los recursos no pueden ser arrebatados"""
        # En nuestro sistema, los recursos solo se liberan cuando el proceso termina
        # Por lo tanto, siempre se cumple esta condición
        return True
    
    def check_circular_wait(self) -> Tuple[bool, List[str]]:
        """Verifica espera circular: detecta ciclos en el grafo de espera"""
        # Construir grafo de espera mejorado (similar a custom_deadlock.py)
        wait_graph = {}
        for process_name, process in self.process_manager.processes.items():
            waiting_for = set()
            
            # Verificar recursos necesarios pero no asignados completamente
            for needed_resource, needed_qty in process.needed_resources.items():
                if needed_qty > 0 and needed_resource in self.resource_manager.resources:
                    resource = self.resource_manager.resources[needed_resource]
                    assigned = process.assigned_resources.get(needed_resource, 0)
                    
                    # Si el proceso necesita más de lo que tiene asignado
                    if needed_qty > assigned:
                        # Primero verificar si resource.assigned_to apunta a otro proceso
                        if resource.assigned_to and resource.assigned_to != process_name:
                            # El recurso está en uso por otro proceso - este proceso espera a ese proceso
                            waiting_for.add(resource.assigned_to)
                        # Si resource.assigned_to no está configurado, buscar en assigned_resources de otros procesos
                        elif resource.state == ResourceState.IN_USE:
                            # Buscar qué proceso tiene este recurso en su assigned_resources
                            for other_process_name, other_process in self.process_manager.processes.items():
                                if other_process_name != process_name:
                                    if needed_resource in other_process.assigned_resources:
                                        if other_process.assigned_resources[needed_resource] > 0:
                                            waiting_for.add(other_process_name)
                                            break
            
            # También considerar procesos bloqueados que pueden estar esperando recursos
            if process.state == ProcessState.BLOCKED:
                # Buscar todos los recursos en uso por otros procesos que este proceso necesita
                for res_name, res in self.resource_manager.resources.items():
                    if res_name in process.needed_resources:
                        if res.state == ResourceState.IN_USE and res.assigned_to:
                            if res.assigned_to != process_name:
                                waiting_for.add(res.assigned_to)
            
            wait_graph[process_name] = list(waiting_for)
        
        # Detectar ciclo usando DFS
        visited = {p: 0 for p in wait_graph}
        cycle_path = []
        
        def dfs(node, path):
            visited[node] = 1
            path.append(node)
            
            for neighbor in wait_graph.get(node, []):
                if neighbor not in wait_graph:
                    continue
                if visited[neighbor] == 0:
                    if dfs(neighbor, path):
                        return True
                elif visited[neighbor] == 1:  # Ciclo detectado
                    cycle_start = path.index(neighbor)
                    cycle_path.extend(path[cycle_start:] + [neighbor])
                    return True
            
            visited[node] = 2
            path.pop()
            return False
        
        has_cycle = False
        for process in wait_graph:
            if visited[process] == 0:
                if dfs(process, []):
                    has_cycle = True
                    break
        
        return (has_cycle, cycle_path if cycle_path else [])



def main():
    app = QApplication(sys.argv)
    
    # Cargar estilos
    try:
        with open("styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass
    
    window = ProcessSimulationWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
