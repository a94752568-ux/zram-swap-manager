# ⚡ Zram & Swap Manager Pro

Aplicación profesional para gestionar Zram y Swapfile en sistemas Linux con interfaz gráfica moderna.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.2.0-purple)
![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Características

- ⚡ **Gestión de Zram** con algoritmos de compresión múltiples (zstd, lzo, lz4, etc.)
- 💾 **Configuración de Swapfile** persistente
- 🎯 **Modo dinámico adaptativo** que ajusta Zram según uso de RAM
- 📊 **Monitoreo en tiempo real** de memoria y swap
- 🎨 **Interfaz moderna y vibrante** con CustomTkinter
- ⚙️ **Comandos avanzados** del sistema
- 💾 **Configuraciones permanentes** mediante systemd

## 📋 Requisitos

- Python 3.8+
- Linux (systemd)
- Permisos de superusuario (para aplicar cambios)

## 🔧 Instalación
```bash
# Clonar el repositorio
git clone https://github.com/a94752568-ux/zram-swap-manager.git
cd zram-swap-manager

# Crear entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
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
