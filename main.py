import math
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (QEasingCurve, QObject, QPointF, Property, QSequentialAnimationGroup,
                            QParallelAnimationGroup, QPropertyAnimation, QTimer, Qt)
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsDropShadowEffect,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


# -----------------------------
# Datos de escenarios
# -----------------------------

@dataclass
class Step:
    kind: str  # "request" | "assign" | "wait"
    process: str
    resource: str
    explain: str


@dataclass
class Scenario:
    name: str
    processes: List[str]
    resources: List[str]
    steps: List[Step]


def build_scenarios() -> List[Scenario]:
    # Caso clásico 2 procesos 2 recursos que entra en interbloqueo
    s1 = Scenario(
        name="Caso clásico: 2 procesos, 2 recursos (deadlock)",
        processes=["P1", "P2"],
        resources=["R1", "R2"],
        steps=[
            Step("assign", "P1", "R1", "P1 toma R1 disponible (asignación)."),
            Step("assign", "P2", "R2", "P2 toma R2 disponible (asignación)."),
            Step("request", "P1", "R2", "P1 solicita R2, pero está ocupado por P2 (espera)."),
            Step("request", "P2", "R1", "P2 solicita R1, pero está ocupado por P1 (espera). Esto crea un ciclo: deadlock."),
        ],
    )

    # Caso 3 procesos 3 recursos, con deadlock al final
    s2 = Scenario(
        name="3 procesos, 3 recursos (deadlock)",
        processes=["P1", "P2", "P3"],
        resources=["R1", "R2", "R3"],
        steps=[
            Step("assign", "P1", "R1", "P1 toma R1."),
            Step("assign", "P2", "R2", "P2 toma R2."),
            Step("assign", "P3", "R3", "P3 toma R3."),
            Step("request", "P1", "R2", "P1 solicita R2 (ocupado por P2)."),
            Step("request", "P2", "R3", "P2 solicita R3 (ocupado por P3)."),
            Step("request", "P3", "R1", "P3 solicita R1 (ocupado por P1). Se forma un ciclo: deadlock."),
        ],
    )

    # Caso sin deadlock (liberación implícita simulada con asignaciones permitidas)
    s3 = Scenario(
        name="Sin deadlock: 2 procesos, 2 recursos", 
        processes=["P1", "P2"],
        resources=["R1", "R2"],
        steps=[
            Step("assign", "P1", "R1", "P1 toma R1."),
            Step("assign", "P1", "R2", "R2 estaba libre, P1 también lo toma (no realista, pero evita espera)."),
            Step("assign", "P2", "R1", "P2 ahora recibe R1 (simulamos que se liberó). No hay ciclo."),
        ],
    )

    return [s1, s2, s3]


# -----------------------------
# Items gráficos
# -----------------------------

class LabelItem(QGraphicsSimpleTextItem):
    def __init__(self, text: str, parent: Optional[QGraphicsItem] = None) -> None:
        super().__init__(text, parent)
        f = QFont("Segoe UI", 10)
        f.setWeight(QFont.Medium)
        self.setFont(f)
        self.setBrush(QColor(30, 30, 30))


class ProcessNode(QGraphicsRectItem):
    def __init__(self, label: str, size: float = 70.0) -> None:
        super().__init__(-size/2, -size/2, size, size)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setBrush(QColor(99, 179, 237))  # azul pastel
        self.setPen(QPen(QColor(35, 110, 170), 2))
        self.radius = 16
        self._label_item = LabelItem(label, self)
        self._label_item.setPos(-self._label_item.boundingRect().width()/2, -10)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        self.setToolTip(f"{label}: sin recursos al inicio")

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        r = self.radius
        path = QPainterPath()
        path.addRoundedRect(rect, r, r)
        painter.fillPath(path, self.brush())
        painter.setPen(self.pen())
        painter.drawPath(path)


class ResourceNode(QGraphicsEllipseItem):
    def __init__(self, label: str, size: float = 60.0) -> None:
        super().__init__(-size/2, -size/2, size, size)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setBrush(QColor(255, 204, 112))  # amarillo suave
        self.setPen(QPen(QColor(190, 140, 60), 2))
        self._label_item = LabelItem(label, self)
        self._label_item.setPos(-self._label_item.boundingRect().width()/2, -10)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        self.setToolTip(f"{label}: disponible")


