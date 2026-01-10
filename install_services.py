import os
import sys
import subprocess
from pathlib import Path

SERVICE_CONTENT = """[Unit]
Description=Zram & Swap Manager Pro Optimizer Daemon (Watchdog)
After=network.target local-fs.target

[Service]
Type=simple
ExecStart={python_path} {script_path}
Restart=always
RestartSec=5
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""

def install():
    if os.geteuid() != 0:
        print("❌ Error: Ejecuta este script como root (sudo python3 install_services.py).")
        sys.exit(1)

    base_dir = Path(__file__).parent.absolute()
    daemon_script = base_dir / "zram_optimizer_daemon.py"
    resolver_script = base_dir / "resolve_conflicts.py"
    
    # 1. Ejecutar Resolución de Conflictos
    print("🔍 Ejecutando resolución de conflictos de servicios...")
    subprocess.run([sys.executable, str(resolver_script)], check=False)
    
    # 2. Instalar Servicio Systemd
    print("⚙️  Instalando servicio de optimización en segundo plano...")
    service_path = Path("/etc/systemd/system/zram-pro-optimizer.service")
    
    content = SERVICE_CONTENT.format(
        python_path=sys.executable,
        script_path=str(daemon_script)
    )
    
    with open(service_path, "w") as f:
        f.write(content)
        
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "zram-pro-optimizer.service"], check=True)
    subprocess.run(["systemctl", "restart", "zram-pro-optimizer.service"], check=True)
    
    print("✅ Servicio instalado y arrancado correctamente.")
    print("   El optimizador ahora funciona en segundo plano (Watchdog activo).")
    print("   Estado: systemctl status zram-pro-optimizer.service")

if __name__ == "__main__":
    install()