import collections
import statistics
from config import logger

class LightweightPredictor:
    """
    Motor de predicción optimizado para CPUs de bajo consumo (como AMD A8/E-Series).
    Utiliza regresión lineal simple y heurística para predecir presión de memoria
    sin overhead significativo.
    """
    def __init__(self, history_len=10):
        self.ram_history = collections.deque(maxlen=history_len)
        self.cpu_history = collections.deque(maxlen=history_len)
        # Pesos "Pre-entrenados" para perfil conservador (AMD A8)
        self.weight_ram_trend = 1.5
        self.weight_cpu_penalty = 0.8
        
    def update(self, ram_percent, cpu_percent):
        self.ram_history.append(ram_percent)
        self.cpu_history.append(cpu_percent)

    def predict_next_minute_ram(self):
        """Calcula la tendencia de RAM para el próximo minuto."""
        if len(self.ram_history) < 2:
            return self.ram_history[-1] if self.ram_history else 0
            
        # Cálculo simplificado de pendiente (slope)
        deltas = [self.ram_history[i] - self.ram_history[i-1] for i in range(1, len(self.ram_history))]
        avg_slope = statistics.mean(deltas)
        
        # Proyección a 30 segundos (asumiendo update cada 2s, son 15 pasos)
        projection = self.ram_history[-1] + (avg_slope * 15 * self.weight_ram_trend)
        return min(100, max(0, projection))

    def get_optimal_swappiness(self, current_swappiness):
        """
        Determina el swappiness ideal basado en la predicción de RAM y carga de CPU.
        """
        if not self.ram_history:
            return current_swappiness

        predicted_ram = self.predict_next_minute_ram()
        avg_cpu = statistics.mean(self.cpu_history) if self.cpu_history else 0
        
        target_swappiness = current_swappiness

        # Lógica Difusa (Fuzzy Logic) optimizada
        if predicted_ram > 90:
            # Emergencia: Necesitamos swap agresivo
            target_swappiness = 100
        elif predicted_ram > 80:
            # Presión alta
            target_swappiness = 80
        elif predicted_ram < 50:
            # Memoria relajada
            target_swappiness = 10
        else:
            # Zona media (50-80%), mantener equilibrio
            target_swappiness = 60

        # Penalización por CPU (Específico para AMD A8)
        # Si la CPU está saturada, comprimir memoria (Zram) cuesta mucho.
        # Reducimos swappiness para dar respiro al procesador.
        if avg_cpu > 85:
            logger.info("CPU saturada (A8 Protection): Reduciendo agresividad de swap.")
            target_swappiness = max(10, target_swappiness - 40)
        elif avg_cpu > 60:
            target_swappiness = max(10, target_swappiness - 20)

        return int(target_swappiness)

    def get_optimal_cache_pressure(self):
        """Ajusta vfs_cache_pressure."""
        # Si falta RAM, preferimos liberar caché de archivos antes que swappear apps
        predicted_ram = self.predict_next_minute_ram()
        if predicted_ram > 80:
            return 200 # Liberar caché agresivamente
        return 100 # Valor por defecto

    def suggest_cpu_cap(self, current_cpu_load, current_temp=0):
        """
        Sugiere un porcentaje de límite de frecuencia (Cap) para ahorrar energía (Undervolt Simulado).
        Considera carga de CPU y Temperatura para mantener el procesador en su zona de eficiencia.
        """
        cap = 100
        
        # 1. Lógica base por carga (evitar saltar a frecuencias turbo por tareas de fondo)
        if current_cpu_load > 85:
            cap = 100 # Necesitamos toda la potencia
        elif current_cpu_load > 50:
            cap = 90  # Ligero recorte, evita picos de voltaje máximos
        elif current_cpu_load > 20:
            cap = 75  # Modo eficiente (sweet spot de muchos CPUs)
        else:
            cap = 60  # Modo ahorro máximo (idle/background)

        # 2. Penalización térmica (Thermal Throttling por Software)
        # Si la temperatura sube, bajamos el techo para reducir voltaje/calor proactivamente
        if current_temp > 85:
            cap = min(cap, 70) # Emergencia: Enfriar sí o sí
        elif current_temp > 75:
            cap = min(cap, 85) # Preventivo: Mantener bajo control
            
        return cap

    def suggest_epp(self, current_cpu_load):
        """
        Sugiere el perfil EPP óptimo.
        Estrategia: Race-to-Idle. Subir rendimiento rápido para acabar tareas, bajar a ahorro en reposo.
        """
        if current_cpu_load > 30:
            return "balance_performance" # Respuesta rápida
        elif current_cpu_load > 10:
            return "balance_power"       # Equilibrio
        return "power"                   # Ahorro máximo