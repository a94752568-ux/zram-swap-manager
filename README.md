# ⚡ Zram & Swap Manager Pro

**Optimización Extrema. Control Total. Diseño Premium.**

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-purple?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Linux-black?style=for-the-badge&logo=linux)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## 🌟 ¿Por qué Zram & Swap Manager Pro?

Transforma tu experiencia en Linux. Ya sea que tengas una máquina antigua luchando por respirar o una estación de trabajo de alto rendimiento, **Zram & Swap Manager Pro** es la navaja suiza que necesitas.

No es solo un gestor de swap; es una suite completa de **optimización de hardware y memoria** diseñada para:

*   🚀 **Eliminar el Lag:** Gestión inteligente de Zram (memoria comprimida) para que nunca te quedes sin RAM.
*   🔋 **Extender tu Batería:** Perfiles de energía avanzados y *Undervolt Automático* impulsado por IA.
*   🎮 **Maximizar FPS:** Modo Gaming dedicado que prioriza el rendimiento bruto.
*   ❄️ **Mantener la Frescura:** Monitoreo térmico proactivo y gestión de frecuencias.

---

## ✨ Características Destacadas

### 🧠 Gestión de Memoria de Nueva Generación
*   **Algoritmo Dinámico:** Ajusta el tamaño de Zram en tiempo real según la presión de memoria.
*   **Compresión Avanzada:** Soporte para `zstd`, `lzo-rle`, `lz4` y más.
*   **Swapfile Inteligente:** Creación y gestión automatizada de archivos de intercambio.

### ⚡ Control de Hardware (Overclock & Undervolt)
*   **Undervolt Seguro:** Reduce temperaturas y consumo sin sacrificar rendimiento (soporte Intel/AMD).
*   **Gestión de CPU:** Control total sobre gobernadores, frecuencias máximas/mínimas y Boost.
*   **Perfiles de Energía:** Cambia instantáneamente entre modos **Gaming 🎮**, **Oficina 🏢** y **Eco 🍃**.

### 📊 Centro de Comando Visual
*   **Monitor en Tiempo Real:** Gráficos históricos de RAM, Swap, CPU, GPU y Temperatura.
*   **Interfaz "MacPro Dark":** Una experiencia visual moderna, limpia y responsiva.
*   **Modo Mini:** Mantén un ojo en tus estadísticas sin distracciones.

### 🛡️ Seguridad Primero
*   **Backups Automáticos:** Tu configuración (`fstab`) se respalda antes de cada cambio.
*   **Modo Seguro:** Detección de cierres inesperados para restaurar la estabilidad.
*   **Validación de Dependencias:** Instalación automática de herramientas del sistema necesarias.

---

## 🔧 Instalación Rápida

Convierte tu sistema en una bestia de rendimiento en segundos.

### Requisitos Previos
*   Python 3.8+
*   Linux (Systemd)
*   Permisos de Root (para aplicar la magia)

### Instalación

```bash
# 1. Clona el repositorio
git clone https://github.com/a94752568-ux/zram-swap-manager.git
cd zram-swap-manager

# 2. Instala el paquete
pip install .

# 3. ¡Ejecuta!
zram-pro
```

## 🎮 Uso
```bash
python zram_swap_manager.py
```

## 🎨 Características de la Interfaz

- **Estadísticas en tiempo real**: Monitoreo de RAM total, disponible, Zram efectivo y ratio de compresión
- **Modo dinámico**: Ajuste automático según carga del sistema
  - >70% uso → 35% de RAM para Zram
  - >50% uso → 25% de RAM para Zram
  - <50% uso → 20% de RAM para Zram
- **Múltiples algoritmos**: zstd (recomendado), lzo-rle, lzo, lz4, 842
- **Swappiness configurable**: Control fino del comportamiento de swap

## ⚠️ Advertencias

- Requiere permisos de root para aplicar cambios
- Modifica configuraciones del sistema permanentemente
- Realiza backup de configuraciones importantes antes de usar

## 📝 Licencia

MIT License - Ver archivo LICENSE para más detalles

## 👨‍💻 Autor

**a94752568-ux**

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request.
