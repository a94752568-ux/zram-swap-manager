import collections
import statistics

from config import logger


class LightweightPredictor:
    """
    Predictor ligero y neutral respecto al hardware para orientar ajustes de memoria.

    La presión de memoria tiene prioridad sobre la carga de CPU: reducir swappiness
    cuando la CPU está ocupada puede empeorar una situación de falta de RAM.
    Este módulo solo calcula sugerencias; no aplica cambios al sistema.
    """

    def __init__(self, history_len=10):
        if not isinstance(history_len, int) or history_len < 2:
            raise ValueError("history_len debe ser un entero >= 2")

        self.ram_history = collections.deque(maxlen=history_len)
        self.cpu_history = collections.deque(maxlen=history_len)
        self.weight_ram_trend = 1.5

    @staticmethod
    def _clamp_percent(value):
        """Convierte una lectura a porcentaje válido; rechaza datos no numéricos."""
        value = float(value)
        if not 0 <= value <= 100:
            raise ValueError("Los porcentajes deben estar entre 0 y 100")
        return value

    def update(self, ram_percent, cpu_percent):
        self.ram_history.append(self._clamp_percent(ram_percent))
        self.cpu_history.append(self._clamp_percent(cpu_percent))

    def predict_next_minute_ram(self):
        """
        Proyecta aproximadamente 30 segundos hacia delante.

        Se asume que update() se llama cada 2 segundos. El nombre del método se
        conserva por compatibilidad con versiones anteriores.
        """
        if not self.ram_history:
            return 0.0
        if len(self.ram_history) < 2:
            return self.ram_history[-1]

        deltas = [
            self.ram_history[i] - self.ram_history[i - 1]
            for i in range(1, len(self.ram_history))
        ]
        avg_slope = statistics.mean(deltas)
        projection = self.ram_history[-1] + (
            avg_slope * 15 * self.weight_ram_trend
        )
        return min(100.0, max(0.0, projection))

    def get_optimal_swappiness(self, current_swappiness):
        """
        Sugiere swappiness según la presión prevista de RAM.

        La carga de CPU no reduce la sugerencia: con RAM escasa, hacerlo podría
        aumentar el riesgo de presión de memoria u OOM. current_swappiness se
        usa como valor de reserva si aún no hay mediciones.
        """
        try:
            fallback = max(0, min(100, int(current_swappiness)))
        except (TypeError, ValueError):
            fallback = 60

        if not self.ram_history:
            return fallback

        predicted_ram = self.predict_next_minute_ram()

        if predicted_ram >= 90:
            target = 100
        elif predicted_ram >= 80:
            target = 80
        elif predicted_ram < 50:
            target = 10
        else:
            target = 60

        if self.cpu_history and statistics.mean(self.cpu_history) > 85:
            logger.info(
                "CPU muy ocupada; se mantiene la política basada en presión "
                "de memoria para no agravar una posible falta de RAM."
            )

        return target

    def get_optimal_cache_pressure(self):
        """Sugiere cache_pressure sin cambios agresivos innecesarios."""
        if not self.ram_history:
            return 100
        return 150 if self.predict_next_minute_ram() >= 80 else 100

    def suggest_cpu_cap(self, current_cpu_load, current_temp=0):
        """
        Sugiere un límite porcentual de frecuencia; no es un undervolt real.

        Los valores son orientativos y no sustituyen límites térmicos del kernel.
        """
        load = self._clamp_percent(current_cpu_load)
        try:
            temp = float(current_temp or 0)
        except (TypeError, ValueError):
            temp = 0

        if load > 85:
            cap = 100
        elif load > 50:
            cap = 90
        elif load > 20:
            cap = 75
        else:
            cap = 60

        if temp > 85:
            cap = min(cap, 70)
        elif temp > 75:
            cap = min(cap, 85)

        return cap

    def suggest_epp(self, current_cpu_load):
        """Sugiere una preferencia EPP según la carga actual de CPU."""
        load = self._clamp_percent(current_cpu_load)
        if load > 30:
            return "balance_performance"
        if load > 10:
            return "balance_power"
        return "power"