class AnimatedArrow(QGraphicsPathItem, QObject):
    def __init__(self, start: QPointF, end: QPointF, color: QColor, width: float = 3.0) -> None:
        QGraphicsPathItem.__init__(self)
        QObject.__init__(self)
        self._start = QPointF(start)
        self._end = QPointF(end)
        self._progress = 0.0
        self._base_color = QColor(color)
        self._pen_width = width
        self.setZValue(-1)  # bajo los nodos
        self._blink_timer: Optional[QTimer] = None
        self._is_blinking = False
        self._rebuild_path()
        self._apply_pen()

    def _rebuild_path(self) -> None:
        path = QPainterPath(self._start)
        dx = self._end.x() - self._start.x()
        dy = self._end.y() - self._start.y()
        length = math.hypot(dx, dy)
        if length == 0:
            length = 1
        ux, uy = dx / length, dy / length
        # Hasta progress
        px = self._start.x() + ux * length * self._progress
        py = self._start.y() + uy * length * self._progress
        path.lineTo(QPointF(px, py))

        # punta de flecha al final del segmento actual si progress>0
        if self._progress > 0.98:
            end_point = QPointF(self._end)
        else:
            end_point = QPointF(px, py)

        # Cabeza de flecha
        head_len = 12.0
        angle = math.atan2(dy, dx)
        left = QPointF(
            end_point.x() - head_len * math.cos(angle - math.pi / 6),
            end_point.y() - head_len * math.sin(angle - math.pi / 6),
        )
        right = QPointF(
            end_point.x() - head_len * math.cos(angle + math.pi / 6),
            end_point.y() - head_len * math.sin(angle + math.pi / 6),
        )
        path.moveTo(end_point)
        path.lineTo(left)
        path.moveTo(end_point)
        path.lineTo(right)
        self.setPath(path)

    def _apply_pen(self) -> None:
        pen = QPen(self._base_color, self._pen_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)

    def getProgress(self) -> float:
        return self._progress

    def setProgress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, value))
        self._rebuild_path()

    progress = Property(float, getProgress, setProgress)

    def start_grow_animation(self, duration_ms: int, easing: QEasingCurve = QEasingCurve.OutCubic) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, b"progress")
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(easing)
        anim.start()
        return anim

    def set_color(self, color: QColor) -> None:
        self._base_color = QColor(color)
        self._apply_pen()

    def start_blink(self, color_a: QColor, color_b: QColor, interval_ms: int = 350) -> None:
        if self._blink_timer is not None:
            return
        self._is_blinking = True
        self._blink_timer = QTimer()
        state = {"toggle": False}

        def tick() -> None:
            state["toggle"] = not state["toggle"]
            self.set_color(color_a if state["toggle"] else color_b)

        self._blink_timer.timeout.connect(tick)
        self._blink_timer.start(interval_ms)

    def stop_blink(self) -> None:
        if self._blink_timer:
            self._blink_timer.stop()
            self._blink_timer.deleteLater()
            self._blink_timer = None
        self._is_blinking = False
        self._apply_pen()


# -----------------------------
# Vista y lógica de simulación
# -----------------------------

