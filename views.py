import customtkinter as ctk
import psutil
from config import THEME
from utils import ToolTip

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class BaseView(ctk.CTkFrame):
    """Clase base para las vistas de la aplicación."""
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        pass

    def create_card(self, title):
        card = ctk.CTkFrame(self, fg_color=THEME["bg_card"], corner_radius=15)
        title_lbl = ctk.CTkLabel(
            card, text=title, 
            font=ctk.CTkFont(size=16, weight="bold"), 
            text_color=THEME["text"]
        )
        title_lbl.pack(padx=20, pady=(15, 10), anchor="w")
        return card

class ZramView(BaseView):
    def setup_ui(self):
        ctk.CTkLabel(self, text="Configuración Zram", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, padx=20, anchor="w")
        
        card = self.create_card("Estado y Modo")
        card.pack(fill="x", padx=20, pady=10)
        
        switch_frame = ctk.CTkFrame(card, fg_color="transparent")
        switch_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(switch_frame, text="Habilitar Zram", font=ctk.CTkFont(size=14)).pack(side="left")
        zram_switch = ctk.CTkSwitch(switch_frame, text="", variable=self.app.zram_enabled, command=self.app.toggle_zram_controls, progress_color=THEME["accent"])
        zram_switch.pack(side="right")
        ToolTip(zram_switch, "Activa/Desactiva el módulo Zram.")

        dyn_frame = ctk.CTkFrame(card, fg_color="transparent")
        dyn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(dyn_frame, text="Modo Dinámico Adaptativo", font=ctk.CTkFont(size=14)).pack(side="left")
        dyn_switch = ctk.CTkSwitch(dyn_frame, text="", variable=self.app.zram_dynamic, progress_color=THEME["success"])
        dyn_switch.pack(side="right")
        ToolTip(dyn_switch, "Ajusta el tamaño automáticamente según el uso de RAM.")

        size_card = self.create_card("Tamaño y Compresión")
        size_card.pack(fill="x", padx=20, pady=10)
        self.app.zram_content_frame = size_card

        self.app.zram_size_label = ctk.CTkLabel(size_card, text="Tamaño: ...", font=ctk.CTkFont(size=13))
        self.app.zram_size_label.pack(pady=(10, 5), padx=20, anchor="w")
        
        slider = ctk.CTkSlider(size_card, from_=1024, to=int(self.app.total_ram * 0.5), variable=self.app.zram_size, command=self.app.update_zram_size_label, button_color=THEME["accent"], progress_color=THEME["accent"])
        slider.pack(fill="x", padx=20, pady=10)
        ToolTip(slider, "Tamaño máximo de Zram en MB.")

        ctk.CTkLabel(size_card, text="Algoritmo:", font=ctk.CTkFont(size=13)).pack(pady=(10, 5), padx=20, anchor="w")
        algo_frame = ctk.CTkFrame(size_card, fg_color="transparent")
        algo_frame.pack(fill="x", padx=20, pady=10)
        
        for algo in ["zstd", "lzo-rle", "lz4"]:
            ctk.CTkRadioButton(algo_frame, text=algo.upper(), variable=self.app.compression_algo, value=algo, fg_color=THEME["accent"]).pack(side="left", padx=10)

