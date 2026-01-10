import subprocess
import psutil
import os
import sys
import glob
import re
import json
import logging
import tempfile
import shutil
from typing import Dict, Any, Union, Tuple

logger = logging.getLogger(__name__)

class SystemManager:
    """
    Maneja todas las interacciones a nivel de sistema, como ejecutar comandos,
    verificar el estado del sistema y generar scripts de configuración.
    Implementa patrones de seguridad para la ejecución de comandos privilegiados.
    """
    
    REQUIRED_TOOLS = ['zramctl', 'swapon', 'pkexec', 'systemctl', 'sysctl']

    def __init__(self):
        self.total_ram_mb = psutil.virtual_memory().total / (1024**2)
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Verifica que las herramientas del sistema necesarias estén instaladas."""
        missing = [tool for tool in self.REQUIRED_TOOLS if not shutil.which(tool)]
        if missing:
            logger.warning(f"Faltan dependencias del sistema: {', '.join(missing)}")
            self._install_missing_dependencies(missing)

    def _install_missing_dependencies(self, missing: list) -> None:
        """Intenta instalar dependencias faltantes automáticamente."""
        logger.info("Intentando instalar dependencias faltantes...")
        
        # Mapeo de gestores de paquetes y nombres de paquetes
        pkg_managers = {
            'apt-get': {'cmd': 'install -y', 'pkgs': {'zramctl': 'util-linux', 'swapon': 'util-linux', 'pkexec': 'policykit-1', 'systemctl': 'systemd'}},
            'dnf': {'cmd': 'install -y', 'pkgs': {'zramctl': 'util-linux', 'swapon': 'util-linux', 'pkexec': 'polkit', 'systemctl': 'systemd'}},
            'pacman': {'cmd': '-S --noconfirm', 'pkgs': {'zramctl': 'util-linux', 'swapon': 'util-linux', 'pkexec': 'polkit', 'systemctl': 'systemd'}},
            'zypper': {'cmd': 'install -y', 'pkgs': {'zramctl': 'util-linux', 'swapon': 'util-linux', 'pkexec': 'polkit', 'systemctl': 'systemd'}},
        }

        manager_name = None
        manager_config = None

        for name, config in pkg_managers.items():
            if shutil.which(name):
                manager_name = name
                manager_config = config
                break
        
        if not manager_name:
            logger.error("No se pudo detectar un gestor de paquetes compatible.")
            return

        packages = set()
        for tool in missing:
            if tool in manager_config['pkgs']:
                packages.add(manager_config['pkgs'][tool])
        
        if not packages:
            return

        install_cmd = f"{manager_name} {manager_config['cmd']} {' '.join(packages)}"
        
        # Manejo especial si falta pkexec (necesario para elevar privilegios)
        if 'pkexec' in missing and os.geteuid() != 0:
            if shutil.which('sudo'):
                logger.info("pkexec no encontrado. Usando sudo para instalar dependencias.")
                try:
                    subprocess.run(['sudo', 'bash', '-c', install_cmd], check=True)
                    logger.info("Dependencias instaladas correctamente con sudo.")
                    return
                except subprocess.CalledProcessError:
                    logger.error("Fallo la instalación con sudo.")
                    return
            else:
                logger.error("Falta pkexec y no se puede elevar privilegios.")
                return

        # Script de instalación
        script = f"""#!/bin/bash
