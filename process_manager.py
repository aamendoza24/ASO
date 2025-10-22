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
    QProgressBar, QTextEdit, QFrame, QScrollArea
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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Proceso", "Prioridad", "Estado", "Procesador"
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
                    self.process_manager.update_process_state(process_name, ProcessState.EXECUTING)
        
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
        """Detecta deadlock en el sistema de procesos y recursos"""
        # Construir grafo de espera: proceso -> recursos que espera
        wait_graph = {}
        for process_name, process in self.process_manager.processes.items():
            if process.state in [ProcessState.BLOCKED, ProcessState.READY]:
                # Buscar recursos que el proceso necesita pero no tiene
                needed_resources = []
                for resource_name, resource in self.resource_manager.resources.items():
                    if resource.assigned_to != process_name and resource.state == ResourceState.IN_USE:
                        needed_resources.append(resource.assigned_to)
                wait_graph[process_name] = needed_resources
        
        # Detectar ciclo con DFS
        visited = {p: 0 for p in wait_graph}  # 0=blanco, 1=gris, 2=negro
        
        def dfs(node):
            visited[node] = 1  # Gris
            for neighbor in wait_graph.get(node, []):
                if neighbor in wait_graph:  # Solo si el vecino es un proceso
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
            self.show_deadlock_alert()

    def show_deadlock_alert(self):
        """Muestra alerta de deadlock detectado"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Deadlock Detectado")
        msg.setText("¡Se ha detectado un interbloqueo en el sistema!")
        msg.setInformativeText("Los procesos están esperando recursos mutuamente, creando un ciclo de espera circular.")
        msg.setDetailedText("Esto ocurre cuando:\n• P1 tiene R1 y necesita R2\n• P2 tiene R2 y necesita R1\n• Ningún proceso puede avanzar")
        msg.exec()

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