class SwapView(BaseView):
    def setup_ui(self):
        ctk.CTkLabel(self, text="Configuración Swapfile", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, padx=20, anchor="w")
        
        card = self.create_card("Gestión de Swap")
        card.pack(fill="x", padx=20, pady=10)
        
        switch_frame = ctk.CTkFrame(card, fg_color="transparent")
        switch_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(switch_frame, text="Habilitar Swapfile", font=ctk.CTkFont(size=14)).pack(side="left")
        swap_switch = ctk.CTkSwitch(switch_frame, text="", variable=self.app.swap_enabled, command=self.app.toggle_swap_controls, progress_color=THEME["accent"])
        swap_switch.pack(side="right")
        
        self.app.swap_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.app.swap_content_frame.pack(fill="x", padx=0, pady=0)
        
        settings_card = ctk.CTkFrame(self.app.swap_content_frame, fg_color=THEME["bg_card"], corner_radius=15)
        settings_card.pack(fill="x", padx=20, pady=10)
        
        self.app.swap_size_label = ctk.CTkLabel(settings_card, text="Tamaño: ...", font=ctk.CTkFont(size=13))
        self.app.swap_size_label.pack(pady=(15, 5), padx=20, anchor="w")
        
        slider = ctk.CTkSlider(settings_card, from_=2048, to=32768, variable=self.app.swap_size, command=self.app.update_swap_size_label, button_color=THEME["accent"], progress_color=THEME["accent"])
        slider.pack(fill="x", padx=20, pady=10)
        
        self.app.swap_location = ctk.CTkEntry(settings_card, placeholder_text="/swapfile")
        self.app.swap_location.pack(fill="x", padx=20, pady=10)
        self.app.swap_location.insert(0, "/swapfile")
        
        self.app.swappiness_label = ctk.CTkLabel(settings_card, text="Swappiness: ...", font=ctk.CTkFont(size=13))
        self.app.swappiness_label.pack(pady=(10, 5), padx=20, anchor="w")
        swappiness_slider = ctk.CTkSlider(settings_card, from_=0, to=100, variable=self.app.swappiness_var, command=self.app.update_swappiness_label, button_color=THEME["accent"], progress_color=THEME["accent"])
        swappiness_slider.pack(fill="x", padx=20, pady=10)

