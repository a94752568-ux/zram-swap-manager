import customtkinter as ctk

class ToolTip:
    """Clase para mostrar tooltips informativos al pasar el mouse."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<ButtonPress>", self.hide)

    def schedule(self, event=None):
        self.id = self.widget.after(500, self.show)

    def show(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes('-topmost', True)
        
        frame = ctk.CTkFrame(self.tooltip_window, fg_color="#1a1a2e", border_width=1, border_color="#8b5cf6")
        frame.pack()
        
        label = ctk.CTkLabel(
            frame, 
            text=self.text, 
            justify="left",
            font=ctk.CTkFont(size=12),
            text_color="#e5e7eb",
            wraplength=300
        )
        label.pack(padx=10, pady=5)

    def hide(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None