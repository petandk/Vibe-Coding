import tkinter as tk
import urllib.request
import json
import threading
import queue
import string
import random
import glob
import sys

class UltimateTrainer:
    # ==========================================
    # CONSTANTES Y CONFIGURACIÓN ESTÁTICA
    # ==========================================
    COLORS = {
        "bg_main": "#121212",           
        "bg_secondary": "#1a1a1a",      
        "text_base": "#444444",         
        "text_correct": "#4ade80",   
        "text_active": "#3498db",       
        "text_error": "#e74c3c",        
        "accent": "#2ecc71",
        "bg_window": "#1e1e1e",
        "key_bg": "#2a2a2a",
        "key_border": "#333333",
        "key_text": "#ffffff",        
        "key_text_shift": "#ffffff"  
    }

    FALLBACK_WORDS = [
        "keyboard", "mouse", "screen", "code", "source", "space", "letter", 
        "system", "typing", "practice", "developer", "function", "variable", 
        "int", "float", "class", "void", "public", "return", "if", "else"
    ]

    QMK_MAP = {
        'a': ('KC_A', False), 'A': ('KC_A', True), 'b': ('KC_B', False), 'B': ('KC_B', True),
        'c': ('KC_C', False), 'C': ('KC_C', True), 'd': ('KC_D', False), 'D': ('KC_D', True),
        'e': ('KC_E', False), 'E': ('KC_E', True), 'f': ('KC_F', False), 'F': ('KC_F', True),
        'g': ('KC_G', False), 'G': ('KC_G', True), 'h': ('KC_H', False), 'H': ('KC_H', True),
        'i': ('KC_I', False), 'I': ('KC_I', True), 'j': ('KC_J', False), 'J': ('KC_J', True),
        'k': ('KC_K', False), 'K': ('KC_K', True), 'l': ('KC_L', False), 'L': ('KC_L', True),
        'm': ('KC_M', False), 'M': ('KC_M', True), 'n': ('KC_N', False), 'N': ('KC_N', True),
        'o': ('KC_O', False), 'O': ('KC_O', True), 'p': ('KC_P', False), 'P': ('KC_P', True),
        'q': ('KC_Q', False), 'Q': ('KC_Q', True), 'r': ('KC_R', False), 'R': ('KC_R', True),
        's': ('KC_S', False), 'S': ('KC_S', True), 't': ('KC_T', False), 'T': ('KC_T', True),
        'u': ('KC_U', False), 'U': ('KC_U', True), 'v': ('KC_V', False), 'V': ('KC_V', True),
        'w': ('KC_W', False), 'W': ('KC_W', True), 'x': ('KC_X', False), 'X': ('KC_X', True),
        'y': ('KC_Y', False), 'Y': ('KC_Y', True), 'z': ('KC_Z', False), 'Z': ('KC_Z', True),
        '1': ('KC_1', False), '!': ('KC_1', True), '2': ('KC_2', False), '@': ('KC_2', True),
        '3': ('KC_3', False), '#': ('KC_3', True), '4': ('KC_4', False), '$': ('KC_4', True),
        '5': ('KC_5', False), '%': ('KC_5', True), '6': ('KC_6', False), '^': ('KC_6', True),
        '7': ('KC_7', False), '&': ('KC_7', True), '8': ('KC_8', False), '*': ('KC_8', True),
        '9': ('KC_9', False), '(': ('KC_9', True), '0': ('KC_0', False), ')': ('KC_0', True),
        '-': ('KC_MINUS', False), '_': ('KC_MINUS', True), '=': ('KC_EQUAL', False), '+': ('KC_EQUAL', True),
        '[': ('KC_LBRACKET', False), '{': ('KC_LBRACKET', True), ']': ('KC_RBRACKET', False), '}': ('KC_RBRACKET', True),
        '\\': ('KC_BSLASH', False), '|': ('KC_BSLASH', True), ';': ('KC_SCOLON', False), ':': ('KC_SCOLON', True),
        "'": ('KC_QUOTE', False), '"': ('KC_QUOTE', True), ',': ('KC_COMMA', False), '<': ('KC_COMMA', True),
        '.': ('KC_DOT', False), '>': ('KC_DOT', True), '/': ('KC_SLASH', False), '?': ('KC_SLASH', True),
        '`': ('KC_GRAVE', False), '~': ('KC_GRAVE', True), ' ': ('KC_SPACE', False), '\n': ('KC_ENTER', False)
    }

    DUAL_LABELS = {
        "KC_1": ("1", "!"), "KC_2": ("2", "@"), "KC_3": ("3", "#"), "KC_4": ("4", "$"),
        "KC_5": ("5", "%"), "KC_6": ("6", "^"), "KC_7": ("7", "&"), "KC_8": ("8", "*"),
        "KC_9": ("9", "("), "KC_0": ("0", ")"), "KC_MINUS": ("-", "_"), "KC_EQUAL": ("=", "+"),
        "KC_LBRACKET": ("[", "{"), "KC_RBRACKET": ("]", "}"), "KC_BSLASH": ("\\", "|"),
        "KC_SCOLON": (";", ":"), "KC_QUOTE": ("'", '"'), "KC_COMMA": (",", "<"),
        "KC_DOT": (".", ">"), "KC_SLASH": ("/", "?"), "KC_GRAVE": ("`", "~")
    }

    QMK_REPLACES = {
        "ESCAPE": "ESC", "BSPACE": "DEL", "ENTER": "ENT", "LSHIFT": "SHIFT", "RSHIFT": "SHIFT",
        "LCTRL": "CTRL", "RCTRL": "CTRL", "LALT": "ALT", "RALT": "ALT", "LGUI": "GUI", "RGUI": "GUI",
        "SPACE": "SPC", "CAPSLOCK": "CAPS", "DELETE": "DEL", "PGDOWN": "PGDN", "PGUP": "PGUP",
        "RIGHT": "→", "LEFT": "←", "UP": "↑", "DOWN": "↓"
    }

    # ==========================================
    # INICIALIZACIÓN
    # ==========================================
    def __init__(self, root):
        self.root = root
        self.root.title("Ultimate Coder Trainer")
        
        # QoL: Centrado automático de la ventana
        win_w, win_h = 1100, 650
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x_c = int((screen_w / 2) - (win_w / 2))
        y_c = int((screen_h / 2) - (win_h / 2))
        self.root.geometry(f"{win_w}x{win_h}+{x_c}+{y_c}")
        
        self.root.configure(bg=self.COLORS["bg_main"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # QoL: Auto-foco para teclear directamente
        self.root.focus_force()
        
        self.is_fullscreen = False
        self.word_queue = queue.Queue()
        self.full_text = ""
        self.typed_buffer = ""
        self.current_mode = "words"
        self.capitalize_next = True
        self.word_count = 0
        self.is_fetching = False
        
        self.vial_file_path = None
        self.vial_data = None
        self.hint_mode_active = False

        self._setup_ui()
        self.start_practice()

    def on_close(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    # ==========================================
    # INTERFAZ GRÁFICA PRINCIPAL
    # ==========================================
    def _setup_ui(self):
        self.header = tk.Frame(self.root, bg=self.COLORS["bg_main"], pady=15)
        self.header.pack(fill="x")
        
        btn_style = {"bg": self.COLORS["bg_secondary"], "fg": "#888", 
                     "font": ("Segoe UI", 10, "bold"), "relief": "flat", "padx": 15, "cursor": "hand2"}
        
        tk.Button(self.header, text="MODO CÓDIGO", command=self.switch_to_words, **btn_style).pack(side="left", padx=10)
        tk.Button(self.header, text="ABECEDARIO", command=self.switch_to_alpha, **btn_style).pack(side="left", padx=10)
        
        self._load_vial_layout(btn_style)

        self.container = tk.Frame(self.root, bg=self.COLORS["bg_main"])
        self.container.pack(fill="both", expand=True)

        self.words_frame = tk.Frame(self.container, bg=self.COLORS["bg_main"])
        self.text_area = tk.Text(self.words_frame, font=("Consolas", 32, "bold"), bg=self.COLORS["bg_main"], 
                                 fg=self.COLORS["text_base"], padx=60, pady=40, bd=0, wrap="word", insertofftime=0)
        self.text_area.pack(fill="both", expand=True) 
        
        self.text_area.tag_configure("correct", foreground=self.COLORS["text_correct"])
        self.text_area.tag_configure("wrong", foreground="#ffffff", background=self.COLORS["text_error"])
        self.text_area.tag_configure("active", foreground=self.COLORS["text_active"])
        
        self.alpha_frame = tk.Frame(self.container, bg=self.COLORS["bg_main"])
        self.alpha_label = tk.Label(self.alpha_frame, text="", font=("Consolas", 180, "bold"), 
                                    bg=self.COLORS["bg_main"], fg=self.COLORS["text_active"])
        self.alpha_label.place(relx=0.5, rely=0.4, anchor="center")

        self.hint_display = tk.Label(self.container, text="", bg=self.COLORS["bg_main"], fg=self.COLORS["accent"], font=("Segoe UI", 16, "bold"))
        self.hint_display.pack(side="bottom", pady=10)

        self.footer = tk.Frame(self.root, bg=self.COLORS["bg_secondary"], height=40)
        self.footer.pack(fill="x", side="bottom")
        
        self.info_label = tk.Label(self.footer, text="F1: Modo Ayuda • F5: Reiniciar • F11: Pantalla Completa", 
                                   bg=self.COLORS["bg_secondary"], fg="#555", font=("Segoe UI", 9))
        self.info_label.pack(pady=10)

        self.root.bind("<Key>", self.handle_keypress)
        self.root.bind("<BackSpace>", self.handle_backspace)
        self.root.bind("<F5>", lambda e: self.start_practice()) 
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<F1>", self.toggle_hint_mode) 

    def _load_vial_layout(self, btn_style):
        vil_files = glob.glob("*.vil")
        if vil_files:
            self.vial_file_path = vil_files[0]
            try:
                with open(self.vial_file_path, 'r', encoding='utf-8') as f:
                    self.vial_data = json.load(f)
                    
                layer_btn_style = btn_style.copy()
                layer_btn_style["fg"] = self.COLORS["text_active"]
                tk.Button(self.header, text="VER CAPAS", command=self.show_layers, **layer_btn_style).pack(side="left", padx=10)
                
                hint_btn_style = btn_style.copy()
                self.hint_btn = tk.Button(self.header, text="AYUDA (F1): OFF", command=self.toggle_hint_mode, **hint_btn_style)
                self.hint_btn.pack(side="left", padx=10)

                status_text = f"Layout: {self.vial_file_path}"
                status_color = "#666"
            except Exception:
                status_text = "Error leyendo .vil"
                status_color = self.COLORS["text_error"]
        else:
            status_text = "No se encontró archivo .vil"
            status_color = "#666"

        self.debug_label = tk.Label(self.header, text=status_text, bg=self.COLORS["bg_main"], fg=status_color, font=("Consolas", 9))
        self.debug_label.pack(side="right", padx=20)

    # ==========================================
    # LÓGICA DE PISTAS DINÁMICA
    # ==========================================
    def toggle_hint_mode(self, event=None):
        if not self.vial_data:
            self.hint_display.config(text="⚠️ Carga un archivo .vil para usar el asistente.", fg=self.COLORS["text_error"])
            self.root.after(3000, lambda: self.hint_display.config(text=""))
            return

        self.hint_mode_active = not self.hint_mode_active
        
        if hasattr(self, 'hint_btn'):
            if self.hint_mode_active:
                self.hint_btn.config(text="AYUDA (F1): ON", fg=self.COLORS["accent"])
            else:
                self.hint_btn.config(text="AYUDA (F1): OFF", fg="#888")
                
        self.update_hint_display()

    def update_hint_display(self):
        if not self.hint_mode_active or not self.vial_data:
            self.hint_display.config(text="")
            return
            
        if self.current_mode != "words" or len(self.typed_buffer) >= len(self.full_text):
            self.hint_display.config(text="")
            return
            
        target_idx = len(self.typed_buffer)
        for i, char in enumerate(self.typed_buffer):
            if char != self.full_text[i]:
                target_idx = i
                break
                
        target_char = self.full_text[target_idx]
        
        if target_char.isalpha() or target_char == " ":
            self.hint_display.config(text="")
            return
            
        if target_char not in self.QMK_MAP:
            self.hint_display.config(text=f"⚠️ Símbolo '{target_char}' no registrado en QMK.", fg=self.COLORS["text_error"])
            return
            
        target_kc, needs_shift = self.QMK_MAP[target_char]
        location = self.find_keycode_in_layers(target_kc)
        
        if not location:
            self.hint_display.config(text=f"⚠️ Símbolo '{target_char}' no configurado en tu teclado.", fg=self.COLORS["text_error"])
            return
            
        layer_idx, r, c = location
        combo = []
        
        if layer_idx > 0:
            mo_loc = self.find_keycode_in_layers(f"MO({layer_idx})")
            combo.append(self.get_physical_key_label(mo_loc[1], mo_loc[2]) if mo_loc else f"L{layer_idx}")
                
        if needs_shift:
            shift_loc = self.find_keycode_in_layers("KC_LSHIFT") or self.find_keycode_in_layers("KC_RSHIFT")
            combo.append(self.get_physical_key_label(shift_loc[1], shift_loc[2]) if shift_loc else "SHIFT")
        
        combo.append(self.get_physical_key_label(r, c))
        
        hint_text = " + ".join([f"[{k}]" for k in combo])
        visual_char = "↵ (Salto de línea)" if target_char == "\n" else target_char
        
        self.hint_display.config(text=f"💡 {visual_char}   ➜   {hint_text}", fg=self.COLORS["accent"])

    def get_physical_key_label(self, r, c):
        if not self.vial_data: return "?"
        kc = self.vial_data["layout"][0][r][c]
        main_lbl, _ = self.format_keycode(kc)
        return main_lbl

    def find_keycode_in_layers(self, target_kc):
        if not self.vial_data: return None
        for layer_idx, layer in enumerate(self.vial_data["layout"]):
            for r in range(10):
                for c in range(6):
                    if layer[r][c] == target_kc:
                        return (layer_idx, r, c)
        return None

    # ==========================================
    # RENDERIZADO VISUAL DEL TECLADO
    # ==========================================
    def show_layers(self):
        if not self.vial_data: return
        
        layer_win = tk.Toplevel(self.root)
        layer_win.title("Visor de Capas - Silakka54")
        layer_win.geometry("1100x500")
        layer_win.configure(bg=self.COLORS["bg_window"])
        layer_win.grab_set()
        
        btn_frame = tk.Frame(layer_win, bg=self.COLORS["bg_window"], pady=15)
        btn_frame.pack(fill="x")
        
        valid_layers = [i for i, layer in enumerate(self.vial_data.get("layout", [])) 
                        if any(kc not in (-1, "KC_TRNS", "KC_NO") for row in layer for kc in row)]
            
        for i in valid_layers:
            tk.Button(btn_frame, text=f"CAPA {i}", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_active"], 
                      font=("Segoe UI", 10, "bold"), relief="flat", padx=15, cursor="hand2",
                      command=lambda idx=i: self.draw_layer(idx)).pack(side="left", padx=10)
        
        self.layout_canvas = tk.Canvas(layer_win, bg=self.COLORS["bg_window"], bd=0, highlightthickness=0)
        self.layout_canvas.pack(fill="both", expand=True, padx=20, pady=10)
        
        if valid_layers:
            self.draw_layer(valid_layers[0])

    def format_keycode(self, kc):
        if kc in (-1, "KC_NO"): return "", ""
        if kc == "KC_TRNS": return "▽", ""
        
        kc_str = str(kc)
        if kc_str in self.DUAL_LABELS:
            return self.DUAL_LABELS[kc_str]
        
        kc_clean = kc_str.replace("KC_", "")
        if "MO(" in kc_clean:
            return f"L{kc_clean.split('(')[1].split(')')[0]}", ""
            
        return self.QMK_REPLACES.get(kc_clean, kc_clean), ""

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, rx=5, **kwargs):
        points = [x1+rx, y1, x2-rx, y1, x2, y1, x2, y1+rx, x2, y2-rx, x2, y2, x2-rx, y2, x1+rx, y2, x1, y2, x1, y2-rx, x1, y1+rx, x1, y1]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def draw_layer(self, layer_idx):
        self.layout_canvas.delete("all")
        layer_matrix = self.vial_data["layout"][layer_idx]
        
        key_w, key_h, pad = 60, 55, 8
        canvas_width, center_gap = 1050, 120 
        
        start_x_left = (canvas_width / 2) - (6 * (key_w + pad)) - (center_gap / 2)
        start_x_right = (canvas_width / 2) + (center_gap / 2)
        start_y = 30
        
        for r in range(10):
            for c in range(6):
                kc = layer_matrix[r][c]
                if kc == -1: continue 
                
                main_lbl, shift_lbl = self.format_keycode(kc)
                is_right = r >= 5
                
                row_visual = r if not is_right else r - 5
                col_visual = c if not is_right else 5 - c
                
                x = start_x_left + (col_visual * (key_w + pad)) if not is_right else start_x_right + (col_visual * (key_w + pad))
                
                finger_stagger = [25, 25, 10, 0, 15, 20] 
                y = start_y + (row_visual * (key_h + pad)) + finger_stagger[c]
                
                if row_visual == 4:
                    y += 15 
                    if c == 3: y -= 5   
                    if c == 5: y += 10  
                
                is_layer_key = len(main_lbl) > 1 and main_lbl.startswith("L") and main_lbl[1:].isdigit()
                
                color_bg = self.COLORS["bg_secondary"] if is_layer_key else self.COLORS["key_bg"]
                color_txt = self.COLORS["accent"] if is_layer_key else ("#555555" if main_lbl == "▽" else self.COLORS["key_text"])

                self._draw_rounded_rect(self.layout_canvas, x, y, x + key_w, y + key_h, rx=5, 
                                        fill=color_bg, outline=self.COLORS["key_border"], width=2)
                
                if shift_lbl:
                    self.layout_canvas.create_text(x + key_w/2, y + key_h/3, text=shift_lbl, fill=self.COLORS["key_text_shift"], font=("Segoe UI", 10, "bold"))
                    self.layout_canvas.create_text(x + key_w/2, y + key_h/1.5, text=main_lbl, fill=color_txt, font=("Segoe UI", 12, "bold"))
                else:
                    self.layout_canvas.create_text(x + key_w/2, y + key_h/2, text=main_lbl, fill=color_txt, font=("Segoe UI", 11, "bold"))
                                               
    # ==========================================
    # CONTROL DE TEXTO Y PRÁCTICA
    # ==========================================
    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def start_practice(self):
        self.typed_buffer = ""
        self.switch_to_words() if self.current_mode == "words" else self.switch_to_alpha()

    def format_word(self, w):
        if self.capitalize_next or random.random() < 0.15: 
            w = w.capitalize()
            self.capitalize_next = False
        
        rng = random.random()
        
        if rng < 0.04: w = f'"{w}"'
        elif rng < 0.08: w = f"'{w}'"
        elif rng < 0.12: w = f"<{w}>"         
        elif rng < 0.15: w = f"</{w}>"        
        elif rng < 0.20: w = f"({w})"         
        elif rng < 0.25: w = f"[{w}]"         
        elif rng < 0.30: w = f"{{{w}}}"       
        elif rng < 0.33: w = f"*{w}"          
        elif rng < 0.36: w = f"&{w}"          
        elif rng < 0.39: w = f"_{w}"          
        elif rng < 0.42: w = f"${w}"          
        elif rng < 0.45: w = f"#{w}"          
        elif rng < 0.48: w = f"@{w}"          
        elif rng < 0.50: w = f"!{w}"          
        elif rng < 0.58: w = f"{w};"          
        elif rng < 0.63: w = f"{w}()"         
        elif rng < 0.68: w = f"{w}();"        
        elif rng < 0.71: w = f"{w}:"          
        elif rng < 0.74: w = f"{w},"          
        elif rng < 0.77: w = f"{w}="          
        elif rng < 0.80: w = f"{w}=="         
        elif rng < 0.82: w = f"{w}!="         
        elif rng < 0.84: w = f"{w}+"          
        elif rng < 0.86: w = f"{w}++"         
        elif rng < 0.88: w = f"{w}->"         
        elif rng < 0.90: w = f"{w}=>"         
        elif rng < 0.92: w = f"{w}::"          
        elif rng < 0.95: w = f"{w}."          

        self.word_count += 1
        if self.word_count > random.randint(3, 8):
            self.word_count = 0
            self.capitalize_next = True 
            return w + "\n"
        return w + " "

    def get_words(self):
        try:
            url = "https://random-word-api.herokuapp.com/word?number=200"
            with urllib.request.urlopen(url, timeout=5) as response:
                words = json.loads(response.read().decode())
                for w in words: self.word_queue.put(self.format_word(w))
        except:
            for _ in range(200): self.word_queue.put(self.format_word(random.choice(self.FALLBACK_WORDS)))

    def switch_to_words(self):
        self.current_mode = "words"
        self.typed_buffer = ""
        self.full_text = ""
        self.is_fetching = True
        self.word_queue = queue.Queue()
        
        for _ in range(15):
            self.word_queue.put(self.format_word(random.choice(self.FALLBACK_WORDS)))
            
        self.capitalize_next = True
        self.word_count = 0

        self.alpha_frame.pack_forget()
        self.words_frame.pack(fill="both", expand=True)
        
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", tk.END)
        self.text_area.config(state="disabled")
        
        threading.Thread(target=self.get_words, daemon=True).start()
        self.load_words()

    def switch_to_alpha(self):
        self.current_mode = "alphabet"
        self.full_text = string.ascii_lowercase
        self.typed_buffer = ""
        
        self.hint_display.config(text="")
        
        self.words_frame.pack_forget()
        self.alpha_frame.pack(fill="both", expand=True)
        self.update_display()

    def load_words(self):
        if self.word_queue.qsize() > 5:
            content = "".join(self.word_queue.get() for _ in range(self.word_queue.qsize()))
            self.full_text += content
            
            self.text_area.config(state="normal")
            self.text_area.insert(tk.END, content)
            self.text_area.config(state="disabled")
            
            self.is_fetching = False
            self.update_display()
        else:
            self.root.after(200, self.load_words)

    def update_display(self):
        if self.current_mode == "words":
            self.text_area.config(state="normal")
            for tag in ["correct", "wrong", "active"]: self.text_area.tag_remove(tag, "1.0", tk.END)
            
            match_len = 0
            error_idx = -1
            
            for i, char in enumerate(self.typed_buffer):
                if char == self.full_text[i]:
                    match_len += 1
                else:
                    error_idx = i
                    break
            
            if error_idx != -1:
                pos = f"1.0 + {error_idx} chars"
                expected_char = self.full_text[error_idx]
                if expected_char not in (" ", "\n"):
                    self.text_area.delete(pos, f"{pos} + 1 chars")
                    self.text_area.insert(pos, self.typed_buffer[error_idx])
                self.text_area.tag_add("wrong", pos, f"{pos} + 1 chars")
            else:
                if len(self.typed_buffer) < len(self.full_text):
                    pos = f"1.0 + {len(self.typed_buffer)} chars"
                    char_actual = self.text_area.get(pos)
                    char_real = self.full_text[len(self.typed_buffer)]
                    if char_actual != char_real:
                        self.text_area.delete(pos, f"{pos} + 1 chars")
                        self.text_area.insert(pos, char_real)

            if match_len > 0:
                self.text_area.tag_add("correct", "1.0", f"1.0 + {match_len} chars")

            if error_idx == -1 and len(self.typed_buffer) < len(self.full_text):
                start = len(self.typed_buffer)
                sp = self.full_text.find(" ", start)
                nl = self.full_text.find("\n", start)
                end = min(sp if sp != -1 else 9999, nl if nl != -1 else 9999)
                if end != 9999:
                    self.text_area.tag_add("active", f"1.0 + {start} chars", f"1.0 + {end} chars")

            self.text_area.config(state="disabled")
            
            cursor_pos = f"1.0 + {len(self.typed_buffer)} chars"
            self.text_area.mark_set("insert", cursor_pos)
            self.text_area.update_idletasks()
            self.text_area.yview(self.text_area.index(cursor_pos))
            self.text_area.yview_scroll(-4, "units")
            
            self.update_hint_display()
            
        else:
            idx = len(self.typed_buffer)
            if idx < len(self.full_text):
                self.alpha_label.config(text=self.full_text[idx].upper(), fg=self.COLORS["text_active"])
            else:
                self.typed_buffer = ""
                self.update_display()

    def handle_keypress(self, event):
        if event.keysym in ("BackSpace", "Shift_L", "Shift_R", "Caps_Lock", "Escape", "Control_L", "Alt_L", "Alt_R", "Win_L", "Win_R", "F11", "F5", "F1"): return
        
        char = "\n" if event.keysym == "Return" else event.char
        if not char or len(self.typed_buffer) >= len(self.full_text): return

        if self.current_mode == "alphabet":
            if char.lower() == self.full_text[len(self.typed_buffer)]:
                self.typed_buffer += char.lower()
                self.update_display()
            else:
                self.alpha_label.config(text=char.upper(), fg=self.COLORS["text_error"])
                self.root.after(400, self.update_display)
            return

        if len(self.typed_buffer) > 0 and self.typed_buffer[-1] != self.full_text[len(self.typed_buffer) - 1]:
            return 

        self.typed_buffer += char
        self.update_display()
        
        if self.current_mode == "words" and len(self.full_text) - len(self.typed_buffer) < 400 and not self.is_fetching:
            self.is_fetching = True
            threading.Thread(target=self.get_words, daemon=True).start()
            self.load_words()

    def handle_backspace(self, event):
        if self.current_mode != "alphabet" and len(self.typed_buffer) > 0:
            self.typed_buffer = self.typed_buffer[:-1]
            self.update_display()

if __name__ == "__main__":
    root = tk.Tk()
    root.columnconfigure(0, weight=1)
    app = UltimateTrainer(root)
    root.mainloop()