import customtkinter as ctk
import json
import os
import subprocess
import threading
import time
import psutil
import logging
import collections
from pathlib import Path
import tkinter.messagebox as messagebox

# Importaciones de módulos locales
from config import THEME, logger
from system_manager import SystemManager
from optimizer import LightweightPredictor
from views import ZramView, SwapView, MonitorView, AdvancedView, HardwareView
from utils import ToolTip

class ZramSwapManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración de la ventana
        title = "Zram & Swap Manager Pro"
        if os.geteuid() == 0:
            title += " (Modo Root 🛡️)"
        self.title(title)
        self.geometry("1200x800")
        
        # Tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.system_manager = SystemManager()
        self.predictor = LightweightPredictor()
        
        # Variables
        self.total_ram = self.system_manager.get_total_ram()
        self.zram_enabled = ctk.BooleanVar(value=False)
        self.zram_dynamic = ctk.BooleanVar(value=True)
        self.zram_size = ctk.IntVar(value=int(self.total_ram * 0.25))
        self.swap_enabled = ctk.BooleanVar(value=False)
        self.swap_size = ctk.IntVar(value=8192)
        self.compression_algo = ctk.StringVar(value="zstd")
        self.swappiness_var = ctk.IntVar(value=60)
        self.monitoring = True
        self.last_notification_time = 0
        self.last_temp_notification_time = 0
        self.last_gpu_notification_time = 0
        self.ram_alert_threshold = ctk.IntVar(value=90)
        self.ram_history = collections.deque([0]*60, maxlen=60)
        self.swap_history = collections.deque([0]*60, maxlen=60)
        self.temp_history = collections.deque([0]*60, maxlen=60)
        self.gpu_load_history = collections.deque([0]*60, maxlen=60)
        self.monitor_view_ref = None
        self.hardware_view_ref = None
        self.sidebar_compact = False
        self.is_mini_mode = False
        self.last_geometry = "1200x800"
        self.current_live_swappiness = 60
        self.current_live_epp = ""
        
        # Safety Mechanism & Custom Profiles
        self.lock_file = Path.home() / ".local" / "share" / "zram-swap-manager" / "app.lock"
        self.custom_profiles = {}
        self.undervolt_profiles = {}
        self.check_safe_mode()
        self.create_lock_file()
        
        # Hardware Vars
        self.cpu_limits = self.system_manager.get_cpu_freq_limits()
        self.available_freqs = self.system_manager.get_available_frequencies()
        self.available_governors = self.system_manager.get_available_governors()
        self.epp_supported = self.system_manager.check_epp_support()
        self.undervolt_tool = self.system_manager.check_undervolt_support()
        self.cpu_cap_percent = ctk.IntVar(value=100)
        self.auto_undervolt = ctk.BooleanVar(value=False)
        self.apply_uv_on_boot = ctk.BooleanVar(value=False)
        if self.undervolt_tool != "none":
            self.apply_uv_on_boot.set(self.system_manager.is_undervolt_service_enabled())
        self.temp_stats = {'min': 1000, 'max': 0}
        
        self.configure(fg_color=THEME["bg_main"])
        
        self.create_layout()
        self.bind("<Configure>", self.check_resize)
        self.load_preferences()
        self.check_current_status()
        self.start_monitoring()
        
    def create_layout(self):
        # Grid Layout: Col 0 = Sidebar, Col 1 = Content
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, fg_color=THEME["bg_sidebar"], width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1) # Spacer

        # Logo / Title
        self.logo_label = ctk.CTkLabel(self.sidebar, text="⚡ ZramPro", font=ctk.CTkFont(size=22, weight="bold"), text_color=THEME["accent"])
        self.logo_label.pack(pady=30)

        # Navigation Buttons
        self.nav_buttons = []
        self.create_nav_btn("📊 Monitor", MonitorView)
        self.create_nav_btn("⚡ Zram", ZramView)
        self.create_nav_btn("💾 Swapfile", SwapView)
        self.create_nav_btn("🎮 Hardware", HardwareView)
        self.create_nav_btn("⚙️ Avanzado", AdvancedView)
        
        # Mini Mode Button
        ctk.CTkButton(self.sidebar, text="📱 Modo Mini", command=self.toggle_mini_mode, fg_color=THEME["bg_card"], hover_color=THEME["accent"]).pack(side="bottom", pady=(0, 20), padx=20, fill="x")
        
        # Service Status Indicator
        self.service_status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.service_status_frame.pack(side="bottom", fill="x", pady=(0, 10), padx=20)
        
        self.service_dot = ctk.CTkLabel(self.service_status_frame, text="●", font=ctk.CTkFont(size=16), text_color="gray")
        self.service_dot.pack(side="left")
        
        self.service_label = ctk.CTkLabel(self.service_status_frame, text="Daemon: --", font=ctk.CTkFont(size=12), text_color=THEME["text_sec"])
        self.service_label.pack(side="left", padx=5)
        
        self.restart_service_btn = ctk.CTkButton(self.service_status_frame, text="↻", width=25, height=25, command=self.restart_daemon, fg_color=THEME["bg_card"], hover_color=THEME["accent"])
        self.restart_service_btn.pack(side="right")
        ToolTip(self.restart_service_btn, "Reiniciar servicio")

        # Save Button at bottom
        self.save_btn = ctk.CTkButton(self.sidebar, text="💾 Aplicar Cambios", command=self.apply_configuration, fg_color=THEME["success"], hover_color="#28a745")
        self.save_btn.pack(side="bottom", pady=20, padx=20, fill="x")

        # Content Area
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # Show default view
        self.show_view(MonitorView)

    def create_nav_btn(self, text, view_class):
        parts = text.split(' ', 1)
        icon = parts[0]
        
        btn = ctk.CTkButton(
            self.sidebar, 
            text=text, 
            command=lambda: self.show_view(view_class),
            fg_color="transparent", 
            text_color=THEME["text_sec"],
            hover_color=THEME["bg_card"],
            anchor="w",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        btn.pack(fill="x", padx=10, pady=2)
        self.nav_buttons.append({
            'btn': btn, 
            'view_class': view_class, 
            'text': text, 
            'icon': icon
        })

    def show_view(self, view_class):
        # Update buttons state
        for item in self.nav_buttons:
            btn = item['btn']
            v_cls = item['view_class']
            if v_cls == view_class:
                btn.configure(fg_color=THEME["bg_card"], text_color=THEME["text"])
            else:
                btn.configure(fg_color="transparent", text_color=THEME["text_sec"])
        
        # Clear content
        for widget in self.content_area.winfo_children():
            widget.destroy()
            
        # Create new view
        view = view_class(self.content_area, self)
        view.pack(fill="both", expand=True)
        
        # Reset references to avoid updating destroyed widgets
        self.monitor_view_ref = view if view_class == MonitorView else None
        self.hardware_view_ref = view if view_class == HardwareView else None

    def check_resize(self, event):
        if event.widget == self:
            if event.width < 900 and not self.sidebar_compact:
                self.set_sidebar_compact(True)
            elif event.width >= 900 and self.sidebar_compact:
                self.set_sidebar_compact(False)

    def set_sidebar_compact(self, compact):
        self.sidebar_compact = compact
        if compact:
            self.sidebar.configure(width=60)
            self.logo_label.configure(text="⚡")
            self.save_btn.configure(text="💾")
            for item in self.nav_buttons:
                item['btn'].configure(text=item['icon'], anchor="center")
        else:
            self.sidebar.configure(width=220)
            self.logo_label.configure(text="⚡ ZramPro")
            self.save_btn.configure(text="💾 Aplicar Cambios")
            for item in self.nav_buttons:
                item['btn'].configure(text=item['text'], anchor="w")

    def toggle_mini_mode(self):
        self.is_mini_mode = not self.is_mini_mode
        
        if self.is_mini_mode:
            self.show_view(MonitorView)
            self.last_geometry = self.geometry()
            self.sidebar.grid_remove()
            self.geometry("450x600")
            self.attributes('-topmost', True)
            
            if isinstance(self.monitor_view_ref, MonitorView):
                 self.monitor_view_ref.toggle_mini_mode(True)
        else:
            self.sidebar.grid()
            self.geometry(self.last_geometry)
            self.attributes('-topmost', False)
            
            if isinstance(self.monitor_view_ref, MonitorView):
                 self.monitor_view_ref.toggle_mini_mode(False)

    def restart_daemon(self):
        """Reinicia el servicio daemon."""
        def run():
            self.system_manager.restart_service()
        threading.Thread(target=run, daemon=True).start()

    def toggle_zram_controls(self):
        if hasattr(self, 'zram_content_frame') and self.zram_content_frame.winfo_exists():
            state = "normal" if self.zram_enabled.get() else "disabled"
            self.set_widget_state(self.zram_content_frame, state)
            
    def toggle_swap_controls(self):
        if hasattr(self, 'swap_content_frame') and self.swap_content_frame.winfo_exists():
            state = "normal" if self.swap_enabled.get() else "disabled"
            self.set_widget_state(self.swap_content_frame, state)
            
    def set_widget_state(self, widget, state):
        try:
            if hasattr(widget, 'configure'):
                widget.configure(state=state)
            for child in widget.winfo_children():
                self.set_widget_state(child, state)
        except: pass
            
    def update_zram_size_label(self, value):
        size = int(float(value))
        percent = (size / self.total_ram * 100)
        if hasattr(self, 'zram_size_label') and self.zram_size_label.winfo_exists():
            self.zram_size_label.configure(text=f"Tamaño: {size} MB ({percent:.1f}%)")
        
    def update_swap_size_label(self, value):
        if hasattr(self, 'swap_size_label') and self.swap_size_label.winfo_exists():
            self.swap_size_label.configure(text=f"Tamaño: {int(float(value))} MB")
        
    def update_swappiness_label(self, value):
        if hasattr(self, 'swappiness_label') and self.swappiness_label.winfo_exists():
            self.swappiness_label.configure(text=f"Swappiness: {int(float(value))}")
        
    def check_current_status(self):
        """Verifica el estado actual de zram y swap"""
        threading.Thread(target=self._check_status_thread, daemon=True).start()
        
    def _check_status_thread(self):
        status = self.system_manager.get_current_status()
        self.after(0, lambda: self.zram_enabled.set(status['zram_enabled']))
        self.after(0, lambda: self.swap_enabled.set(status['swapfile_enabled']))
        self.after(0, self.toggle_zram_controls)
        self.after(0, self.toggle_swap_controls)
            
    # --- Safety Mechanism ---
    def check_safe_mode(self):
        """Verifica si hubo un cierre inesperado y ofrece restaurar defaults."""
        if self.lock_file.exists():
            if messagebox.askyesno("Modo Seguro", "⚠️ La aplicación no se cerró correctamente.\n\n¿Deseas restaurar la configuración por defecto para asegurar la estabilidad del sistema?"):
                self.restore_defaults()
                self.save_preferences()
                logger.warning("Configuración restaurada por Modo Seguro tras crash detectado.")

    def create_lock_file(self):
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_file.touch()
        except Exception as e:
            logger.error(f"No se pudo crear archivo de bloqueo: {e}")

    def remove_lock_file(self):
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            logger.error(f"No se pudo eliminar archivo de bloqueo: {e}")

    # --- Hardware Control Methods ---
    def calibrate_cpu(self):
        """Restablece las frecuencias a los límites de hardware."""
        self.system_manager.set_cpu_min_freq(self.cpu_limits['min'])
        self.system_manager.set_cpu_max_freq(self.cpu_limits['max'])
        messagebox.showinfo("Calibración", "Frecuencias de CPU restablecidas a los valores de fábrica.")

    def set_manual_max_freq(self, freq_str):
        try:
            freq = int(freq_str)
            self.system_manager.set_cpu_max_freq(freq)
        except ValueError: pass
            
    def set_manual_min_freq(self, freq_str):
        try:
            freq = int(freq_str)
            self.system_manager.set_cpu_min_freq(freq)
        except ValueError: pass

    def apply_voltage_offset(self, value):
        """Aplica el offset de voltaje seleccionado."""
        offset = int(value)
        if messagebox.askyesno("⚠️ Advertencia de Seguridad", 
                               f"Estás a punto de aplicar un undervolt de {offset}mV.\n\nUn valor excesivo puede congelar el sistema.\n¿Deseas continuar?"):
            msg = self.system_manager.set_cpu_voltage_offset(offset)
            messagebox.showinfo("Undervolt", msg)

    def toggle_uv_on_boot(self):
        """Alterna la aplicación del undervolt al inicio."""
        self.system_manager.enable_undervolt_at_boot(self.apply_uv_on_boot.get())

    def save_uv_profile(self):
        """Guarda el perfil de undervolt actual."""
        if not hasattr(self, 'uv_slider'): return
        
        dialog = ctk.CTkInputDialog(text="Nombre del perfil UV:", title="Guardar Perfil Undervolt")
        name = dialog.get_input()
        if name:
            self.undervolt_profiles[name] = int(self.uv_slider.get())
            self.save_preferences()
            if self.hardware_view_ref:
                self.hardware_view_ref.update_uv_profiles_combo()
            messagebox.showinfo("Guardado", f"Perfil UV '{name}' guardado.")

    def load_uv_profile(self, name):
        """Carga un perfil de undervolt."""
        if name in self.undervolt_profiles:
            val = self.undervolt_profiles[name]
            if hasattr(self, 'uv_slider'):
                self.uv_slider.set(val)
                if hasattr(self, 'uv_label'):
                    self.uv_label.configure(text=f"Offset: {val} mV")
            self.apply_voltage_offset(val)

    def delete_uv_profile(self, name):
        """Elimina un perfil de undervolt."""
        if name in self.undervolt_profiles:
            del self.undervolt_profiles[name]
            self.save_preferences()
            if self.hardware_view_ref:
                self.hardware_view_ref.update_uv_profiles_combo()

    def test_undervolt_stability(self):
        """Ejecuta una prueba de estabilidad."""
        if messagebox.askyesno("Prueba de Estabilidad", "Se ejecutará una carga alta de CPU durante 10 segundos.\nSi el sistema se congela, reinicia forzosamente.\n\n¿Continuar?"):
            def run_test():
                success, res = self.system_manager.run_stress_test(10)
                icon = "info" if success else "warning"
                self.after(0, lambda: messagebox.showinfo("Resultado", res, icon=icon))
            
            threading.Thread(target=run_test, daemon=True).start()

    def run_progressive_undervolt(self):
        """Baja el voltaje paso a paso probando estabilidad."""
        if self.undervolt_tool == "none":
            messagebox.showerror("Error", "Herramienta de undervolt no detectada.")
            return

        if not messagebox.askyesno("Undervolt Progresivo", 
            "⚠️ ATENCIÓN: Este proceso bajará el voltaje paso a paso (-5mV) y probará la estabilidad.\n\n"
            "El sistema podría congelarse. Si eso ocurre, reinicia forzosamente.\n"
            "El modo seguro restaurará los valores al reiniciar.\n\n"
            "¿Continuar?"):
            return

        # Ventana de progreso
        prog_win = ctk.CTkToplevel(self)
        prog_win.title("Optimizando Voltaje")
        prog_win.geometry("400x150")
        prog_win.transient(self)
        prog_win.grab_set()
        
        lbl = ctk.CTkLabel(prog_win, text="Iniciando análisis...", font=ctk.CTkFont(size=14))
        lbl.pack(pady=20)

        self.progressive_uv_running = True
        def on_close_prog():
            self.progressive_uv_running = False
            prog_win.destroy()
        prog_win.protocol("WM_DELETE_WINDOW", on_close_prog)
        
        def process():
            step = -5
            limit = -125
            safe_offset = 0
            
            # Reset inicial
            self.system_manager.set_cpu_voltage_offset(0)
            
            for offset in range(step, limit - 1, step):
                if not self.progressive_uv_running: break
                
                self.after(0, lambda o=offset: lbl.configure(text=f"Probando estabilidad a {o} mV..."))
                self.system_manager.set_cpu_voltage_offset(offset)
                
                # Prueba corta de 5s
                success, _ = self.system_manager.run_stress_test(5)
                
                if not success:
                    self.after(0, lambda: lbl.configure(text="Inestabilidad detectada. Revertiendo..."))
                    time.sleep(1)
                    break
                
                safe_offset = offset
                self.after(0, lambda v=offset: self.uv_slider.set(v) if hasattr(self, 'uv_slider') and self.uv_slider.winfo_exists() else None)
                self.after(0, lambda v=offset: self.uv_label.configure(text=f"Offset: {v} mV") if hasattr(self, 'uv_label') and self.uv_label.winfo_exists() else None)

            self.system_manager.set_cpu_voltage_offset(safe_offset)
            if self.progressive_uv_running:
                self.after(0, lambda: prog_win.destroy())
            self.after(0, lambda: messagebox.showinfo("Finalizado", f"Proceso completado.\nLímite estable encontrado: {safe_offset} mV"))

        threading.Thread(target=process, daemon=True).start()

    def run_smart_undervolt(self):
        """
        Implementa una estrategia de 'Mejor Undervolt Seguro'.
        Aplica un offset conservador (-60mV) que suele ser estable en la mayoría de CPUs modernas,
        y ajusta el EPP para maximizar la eficiencia de ese voltaje.
        """
        if self.undervolt_tool == "none":
            messagebox.showerror("Error", "No se detectó herramienta de undervolt compatible (intel-undervolt).")
            return

        if messagebox.askyesno("Smart Undervolt", 
            "El sistema intentará aplicar el 'Mejor Undervolt Seguro'.\n\n"
            "Configuración:\n"
            "- Offset: -60mV (Sweet spot seguro)\n"
            "- EPP: Balance Power (Eficiencia)\n\n"
            "Esto reducirá temperaturas y consumo sin sacrificar rendimiento notable.\n"
            "¿Deseas proceder?"):
            
            res = self.system_manager.set_cpu_voltage_offset(-60)
            if self.epp_supported:
                self.system_manager.set_energy_performance_preference("balance_power")
                self.current_live_epp = "balance_power"
            
            if hasattr(self, 'uv_slider'): self.uv_slider.set(-60)
            if hasattr(self, 'uv_label'): self.uv_label.configure(text="Offset: -60 mV")
            
            messagebox.showinfo("Optimización Completada", f"{res}\nPerfil de energía ajustado a Eficiencia.")

    def on_cpu_slider_change(self, value):
        """Aplica el límite de frecuencia manualmente."""
        if self.auto_undervolt.get(): return # Ignorar si está en auto
        
        freq_khz = int(self.cpu_limits['min'] + (self.cpu_limits['max'] - self.cpu_limits['min']) * (value / 100))
        self.system_manager.set_cpu_max_freq(freq_khz)
        if hasattr(self, 'cpu_freq_label'):
            self.cpu_freq_label.configure(text=f"Límite Manual: {freq_khz//1000} MHz")

    def change_governor(self, governor):
        self.system_manager.set_cpu_governor(governor)
        logger.info(f"Gobernador cambiado a: {governor}")

    def toggle_boost(self):
        self.system_manager.set_cpu_boost(self.boost_switch.get())

    def toggle_undervolt(self):
        """Activa el modo de optimización energética (Undervolt Simulado)."""
        if self.auto_undervolt.get():
            # Activar: Desactivar boost, poner powersave/schedutil
            self.system_manager.set_cpu_boost(False)
            self.system_manager.set_energy_performance_preference("balance_power")
            if hasattr(self, 'boost_switch'): self.boost_switch.deselect()
            
            # El control fino lo hará el monitor loop
            logger.info("Undervolt Automático ACTIVADO")
            if hasattr(self, 'cpu_slider'): self.cpu_slider.configure(state="disabled")
            if hasattr(self, 'freq_max_combo'): self.freq_max_combo.configure(state="disabled")
            if hasattr(self, 'freq_min_combo'): self.freq_min_combo.configure(state="disabled")
            if hasattr(self, 'optimization_status_label'):
                self.optimization_status_label.configure(text="Iniciando IA...", text_color=THEME["accent"])
        else:
            # Desactivar: Restaurar
            self.system_manager.set_cpu_boost(True)
            if hasattr(self, 'boost_switch'): self.boost_switch.select()
            self.system_manager.set_energy_performance_preference("balance_performance")
            self.system_manager.set_cpu_max_freq(self.cpu_limits['max'])
            logger.info("Undervolt Automático DESACTIVADO")
            if hasattr(self, 'cpu_slider'): self.cpu_slider.configure(state="normal")
            if hasattr(self, 'freq_max_combo'): self.freq_max_combo.configure(state="normal")
            if hasattr(self, 'freq_min_combo'): self.freq_min_combo.configure(state="normal")
            if hasattr(self, 'optimization_status_label'):
                self.optimization_status_label.configure(text="")

    def apply_energy_profile(self, profile):
        """Aplica un perfil de energía predefinido."""
        if profile == "gaming":
            # Máximo rendimiento, sin ahorro
            self.system_manager.set_cpu_governor("performance")
            self.system_manager.set_cpu_boost(True)
            self.system_manager.set_cpu_max_freq(self.cpu_limits['max'])
            self.system_manager.set_energy_performance_preference("performance")
            self.swappiness_var.set(10) # Preferir RAM física
            self.auto_undervolt.set(False)
            
            if hasattr(self, 'boost_switch'): self.boost_switch.select()
            if hasattr(self, 'undervolt_switch'): self.undervolt_switch.deselect()
            if hasattr(self, 'cpu_slider'): 
                self.cpu_slider.configure(state="normal")
                self.cpu_slider.set(100)
            if hasattr(self, 'freq_max_combo') and self.available_freqs:
                self.freq_max_combo.set(str(self.available_freqs[0]))
            
        elif profile == "office":
            # Balanceado
            self.system_manager.set_cpu_governor("schedutil")
            self.system_manager.set_cpu_boost(True)
            self.system_manager.set_cpu_max_freq(self.cpu_limits['max'])
            self.system_manager.set_energy_performance_preference("balance_performance")
            self.swappiness_var.set(60)
            self.auto_undervolt.set(False)
            
            if hasattr(self, 'boost_switch'): self.boost_switch.select()
            if hasattr(self, 'undervolt_switch'): self.undervolt_switch.deselect()
            if hasattr(self, 'cpu_slider'): 
                self.cpu_slider.configure(state="normal")
                self.cpu_slider.set(100)
            if hasattr(self, 'freq_max_combo') and self.available_freqs:
                self.freq_max_combo.set(str(self.available_freqs[0]))

        elif profile == "eco":
            # Ahorro máximo
            self.system_manager.set_cpu_governor("powersave")
            self.system_manager.set_cpu_boost(False)
            self.system_manager.set_energy_performance_preference("power")
            self.swappiness_var.set(100) # Usar Zram agresivamente
            self.auto_undervolt.set(True) # Activar IA de undervolt
            
            if hasattr(self, 'boost_switch'): self.boost_switch.deselect()
            if hasattr(self, 'undervolt_switch'): self.undervolt_switch.select()
        
        self.system_manager.apply_live_tuning(self.swappiness_var.get(), 100)
        messagebox.showinfo("Perfil Aplicado", f"Se ha activado el perfil: {profile.upper()}")

    def open_backups_folder(self):
        """Abre la carpeta de backups del sistema."""
        backup_dir = "/var/backups/zram-swap-manager"
        if not os.path.exists(backup_dir):
            messagebox.showinfo("Backups", "Aún no se han generado backups.\nSe crearán al aplicar la primera configuración.")
            return
        
        try:
            subprocess.Popen(['xdg-open', backup_dir])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el explorador:\n{e}")

    # --- Custom Profiles ---
    def save_current_as_profile(self):
        dialog = ctk.CTkInputDialog(text="Nombre del perfil:", title="Guardar Perfil Personalizado")
        name = dialog.get_input()
        if name:
            # Capturar estado actual
            current_max_freq = self.cpu_limits['max']
            try:
                with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq", "r") as f:
                    current_max_freq = int(f.read().strip())
            except: pass

            gov = "schedutil"
            try:
                with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "r") as f:
                    gov = f.read().strip()
            except: pass

            profile_data = {
                'governor': gov,
                'boost': self.boost_switch.get() if hasattr(self, 'boost_switch') else True,
                'max_freq': current_max_freq,
                'swappiness': self.swappiness_var.get(),
                'auto_undervolt': self.auto_undervolt.get()
            }
            
            self.custom_profiles[name] = profile_data
            self.save_preferences()
            messagebox.showinfo("Perfil Guardado", f"Perfil '{name}' guardado correctamente.")
            
            if self.hardware_view_ref:
                self.hardware_view_ref.update_profiles_combo()

    def apply_custom_profile(self, name):
        if name in self.custom_profiles:
            data = self.custom_profiles[name]
            
            self.system_manager.set_cpu_governor(data.get('governor', 'schedutil'))
            self.system_manager.set_cpu_boost(data.get('boost', True))
            self.system_manager.set_cpu_max_freq(data.get('max_freq', self.cpu_limits['max']))
            
            self.swappiness_var.set(data.get('swappiness', 60))
            self.auto_undervolt.set(data.get('auto_undervolt', False))
            
            # Actualizar UI
            if hasattr(self, 'boost_switch'): 
                if data.get('boost', True): self.boost_switch.select()
                else: self.boost_switch.deselect()
            
            if hasattr(self, 'undervolt_switch'):
                if data.get('auto_undervolt', False): self.undervolt_switch.select()
                else: self.undervolt_switch.deselect()

            messagebox.showinfo("Perfil Aplicado", f"Perfil '{name}' aplicado.")

    def delete_custom_profile(self, name):
        if name in self.custom_profiles:
            del self.custom_profiles[name]
            self.save_preferences()
            if self.hardware_view_ref:
                self.hardware_view_ref.update_profiles_combo()

    def start_monitoring(self):
        """Inicia el monitoreo en tiempo real"""
        def monitor():
            while self.monitoring:
                try:
                    mem = psutil.virtual_memory()
                    swap = psutil.swap_memory()
                    cpu = psutil.cpu_percent(interval=None) # Non-blocking
                    available = mem.available / (1024**2)
                    used_percent = mem.percent
                    swap_percent = swap.percent
                    
                    # Hardware Stats
                    cpu_freq = psutil.cpu_freq()
                    cpu_freq_per_core = psutil.cpu_freq(percpu=True)
                    temps = psutil.sensors_temperatures()
                    gpu_stats = self.system_manager.get_gpu_stats()
                    cpu_voltage = self.system_manager.get_cpu_voltage()
                    service_active = self.system_manager.check_service_status()
                    
                    # Alerta GPU: Si hay carga (>50%) y la frecuencia es baja (<300MHz), posible throttling
                    gpu_throttling = gpu_stats['load'] > 50 and gpu_stats['freq'] < 300 and gpu_stats['freq'] > 0
                    gpu_color = THEME['danger'] if gpu_throttling else THEME['text']
                    
                    if gpu_throttling:
                        current_time = time.time()
                        if current_time - self.last_gpu_notification_time > 300:
                            self.system_manager.send_notification(
                                "⚠️ GPU Throttling Detectado",
                                f"Carga alta ({gpu_stats['load']}%) con frecuencia baja ({gpu_stats['freq']} MHz).\nVerifique temperaturas."
                            )
                            self.last_gpu_notification_time = current_time
                    
                    # Extraer temperatura actual para el predictor
                    cur_temp = 0
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'k10temp' in name.lower() or 'core' in name.lower():
                            cur_temp = entries[0].current
                            break
                    
                    self.predictor.update(used_percent, cpu)
                    
                    # Calcular valores de IA para visualización (y uso posterior)
                    predicted_ram = self.predictor.predict_next_minute_ram()
                    opt_swappiness = self.predictor.get_optimal_swappiness(self.swappiness_var.get())
                    opt_cache = self.predictor.get_optimal_cache_pressure()
                    
                    self.ram_history.append(used_percent)
                    self.swap_history.append(swap_percent)
                    self.gpu_load_history.append(gpu_stats['load'])
                    
                    # --- Update MonitorView ---
                    if self.monitor_view_ref:
                        temp_text = f"{cur_temp}°C" if cur_temp > 0 else "--"
                        temp_color = THEME['danger'] if cur_temp > 85 else THEME['accent']
                        gpu_text = f"{gpu_stats['freq']} MHz" if gpu_stats['freq'] > 0 else "--"
                        if gpu_stats['load'] > 0: gpu_text += f" ({gpu_stats['load']}%)"
                        
                        monitor_data = {
                            'ram_available': available,
                            'zram_effective': self.zram_size.get() * (2.8 if self.zram_dynamic.get() else 2.5),
                            'compression_ratio': 2.8 if self.zram_dynamic.get() else 2.5,
                            'cpu_percent': cpu,
                            'predicted_ram': predicted_ram,
                            'opt_swappiness': opt_swappiness,
                            'opt_cache': opt_cache,
                            'temp_text': temp_text,
                            'temp_color': temp_color,
                            'gpu_text': gpu_text,
                            'gpu_color': gpu_color,
                            'cpu_freq_per_core': cpu_freq_per_core,
                            'ram_history': self.ram_history,
                            'swap_history': self.swap_history,
                            'gpu_history': self.gpu_load_history
                        }
                        self.after(0, lambda: self.monitor_view_ref.update_stats(monitor_data) if self.monitor_view_ref else None)

                    # --- Update Hardware View ---
                    opt_status = ""
                    opt_status_color = THEME["text"]
                    if hasattr(self, 'optimization_status_label'):
                        opt_status = self.optimization_status_label.cget("text")
                        opt_status_color = self.optimization_status_label.cget("text_color")

                    if cur_temp > 0:
                        self.temp_stats['min'] = min(self.temp_stats['min'], cur_temp)
                        self.temp_stats['max'] = max(self.temp_stats['max'], cur_temp)
                        self.temp_history.append(cur_temp)
                        
                        if self.hardware_view_ref:
                            gpu_text = f"{gpu_stats['freq']} MHz" if gpu_stats['freq'] > 0 else "--"
                            hw_data = {
                                'cur_temp': cur_temp,
                                'temp_color': THEME['danger'] if cur_temp > 80 else THEME['text'],
                                'temp_min': self.temp_stats['min'],
                                'temp_max': self.temp_stats['max'],
                                'temp_history': self.temp_history,
                                'cpu_freq_current': cpu_freq.current if cpu_freq else 0,
                                'cpu_voltage': cpu_voltage,
                                'opt_status': opt_status,
                                'opt_status_color': opt_status_color,
                                'gpu_text': gpu_text,
                                'gpu_color': gpu_color
                            }
                            self.after(0, lambda: self.hardware_view_ref.update_stats(hw_data) if self.hardware_view_ref else None)
                        
                        # Alerta de Temperatura Alta (> 85°C)
                        if cur_temp > 85:
                            current_time = time.time()
                            if current_time - self.last_temp_notification_time > 300:  # 5 minutos de enfriamiento
                                self.system_manager.send_notification(
                                    "🔥 Temperatura Crítica",
                                    f"La CPU ha alcanzado {cur_temp}°C.\nSe recomienda reducir la carga o verificar la refrigeración."
                                )
                                self.last_temp_notification_time = current_time

                    # Service Status
                    if hasattr(self, 'service_label') and self.service_label.winfo_exists():
                        color = THEME["success"] if service_active else THEME["danger"]
                        text = "Daemon: Activo" if service_active else "Daemon: Inactivo"
                        self.after(0, lambda: self.service_dot.configure(text_color=color))
                        self.after(0, lambda: self.service_label.configure(text=text))

                    # --- Lógica de Undervolt Automático ---
                    if self.auto_undervolt.get():
                        # Sugerir límite basado en carga de CPU (LightweightPredictor)
                        # Si la carga es baja, bajamos el techo de frecuencia para forzar P-states bajos (menos voltaje)
                        target_cap_percent = self.predictor.suggest_cpu_cap(cpu, cur_temp)
                        target_freq = int(self.cpu_limits['min'] + (self.cpu_limits['max'] - self.cpu_limits['min']) * (target_cap_percent / 100))
                        self.system_manager.set_cpu_max_freq(target_freq)
                        self.after(0, lambda: self.cpu_slider.set(target_cap_percent) if hasattr(self, 'cpu_slider') else None)
                        
                        # Actualizar etiqueta de estado de optimización
                        if hasattr(self.hardware_view_ref, 'optimization_status_label') and self.hardware_view_ref.optimization_status_label.winfo_exists():
                            status_text = f"⚡ IA Activa: Cap {target_cap_percent}% ({target_freq//1000} MHz)" # This is just for internal state, UI updated via update_stats
                            self.after(0, lambda: self.hardware_view_ref.optimization_status_label.configure(text=status_text, text_color=THEME["success"]))
                        
                        # Ajuste dinámico de EPP (Energy Performance Preference)
                        if self.epp_supported:
                            target_epp = self.predictor.suggest_epp(cpu)
                            if target_epp != self.current_live_epp:
                                self.system_manager.set_energy_performance_preference(target_epp)
                                self.current_live_epp = target_epp
                    
                    # Sistema de Notificaciones de RAM Crítica
                    if used_percent > self.ram_alert_threshold.get():
                        current_time = time.time()
                        if current_time - self.last_notification_time > 300:  # 5 minutos de enfriamiento
                            self.system_manager.send_notification(
                                "⚠️ Memoria Crítica",
                                f"El uso de RAM ha alcanzado el {used_percent}%.\nEl sistema podría volverse inestable."
                            )
                            self.last_notification_time = current_time
                    
                    # --- Optimización Dinámica (AI/Heurística) ---
                    if self.zram_dynamic.get():
                        # Aplicar solo si hay un cambio significativo (evitar thrashing)
                        if abs(opt_swappiness - self.current_live_swappiness) > 5:
                            self.system_manager.apply_live_tuning(opt_swappiness, opt_cache)
                            self.current_live_swappiness = opt_swappiness
                    
                    # Ajuste dinámico de Zram
                    if self.zram_enabled.get() and self.zram_dynamic.get():
                        if used_percent > 70:
                            new_size = int(self.total_ram * 0.35)
                        elif used_percent > 50:
                            new_size = int(self.total_ram * 0.25)
                        else:
                            new_size = int(self.total_ram * 0.20)
                        
                        self.after(0, lambda s=new_size: self.zram_size.set(s))
                        self.after(0, lambda s=new_size: self.update_zram_size_label(s))
                    
                    
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Error en el hilo de monitoreo: {e}")
                    time.sleep(5) # Esperar antes de reintentar si hay error
                
        threading.Thread(target=monitor, daemon=True).start()
        
    def get_detailed_monitor_info(self):
        """Genera la información detallada del monitor"""
        info = f"""
{'='*60}
ESTADO DEL SISTEMA
{'='*60}

Memoria RAM:
  Total: {int(self.total_ram)} MB
  Disponible: {int(psutil.virtual_memory().available / (1024**2))} MB
  Uso: {psutil.virtual_memory().percent}%

"""     
        monitor_data = self.system_manager.get_live_monitor_data()
        info += monitor_data['zram_info']
        info += monitor_data['swap_info']
        return info
        
    def run_command(self, command):
        """Ejecuta un comando y muestra el resultado"""
        def do_run():
            output = self.system_manager.run_shell_command(command)
            if hasattr(self, 'command_output') and self.command_output.winfo_exists():
                self.after(0, lambda: self.command_output.delete("1.0", "end"))
                self.after(0, lambda: self.command_output.insert("1.0", output))
        threading.Thread(target=do_run, daemon=True).start()
        
    def drop_caches(self):
        """Ejecuta el proceso de limpieza de caché."""
        if messagebox.askyesno("Limpiar Caché", "¿Estás seguro de que deseas limpiar la caché del sistema?\n\nEsto liberará RAM inmediatamente, pero el sistema podría ir un poco más lento momentáneamente mientras reconstruye la caché necesaria."):
            script = """#!/bin/bash
echo "🧹 Limpiando caché del sistema..."
sync
echo 3 > /proc/sys/vm/drop_caches
echo "✅ Caché liberada correctamente."
echo ""
free -h
"""
            self.execute_script(script)

    def apply_configuration(self):
        """Aplica la configuración de Zram y Swap"""
        # Crear ventana de confirmación
        confirm_window = ctk.CTkToplevel(self)
        confirm_window.title("Confirmar Configuración")
        confirm_window.geometry("700x600")
        confirm_window.transient(self)
        
        # Centrar ventana
        confirm_window.update_idletasks()
        x = (confirm_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (confirm_window.winfo_screenheight() // 2) - (600 // 2)
        confirm_window.geometry(f"700x600+{x}+{y}")
        
        # Esperar a que la ventana sea visible antes de grab_set
        confirm_window.wait_visibility()
        confirm_window.grab_set()
        
        # Header
        header = ctk.CTkFrame(confirm_window, fg_color=THEME['accent'])
        header.pack(fill="x")
        
        ctk.CTkLabel(
            header,
            text="⚠️ Revisar Configuración",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=15)
        
        # Script preview
        script_frame = ctk.CTkFrame(confirm_window, fg_color="transparent")
        script_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            script_frame,
            text="Script que se ejecutará:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 10))
        
        config = {
            'zram_enabled': self.zram_enabled.get(),
            'zram_size': self.zram_size.get(),
            'compression_algo': self.compression_algo.get(),
            'swap_enabled': self.swap_enabled.get(),
            'swap_location': self.swap_location.get(),
            'swap_size': self.swap_size.get(),
            'swappiness': self.swappiness_var.get()
        }
        script = self.system_manager.generate_configuration_script(config)
        
        textbox = ctk.CTkTextbox(
            script_frame,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=THEME['bg_card']
        )
        textbox.pack(fill="both", expand=True)
        textbox.insert("1.0", script)
        textbox.configure(state="disabled")
        
        # Botones
        btn_frame = ctk.CTkFrame(confirm_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def on_apply():
            confirm_window.grab_release()
            confirm_window.destroy()
            self.execute_script(script)
            
        def on_cancel():
            confirm_window.grab_release()
            confirm_window.destroy()
        
        # Permitir cerrar con la X de la ventana
        confirm_window.protocol("WM_DELETE_WINDOW", on_cancel)
            
        ctk.CTkButton(
            btn_frame,
            text="✅ Aplicar Configuración",
            command=on_apply,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=THEME['success'],
            hover_color="#059669"
        ).pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="❌ Cancelar",
            command=on_cancel,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=THEME['warning'],
            hover_color="#d97706"
        ).pack(side="left", expand=True, fill="x")
        
    def execute_script(self, script):
        """Ejecuta el script de configuración"""
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Aplicando Configuración")
        progress_window.geometry("500x300")
        progress_window.transient(self)
        
        # Centrar
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (250)
        y = (progress_window.winfo_screenheight() // 2) - (150)
        progress_window.geometry(f"500x300+{x}+{y}")
        
        # Esperar a que la ventana sea visible antes de grab_set
        progress_window.wait_visibility()
        progress_window.grab_set()
        
        ctk.CTkLabel(
            progress_window,
            text="⚙️ Ejecutando configuración...",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=30)
        
        progress = ctk.CTkProgressBar(progress_window, mode="indeterminate")
        progress.pack(pady=20, padx=40, fill="x")
        progress.start()
        
        status_label = ctk.CTkLabel(
            progress_window,
            text="Guardando script...",
            font=ctk.CTkFont(size=12)
        )
        status_label.pack(pady=10)
        
        # Prevenir cierre accidental durante la ejecución
        progress_window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        def execute():
            try:
                def status_callback(message):
                    progress_window.after(0, lambda: status_label.configure(text=message))
                
                result = self.system_manager.execute_script_with_privileges(script, status_callback)
                
                def cleanup_and_show_result():
                    progress.stop()
                    progress_window.grab_release()
                    progress_window.destroy()
                    
                    if isinstance(result, subprocess.CompletedProcess):
                        if result.returncode == 0:
                            self.show_result_dialog(
                                "✅ Configuración Aplicada",
                                "La configuración se aplicó correctamente.\n\nSalida:\n" + result.stdout,
                                "success"
                            )
                            self.update_monitor()
                        else:
                            self.show_result_dialog(
                                "❌ Error al Aplicar",
                                f"Hubo un error al aplicar la configuración.\n\nError:\n{result.stderr}",
                                "error"
                            )
                    elif result == "TIMEOUT":
                        self.show_result_dialog(
                            "⏱️ Tiempo Agotado",
                            "La operación tardó demasiado tiempo.",
                            "warning"
                        )
                    else:
                        self.show_result_dialog(
                            "❌ Error Inesperado",
                            f"Ocurrió un error inesperado:\n{str(result)}",
                            "error"
                        )
                self.after(0, cleanup_and_show_result)
            except Exception as e: # Captura de errores en el hilo mismo
                logger.error(f"Excepción no controlada en hilo de ejecución: {e}")
                self.after(0, lambda: self.show_result_dialog("❌ Error de Hilo", str(e), "error"))
                
        threading.Thread(target=execute, daemon=True).start()
        
    def show_result_dialog(self, title, message, dialog_type="info"):
        """Muestra diálogo de resultado"""
        result_window = ctk.CTkToplevel(self)
        result_window.title(title)
        result_window.geometry("600x400")
        result_window.transient(self)
        
        # Centrar
        result_window.update_idletasks()
        x = (result_window.winfo_screenwidth() // 2) - (300)
        y = (result_window.winfo_screenheight() // 2) - (200)
        result_window.geometry(f"600x400+{x}+{y}")
        
        # Esperar a que la ventana sea visible antes de grab_set
        result_window.wait_visibility()
        result_window.grab_set()
        
        color = {
            "success": THEME['success'],
            "error": THEME['danger'],
            "warning": THEME['warning'],
            "info": THEME['accent']
        }.get(dialog_type, THEME['accent'])
        
        header = ctk.CTkFrame(result_window, fg_color=color)
        header.pack(fill="x")
        
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=15)
        
        textbox = ctk.CTkTextbox(
            result_window,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=THEME['bg_card']
        )
        textbox.pack(fill="both", expand=True, padx=20, pady=20)
        textbox.insert("1.0", message)
        textbox.configure(state="disabled")
        
        def close_dialog():
            result_window.grab_release()
            result_window.destroy()
        
        ctk.CTkButton(
            result_window,
            text="Cerrar",
            command=close_dialog,
            height=40,
            fg_color=color
        ).pack(pady=20, padx=20, fill="x")
        
        # Permitir cerrar con la X de la ventana
        result_window.protocol("WM_DELETE_WINDOW", close_dialog)
        
    def load_preferences(self):
        """Carga las preferencias del usuario desde un archivo JSON."""
        config_dir = Path.home() / ".config" / "zram-swap-manager"
        config_file = config_dir / "preferences.json"
        
        if not config_file.exists():
            return

        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            if 'zram_size' in data: self.zram_size.set(data['zram_size'])
            if 'zram_dynamic' in data: self.zram_dynamic.set(data['zram_dynamic'])
            if 'swap_size' in data: self.swap_size.set(data['swap_size'])
            if 'compression_algo' in data: self.compression_algo.set(data['compression_algo'])
            if 'swappiness' in data: self.swappiness_var.set(data['swappiness'])
            if 'ram_alert_threshold' in data: self.ram_alert_threshold.set(data['ram_alert_threshold'])
            if 'custom_profiles' in data: self.custom_profiles = data['custom_profiles']
            if 'undervolt_profiles' in data: self.undervolt_profiles = data['undervolt_profiles']
            
            # Actualizar UI
            self.update_zram_size_label(self.zram_size.get())
            self.update_swap_size_label(self.swap_size.get())
            self.update_swappiness_label(self.swappiness_var.get())
            if hasattr(self, 'alert_label'):
                self.alert_label.configure(text=f"{self.ram_alert_threshold.get()}%")

            if 'swap_location' in data and hasattr(self, 'swap_location'):
                self.swap_location.delete(0, "end")
                self.swap_location.insert(0, data['swap_location'])
                
            logger.info("Preferencias cargadas correctamente.")
        except Exception as e:
            logger.error(f"Error al cargar preferencias: {e}")

    def restore_defaults(self):
        """Restaura las preferencias a sus valores por defecto."""
        if messagebox.askyesno("Restaurar Defaults", "¿Estás seguro de que quieres restaurar la configuración por defecto?"):
            self.zram_enabled.set(False)
            self.zram_dynamic.set(True)
            self.zram_size.set(int(self.total_ram * 0.25))
            self.swap_enabled.set(False)
            self.swap_size.set(8192)
            self.compression_algo.set("zstd")
            self.swappiness_var.set(60)
            self.ram_alert_threshold.set(90)
            
            if hasattr(self, 'swap_location'):
                self.swap_location.delete(0, "end")
                self.swap_location.insert(0, "/swapfile")
            
            # Actualizar UI
            self.update_zram_size_label(self.zram_size.get())
            self.update_swap_size_label(self.swap_size.get())
            self.update_swappiness_label(self.swappiness_var.get())
            if hasattr(self, 'alert_label'):
                self.alert_label.configure(text=f"{self.ram_alert_threshold.get()}%")
            
            self.toggle_zram_controls()
            self.toggle_swap_controls()
            self.save_preferences()
            logger.info("Preferencias restauradas a valores por defecto.")

    def save_preferences(self):
        """Guarda las preferencias actuales en un archivo JSON."""
        config_dir = Path.home() / ".config" / "zram-swap-manager"
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "preferences.json"
            
            data = {
                'custom_profiles': self.custom_profiles,
                'undervolt_profiles': self.undervolt_profiles,
                'zram_size': self.zram_size.get(),
                'zram_dynamic': self.zram_dynamic.get(),
                'swap_size': self.swap_size.get(),
                'compression_algo': self.compression_algo.get(),
                'swappiness': self.swappiness_var.get(),
                'ram_alert_threshold': self.ram_alert_threshold.get(),
                'swap_location': self.swap_location.get() if hasattr(self, 'swap_location') else "/swapfile"
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Preferencias guardadas en {config_file}")
        except Exception as e:
            logger.error(f"Error al guardar preferencias: {e}")

    def on_closing(self):
        self.save_preferences()
        self.remove_lock_file()
        logger.info("Cerrando aplicación...")
        self.monitoring = False
        self.destroy()

def main():
    logger.info("Iniciando Zram & Swap Manager Pro")
    app = ZramSwapManager()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()
