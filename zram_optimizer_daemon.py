import time
import psutil
import json
import os
import sys
import logging
import signal
from pathlib import Path
from system_manager import SystemManager
from optimizer import LightweightPredictor

# Configuración de logging para el demonio
LOG_FILE = "/var/log/zram_optimizer.log"

def _setup_logging():
    """
    Configura los handlers del demonio.
    Nota: config.py ya añade handlers al logger raíz, por lo que se usa force=True
    para que este proceso realmente escriba en su propio archivo de log.
    Si no hay permisos para /var/log (ej. ejecución sin root), solo usa consola.
    """
    try:
        handlers = [
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    except (PermissionError, OSError):
        handlers = [logging.StreamHandler()]
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [DAEMON] - %(message)s',
        handlers=handlers,
        force=True
    )

_setup_logging()
logger = logging.getLogger(__name__)

class OptimizerDaemon:
    def __init__(self):
        self.running = True
        self.system_manager = SystemManager()
        self.predictor = LightweightPredictor()
        self.config = {}
        self.current_live_swappiness = 60
        self.current_live_epp = ""
        
        # Cargar configuración inicial
        self.load_config()
        self.last_config_check = time.time()
        
        # Manejo de señales para cierre limpio
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)

    def load_config(self, quiet=False):
        """Intenta cargar la configuración del usuario."""
        config_path = None
        
        # Intentar encontrar la configuración del usuario real (no root)
        possible_paths = []
        
        # 1. Si se ejecuta con sudo
        if os.environ.get('SUDO_USER'):
            user_home = os.path.expanduser(f"~{os.environ.get('SUDO_USER')}")
            possible_paths.append(Path(user_home) / ".config" / "zram-swap-manager" / "preferences.json")
        
        # 2. Buscar en directorios home comunes
        base_home = Path("/home")
        if base_home.exists():
            for user_dir in base_home.iterdir():
                if user_dir.is_dir():
                    possible_paths.append(user_dir / ".config" / "zram-swap-manager" / "preferences.json")
        
        for p in possible_paths:
            if p.exists():
                config_path = p
                break
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                if not quiet:
                    logger.info(f"Configuración cargada desde {config_path}")
            except Exception as e:
                logger.error(f"Error cargando configuración: {e}")
        else:
            logger.warning("No se encontró archivo de configuración. Usando valores por defecto.")

    def stop(self, signum, frame):
        logger.info("Deteniendo demonio de optimización...")
        self.running = False

    def run(self):
        logger.info("🚀 Iniciando bucle de optimización en segundo plano...")
        
        while self.running:
            try:
                # Estadísticas
                mem = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=2) # Bloqueante 2s (ciclo del demonio)

                # Recargar preferencias cada 2 min (incluye llm_overrides aplicados desde la GUI)
                if time.time() - self.last_config_check > 120:
                    self.last_config_check = time.time()
                    self.load_config(quiet=True)
                overrides = self.config.get('llm_overrides') or {}
                
                # Actualizar predictor IA
                self.predictor.update(mem.percent, cpu)
                
                # 1. Optimización Dinámica de Memoria
                if self.config.get('zram_dynamic', True):
                    # El asesor LLM (si fue consultado) define la base de swappiness
                    base_swappiness = overrides.get('swappiness', self.config.get('swappiness', 60))
                    opt_swappiness = self.predictor.get_optimal_swappiness(base_swappiness)
                    opt_cache = self.predictor.get_optimal_cache_pressure()
                    
                    if abs(opt_swappiness - self.current_live_swappiness) > 5:
                        self.system_manager.apply_live_tuning(opt_swappiness, opt_cache)
                        self.current_live_swappiness = opt_swappiness
                        logger.debug(f"Ajuste Memoria: Swappiness={opt_swappiness}, Cache={opt_cache}")

                # 2. Undervolt Automático / CPU Tuning
                if self.config.get('auto_undervolt', False):
                    # Obtener temperatura para seguridad
                    temps = psutil.sensors_temperatures()
                    cur_temp = 0
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'k10temp' in name.lower() or 'core' in name.lower():
                            cur_temp = entries[0].current
                            break
                    
                    # Ajuste de Frecuencia (Cap)
                    target_cap = self.predictor.suggest_cpu_cap(cpu, cur_temp)
                    # Techo estratégico definido por el asesor LLM (si existe)
                    if 'cpu_cap' in overrides:
                        target_cap = min(target_cap, overrides['cpu_cap'])
                    limits = self.system_manager.get_cpu_freq_limits()
                    target_freq = int(limits['min'] + (limits['max'] - limits['min']) * (target_cap / 100))
                    self.system_manager.set_cpu_max_freq(target_freq)
                    
                    # Ajuste de EPP (el asesor LLM puede fijar una preferencia estratégica)
                    if self.system_manager.check_epp_support():
                        target_epp = overrides.get('epp') or self.predictor.suggest_epp(cpu)
                        if target_epp != self.current_live_epp:
                            self.system_manager.set_energy_performance_preference(target_epp)
                            self.current_live_epp = target_epp

            except Exception as e:
                logger.error(f"Error en bucle: {e}")
                time.sleep(5)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Este demonio debe ejecutarse como root.")
        sys.exit(1)
        
    daemon = OptimizerDaemon()
    daemon.run()

