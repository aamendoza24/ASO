import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from main import MainWindow as DeadlockWindow
from process_manager import ProcessSimulationWindow
from custom_deadlock import CustomDeadlockWindow


class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador de Sistemas Operativos")
        self.resize(1400, 900)
        
        # Crear widget central con pestañas
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear pestañas
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Crear ventanas de simulación
        self.deadlock_window = DeadlockWindow()
        self.process_window = ProcessSimulationWindow()
        self.custom_deadlock_window = CustomDeadlockWindow()
        
        # Agregar pestañas
        self.tabs.addTab(self.deadlock_window, "Simulador de Deadlock")
        self.tabs.addTab(self.process_window, "Gestión de Procesos")
        self.tabs.addTab(self.custom_deadlock_window, "Deadlock Personalizado")
        
        # Cargar estilos
        self.load_styles()

    def load_styles(self):
        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)
    
    # Cargar estilos globales
    try:
        with open("styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass
    
    window = MainApplication()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