class DeadlockView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.setDragMode(QGraphicsView.NoDrag)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.process_nodes: Dict[str, ProcessNode] = {}
        self.resource_nodes: Dict[str, ResourceNode] = {}
        self.arrows: List[AnimatedArrow] = []
        self.current_scenario: Optional[Scenario] = None
        self.current_step_index = -1
        self.speed_factor = 1.0  # 1.0 normal, >1 más rápido
        self.assigned: Dict[str, Optional[str]] = {}  # recurso -> proceso asignado
        self.waits: Dict[str, Optional[str]] = {}  # proceso -> recurso solicitado (si está esperando)
        self._running_animations: List[QPropertyAnimation] = []  # mantener referencias vivas

    # Layout circular responsivo
    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._relayout()

    def load_scenario(self, scenario: Scenario) -> None:
        self.scene.clear()
        self.process_nodes.clear()
        self.resource_nodes.clear()
        self.arrows.clear()
        self.current_scenario = scenario
        self.current_step_index = -1
        self.assigned = {r: None for r in scenario.resources}
        self.waits = {p: None for p in scenario.processes}

        # Crear nodos
        for p in scenario.processes:
            node = ProcessNode(p)
            self.scene.addItem(node)
            self.process_nodes[p] = node
        colors = [QColor(255, 204, 112), QColor(255, 157, 177), QColor(255, 180, 120)]
        for i, r in enumerate(scenario.resources):
            node = ResourceNode(r)
            node.setBrush(colors[i % len(colors)])
            self.scene.addItem(node)
            self.resource_nodes[r] = node

        self._relayout()

    def _relayout(self) -> None:
        if not self.current_scenario:
            return
        rect = self.viewport().rect()
        cx = rect.width() / 2
        cy = rect.height() / 2
        radius = min(rect.width(), rect.height()) * 0.35

        items = list(self.process_nodes.values()) + list(self.resource_nodes.values())
        labels = list(self.process_nodes.keys()) + list(self.resource_nodes.keys())
        total = len(items)
        if total == 0:
            return
        angle_step = 2 * math.pi / total
        for i, item in enumerate(items):
            angle = i * angle_step - math.pi / 2
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            item.setPos(x, y)
        self.scene.setSceneRect(0, 0, rect.width(), rect.height())

    def _center_of(self, it: QGraphicsItem) -> QPointF:
        return it.sceneBoundingRect().center()

    def _arrow_between(self, a: QGraphicsItem, b: QGraphicsItem, color: QColor) -> AnimatedArrow:
        start = self._center_of(a)
        end = self._center_of(b)
        arr = AnimatedArrow(start, end, color)
        self.scene.addItem(arr)
        self.arrows.append(arr)
        return arr

    def step_forward(self, status_cb=None, explain_cb=None) -> None:
        if not self.current_scenario:
            return
        if self.current_step_index + 1 >= len(self.current_scenario.steps):
            if status_cb:
                status_cb("Fin del escenario.")
            return
        self.current_step_index += 1
        step = self.current_scenario.steps[self.current_step_index]

        duration = int(650 / self.speed_factor)
        green = QColor(46, 204, 113)
        red = QColor(231, 76, 60)
        blue = QColor(52, 152, 219)

        p_node = self.process_nodes[step.process]
        r_node = self.resource_nodes[step.resource]

        if step.kind == "assign":
            # Si el recurso está libre, asignar con flecha verde
            if self.assigned[step.resource] is None:
                arrow = self._arrow_between(p_node, r_node, blue)
                anim = arrow.start_grow_animation(duration)
                self._keep_animation(anim)

                def on_finished() -> None:
                    arrow.set_color(green)
                    self.assigned[step.resource] = step.process
                    p_node.setToolTip(f"{step.process}: tiene {step.resource}")
                    r_node.setToolTip(f"{step.resource}: asignado a {step.process}")
                    if status_cb:
                        status_cb(f"{step.process} → {step.resource} asignado")

                anim.finished.connect(on_finished)
            else:
                # ya asignado: tratar como request bloqueada
                self._blocked_request(p_node, r_node, step, red, duration, status_cb)

        elif step.kind in ("request", "wait"):
            if self.assigned[step.resource] is None:
                # solicitud satisfecha inmediatamente
                arrow = self._arrow_between(p_node, r_node, blue)
                anim = arrow.start_grow_animation(duration)
                self._keep_animation(anim)

                def on_finished2() -> None:
                    arrow.set_color(green)
                    self.assigned[step.resource] = step.process
                    p_node.setToolTip(f"{step.process}: tiene {step.resource}")
                    r_node.setToolTip(f"{step.resource}: asignado a {step.process}")
                    if status_cb:
                        status_cb(f"{step.process} → {step.resource} asignado")

                anim.finished.connect(on_finished2)
            else:
                self._blocked_request(p_node, r_node, step, red, duration, status_cb)

        # Explicación educativa
        if explain_cb:
            explain_cb(step.explain)

        # Chequeo de deadlock tras cada paso
        QTimer.singleShot(duration + 50, self._check_deadlock_and_alert)

    def _blocked_request(self, p_node: ProcessNode, r_node: ResourceNode, step: Step, red: QColor, duration: int, status_cb) -> None:
        arrow = self._arrow_between(p_node, r_node, red)
        anim = arrow.start_grow_animation(duration)
        self._keep_animation(anim)

        def on_finished_block() -> None:
            arrow.start_blink(QColor(220, 70, 70), QColor(255, 120, 120), 350)
            self.waits[step.process] = step.resource
            holder = self.assigned.get(step.resource)
            p_node.setToolTip(f"{step.process}: espera {step.resource} (lo tiene {holder})")
            r_node.setToolTip(f"{step.resource}: asignado a {holder}")
            if status_cb:
                status_cb(f"{step.process} → solicita {step.resource} (ocupado por {holder})")

        anim.finished.connect(on_finished_block)

    def _keep_animation(self, anim: QPropertyAnimation) -> None:
        # Conserva la animación para evitar GC prematuro; limpia al finalizar
        self._running_animations.append(anim)

        def cleanup() -> None:
            try:
                self._running_animations.remove(anim)
            except ValueError:
                pass

        anim.finished.connect(cleanup)

    # Detección simple de ciclo en el grafo de espera (wait-for graph)
    def _check_deadlock_and_alert(self) -> None:
        if not self.current_scenario:
            return
        # Construir grafo: proceso A -> proceso B si A espera un recurso poseído por B
        graph: Dict[str, List[str]] = {p: [] for p in self.current_scenario.processes}
        for p, r in self.waits.items():
            if r is None:
                continue
            holder = self.assigned.get(r)
            if holder and holder != p:
                graph[p].append(holder)

        # Detectar ciclo con DFS
        visited: Dict[str, int] = {p: 0 for p in graph}  # 0=blanco,1=gris,2=negro

        def dfs(u: str) -> bool:
            visited[u] = 1
            for v in graph[u]:
                if visited[v] == 0:
                    if dfs(v):
                        return True
                elif visited[v] == 1:
                    return True
            visited[u] = 2
            return False

        has_cycle = any(dfs(p) for p in graph if visited[p] == 0)
        if has_cycle:
            self._deadlock_animation()

    def _deadlock_animation(self) -> None:
        # Parpadeo global en rojo en todos los nodos
        blink_items: List[QGraphicsItem] = list(self.process_nodes.values()) + list(self.resource_nodes.values())
        timers: List[QTimer] = []
        state = {"on": False, "count": 0}

        def tick() -> None:
            state["on"] = not state["on"]
            color_on = QColor(255, 90, 90)
            for it in blink_items:
                if isinstance(it, ProcessNode):
                    it.setBrush(color_on if state["on"] else QColor(99, 179, 237))
                elif isinstance(it, ResourceNode):
                    it.setBrush(color_on if state["on"] else QColor(255, 204, 112))
            state["count"] += 1
            if state["count"] >= 8:
                for t in timers:
                    t.stop()
                    t.deleteLater()
                # Mensaje
                dlg = QMessageBox()
                dlg.setIcon(QMessageBox.Warning)
                dlg.setWindowTitle("Deadlock detectado")
                dlg.setText("Se ha detectado un interbloqueo (ciclo de espera circular).")
                dlg.setInformativeText("Los procesos esperan recursos mutuamente y ninguno puede avanzar.")
                dlg.exec()

        timer = QTimer()
        timer.timeout.connect(tick)
        timer.start(180)
        timers.append(timer)

    # Utilidades
    def reset(self) -> None:
        if self.current_scenario:
            self.load_scenario(self.current_scenario)


