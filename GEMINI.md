# Contexto del Proyecto para Gemini (Checkpoint v2.0 - Modular)

## Roles del Agente
Actúa bajo los siguientes roles profesionales:
- **Ingeniero en desarrollo de software**: Para arquitectura, código limpio, patrones de diseño y optimización.
- **Diseñador Gráfico**: Para la estética de la UI, paleta de colores (MacPro Dark) y experiencia de usuario (UX).
- **Director de Marketing**: Para la presentación del producto, redacción de README atractivo y enfoque en el valor para el usuario.

## Descripción General
**Zram & Swap Manager Pro** es una herramienta gráfica para Linux desarrollada en Python que permite gestionar y optimizar la memoria del sistema mediante Zram y Swapfiles. Utiliza `CustomTkinter` para la interfaz de usuario.

## Estructura del Proyecto (Modular)
El proyecto ha sido refactorizado desde una estructura monolítica a una modular:

1.  **`zram_swap_manager.py` (Entry Point)**:
    - Clase `ZramSwapManager`: Controlador principal.
    - Gestiona el ciclo de vida de la app, la navegación (Sidebar) y la persistencia de preferencias.
    - Implementa lógica de UI responsiva (Modo Compacto).

2.  **`system_manager.py`**:
    - Clase `SystemManager`: Lógica de negocio del sistema operativo.
    - Encapsula la lógica del sistema operativo.
    - Ejecuta comandos de shell (`subprocess`).
    - Genera scripts Bash para la configuración persistente (`systemd`).
    - Maneja la elevación de privilegios mediante `pkexec`.

3.  **`views.py`**:
    - Contiene las clases de vista: `ZramView`, `SwapView`, `MonitorView`, `AdvancedView`.
    - Heredan de `BaseView` para consistencia.
    - Implementan la UI específica de cada sección.

4.  **`config.py`**:
    - Constantes globales.
    - Definición del tema `THEME` ("MacPro Dark").
    - Configuración de `logging`.

5.  **`utils.py`**:
    - Utilidades compartidas como la clase `ToolTip`.

## Reglas de Desarrollo
- **Idioma**: Todo el código, comentarios y textos de UI deben estar en **Español**.
- **Estilo**: Seguir PEP 8. Usar f-strings.
- **Seguridad**:
    - Nunca ejecutar `sudo` directamente en el código Python.
    - Usar `tempfile` para scripts temporales seguros ejecutados con `pkexec`.
- **UI**:
    - Tema "MacPro Dark" definido en `config.py`.
    - Diseño responsivo con Sidebar que se compacta automáticamente (<900px).

## Comandos Críticos
La aplicación interactúa con:
- `zramctl`: Para estado y configuración de Zram.
- `swapon` / `swapoff`: Para gestión de swap.
- `systemctl`: Para persistencia de servicios.
- `pkexec`: Para ejecución privilegiada.
- `notify-send`: Para notificaciones de escritorio.

## Notas Importantes
- La configuración de Zram se hace persistente creando un servicio systemd (`zram.service`).
- El monitoreo en vivo se ejecuta en un hilo demonio (`daemon thread`).
- Se utiliza `matplotlib` para gráficos históricos si está disponible.
- Las preferencias se guardan en `~/.config/zram-swap-manager/preferences.json`.