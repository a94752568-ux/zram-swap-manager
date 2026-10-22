import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Configuración de directorios para logs
LOG_DIR = Path.home() / ".local" / "share" / "zram-swap-manager" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "optimization_history.log"

# Configuración de Logging Profesional
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Formato
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

# Evitar duplicación de handlers si el módulo se recarga
if not root_logger.handlers:
    # Handler de Consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler de Archivo Rotativo (5MB, 3 backups)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

# Configuración de Tema "MacPro Dark"
THEME = {
    "bg_main": "#1C1C1E",       # Fondo Principal (Apple Dark)
    "bg_sidebar": "#000000",    # Sidebar (Negro puro)
    "bg_card": "#2C2C2E",       # Tarjetas (Gris oscuro)
    "accent": "#0A84FF",        # Azul Apple
    "accent_hover": "#007AFF",  # Azul Apple Hover
    "success": "#30D158",       # Verde Apple
    "warning": "#FF9F0A",       # Naranja Apple
    "danger": "#FF453A",        # Rojo Apple
    "text": "#FFFFFF",          # Blanco
    "text_sec": "#8E8E93"       # Gris secundario
}

# --- Asesor LLM local (Ollama), consulta bajo demanda desde la GUI ---
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 120       # segundos; la inferencia 100% CPU puede tardar
OLLAMA_KEEP_ALIVE = "5m"   # corto: no dejar el modelo residente demasiado tiempo
