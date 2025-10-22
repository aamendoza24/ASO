# Simulador de Sistemas Operativos (PySide6)

Aplicación educativa completa para simular gestión de procesos, recursos, procesadores y detección de deadlock con interfaz moderna e interactiva.

## Características

### 🎯 Simulador de Deadlock
- Visualización paso a paso de interbloqueos entre procesos y recursos
- Animaciones fluidas con flechas que crecen y parpadean
- Detección automática de ciclos de espera circular
- Múltiples escenarios predefinidos

### ⚙️ Gestión de Procesos
- **Recursos**: Agregar recursos con nombre, tamaño y estado (disponible/en uso)
- **Procesos**: Configurar nombre, estado, prioridad y tiempo de ejecución
- **Procesadores**: Definir procesadores con número de hilos
- **Simulación**: Tabla principal con estado en tiempo real
- **Detección de Deadlock**: Integrada en el sistema de gestión

## Requisitos

- Python 3.9+
- PySide6

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar

### Aplicación completa (recomendado)
```bash
python -m ArquiSO.main_window
```

### Solo simulador de deadlock
```bash
python -m ArquiSO.main
```

### Solo gestión de procesos
```bash
python -m ArquiSO.process_manager
```

### Solo deadlock personalizado
```bash
python -m ArquiSO.custom_deadlock
```

## Uso

### Pestaña "Simulador de Deadlock"
- **Inicio**: Comienza el escenario desde el primer paso
- **Siguiente Paso**: Avanza una transición animada
- **Auto-play**: Reproducción automática con velocidad configurable
- **Reiniciar**: Reinicia el escenario actual
- **Selector de escenario**: Elige entre casos predefinidos
- **¿Por qué ocurre esto?**: Explicación educativa del paso actual

### Pestaña "Gestión de Procesos"
1. **Configurar elementos**:
   - Agregar recursos (R1, R2, etc.) con tamaño
   - Crear procesos (P1, P2, etc.) con prioridad y tiempo
   - Definir procesadores (CPU1, CPU2, etc.) con hilos

2. **Simular**:
   - Ajustar velocidad (0.5X a 8X)
   - Iniciar/Pausar simulación
   - Observar estados en tiempo real
   - **Limpiar Sistema**: Reinicia todo el sistema
   - **Escenario Aleatorio**: Genera configuración aleatoria

3. **Monitorear**:
   - Tabla principal con estado de procesos
   - Colector de procesos terminados
   - Barra de estado con información actual
   - **Estadísticas finales**: Ciclos, tiempo y procesos completados

### Pestaña "Deadlock Personalizado"
1. **Configurar escenario**:
   - **Procesos**: Agregar procesos con nombre y prioridad
   - **Recursos**: Definir recursos con número de instancias totales
   - **Asignación**: Controlar asignación/liberación manual de recursos

2. **Visualizar**:
   - **Grafo dinámico**: Visualización de procesos, recursos y asignaciones
   - **Flechas verdes**: Recursos asignados exitosamente
   - **Flechas rojas**: Solicitudes bloqueadas o pendientes

3. **Monitorear**:
   - **Registro de eventos**: Log cronológico de todas las acciones
   - **Detección automática**: Alerta inmediata cuando se detecta deadlock
   - **Análisis educativo**: Explicación detallada del interbloqueo

## Arquitectura

- `main_window.py`: Ventana principal con pestañas
- `main.py`: Simulador de deadlock original
- `process_manager.py`: Sistema de gestión de procesos
- `custom_deadlock.py`: Simulador de deadlock personalizado con grafos
- `styles.qss`: Estilos modernos con QSS

## Estilo

Interfaz moderna inspirada en las imágenes de referencia con:
- Colores pastel y gradientes suaves
- Tipografía sans-serif (Segoe UI, Roboto)
- Indicadores de estado con colores distintivos
- Animaciones fluidas y transiciones suaves