class MonitorView(BaseView):
    def setup_ui(self):
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=20, pady=20)
        
        self.title_lbl = ctk.CTkLabel(self.header, text="Monitor del Sistema", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_lbl.pack(side="left")
        self.activity_dot = ctk.CTkLabel(self.header, text="●", font=ctk.CTkFont(size=16), text_color=THEME["bg_card"])
        self.activity_dot.pack(side="left", padx=10)
        
        self.exit_mini_btn = ctk.CTkButton(self.header, text="⤢ Expandir", width=80, command=self.app.toggle_mini_mode, fg_color=THEME["accent"])
        
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=20, pady=10)
        self.stats_frame.grid_columnconfigure((0,1,2), weight=1)
        
        self.ram_available_label = self.create_mini_stat(self.stats_frame, "RAM Disponible", 0)
        self.zram_effective_label = self.create_mini_stat(self.stats_frame, "Zram Efectivo", 1)
        self.compression_label = self.create_mini_stat(self.stats_frame, "Compresión", 2)
        
        # Sección de Análisis de IA
        self.ai_label = ctk.CTkLabel(self, text="🧠 Análisis de IA (LightweightPredictor)", font=ctk.CTkFont(size=18, weight="bold"))
        self.ai_label.pack(pady=(20,10), padx=20, anchor="w")
        
        self.ai_stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ai_stats_frame.pack(fill="x", padx=20, pady=5)
        self.ai_stats_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.ai_cpu_label = self.create_mini_stat(self.ai_stats_frame, "Carga CPU", 0)
        self.ai_pred_ram_label = self.create_mini_stat(self.ai_stats_frame, "RAM Predicha", 1)
        self.ai_swappiness_label = self.create_mini_stat(self.ai_stats_frame, "Swappiness IA", 2)
        self.ai_cache_label = self.create_mini_stat(self.ai_stats_frame, "Presión Caché", 3)

        # Asesor LLM local (Ollama): consulta bajo demanda
        self.llm_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.llm_frame.pack(fill="x", padx=20, pady=5)

        self.llm_btn = ctk.CTkButton(
            self.llm_frame,
            text="🧠 Consultar al LLM (Ollama)",
            command=self.app.consult_llm,
            fg_color=THEME["success"],
            hover_color="#28a745",
            height=30
        )
        self.llm_btn.pack(side="left", pady=5)
        ToolTip(self.llm_btn, "Consulta a un LLM local (Ollama) para obtener recomendaciones de optimización y su explicación.")

        self.llm_status_label = ctk.CTkLabel(self.llm_frame, text="Ollama: --", font=ctk.CTkFont(size=12), text_color=THEME["text_sec"])
        self.llm_status_label.pack(side="left", padx=10)

        self.llm_result_text = ctk.CTkTextbox(self, font=ctk.CTkFont(size=12), fg_color="#111111", height=140)
        self.llm_result_text.pack(fill="x", padx=20, pady=(0, 10))
        self.llm_result_text.insert("1.0", "Las recomendaciones del LLM local aparecerán aquí tras pulsar el botón.")
        self.llm_result_text.configure(state="disabled")
        
        # Sección de Hardware en Tiempo Real
        self.hw_label = ctk.CTkLabel(self, text="🖥️ Hardware en Tiempo Real", font=ctk.CTkFont(size=18, weight="bold"))
        self.hw_label.pack(pady=(20,10), padx=20, anchor="w")
        
        self.hw_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.hw_frame.pack(fill="x", padx=20, pady=5)
        self.hw_frame.grid_columnconfigure((0,1,2), weight=1)

        self.mon_cpu_usage_label = self.create_mini_stat(self.hw_frame, "Uso CPU Global", 0)
        self.mon_temp_label = self.create_mini_stat(self.hw_frame, "Temperatura CPU", 1)
        self.mon_gpu_freq_label = self.create_mini_stat(self.hw_frame, "Frecuencia GPU", 2)

        # Frecuencias por Núcleo
        self.cores_label = ctk.CTkLabel(self, text="Frecuencia por Núcleo (MHz):", font=ctk.CTkFont(size=14, weight="bold"))
        self.cores_label.pack(pady=(10,5), padx=20, anchor="w")
        self.cores_frame = ctk.CTkFrame(self, fg_color=THEME["bg_card"], corner_radius=10)
        self.cores_frame.pack(fill="x", padx=20, pady=5)
        
        self.mon_core_labels = []
        try:
            cpu_count = psutil.cpu_count(logical=True)
            cols = 4
            for i in range(cpu_count):
                self.cores_frame.grid_columnconfigure(i % cols, weight=1)
                lbl = ctk.CTkLabel(self.cores_frame, text=f"Core {i}: ...", font=ctk.CTkFont(size=12, family="Courier"))
                lbl.grid(row=i // cols, column=i % cols, padx=5, pady=5, sticky="ew")
                self.mon_core_labels.append(lbl)
        except Exception: pass

        # Establecer referencia para que el hilo de monitoreo pueda actualizar la UI
        self.app.monitor_view_ref = self
        
        if MATPLOTLIB_AVAILABLE:
            self.graph_card = self.create_card("Histórico de Memoria")
            self.graph_card.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.fig = Figure(figsize=(5, 3), dpi=100)
            self.fig.patch.set_facecolor(THEME["bg_card"])
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor(THEME["bg_card"])
            
            for spine in self.ax.spines.values(): spine.set_color(THEME["text_sec"])
            self.ax.tick_params(colors=THEME["text_sec"])
            self.ax.set_ylim(0, 100)
            self.ax.grid(True, color='#444444', linestyle='--', alpha=0.3)
            
            self.line_ram, = self.ax.plot([], [], color=THEME["accent"], linewidth=2, label='RAM')
            self.line_swap, = self.ax.plot([], [], color=THEME["danger"], linewidth=2, label='Swap')
            self.ax.legend(facecolor=THEME["bg_card"], edgecolor='none', labelcolor=THEME["text"], fontsize=8)
            
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_card)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
            
            # Gráfico de GPU
            self.gpu_card = self.create_card("Histórico de Carga GPU")
            self.gpu_card.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.fig_gpu = Figure(figsize=(5, 2.5), dpi=100)
            self.fig_gpu.patch.set_facecolor(THEME["bg_card"])
            self.ax_gpu = self.fig_gpu.add_subplot(111)
            self.ax_gpu.set_facecolor(THEME["bg_card"])
            
            for spine in self.ax_gpu.spines.values(): spine.set_color(THEME["text_sec"])
            self.ax_gpu.tick_params(colors=THEME["text_sec"])
            self.ax_gpu.set_ylim(0, 100)
            self.ax_gpu.grid(True, color='#444444', linestyle='--', alpha=0.3)
            
            self.line_gpu, = self.ax_gpu.plot([], [], color=THEME["warning"], linewidth=2, label='Carga GPU')
            self.ax_gpu.legend(facecolor=THEME["bg_card"], edgecolor='none', labelcolor=THEME["text"], fontsize=8)
            
            self.canvas_gpu = FigureCanvasTkAgg(self.fig_gpu, master=self.gpu_card)
            self.canvas_gpu.draw()
            self.canvas_gpu.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.log_card = self.create_card("Detalles en Vivo")
        self.log_card.pack(fill="both", expand=True, padx=20, pady=10)
        self.zram_info_text = ctk.CTkTextbox(self.log_card, font=ctk.CTkFont(family="Courier", size=12), fg_color="#111111")
        self.zram_info_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkButton(self.log_card, text="Actualizar", command=self.refresh_text_info, fg_color=THEME["accent"], height=30).pack(pady=10)

    def toggle_mini_mode(self, is_mini):
        widgets_to_hide = [
            self.stats_frame, self.ai_label, self.ai_stats_frame, 
            self.hw_label, self.hw_frame, self.cores_label, self.cores_frame, 
            self.llm_frame, self.llm_result_text, self.log_card
        ]
        
        if is_mini:
            for w in widgets_to_hide:
                w.pack_forget()
            
            self.exit_mini_btn.pack(side="right", padx=10)
            
            if hasattr(self, 'graph_card'):
                self.graph_card.pack(fill="both", expand=True, padx=5, pady=5)
            if hasattr(self, 'gpu_card'):
                self.gpu_card.pack(fill="both", expand=True, padx=5, pady=5)
        else:
            self.exit_mini_btn.pack_forget()
            
            self.stats_frame.pack(fill="x", padx=20, pady=10)
            self.ai_label.pack(pady=(20,10), padx=20, anchor="w")
            self.ai_stats_frame.pack(fill="x", padx=20, pady=5)
            self.llm_frame.pack(fill="x", padx=20, pady=5)
            self.llm_result_text.pack(fill="x", padx=20, pady=(0, 10))
            self.hw_label.pack(pady=(20,10), padx=20, anchor="w")
            self.hw_frame.pack(fill="x", padx=20, pady=5)
            self.cores_label.pack(pady=(10,5), padx=20, anchor="w")
            self.cores_frame.pack(fill="x", padx=20, pady=5)
            
            if hasattr(self, 'graph_card'):
                self.graph_card.pack(fill="both", expand=True, padx=20, pady=10)
            if hasattr(self, 'gpu_card'):
                self.gpu_card.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.log_card.pack(fill="both", expand=True, padx=20, pady=10)

    def create_mini_stat(self, parent, title, col):
        f = ctk.CTkFrame(parent, fg_color=THEME["bg_card"], corner_radius=10)
        f.grid(row=0, column=col, padx=5, sticky="ew")
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12), text_color=THEME["text_sec"]).pack(pady=(10,0))
        lbl = ctk.CTkLabel(f, text="...", font=ctk.CTkFont(size=20, weight="bold"), text_color=THEME["accent"])
        lbl.pack(pady=(0,10))
        return lbl

    def update_graph(self, ram_data, swap_data):
        if hasattr(self, 'line_ram'):
            x = range(len(ram_data))
            self.line_ram.set_data(x, list(ram_data))
            self.line_swap.set_data(x, list(swap_data))
            self.canvas.draw()

    def update_gpu_graph(self, gpu_data):
        if hasattr(self, 'line_gpu'):
            x = range(len(gpu_data))
            self.line_gpu.set_data(x, list(gpu_data))
            self.canvas_gpu.draw()

    def update_stats(self, data):
        """Actualiza todos los widgets de monitoreo con un diccionario de datos."""
        if not self.winfo_exists(): return

        # Stats básicos
        self.ram_available_label.configure(text=f"{int(data['ram_available'])} MB")
        self.zram_effective_label.configure(text=f"{int(data['zram_effective'])} MB")
        self.compression_label.configure(text=f"{data['compression_ratio']:.2f}x")
        
        # IA Stats
        self.ai_cpu_label.configure(text=f"{data['cpu_percent']:.1f}%")
        self.ai_pred_ram_label.configure(text=f"{data['predicted_ram']:.1f}%")
        self.ai_swappiness_label.configure(text=f"{data['opt_swappiness']}")
        self.ai_cache_label.configure(text=f"{data['opt_cache']}")
        
        # Hardware Stats
        self.mon_cpu_usage_label.configure(text=f"{data['cpu_percent']:.1f}%")
        self.mon_temp_label.configure(text=data['temp_text'], text_color=data['temp_color'])
        self.mon_gpu_freq_label.configure(text=data['gpu_text'], text_color=data['gpu_color'])
        
        # Cores
        if data.get('cpu_freq_per_core') and self.mon_core_labels:
            for i, freq_info in enumerate(data['cpu_freq_per_core']):
                if i < len(self.mon_core_labels):
                    self.mon_core_labels[i].configure(text=f"Core {i}: {int(freq_info.current)} MHz")
        
        # Gráficos
        self.update_graph(data['ram_history'], data['swap_history'])
        self.update_gpu_graph(data['gpu_history'])
        self.flash_indicator()

    def refresh_text_info(self):
        """Actualiza el cuadro de texto con info detallada."""
        info = self.app.get_detailed_monitor_info()
        self.zram_info_text.delete("1.0", "end")
        self.zram_info_text.insert("1.0", info)

    def flash_indicator(self):
        """Hace parpadear el indicador de actividad."""
        if self.winfo_exists():
            self.activity_dot.configure(text_color=THEME["success"])
            self.after(200, lambda: self.activity_dot.configure(text_color=THEME["bg_card"]) if self.winfo_exists() else None)

