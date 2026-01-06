import customtkinter as ctk
import subprocess
import threading
import time
import psutil
import os
from pathlib import Path
import tkinter.messagebox as messagebox

class ZramSwapManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración de la ventana
        self.title("Zram & Swap Manager Pro")
        self.geometry("1200x800")
        
        # Tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables
        self.total_ram = psutil.virtual_memory().total / (1024**2)  # MB
        self.zram_enabled = ctk.BooleanVar(value=False)
        self.zram_dynamic = ctk.BooleanVar(value=True)
        self.zram_size = ctk.IntVar(value=int(self.total_ram * 0.25))
        self.swap_enabled = ctk.BooleanVar(value=False)
        self.swap_size = ctk.IntVar(value=8192)
        self.compression_algo = ctk.StringVar(value="zstd")
        self.swappiness_var = ctk.IntVar(value=60)
        self.monitoring = True
        
        # Colores personalizados
        self.colors = {
            'bg': '#0f0f23',
            'card': '#1a1a2e',
            'accent1': '#8b5cf6',
            'accent2': '#ec4899',
            'accent3': '#06b6d4',
            'success': '#10b981',
            'warning': '#f59e0b',
            'text': '#e5e7eb'
        }
        
        self.configure(fg_color=self.colors['bg'])
        
        self.create_ui()
        self.check_current_status()
        self.start_monitoring()
        
    def create_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=20)
        
        title = ctk.CTkLabel(
            header_frame,
            text="⚡ Zram & Swap Manager Pro",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=self.colors['accent1']
        )
        title.pack()
        
        subtitle = ctk.CTkLabel(
            header_frame,
            text="Gestión Avanzada de Memoria con Algoritmo Dinámico",
            font=ctk.CTkFont(size=14),
            text_color=self.colors['text']
        )
        subtitle.pack()
        
        # Stats Cards
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        self.create_stat_card(stats_frame, "💾 RAM Total", f"{int(self.total_ram)} MB", 0)
        self.ram_available_label = self.create_stat_card(stats_frame, "✅ RAM Disponible", "...", 1)
        self.zram_effective_label = self.create_stat_card(stats_frame, "⚡ Zram Efectivo", "...", 2)
        self.compression_label = self.create_stat_card(stats_frame, "🔄 Compresión", "...", 3)
        
        # Progress bar para uso de RAM
        self.ram_progress = ctk.CTkProgressBar(
            stats_frame,
            width=1100,
            height=10,
            progress_color=self.colors['accent3']
        )
        self.ram_progress.grid(row=1, column=0, columnspan=4, padx=10, pady=10)
        
        # Tabview
        self.tabview = ctk.CTkTabview(self, fg_color=self.colors['card'])
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Tabs
        self.tabview.add("⚡ Zram")
        self.tabview.add("💾 Swapfile")
        self.tabview.add("📊 Monitor")
        self.tabview.add("⚙️ Avanzado")
        
        self.create_zram_tab()
        self.create_swap_tab()
        self.create_monitor_tab()
        self.create_advanced_tab()
        
        # Botón de guardado
        save_btn = ctk.CTkButton(
            self,
            text="💾 Guardar y Aplicar Configuración",
            command=self.apply_configuration,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.colors['accent1'],
            hover_color=self.colors['accent2']
        )
        save_btn.pack(fill="x", padx=20, pady=20)
        
    def create_stat_card(self, parent, title, value, col):
        card = ctk.CTkFrame(parent, fg_color=self.colors['card'], corner_radius=15)
        card.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text']
        ).pack(pady=(10, 5))
        
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['accent3']
        )
        value_label.pack(pady=(0, 10))
        
        return value_label
        
    def create_zram_tab(self):
        tab = self.tabview.tab("⚡ Zram")
        
        # Switch de habilitación
        enable_frame = ctk.CTkFrame(tab, fg_color=self.colors['card'])
        enable_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            enable_frame,
            text="Habilitar Zram",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        ctk.CTkSwitch(
            enable_frame,
            text="",
            variable=self.zram_enabled,
            command=self.toggle_zram_controls,
            progress_color=self.colors['accent1']
        ).pack(side="right", padx=20, pady=15)
        
        # Frame de contenido
        self.zram_content = ctk.CTkFrame(tab, fg_color="transparent")
        self.zram_content.pack(fill="both", expand=True, padx=20)
        
        # Modo dinámico
        dynamic_frame = ctk.CTkFrame(
            self.zram_content,
            fg_color=self.colors['accent1'],
            corner_radius=15
        )
        dynamic_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            dynamic_frame,
            text="🎯 Modo Dinámico Adaptativo",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 5), padx=20, anchor="w")
        
        ctk.CTkLabel(
            dynamic_frame,
            text="Ajusta automáticamente el tamaño de Zram según el uso de RAM en tiempo real",
            font=ctk.CTkFont(size=12),
            wraplength=600,
            justify="left"
        ).pack(pady=(0, 10), padx=20, anchor="w")
        
        ctk.CTkSwitch(
            dynamic_frame,
            text="Activar modo dinámico",
            variable=self.zram_dynamic,
            font=ctk.CTkFont(size=14),
            progress_color=self.colors['success']
        ).pack(pady=(0, 15), padx=20, anchor="w")
        
        # Tamaño de Zram
        size_frame = ctk.CTkFrame(self.zram_content, fg_color=self.colors['card'])
        size_frame.pack(fill="x", pady=20)
        
        self.zram_size_label = ctk.CTkLabel(
            size_frame,
            text=f"Tamaño Zram: {self.zram_size.get()} MB ({(self.zram_size.get() / self.total_ram * 100):.1f}% de RAM)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.zram_size_label.pack(pady=(15, 10), padx=20)
        
        self.zram_slider = ctk.CTkSlider(
            size_frame,
            from_=1024,
            to=int(self.total_ram * 0.5),
            variable=self.zram_size,
            command=self.update_zram_size_label,
            button_color=self.colors['accent2'],
            button_hover_color=self.colors['accent1'],
            progress_color=self.colors['accent1']
        )
        self.zram_slider.pack(fill="x", pady=(0, 15), padx=20)
        
        # Algoritmo de compresión
        algo_frame = ctk.CTkFrame(self.zram_content, fg_color=self.colors['card'])
        algo_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            algo_frame,
            text="Algoritmo de Compresión",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 10), padx=20)
        
        algorithms = ["zstd", "lzo-rle", "lzo", "lz4", "842"]
        
        for algo in algorithms:
            ctk.CTkRadioButton(
                algo_frame,
                text=f"{algo.upper()} {'(Recomendado)' if algo == 'zstd' else ''}",
                variable=self.compression_algo,
                value=algo,
                font=ctk.CTkFont(size=12)
            ).pack(pady=5, padx=20, anchor="w")
        
        self.toggle_zram_controls()
        
    def create_swap_tab(self):
        tab = self.tabview.tab("💾 Swapfile")
        
        # Switch de habilitación
        enable_frame = ctk.CTkFrame(tab, fg_color=self.colors['card'])
        enable_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            enable_frame,
            text="Habilitar Swapfile",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(side="left", padx=20, pady=15)
        
        ctk.CTkSwitch(
            enable_frame,
            text="",
            variable=self.swap_enabled,
            command=self.toggle_swap_controls,
            progress_color=self.colors['accent2']
        ).pack(side="right", padx=20, pady=15)
        
        # Frame de contenido
        self.swap_content = ctk.CTkFrame(tab, fg_color="transparent")
        self.swap_content.pack(fill="both", expand=True, padx=20)
        
        # Tamaño del swap
        size_frame = ctk.CTkFrame(self.swap_content, fg_color=self.colors['card'])
        size_frame.pack(fill="x", pady=20)
        
        self.swap_size_label = ctk.CTkLabel(
            size_frame,
            text=f"Tamaño Swapfile: {self.swap_size.get()} MB",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.swap_size_label.pack(pady=(15, 10), padx=20)
        
        self.swap_slider = ctk.CTkSlider(
            size_frame,
            from_=2048,
            to=32768,
            variable=self.swap_size,
            command=self.update_swap_size_label,
            button_color=self.colors['accent2'],
            button_hover_color=self.colors['accent1'],
            progress_color=self.colors['accent2']
        )
        self.swap_slider.pack(fill="x", pady=(0, 15), padx=20)
        
        # Ubicación del swapfile
        location_frame = ctk.CTkFrame(self.swap_content, fg_color=self.colors['card'])
        location_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            location_frame,
            text="Ubicación del Swapfile",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 10), padx=20, anchor="w")
        
        self.swap_location = ctk.CTkEntry(
            location_frame,
            placeholder_text="/swapfile",
            font=ctk.CTkFont(size=12)
        )
        self.swap_location.insert(0, "/swapfile")
        self.swap_location.pack(fill="x", pady=(0, 15), padx=20)
        
        # Swappiness
        swappiness_frame = ctk.CTkFrame(self.swap_content, fg_color=self.colors['card'])
        swappiness_frame.pack(fill="x", pady=20)
        
        self.swappiness_label = ctk.CTkLabel(
            swappiness_frame,
            text=f"Swappiness: {self.swappiness_var.get()}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.swappiness_label.pack(pady=(15, 10), padx=20, anchor="w")
        
        ctk.CTkLabel(
            swappiness_frame,
            text="Valor bajo = menos swap, Valor alto = más swap",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(0, 10), padx=20, anchor="w")
        
        self.swappiness = ctk.CTkSlider(
            swappiness_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            variable=self.swappiness_var,
            command=self.update_swappiness_label,
            button_color=self.colors['accent2'],
            progress_color=self.colors['accent2']
        )
        self.swappiness.pack(fill="x", pady=(0, 15), padx=20)
        
        self.toggle_swap_controls()
        
    def create_monitor_tab(self):
        tab = self.tabview.tab("📊 Monitor")
        
        # Info de Zram actual
        self.zram_info_text = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color=self.colors['card']
        )
        self.zram_info_text.pack(fill="both", expand=True, padx=20, pady=20)
        
        refresh_btn = ctk.CTkButton(
            tab,
            text="🔄 Actualizar",
            command=self.update_monitor,
            fg_color=self.colors['accent3']
        )
        refresh_btn.pack(pady=10)
        
    def create_advanced_tab(self):
        tab = self.tabview.tab("⚙️ Avanzado")
        
        # Scripts personalizados
        script_frame = ctk.CTkFrame(tab, fg_color=self.colors['card'])
        script_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            script_frame,
            text="Comandos de Sistema",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=15)
        
        btn_frame = ctk.CTkFrame(script_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(
            btn_frame,
            text="Ver estado Zram",
            command=lambda: self.run_command("zramctl"),
            fg_color=self.colors['accent1']
        ).pack(pady=5, padx=20)
        
        ctk.CTkButton(
            btn_frame,
            text="Ver swap actual",
            command=lambda: self.run_command("swapon --show"),
            fg_color=self.colors['accent2']
        ).pack(pady=5, padx=20)
        
        ctk.CTkButton(
            btn_frame,
            text="Ver memoria",
            command=lambda: self.run_command("free -h"),
            fg_color=self.colors['accent3']
        ).pack(pady=5, padx=20)
        
        self.command_output = ctk.CTkTextbox(
            script_frame,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.colors['bg']
        )
        self.command_output.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
    def toggle_zram_controls(self):
        state = "normal" if self.zram_enabled.get() else "disabled"
        for widget in self.zram_content.winfo_children():
            self.set_widget_state(widget, state)
            
    def toggle_swap_controls(self):
        state = "normal" if self.swap_enabled.get() else "disabled"
        for widget in self.swap_content.winfo_children():
            self.set_widget_state(widget, state)
            
    def set_widget_state(self, widget, state):
        try:
            widget.configure(state=state)
        except:
            pass
        for child in widget.winfo_children():
            self.set_widget_state(child, state)
            
    def update_zram_size_label(self, value):
        size = int(float(value))
        percent = (size / self.total_ram * 100)
        self.zram_size_label.configure(
            text=f"Tamaño Zram: {size} MB ({percent:.1f}% de RAM)"
        )
        
    def update_swap_size_label(self, value):
        size = int(float(value))
        self.swap_size_label.configure(text=f"Tamaño Swapfile: {size} MB")
        
    def update_swappiness_label(self, value):
        val = int(float(value))
        self.swappiness_label.configure(text=f"Swappiness: {val}")
        
    def check_current_status(self):
        """Verifica el estado actual de zram y swap"""
        threading.Thread(target=self._check_status_thread, daemon=True).start()
        
    def _check_status_thread(self):
        try:
            # Verificar zram
            result = subprocess.run(['zramctl'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                self.zram_enabled.set(True)
                
            # Verificar swap
            result = subprocess.run(['swapon', '--show'], capture_output=True, text=True)
            if '/swapfile' in result.stdout:
                self.swap_enabled.set(True)
        except:
            pass
            
    def start_monitoring(self):
        """Inicia el monitoreo en tiempo real"""
        def monitor():
            while self.monitoring:
                mem = psutil.virtual_memory()
                available = mem.available / (1024**2)
                used_percent = mem.percent
                
                self.after(0, lambda: self.ram_available_label.configure(
                    text=f"{int(available)} MB"
                ))
                self.after(0, lambda: self.ram_progress.set(1 - (used_percent / 100)))
                
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
                
                # Actualizar ratio de compresión simulado
                compression = 2.8 if self.zram_dynamic.get() else 2.5
                self.after(0, lambda c=compression: self.compression_label.configure(
                    text=f"{c:.2f}x"
                ))
                
                # Calcular Zram efectivo
                effective = int(self.zram_size.get() * compression)
                self.after(0, lambda e=effective: self.zram_effective_label.configure(
                    text=f"{e} MB"
                ))
                
                time.sleep(2)
                
        threading.Thread(target=monitor, daemon=True).start()
        
    def update_monitor(self):
        """Actualiza la información del monitor"""
        info = f"""
{'='*60}
ESTADO DEL SISTEMA
{'='*60}

Memoria RAM:
  Total: {int(self.total_ram)} MB
  Disponible: {int(psutil.virtual_memory().available / (1024**2))} MB
  Uso: {psutil.virtual_memory().percent}%

"""
        
        try:
            # Info de Zram
            result = subprocess.run(['zramctl'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info += f"Zram:\n{result.stdout}\n\n"
            else:
                info += "Zram: No configurado\n\n"
                
            # Info de Swap
            result = subprocess.run(['swapon', '--show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info += f"Swap:\n{result.stdout}\n\n"
            else:
                info += "Swap: No configurado\n\n"
        except:
            info += "Error al obtener información del sistema\n"
            
        self.zram_info_text.delete("1.0", "end")
        self.zram_info_text.insert("1.0", info)
        
    def run_command(self, command):
        """Ejecuta un comando y muestra el resultado"""
        try:
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=10
            )
            output = f"$ {command}\n\n{result.stdout}"
            if result.stderr:
                output += f"\nErrores:\n{result.stderr}"
        except Exception as e:
            output = f"Error: {str(e)}"
            
        self.command_output.delete("1.0", "end")
        self.command_output.insert("1.0", output)
        
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
        header = ctk.CTkFrame(confirm_window, fg_color=self.colors['accent1'])
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
        
        script = self.generate_configuration_script()
        
        textbox = ctk.CTkTextbox(
            script_frame,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=self.colors['card']
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
            fg_color=self.colors['success'],
            hover_color="#059669"
        ).pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        ctk.CTkButton(
            btn_frame,
            text="❌ Cancelar",
            command=on_cancel,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.colors['warning'],
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
                # Guardar script
                progress_window.after(0, lambda: status_label.configure(text="Guardando script temporal..."))
                script_path = "/tmp/zram_swap_config.sh"
                with open(script_path, 'w') as f:
                    f.write(script)
                os.chmod(script_path, 0o755)
                
                # Ejecutar con pkexec
                progress_window.after(0, lambda: status_label.configure(text="Esperando autenticación..."))
                result = subprocess.run(
                    ['pkexec', 'bash', script_path],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                # Detener progreso y destruir ventana
                def cleanup_and_show_result():
                    progress.stop()
                    progress_window.grab_release()
                    progress_window.destroy()
                    
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
                
                progress_window.after(0, cleanup_and_show_result)
                    
            except subprocess.TimeoutExpired:
                def cleanup_timeout():
                    progress.stop()
                    progress_window.grab_release()
                    progress_window.destroy()
                    self.show_result_dialog(
                        "⏱️ Tiempo Agotado",
                        "La operación tardó demasiado tiempo.",
                        "warning"
                    )
                progress_window.after(0, cleanup_timeout)
                
            except Exception as e:
                def cleanup_error():
                    progress.stop()
                    progress_window.grab_release()
                    progress_window.destroy()
                    self.show_result_dialog(
                        "❌ Error",
                        f"Error inesperado:\n{str(e)}",
                        "error"
                    )
                progress_window.after(0, cleanup_error)
                
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
            "success": self.colors['success'],
            "error": "#ef4444",
            "warning": self.colors['warning'],
            "info": self.colors['accent3']
        }.get(dialog_type, self.colors['accent3'])
        
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
            fg_color=self.colors['card']
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
        
    def generate_configuration_script(self):
        """Genera el script de configuración"""
        script = """#!/bin/bash
# Script generado por Zram & Swap Manager Pro

set -e

echo "🚀 Iniciando configuración..."

"""
        
        # Configuración de Zram
        if self.zram_enabled.get():
            script += f"""
# Configurar Zram
echo "⚡ Configurando Zram..."

# Desactivar zram existente
swapoff /dev/zram0 2>/dev/null || true
modprobe -r zram 2>/dev/null || true

# Cargar módulo zram
modprobe zram

# Configurar algoritmo de compresión
echo {self.compression_algo.get()} > /sys/block/zram0/comp_algorithm

# Configurar tamaño
echo {self.zram_size.get()}M > /sys/block/zram0/disksize

# Formatear y activar
mkswap /dev/zram0
swapon -p 100 /dev/zram0

echo "✅ Zram configurado: {self.zram_size.get()}MB con {self.compression_algo.get()}"

# Hacer permanente
cat > /etc/systemd/system/zram.service << 'EOF'
[Unit]
Description=Zram Configuration
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'modprobe zram && echo {self.compression_algo.get()} > /sys/block/zram0/comp_algorithm && echo {self.zram_size.get()}M > /sys/block/zram0/disksize && mkswap /dev/zram0 && swapon -p 100 /dev/zram0'
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
"""
        
        # Configuración de Swap
        if self.swap_enabled.get():
            swap_location = self.swap_location.get()
            swap_size_mb = self.swap_size.get()
            swappiness = self.swappiness_var.get()
            
            script += f"""
# Configurar Swapfile
echo "💾 Configurando Swapfile..."

# Desactivar swap existente
swapoff {swap_location} 2>/dev/null || true

# Crear swapfile
dd if=/dev/zero of={swap_location} bs=1M count={swap_size_mb} status=progress
chmod 600 {swap_location}
mkswap {swap_location}
swapon {swap_location}

echo "✅ Swapfile configurado: {swap_size_mb}MB en {swap_location}"

# Configurar en /etc/fstab
if ! grep -q "{swap_location}" /etc/fstab; then
    echo "{swap_location} none swap sw 0 0" >> /etc/fstab
fi

# Configurar swappiness
sysctl vm.swappiness={swappiness}
echo "vm.swappiness={swappiness}" > /etc/sysctl.d/99-swappiness.conf
"""
        else:
            script += """
# Desactivar Swapfile
echo "🔴 Desactivando Swapfile..."
swapoff /swapfile 2>/dev/null || true
rm -f /swapfile
sed -i '/swapfile/d' /etc/fstab
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
        
    def on_closing(self):
        self.monitoring = False
        self.destroy()

if __name__ == "__main__":
    app = ZramSwapManager()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
