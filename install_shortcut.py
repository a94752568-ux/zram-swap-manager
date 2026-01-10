import os
import sys
from pathlib import Path

def create_shortcut():
    # Detectar rutas absolutas del entorno actual
    app_dir = Path(__file__).parent.absolute()
    script_path = app_dir / "zram_swap_manager.py"
    python_exe = sys.executable
    wrapper_path = app_dir / "launch_as_root.sh"
    
    # 1. Crear el wrapper script (Lanzador inteligente)
    # Este script se relanza a sí mismo con pkexec si no es root, preservando el display
    wrapper_content = f"""#!/bin/bash
if [ "$EUID" -ne 0 ]; then
    echo "Elevando privilegios..."
    exec pkexec env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY "$0" "$@"
fi
"{python_exe}" "{script_path}" "$@"
"""
    
    with open(wrapper_path, "w") as f:
        f.write(wrapper_content)
    os.chmod(wrapper_path, 0o755)
    print(f"✅ Lanzador creado en: {wrapper_path}")

    # 2. Crear el archivo .desktop
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Zram Manager Pro
Comment=Gestor de Memoria con Optimización Dinámica
Exec="{wrapper_path}"
Icon=utilities-system-monitor
Terminal=false
Categories=System;Settings;
"""

    dest_dir = Path.home() / ".local" / "share" / "applications"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "zram-manager-pro.desktop"
    
    with open(dest_file, "w") as f:
        f.write(desktop_content)
    
    print(f"✅ Acceso directo instalado en: {dest_file}")
    print("ℹ️  Busca 'Zram Manager Pro' en tu menú de aplicaciones.")

if __name__ == "__main__":
    create_shortcut()