echo "📦 Instalando dependencias del sistema..."
{install_cmd}
"""
        def log_cb(msg): logger.info(msg)
        
        self.execute_script_with_privileges(script, log_cb)

    def get_total_ram(self) -> float:
        return self.total_ram_mb

    def get_current_status(self) -> Dict[str, bool]:
        """Verifica el estado actual de zram y swap."""
        status = {'zram_enabled': False, 'swapfile_enabled': False}
        try:
            # Verificar zram
            result = subprocess.run(['zramctl'], capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                status['zram_enabled'] = True

            # Verificar swapfile
            result = subprocess.run(['swapon', '--show'], capture_output=True, text=True, check=False)
            for line in result.stdout.strip().split('\n'):
                if line and 'file' in line.lower():
                    status['swapfile_enabled'] = True
                    break
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Error al verificar el estado del sistema: {e}")
        return status

    def get_live_monitor_data(self) -> Dict[str, str]:
        """Devuelve datos en vivo para la pestaña del monitor."""
        data = {
            'zram_info': "Zram: No configurado\n\n",
            'swap_info': "Swap: No configurado\n\n"
        }
        try:
            result = subprocess.run(['zramctl'], capture_output=True, text=True, timeout=2, check=False)
            if result.returncode == 0 and result.stdout.strip():
                data['zram_info'] = f"Zram:\n{result.stdout}\n\n"

            result = subprocess.run(['swapon', '--show'], capture_output=True, text=True, timeout=2, check=False)
            if result.returncode == 0 and result.stdout.strip():
                data['swap_info'] = f"Swap:\n{result.stdout}\n\n"
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Error al obtener datos del monitor en vivo: {e}")
            data['zram_info'] = "Error al obtener información de Zram\n"
            data['swap_info'] = "Error al obtener información de Swap\n"
        return data

    def run_shell_command(self, command: str) -> str:
        """Ejecuta un comando de shell y devuelve su salida y errores."""
        try:
            logger.info(f"Ejecutando comando de shell: {command}")
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            output = f"$ {command}\n\n{result.stdout}"
            if result.stderr:
                output += f"\nErrores:\n{result.stderr}"
            return output
        except Exception as e:
            logger.error(f"Excepción al ejecutar comando '{command}': {e}")
            return f"Error: {str(e)}"

    def apply_live_tuning(self, swappiness: int, cache_pressure: int) -> None:
        """Aplica ajustes de kernel en tiempo real sin persistencia."""
        try:
            # Solo aplicamos si tenemos permisos, si no, fallará silenciosamente para no spammear logs
            # o requerir contraseña constantemente.
            if os.geteuid() == 0:
                subprocess.run(['sysctl', f'vm.swappiness={swappiness}'], check=False, capture_output=True)
                subprocess.run(['sysctl', f'vm.vfs_cache_pressure={cache_pressure}'], check=False, capture_output=True)
            else:
                # Intentar con pkexec es demasiado intrusivo para un bucle de monitoreo.
                # En modo usuario, esta optimización dinámica se omite.
                pass
        except Exception as e:
            logger.debug(f"No se pudo aplicar tuning en vivo: {e}")

    # --- Gestión de Hardware (CPU/GPU) ---

    def get_available_frequencies(self) -> list[int]:
        """Obtiene las frecuencias disponibles (KHz) si el driver lo soporta."""
        try:
            base = "/sys/devices/system/cpu/cpu0/cpufreq"
            if os.path.exists(f"{base}/scaling_available_frequencies"):
                with open(f"{base}/scaling_available_frequencies", 'r') as f:
                    # Parsear y ordenar de mayor a menor
                    freqs = sorted([int(x) for x in f.read().strip().split()], reverse=True)
                    return freqs
        except Exception:
            pass
        return []

    def get_available_governors(self) -> list[str]:
        """Obtiene los gobernadores disponibles."""
        try:
            base = "/sys/devices/system/cpu/cpu0/cpufreq"
            if os.path.exists(f"{base}/scaling_available_governors"):
                with open(f"{base}/scaling_available_governors", 'r') as f:
                    return f.read().strip().split()
        except Exception:
            pass
        return ["performance", "powersave"] # Fallback

    def get_cpu_freq_limits(self) -> Dict[str, int]:
        """Obtiene los límites físicos de frecuencia de la CPU (KHz)."""
        try:
            # Intentar leer del primer núcleo (asumiendo simetría)
            base = "/sys/devices/system/cpu/cpu0/cpufreq"
            with open(f"{base}/cpuinfo_min_freq", 'r') as f:
                min_freq = int(f.read().strip())
            with open(f"{base}/cpuinfo_max_freq", 'r') as f:
                max_freq = int(f.read().strip())
            return {'min': min_freq, 'max': max_freq}
        except FileNotFoundError:
            # Fallback a psutil si sysfs no es accesible
            freq = psutil.cpu_freq()
            if freq:
                return {'min': int(freq.min * 1000), 'max': int(freq.max * 1000)}
            return {'min': 800000, 'max': 2400000} # Valores dummy seguros

    def get_cpu_details(self) -> Dict[str, Any]:
        """Obtiene estado detallado de la CPU."""
        info = {'governor': 'unknown', 'boost': False, 'driver': 'unknown'}
        base = "/sys/devices/system/cpu/cpu0/cpufreq"
        try:
            if os.path.exists(f"{base}/scaling_governor"):
                with open(f"{base}/scaling_governor", 'r') as f:
                    info['governor'] = f.read().strip()
            
            # Detectar Boost (Intel P-state o AMD CPB)
            boost_paths = [
                "/sys/devices/system/cpu/cpufreq/boost",
                "/sys/devices/system/cpu/intel_pstate/no_turbo"
            ]
            for p in boost_paths:
                if os.path.exists(p):
                    with open(p, 'r') as f:
                        val = f.read().strip()
                        # no_turbo: 1 = disabled (boost off), 0 = enabled (boost on)
                        # boost: 1 = enabled, 0 = disabled
                        if "no_turbo" in p:
                            info['boost'] = (val == "0")
                        else:
                            info['boost'] = (val == "1")
                    break
        except Exception as e:
            logger.error(f"Error leyendo detalles CPU: {e}")
        return info

    def set_cpu_governor(self, governor: str):
        """Cambia el gobernador de la CPU."""
        cmd = f"echo {governor} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
        self.execute_script_with_privileges(f"#!/bin/bash\n{cmd}", lambda x: None)

    def set_cpu_max_freq(self, freq_khz: int):
        """Establece la frecuencia máxima de la CPU."""
        cmd = f"echo {freq_khz} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq"
        self.execute_script_with_privileges(f"#!/bin/bash\n{cmd}", lambda x: None)

    def set_cpu_min_freq(self, freq_khz: int):
        """Establece la frecuencia mínima de la CPU."""
        cmd = f"echo {freq_khz} | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq"
        self.execute_script_with_privileges(f"#!/bin/bash\n{cmd}", lambda x: None)

    def set_cpu_boost(self, enable: bool):
        """Activa o desactiva el Boost de la CPU."""
        val_boost = "1" if enable else "0"
        val_no_turbo = "0" if enable else "1"
        
        script = "#!/bin/bash\n"
        script += f"[ -f /sys/devices/system/cpu/cpufreq/boost ] && echo {val_boost} > /sys/devices/system/cpu/cpufreq/boost\n"
        script += f"[ -f /sys/devices/system/cpu/intel_pstate/no_turbo ] && echo {val_no_turbo} > /sys/devices/system/cpu/intel_pstate/no_turbo\n"
        
        self.execute_script_with_privileges(script, lambda x: None)

    def set_energy_performance_preference(self, preference: str):
        """Establece la preferencia de energía (EPP) para drivers P-State (Intel/AMD)."""
        # Optimización: Si somos root, escribir directamente para evitar overhead de subprocesos
        if os.geteuid() == 0:
            try:
                # Buscar todos los núcleos
                import glob
                paths = glob.glob("/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference")
                for p in paths:
                    with open(p, 'w') as f:
                        f.write(preference)
                return
            except Exception as e:
                logger.error(f"Error escribiendo EPP directamente: {e}")

        # Fallback a script seguro
        script = f"""#!/bin/bash