class HardwareView(BaseView):
    def setup_ui(self):
        ctk.CTkLabel(self, text="Control de Hardware", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, padx=20, anchor="w")

        # --- Perfiles de Energía ---
        profiles_card = self.create_card("Perfiles de Energía")
        profiles_card.pack(fill="x", padx=20, pady=10)
        
        btn_frame = ctk.CTkFrame(profiles_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        profiles = [
            ("🎮 Gaming", "gaming", THEME["danger"]),
            ("🏢 Oficina", "office", THEME["accent"]),
            ("🍃 Ahorro", "eco", THEME["success"])
        ]
        
        for txt, mode, col in profiles:
            ctk.CTkButton(
                btn_frame, 
                text=txt, 
                command=lambda m=mode: self.app.apply_energy_profile(m),
                fg_color=col,
                width=100
            ).pack(side="left", padx=10, expand=True)

        # --- Perfiles Personalizados ---
        custom_frame = ctk.CTkFrame(profiles_card, fg_color="transparent")
        custom_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(custom_frame, text="Personalizados:", font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
        
        self.profiles_combo = ctk.CTkComboBox(custom_frame, values=list(self.app.custom_profiles.keys()), width=150)
        self.profiles_combo.pack(side="left", padx=5)
        if self.app.custom_profiles:
            self.profiles_combo.set(list(self.app.custom_profiles.keys())[0])
        
        ctk.CTkButton(custom_frame, text="💾 Guardar", command=self.app.save_current_as_profile, width=80, fg_color=THEME["accent"]).pack(side="left", padx=5)
        ctk.CTkButton(custom_frame, text="▶️ Cargar", command=self.load_selected_profile, width=80, fg_color=THEME["success"]).pack(side="left", padx=5)
        ctk.CTkButton(custom_frame, text="🗑️", command=self.delete_selected_profile, width=40, fg_color=THEME["danger"]).pack(side="left", padx=5)

        # --- CPU Control ---
        cpu_card = self.create_card("Procesador (CPU)")
        cpu_card.pack(fill="x", padx=20, pady=10)

        # Frecuencia y Gobernador
        freq_frame = ctk.CTkFrame(cpu_card, fg_color="transparent")
        freq_frame.pack(fill="x", padx=20, pady=10)
        
        self.cpu_freq_label = ctk.CTkLabel(freq_frame, text="Frecuencia: ...", font=ctk.CTkFont(size=14))
        self.cpu_freq_label.pack(anchor="w")

        self.cpu_voltage_label = ctk.CTkLabel(freq_frame, text="Voltaje (VID): -- V", font=ctk.CTkFont(size=14))
        self.cpu_voltage_label.pack(anchor="w")

        # Botón de Calibración
        ctk.CTkButton(freq_frame, text="📏 Calibrar Límites", command=self.app.calibrate_cpu, fg_color=THEME["accent"], width=120).pack(anchor="e", pady=(0, 10))

        if self.app.available_freqs:
            # Usar ComboBox si hay frecuencias específicas
            ctk.CTkLabel(freq_frame, text="Frecuencia Máxima:", font=ctk.CTkFont(size=12)).pack(anchor="w")
            freq_values = [str(f) for f in self.app.available_freqs]
            self.app.freq_max_combo = ctk.CTkComboBox(freq_frame, values=freq_values, command=self.app.set_manual_max_freq)
            self.app.freq_max_combo.set(freq_values[0])
            self.app.freq_max_combo.pack(fill="x", pady=5)
            
            ctk.CTkLabel(freq_frame, text="Frecuencia Mínima:", font=ctk.CTkFont(size=12)).pack(anchor="w")
            self.app.freq_min_combo = ctk.CTkComboBox(freq_frame, values=freq_values, command=self.app.set_manual_min_freq)
            self.app.freq_min_combo.set(freq_values[-1])
            self.app.freq_min_combo.pack(fill="x", pady=5)
        else:
            # Fallback a Slider
            self.app.cpu_slider = ctk.CTkSlider(
                freq_frame, 
                from_=0, to=100, 
                command=self.app.on_cpu_slider_change,
                progress_color=THEME["accent"]
            )
            self.app.cpu_slider.pack(fill="x", pady=10)
            ToolTip(self.app.cpu_slider, "Limita la frecuencia máxima de la CPU (Cap).")

        gov_frame = ctk.CTkFrame(cpu_card, fg_color="transparent")
        gov_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(gov_frame, text="Gobernador:", font=ctk.CTkFont(size=12)).pack(side="left")
        
        govs = self.app.available_governors if self.app.available_governors else ["performance", "powersave"]
        self.app.gov_option = ctk.CTkOptionMenu(
            gov_frame, 
            values=govs,
            command=self.app.change_governor,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent"]
        )
        self.app.gov_option.pack(side="left", padx=10)

        # Boost y Undervolt
        switches_frame = ctk.CTkFrame(cpu_card, fg_color="transparent")
        switches_frame.pack(fill="x", padx=20, pady=10)
        
        self.app.boost_switch = ctk.CTkSwitch(switches_frame, text="CPU Boost / Turbo", command=self.app.toggle_boost, progress_color=THEME["danger"])
        self.app.boost_switch.pack(side="left", padx=(0, 20))
        ToolTip(self.app.boost_switch, "Habilita frecuencias turbo. Desactivar para ahorrar energía y calor.")

        uv_text = "Undervolt Automático (Eco)"
        uv_tooltip = "Ajusta dinámicamente EPP y frecuencia para trabajar en el punto óptimo."
        
        if not self.app.epp_supported:
            uv_text += " (Limitado)"
            uv_tooltip = "Tu CPU no soporta EPP. La optimización se limitará a ajustar frecuencias máximas."

        self.app.undervolt_switch = ctk.CTkSwitch(switches_frame, text=uv_text, command=self.app.toggle_undervolt, progress_color=THEME["success"])
        self.app.undervolt_switch.pack(side="left")
        ToolTip(self.app.undervolt_switch, uv_tooltip)
        
        # Etiqueta de estado dinámico
        self.optimization_status_label = ctk.CTkLabel(switches_frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.optimization_status_label.pack(side="left", padx=10)

        # --- Calibración de Voltaje (Real) ---
        uv_card = self.create_card("⚡ Calibración de Voltaje (Real)")
        uv_card.pack(fill="x", padx=20, pady=10)
        
        uv_frame = ctk.CTkFrame(uv_card, fg_color="transparent")
        uv_frame.pack(fill="x", padx=20, pady=10)

        if self.app.undervolt_tool != "none":
            self.app.uv_boot_switch = ctk.CTkSwitch(uv_frame, text="Aplicar al Inicio (Systemd)", command=self.app.toggle_uv_on_boot, variable=self.app.apply_uv_on_boot, progress_color=THEME["success"])
            self.app.uv_boot_switch.pack(anchor="w", pady=(0, 10))

            self.app.uv_label = ctk.CTkLabel(uv_frame, text="Offset: 0 mV", font=ctk.CTkFont(size=14))
            self.app.uv_label.pack(anchor="w")
            
            self.app.uv_slider = ctk.CTkSlider(
                uv_frame, 
                from_=-150, to=0, 
                number_of_steps=30, # Pasos de 5mV
                command=lambda v: self.app.uv_label.configure(text=f"Offset: {int(v)} mV"),
                progress_color=THEME["warning"]
            )
            self.app.uv_slider.set(0)
            self.app.uv_slider.pack(fill="x", pady=10)
            
            # Botones de acción principales
            action_frame = ctk.CTkFrame(uv_frame, fg_color="transparent")
            action_frame.pack(fill="x", pady=5)
            
            ctk.CTkButton(action_frame, text="Aplicar Offset", command=lambda: self.app.apply_voltage_offset(self.app.uv_slider.get()), fg_color=THEME["warning"], width=120).pack(side="right", padx=5)
            ctk.CTkButton(action_frame, text="🪄 Smart Undervolt", command=self.app.run_smart_undervolt, fg_color=THEME["accent"], width=120).pack(side="right", padx=5)
            ctk.CTkButton(action_frame, text="📉 Auto Progresivo", command=self.app.run_progressive_undervolt, fg_color=THEME["success"], width=120).pack(side="right", padx=5)
            
            # Gestión de Perfiles UV
            uv_profiles_frame = ctk.CTkFrame(uv_frame, fg_color="transparent")
            uv_profiles_frame.pack(fill="x", pady=(10, 0))
            
            ctk.CTkLabel(uv_profiles_frame, text="Perfiles UV:", font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
            
            self.uv_profiles_combo = ctk.CTkComboBox(uv_profiles_frame, values=list(self.app.undervolt_profiles.keys()), width=120)
            self.uv_profiles_combo.pack(side="left", padx=5)
            if self.app.undervolt_profiles:
                self.uv_profiles_combo.set(list(self.app.undervolt_profiles.keys())[0])
                
            ctk.CTkButton(uv_profiles_frame, text="💾", command=self.app.save_uv_profile, width=40, fg_color=THEME["accent"]).pack(side="left", padx=2)
            ctk.CTkButton(uv_profiles_frame, text="▶️", command=self.load_selected_uv_profile, width=40, fg_color=THEME["success"]).pack(side="left", padx=2)
            ctk.CTkButton(uv_profiles_frame, text="🗑️", command=self.delete_selected_uv_profile, width=40, fg_color=THEME["danger"]).pack(side="left", padx=2)
            
            # Botón de prueba de estabilidad
            ctk.CTkButton(uv_profiles_frame, text="🧪 Probar", command=self.app.test_undervolt_stability, width=60, fg_color=THEME["bg_card"], border_width=1, border_color=THEME["text_sec"]).pack(side="right", padx=5)
            
            ToolTip(self.app.uv_slider, "Reduce el voltaje real de la CPU. Valores negativos ahorran energía pero pueden causar inestabilidad.")
        else:
            ctk.CTkLabel(uv_frame, text="⚠️ Herramienta 'intel-undervolt' no detectada.\nInstálala para habilitar esta función.", text_color=THEME["text_sec"]).pack()

        # --- GPU & Temps ---
        gpu_card = self.create_card("Gráficos y Temperatura")
        gpu_card.pack(fill="x", padx=20, pady=10)
        
        stats_grid = ctk.CTkFrame(gpu_card, fg_color="transparent")
        stats_grid.pack(fill="x", padx=10, pady=10)
        stats_grid.grid_columnconfigure((0,1,2,3), weight=1)

        self.gpu_freq_label = self.create_mini_stat(stats_grid, "Frecuencia GPU", 0)
        self.temp_cur_label = self.create_mini_stat(stats_grid, "Temp Actual", 1)
        self.temp_min_label = self.create_mini_stat(stats_grid, "Temp Mín", 2)
        self.temp_max_label = self.create_mini_stat(stats_grid, "Temp Máx", 3)

        # --- Histórico de Temperatura ---
        if MATPLOTLIB_AVAILABLE:
            graph_card = self.create_card("Histórico de Temperatura")
            graph_card.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.fig = Figure(figsize=(5, 2.5), dpi=100)
            self.fig.patch.set_facecolor(THEME["bg_card"])
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor(THEME["bg_card"])
            
            for spine in self.ax.spines.values(): spine.set_color(THEME["text_sec"])
            self.ax.tick_params(colors=THEME["text_sec"])
            self.ax.grid(True, color='#444444', linestyle='--', alpha=0.3)
            
            self.line_temp, = self.ax.plot([], [], color=THEME["warning"], linewidth=2, label='Temp CPU')
            self.ax.legend(facecolor=THEME["bg_card"], edgecolor='none', labelcolor=THEME["text"], fontsize=8)
            
            self.canvas = FigureCanvasTkAgg(self.fig, master=graph_card)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
            
            self.app.hardware_view_ref = self

    def update_profiles_combo(self):
        self.profiles_combo.configure(values=list(self.app.custom_profiles.keys()))
        if self.app.custom_profiles:
            self.profiles_combo.set(list(self.app.custom_profiles.keys())[0])
        else:
            self.profiles_combo.set("")

    def load_selected_profile(self):
        name = self.profiles_combo.get()
        if name: self.app.apply_custom_profile(name)

    def delete_selected_profile(self):
        name = self.profiles_combo.get()
        if name: self.app.delete_custom_profile(name)

    def update_uv_profiles_combo(self):
        self.uv_profiles_combo.configure(values=list(self.app.undervolt_profiles.keys()))
        if self.app.undervolt_profiles:
            self.uv_profiles_combo.set(list(self.app.undervolt_profiles.keys())[0])
        else:
            self.uv_profiles_combo.set("")

    def load_selected_uv_profile(self):
        name = self.uv_profiles_combo.get()
        if name: self.app.load_uv_profile(name)

    def delete_selected_uv_profile(self):
        name = self.uv_profiles_combo.get()
        if name: self.app.delete_uv_profile(name)

    def update_temp_graph(self, temp_data):
        if hasattr(self, 'line_temp'):
            x = range(len(temp_data))
            data = list(temp_data)
            self.line_temp.set_data(x, data)
            
            # Ajuste dinámico del eje Y
            if data:
                min_y = max(0, min(data) - 5)
                max_y = max(data) + 5
                self.ax.set_ylim(min_y, max_y)
                
            self.canvas.draw()

    def update_stats(self, data):
        """Actualiza widgets de hardware."""
        if not self.winfo_exists(): return

        # Temps
        self.temp_cur_label.configure(text=f"{data['cur_temp']}°C", text_color=data['temp_color'])
        self.temp_min_label.configure(text=f"{data['temp_min']}°C")
        self.temp_max_label.configure(text=f"{data['temp_max']}°C")
        self.update_temp_graph(data['temp_history'])
        
        # CPU
        self.cpu_freq_label.configure(text=f"Actual: {int(data['cpu_freq_current'])} MHz")
        self.cpu_voltage_label.configure(text=f"Voltaje (VID): {data['cpu_voltage']:.3f} V" if data['cpu_voltage'] > 0 else "Voltaje (VID): --")
        self.optimization_status_label.configure(text=data['opt_status'], text_color=data['opt_status_color'])
        
        # GPU
        self.gpu_freq_label.configure(text=data['gpu_text'], text_color=data['gpu_color'])

    def create_mini_stat(self, parent, title, col):
        f = ctk.CTkFrame(parent, fg_color=THEME["bg_card"], corner_radius=10)
        f.grid(row=0, column=col, padx=5, sticky="ew")
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12), text_color=THEME["text_sec"]).pack(pady=(10,0))
        lbl = ctk.CTkLabel(f, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=THEME["text"])
        lbl.pack(pady=(0,10))
        return lbl

class AdvancedView(BaseView):
    def setup_ui(self):
        ctk.CTkLabel(self, text="Opciones Avanzadas", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, padx=20, anchor="w")
        
        card = self.create_card("Acciones del Sistema")
        card.pack(fill="x", padx=20, pady=10)
        
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        cmds = [("Ver Zram", "zramctl", THEME["accent"]), ("Ver Swap", "swapon --show", THEME["accent"]), ("Ver Memoria", "free -h", THEME["accent"])]
        for txt, cmd, col in cmds:
            ctk.CTkButton(btn_frame, text=txt, command=lambda c=cmd: self.app.run_command(c), fg_color=col).pack(side="left", padx=5, expand=True, fill="x")
            
        ctk.CTkButton(card, text="🧹 Limpiar Caché", command=self.app.drop_caches, fg_color=THEME["warning"], hover_color=THEME["danger"]).pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(card, text="🔄 Restaurar Defaults", command=self.app.restore_defaults, fg_color=THEME["bg_main"], border_width=1, border_color=THEME["warning"]).pack(fill="x", padx=20, pady=(0,10))
        ctk.CTkButton(card, text="📂 Abrir Carpeta de Backups", command=self.app.open_backups_folder, fg_color=THEME["accent"]).pack(fill="x", padx=20, pady=(0,10))

        console_card = self.create_card("Salida de Consola")
        console_card.pack(fill="both", expand=True, padx=20, pady=10)
        self.app.command_output = ctk.CTkTextbox(console_card, font=ctk.CTkFont(family="Courier", size=12), fg_color="#000000")
        self.app.command_output.pack(fill="both", expand=True, padx=10, pady=10)

