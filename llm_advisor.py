"""
Asesor LLM local para Zram & Swap Manager Pro.

Consulta a un LLM servido por Ollama (http://127.0.0.1:11434) BAJO DEMANDA para
obtener recomendaciones estratégicas de optimización (swappiness, caché, cap de
CPU, EPP) junto con una explicación en lenguaje natural.

Principios de diseño:
- SIEMPRE seguro: salida restringida a JSON, whitelist estricta de campos,
  rangos acotados con clamp y fallback total ante errores. El LLM jamás puede
  emitir comandos, rutas ni valores fuera de rango.
- Nunca bloquea la app: se llama desde un hilo aparte con timeout propio.
- Si Ollama está apagado o el modelo falla, la heurística local
  (LightweightPredictor) sigue funcionando exactamente igual.
"""

import json
import logging
import urllib.request
import urllib.error

from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_KEEP_ALIVE

logger = logging.getLogger(__name__)

# Valores permitidos para EPP (whitelist; nada fuera de aquí se acepta)
EPP_WHITELIST = ("power", "balance_power", "balance_performance", "performance")

SYSTEM_PROMPT = """Eres un asesor experto en optimización de memoria Linux (zram, swap, vm.swappiness, vfs_cache_pressure) y en gestión de energía de CPU (gobernadores, EPP, límites de frecuencia).
Analizas las métricas del sistema y respondes SOLO con un objeto JSON válido, sin markdown, sin comillas de código y sin texto adicional, con exactamente este esquema:
{
  "swappiness": entero entre 0 y 100,
  "vfs_cache_pressure": entero entre 50 y 300,
  "cpu_cap": entero entre 50 y 100 (100 = sin límite de frecuencia),
  "epp": uno de "power", "balance_power", "balance_performance", "performance",
  "summary": resumen de una línea en español (máximo 120 caracteres),
  "reason": explicación breve en español (máximo 400 caracteres)
}
Reglas:
- Con RAM holgada (uso bajo y sin tendencia al alza) prefiere swappiness bajo (10-30).
- Con presión de memoria alta o creciente, sube swappiness para aprovechar zram (60-100).
- Si la CPU está muy cargada (>85%), evita swappiness muy alto: comprimir páginas cuesta CPU.
- Con temperatura alta (>80°C) o buscando ahorro de energía, reduce cpu_cap y usa un epp de ahorro.
- vfs_cache_pressure > 100 solo si hay presión de memoria (conviene liberar caché antes que swapear)."""


class OllamaAdvisor:
    """Cliente ligero de la API REST de Ollama (/api/chat) con salida JSON validada."""

    def __init__(self, url=None, model=None, timeout=None, keep_alive=None):
        self.url = (url or OLLAMA_URL).rstrip('/')
        self.model = model or OLLAMA_MODEL
        self.timeout = timeout or OLLAMA_TIMEOUT
        # keep_alive corto: no dejar el modelo residente 30 min en un daemon de memoria
        self.keep_alive = keep_alive or OLLAMA_KEEP_ALIVE

    def is_available(self, timeout=3):
        """
        Verifica si el servicio de Ollama responde.
        Devuelve (bool, lista_de_modelos). En error, la lista contiene el mensaje.
        """
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return True, [m.get('name', '') for m in data.get('models', [])]
        except Exception as e:
            logger.debug(f"Ollama no disponible: {e}")
            return False, [str(e)]

    def consult(self, metrics):
        """
        Envía las métricas del sistema al LLM y devuelve un dict de recomendaciones
        VALIDADAS (solo claves seguras, valores dentro de rango).
        Lanza excepción si Ollama no responde o la salida no es JSON procesable.
        """
        user_prompt = (
            "Métricas actuales del sistema (JSON):\n"
            + json.dumps(metrics, ensure_ascii=False, indent=2)
            + "\n\nDevuelve únicamente el JSON con tus recomendaciones."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "format": "json",
            "options": {"temperature": 0.2},
            "stream": False,
            "keep_alive": self.keep_alive
        }

        req = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        content = (data.get('message') or {}).get('content', '')
        rec = self._parse(content)
        if not rec:
            raise ValueError("El LLM no devolvió un JSON con recomendaciones válidas.")

        logger.info(f"Recomendación del LLM local ({self.model}): {rec.get('summary', '')}")
        return rec

    def _parse(self, content):
        """Extrae el primer objeto JSON de la respuesta y lo valida."""
        if not content:
            return None
        try:
            start = content.find('{')
            end = content.rfind('}')
            if start == -1 or end == -1 or end <= start:
                return None
            data = json.loads(content[start:end + 1])
        except (ValueError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        return self._validate(data)

    def _validate(self, data):
        """
        Whitelist + rangos: cualquier valor fuera de rango se acota (clamp),
        cualquier campo inválido se descarta en silencio.
        """
        rec = {}

        def clamp_int(key, lo, hi):
            v = data.get(key)
            if v is None or isinstance(v, bool):
                return
            try:
                v = int(v)
            except (TypeError, ValueError):
                return
            rec[key] = max(lo, min(hi, v))

        clamp_int('swappiness', 0, 100)
        clamp_int('vfs_cache_pressure', 50, 300)
        clamp_int('cpu_cap', 50, 100)

        epp = data.get('epp')
        if epp in EPP_WHITELIST:
            rec['epp'] = epp

        for key in ('summary', 'reason'):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                rec[key] = v.strip()[:500]

        return rec