# Aplicar EPP si el archivo existe (Intel P-State / AMD P-State)
if ls /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference 1> /dev/null 2>&1; then
    echo {preference} | tee /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference > /dev/null
fi
"""
        self.execute_script_with_privileges(script, lambda x: None)

    def get_cpu_voltage(self) -> float:
        """Intenta leer el voltaje de la CPU (Vcore/VID) usando sysfs (rápido) o sensors (fallback)."""
        # 1. Método Sysfs (Lectura directa de hwmon)
        try:
            for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
                # Buscar entradas de voltaje (in*_input)
                for input_path in glob.glob(os.path.join(hwmon, "in*_input")):
                    # Verificar etiqueta si existe
                    label_path = input_path.replace("_input", "_label")
                    is_vcore = False
                    
                    if os.path.exists(label_path):
                        with open(label_path, "r") as f:
                            label = f.read().strip().lower()
                            if "vcore" in label or "vid" in label or "cpu" in label:
                                is_vcore = True
                    
                    # Si no hay etiqueta, in0 suele ser Vcore en muchos chips
                    if not is_vcore and input_path.endswith("in0_input"):
                        is_vcore = True

                    if is_vcore:
                        with open(input_path, "r") as f:
                            # sysfs reporta en milivoltios
                            val = int(f.read().strip()) / 1000.0
                            if 0.2 < val < 2.5: # Filtro de valores realistas
                                return val
        except Exception:
            pass

        # 2. Método Fallback (Comando sensors)
        try:
            if shutil.which("sensors"):
                result = subprocess.run(["sensors"], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    # Heurística para encontrar voltaje de CPU (Vcore, vid, in0, etc.)
                    l = line.lower()
                    if "vcore" in l or "vid" in l or "cpu" in l:
                        if ":" in line and "V" in line:
                            parts = line.split(":")
                            val_part = parts[1].strip().split()[0]
                            try:
                                val = float(''.join(c for c in val_part if c.isdigit() or c == '.'))
                                if 0.2 < val < 2.5:
                                    return val
                            except: continue
        except Exception:
            pass
        return 0.0

    def check_epp_support(self) -> bool:
        """Verifica si la CPU soporta EPP (Energy Performance Preference)."""
        return os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference")

    def check_undervolt_support(self) -> str:
        """Detecta si hay herramientas de undervolt soportadas (ej. intel-undervolt)."""
        if shutil.which("intel-undervolt"):
            return "intel"
        return "none"

    def set_cpu_voltage_offset(self, offset_mv: int) -> str:
        """Aplica un offset de voltaje real modificando la configuración de intel-undervolt."""
        tool = self.check_undervolt_support()
        
        if tool == "intel":
            # Límite de seguridad estricto para evitar inestabilidad inmediata
            safe_offset = max(-150, min(0, int(offset_mv)))
            
            script = f"""#!/bin/bash