class ControlPanel(QWidget):
    def __init__(self, on_start, on_next, on_reset, on_autoplay_toggle, on_speed_change, on_scenario_change, on_explain) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.start_btn = QPushButton("Inicio")
        self.next_btn = QPushButton("Siguiente Paso")
        self.reset_btn = QPushButton("Reiniciar")
        self.autoplay_btn = QPushButton("Auto-play")
        self.explain_btn = QPushButton("¿Por qué ocurre esto?")

        self.scenario_combo = QComboBox()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 400)  # 1% a 400%
        self.speed_slider.setValue(100)

        layout.addWidget(QLabel("Escenario"))
        layout.addWidget(self.scenario_combo)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.next_btn)
        layout.addWidget(self.autoplay_btn)
        layout.addWidget(self.reset_btn)
        layout.addWidget(QLabel("Velocidad animación"))
        layout.addWidget(self.speed_slider)
        layout.addWidget(self.explain_btn)
        layout.addStretch(1)

        self.start_btn.clicked.connect(on_start)
        self.next_btn.clicked.connect(on_next)
        self.reset_btn.clicked.connect(on_reset)
        self.autoplay_btn.setCheckable(True)
        self.autoplay_btn.toggled.connect(on_autoplay_toggle)
        self.speed_slider.valueChanged.connect(on_speed_change)
        self.scenario_combo.currentIndexChanged.connect(on_scenario_change)
        self.explain_btn.clicked.connect(on_explain)


class StatusPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("statusLabel")
        self.explain_label = QLabel("")
        self.explain_label.setWordWrap(True)
        self.explain_label.setObjectName("explainLabel")
        layout.addWidget(QLabel("Estado del sistema"))
        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("Explicación"))
        layout.addWidget(self.explain_label)
        layout.addStretch(1)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_explain(self, text: str) -> None:
        self.explain_label.setText(text)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simulación de Deadlock - SO")
        self.resize(1200, 800)

        self.view = DeadlockView()
        self.status_panel = StatusPanel()
        self.scenarios = build_scenarios()
        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.timeout.connect(self._auto_step)

        # Panel de control a la izquierda, estado a la derecha
        self.control_panel = ControlPanel(
            on_start=self.on_start,
            on_next=self.on_next,
            on_reset=self.on_reset,
            on_autoplay_toggle=self.on_autoplay_toggle,
            on_speed_change=self.on_speed_change,
            on_scenario_change=self.on_scenario_change,
            on_explain=self.on_explain,
        )

        for sc in self.scenarios:
            self.control_panel.scenario_combo.addItem(sc.name)

        splitter = QSplitter()
        left = QWidget()
        lyt_left = QVBoxLayout(left)
        lyt_left.setContentsMargins(0, 0, 0, 0)
        lyt_left.addWidget(self.control_panel)

        center = self.view
        right = self.status_panel

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        self.setCentralWidget(splitter)

        # Cargar estilos
        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass

        # Cargar primer escenario
        self.view.load_scenario(self.scenarios[0])
        self.status_panel.set_status("Escenario cargado. Pulsa Inicio o Siguiente Paso.")

    # Callbacks UI
    def on_start(self) -> None:
        self.view.current_step_index = -1
        self.status_panel.set_status("Inicio del escenario")
        self.on_next()

    def on_next(self) -> None:
        self.view.step_forward(self.status_panel.set_status, self.status_panel.set_explain)

    def on_reset(self) -> None:
        self.view.reset()
        self.status_panel.set_status("Reiniciado")
        self.status_panel.set_explain("")

    def on_autoplay_toggle(self, checked: bool) -> None:
        if checked:
            self.control_panel.autoplay_btn.setText("Auto-play (ON)")
            interval = max(250, int(1200 / self.view.speed_factor))
            self.autoplay_timer.start(interval)
        else:
            self.control_panel.autoplay_btn.setText("Auto-play")
            self.autoplay_timer.stop()

    def _auto_step(self) -> None:
        prev = self.view.current_step_index
        self.on_next()
        if self.view.current_step_index == prev:
            # fin del escenario
            self.autoplay_timer.stop()
            self.control_panel.autoplay_btn.setChecked(False)

    def on_speed_change(self, value: int) -> None:
        # 100 => 1.0, 200 => 2.0, etc.
        self.view.speed_factor = max(0.05, value / 100.0)
        if self.autoplay_timer.isActive():
            interval = max(250, int(1200 / self.view.speed_factor))
            self.autoplay_timer.start(interval)

    def on_scenario_change(self, idx: int) -> None:
        if 0 <= idx < len(self.scenarios):
            self.view.load_scenario(self.scenarios[idx])
            self.status_panel.set_status("Escenario cambiado. Pulsa Inicio o Siguiente Paso.")
            self.status_panel.set_explain("")
            if self.autoplay_timer.isActive():
                self.autoplay_timer.stop()
                self.control_panel.autoplay_btn.setChecked(False)

    def on_explain(self) -> None:
        # Botón educativo adicional: resume el paso actual
        sc = self.view.current_scenario
        i = self.view.current_step_index
        if sc and 0 <= i < len(sc.steps):
            msg = sc.steps[i].explain
        else:
            msg = "Aún no hay paso activo. Usa Inicio o Siguiente Paso."
        self.status_panel.set_explain(msg)


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


