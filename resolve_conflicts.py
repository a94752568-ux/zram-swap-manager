import subprocess
import logging
import sys
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lista de servicios conocidos que pueden entrar en conflicto
CONFLICTING_SERVICES = [
    "zram-config",
    "zram-tools",
    "ubuntu-zram-config",
    "systemd-zram-setup",
    "zramswap",
    "earlyoom", # A veces interfiere con la gestión de memoria
    "nohang"    # Similar a earlyoom
]

def resolve():
    if os.geteuid() != 0:
        logger.error("Este script debe ejecutarse como root (sudo) para gestionar servicios del sistema.")
        sys.exit(1)

    logger.info("🛡️  Analizando servicios del sistema en busca de conflictos...")
    
    for service in CONFLICTING_SERVICES:
        try:
            # Verificar si el servicio existe y está cargado
            res = subprocess.run(["systemctl", "status", service], capture_output=True, text=True)
            
            # Si el código de retorno no es 4 (Not Found), el servicio existe
            if res.returncode != 4:
                logger.warning(f"⚠️  Conflicto detectado: {service}")
                
                # Deshabilitar y enmascarar para asegurar prioridad absoluta de nuestro daemon
                logger.info(f"   Neutralizando {service}...")
                subprocess.run(["systemctl", "stop", service], check=False)
                subprocess.run(["systemctl", "disable", service], check=False)
                subprocess.run(["systemctl", "mask", service], check=False) # Mask evita que otros scripts lo reactiven
                logger.info(f"   ✅ {service} ha sido desactivado.")
        except Exception as e:
            logger.error(f"Error gestionando {service}: {e}")

    logger.info("✨ Resolución de conflictos completada. Zram & Swap Manager Pro tiene prioridad absoluta.")

if __name__ == "__main__":
    resolve()