CONF="/etc/intel-undervolt.conf"
if [ -f "$CONF" ]; then
    # Backup de seguridad
    cp "$CONF" "$CONF.bak"
    
    # Actualizar el valor para CPU (Index 0) y CPU Cache (Index 2 - suelen ir vinculados)
    sed -i "s/^undervolt 0 'CPU'.*/undervolt 0 'CPU' {safe_offset}/" "$CONF"
    sed -i "s/^undervolt 2 'CPU Cache'.*/undervolt 2 'CPU Cache' {safe_offset}/" "$CONF"
    
    intel-undervolt apply
fi
"""
            self.execute_script_with_privileges(script, lambda x: None)
            return f"Offset de {safe_offset}mV aplicado (Intel)."
        return "Herramienta de undervolt no detectada."

    def is_undervolt_service_enabled(self) -> bool:
        """Verifica si el servicio de undervolt está habilitado para el inicio."""
        if self.check_undervolt_support() == "intel":
            try:
                res = subprocess.run(['systemctl', 'is-enabled', 'intel-undervolt'], capture_output=True, text=True)
                return res.returncode == 0
            except:
                pass
        return False

    def check_service_status(self, service_name: str = "zram-pro-optimizer.service") -> bool:
        """Verifica si el servicio de optimización en segundo plano está activo."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def restart_service(self, service_name: str = "zram-pro-optimizer.service"):
        """Reinicia el servicio de optimización en segundo plano."""
        script = f"#!/bin/bash\nsystemctl restart {service_name}"
        self.execute_script_with_privileges(script, lambda x: None)

    def enable_undervolt_at_boot(self, enable: bool):
        """Habilita o deshabilita el servicio de undervolt al inicio."""
        if self.check_undervolt_support() == "intel":
            action = "enable" if enable else "disable"
            script = f"#!/bin/bash\nsystemctl {action} --now intel-undervolt"
            self.execute_script_with_privileges(script, lambda x: None)

    def run_stress_test(self, duration: int = 10) -> Tuple[bool, str]:
        """Ejecuta una prueba de estrés corta en la CPU para verificar estabilidad."""
        try:
            # Intentar usar stress-ng o stress si están disponibles
            tool = None
            if shutil.which("stress-ng"): tool = "stress-ng"
            elif shutil.which("stress"): tool = "stress"
            
            if tool:
                cmd = [tool, "--cpu", str(psutil.cpu_count()), "--timeout", f"{duration}s"]
                subprocess.run(cmd, check=True, capture_output=True)
                return True, f"Prueba con {tool} completada sin errores."
            else:
                # Fallback: Generar carga usando procesos Python
                procs = []
                code = f"import time; end=time.time()+{duration}; \nwhile time.time()<end: _=1234567*7654321"
                for _ in range(psutil.cpu_count()):
                    procs.append(subprocess.Popen([sys.executable, "-c", code]))
                for p in procs:
                    p.wait()
                return True, "Prueba interna completada."
        except Exception as e:
            return False, f"Fallo en prueba: {str(e)}"

    def get_gpu_stats(self) -> Dict[str, Any]:
        """Intenta obtener estadísticas de la GPU (Genérico/AMD/Intel)."""
        stats = {'freq': 0, 'temp': 0, 'load': 0}
        try:
            # Método 1: Sysfs genérico (común en AMD/Intel modernos)
            # Buscar en /sys/class/drm/card*/device/hwmon/hwmon*/
            import glob
            
            # 1. AMD (pp_dpm_sclk) - Legacy/Specific
            if stats['freq'] == 0:
                pp_dpm = glob.glob("/sys/class/drm/card*/device/pp_dpm_sclk")
                if pp_dpm:
                    try:
                        with open(pp_dpm[0], 'r') as f:
                            content = f.read()
                            # Busca la línea con '*' que indica la frecuencia actual
                            for line in content.splitlines():
                                if '*' in line:
                                    stats['freq'] = int(line.split(':')[1].replace('Mhz', '').replace('*', '').strip())
                                    break
                    except: pass

            # 2. Intel (gt_cur_freq_mhz / gt_act_freq_mhz)
            if stats['freq'] == 0:
                intel_freq_paths = glob.glob("/sys/class/drm/card*/gt_cur_freq_mhz") + \
                                   glob.glob("/sys/class/drm/card*/gt_act_freq_mhz")
                if intel_freq_paths:
                    try:
                        with open(intel_freq_paths[0], 'r') as f:
                            stats['freq'] = int(f.read().strip())
                    except: pass

            # 3. Generic hwmon (freq1_input) - Common in newer kernels for AMD
            if stats['freq'] == 0:
                hwmon_freqs = glob.glob("/sys/class/drm/card*/device/hwmon/hwmon*/freq1_input")
                if hwmon_freqs:
                    try:
                        with open(hwmon_freqs[0], 'r') as f:
                            val = int(f.read().strip())
                            # Convertir a MHz si parece ser Hz (valor muy grande)
                            if val > 1000000: 
                                stats['freq'] = val // 1000000
                            else:
                                stats['freq'] = val
                    except: pass
            
            # Carga (AMD gpu_busy_percent)
            if stats['load'] == 0:
                gpu_load = glob.glob("/sys/class/drm/card*/device/gpu_busy_percent")
                if gpu_load:
                    try:
                        with open(gpu_load[0], 'r') as f:
                            stats['load'] = int(f.read().strip())
                    except: pass

            # --- Herramientas Externas (Fallback) ---
            
            # 4. radeontop (AMD)
            if (stats['freq'] == 0 or stats['load'] == 0) and shutil.which("radeontop"):
                try:
                    # radeontop -d - -l 1 (dump to stdout, limit 1 sample)
                    cmd = ["radeontop", "-d", "-", "-l", "1"]
                    # Timeout corto para no bloquear la UI
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
                    if result.returncode == 0:
                        output = result.stdout
                        # Parsear: "gpu 10.00%, ... sclk 800.00mhz"
                        if stats['freq'] == 0:
                            sclk = re.search(r'sclk ([\d\.]+)mhz', output)
                            if sclk: stats['freq'] = int(float(sclk.group(1)))
                        
                        if stats['load'] == 0:
                            gpu = re.search(r'gpu ([\d\.]+)%', output)
                            if gpu: stats['load'] = int(float(gpu.group(1)))
                except Exception: pass

            # 5. intel_gpu_top (Intel) - Requiere Root
            if (stats['freq'] == 0 or stats['load'] == 0) and shutil.which("intel_gpu_top") and os.geteuid() == 0:
                try:
                    # intel_gpu_top -J -s 100 (JSON output, 100ms sample)
                    cmd = ["intel_gpu_top", "-J", "-s", "100"]
                    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True) as proc:
                        try:
                            stdout, _ = proc.communicate(timeout=0.3)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            stdout, _ = proc.communicate()
                        
                        if stdout:
                            # Buscar el primer bloque JSON válido
                            json_match = re.search(r'\{.*?\}', stdout, re.DOTALL)
                            if json_match:
                                data = json.loads(json_match.group(0))
                                
                                if stats['freq'] == 0 and 'frequency' in data:
                                    stats['freq'] = int(data['frequency'].get('actual', 0))
                                
                                if stats['load'] == 0 and 'engines' in data:
                                    max_load = 0.0
                                    for eng in data['engines'].values():
                                        if 'busy' in eng:
                                            max_load = max(max_load, eng['busy'])
                                    stats['load'] = int(max_load)
                except Exception: pass
            
            # Temperatura (vía psutil sensors es más fiable, pero intentamos fallback)
            # Se maneja mejor en get_temperatures()
            
        except Exception as e:
            # Es normal fallar si no hay GPU dedicada o drivers específicos
            pass
        return stats

    def send_notification(self, title: str, message: str) -> None:
        """Envía una notificación de escritorio si notify-send está disponible."""
        if shutil.which('notify-send'):
            try:
                subprocess.run(
                    ['notify-send', '-u', 'critical', '-a', 'ZramManager', title, message],
                    check=False,
                    timeout=2
                )
            except Exception as e:
                logger.error(f"Error al enviar notificación: {e}")

    def generate_configuration_script(self, config: Dict[str, Any]) -> str:
        """Genera el script de configuración a partir de un diccionario de configuración."""
        script = """#!/bin/bash
# Script generado por Zram & Swap Manager Pro
set -e
echo "🚀 Iniciando configuración..."

# --- Backup Automático ---
BACKUP_DIR="/var/backups/zram-swap-manager"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "📦 Creando respaldo de seguridad del sistema..."
mkdir -p "$BACKUP_DIR"

if [ -f /etc/fstab ]; then
    cp /etc/fstab "$BACKUP_DIR/fstab.$TIMESTAMP.bak"
    echo "✅ fstab respaldado: $BACKUP_DIR/fstab.$TIMESTAMP.bak"
    # Rotación: Mantener últimos 5 backups para ahorrar espacio
    ls -1t "$BACKUP_DIR"/fstab.*.bak 2>/dev/null | tail -n +6 | xargs -r rm -f
fi
"""
        # Configuración de Zram
        if config['zram_enabled']:
            zram_size = config['zram_size']
            compression_algo = config['compression_algo']
            script += f"""
# Configurar Zram
echo "⚡ Configurando Zram..."
swapoff /dev/zram0 2>/dev/null || true
modprobe -r zram 2>/dev/null || true
modprobe zram
echo {compression_algo} > /sys/block/zram0/comp_algorithm
echo {zram_size}M > /sys/block/zram0/disksize
mkswap /dev/zram0
swapon -p 100 /dev/zram0
echo "✅ Zram configurado: {zram_size}MB con {compression_algo}"

# Hacer permanente
cat > /etc/systemd/system/zram.service << EOF
[Unit]
Description=Zram Configuration
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'modprobe zram && echo {compression_algo} > /sys/block/zram0/comp_algorithm && echo {zram_size}M > /sys/block/zram0/disksize && mkswap /dev/zram0 && swapon -p 100 /dev/zram0'
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable zram.service
"""
        else:
            script += """
# Desactivar Zram
echo "🔴 Desactivando Zram..."
swapoff /dev/zram0 2>/dev/null || true
modprobe -r zram 2>/dev/null || true
systemctl disable zram.service 2>/dev/null || true
rm -f /etc/systemd/system/zram.service
systemctl daemon-reload
"""

        # Configuración de Swapfile
        swap_location = config['swap_location']
        if config['swap_enabled']:
            swap_size_mb = config['swap_size']
            swappiness = config['swappiness']
            script += f"""
# Configurar Swapfile en {swap_location}
echo "💾 Verificando Swapfile..."

# Desactivar swap temporalmente para cambios
swapoff {swap_location} 2>/dev/null || true

# Verificar tamaño actual para evitar recreación innecesaria (dd es lento)
CURRENT_SIZE=$(stat -c%s "{swap_location}" 2>/dev/null || echo 0)
TARGET_SIZE=$(( {swap_size_mb} * 1024 * 1024 ))

if [ "$CURRENT_SIZE" -eq "$TARGET_SIZE" ]; then
    echo "✅ El archivo swap ya existe con el tamaño correcto. Omitiendo creación."
else
    echo "⚙️ Creando nuevo Swapfile de {swap_size_mb}MB... (Esto puede tardar)"
    rm -f {swap_location}
    dd if=/dev/zero of={swap_location} bs=1M count={swap_size_mb} status=progress
    chmod 600 {swap_location}
    mkswap {swap_location}
fi

# Asegurar formato y activación
if ! swapon {swap_location} 2>/dev/null; then
    echo "⚠️ Reactivando formato swap..."
    mkswap {swap_location}
    swapon {swap_location}
fi

echo "✅ Swapfile activo: {swap_size_mb}MB en {swap_location}"
if ! grep -q "{swap_location}" /etc/fstab; then
    echo "{swap_location} none swap sw 0 0" >> /etc/fstab
fi
sysctl vm.swappiness={swappiness}
echo "vm.swappiness={swappiness}" > /etc/sysctl.d/99-swappiness.conf
"""
        else:
            script += f"""
# Desactivar Swapfile en {swap_location}
echo "🔴 Desactivando Swapfile..."
swapoff {swap_location} 2>/dev/null || true
rm -f {swap_location}
sed -i '\\|{swap_location}|d' /etc/fstab
"""

        script += """
echo "✨ Configuración completada!"
echo ""
echo "Estado final:"
free -h
echo ""
swapon --show
"""
        return script

    def execute_script_with_privileges(self, script: str, status_callback) -> Union[subprocess.CompletedProcess, str, Exception]:
        """
        Guarda y ejecuta el script con pkexec, llamando a status_callback
        para reportar el progreso. Devuelve el objeto de resultado,
        una cadena de 'TIMEOUT' o una Excepción. Utiliza archivos temporales seguros.
        """
        try:
            status_callback("Guardando script temporal...")
            
            # Uso seguro de archivos temporales
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as temp_script:
                temp_script.write(script)
                temp_script_path = temp_script.name
            
            try:
                os.chmod(temp_script_path, 0o755)
                logger.info(f"Script temporal creado en: {temp_script_path}")

                # Verificar si ya tenemos privilegios de root
                if os.geteuid() == 0:
                    logger.info("Ejecutando script directamente (permisos de root detectados).")
                    status_callback("Ejecutando configuración...")
                    cmd = ['bash', temp_script_path]
                else:
                    logger.info("Invocando pkexec para elevación de privilegios.")
                    status_callback("Esperando autenticación...")
                    cmd = ['pkexec', 'bash', temp_script_path]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                return result
            finally:
                # Limpieza asegurada
                if os.path.exists(temp_script_path):
                    os.unlink(temp_script_path)
                    logger.info("Script temporal eliminado.")

        except subprocess.TimeoutExpired:
            logger.error("Timeout al ejecutar el script privilegiado.")
            return "TIMEOUT"
        except Exception as e:
            logger.critical(f"Error crítico en ejecución privilegiada: {e}")
            return e