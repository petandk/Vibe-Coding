#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog, ttk
import os
import re

class CodingTutorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Muscle Tutor")
        self.geometry("1100x700")
        self.configure(bg="#1E1E1E")
        
        # Application State
        self.target_text = ""
        self.current_index = 0
        self.has_error = False
        self.sidebar_visible = True
        self.current_filepath = None
        self.is_completed = False
        self.next_file_path = None
        self.overlay_frame = None
        self.skip_intervals = [] 
        
        # Colors
        self.bg_color = (30, 30, 30)       # #1E1E1E
        self.fg_color = (212, 212, 212)    # #D4D4D4
        self.green_color = "#4CAF50"
        self.red_color = "#F44336"
        self.red_bg = "#5C1010"

        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam") 
        
        style.configure("Treeview", 
                        background="#1E1E1E", 
                        foreground="#D4D4D4", 
                        fieldbackground="#1E1E1E", 
                        borderwidth=0,
                        font=("Consolas", 12),
                        rowheight=40)
        style.map('Treeview', background=[('selected', '#094771')])
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        style.configure("Vertical.TScrollbar",
                        background="#424242",
                        troughcolor="#1E1E1E",
                        bordercolor="#1E1E1E",
                        arrowcolor="#D4D4D4",
                        relief="flat")
        style.map("Vertical.TScrollbar",
                  background=[("active", "#555555")])

    def setup_ui(self):
        # --- Left Panel (Sidebar) ---
        self.left_frame = tk.Frame(self, bg="#252526", width=420) 
        self.left_frame.pack_propagate(False)
        self.left_frame.pack(side="left", fill="y")
        
        sidebar_top = tk.Frame(self.left_frame, bg="#252526")
        sidebar_top.pack(fill="x", padx=5, pady=5)
        
        tk.Button(sidebar_top, text="Open Folder", bg="#333333", fg="white", 
                  relief="flat", activebackground="#444444", activeforeground="white",
                  command=self.open_folder).pack(fill="x")

        tree_frame = tk.Frame(self.left_frame, bg="#1E1E1E")
        tree_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        self.tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse", yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.config(command=self.tree.yview)
        
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # --- Right Panel (Typing Area) ---
        self.right_frame = tk.Frame(self, bg="#1E1E1E")
        self.right_frame.pack(side="right", fill="both", expand=True)

        top_bar = tk.Frame(self.right_frame, bg="#1E1E1E")
        top_bar.pack(fill="x", padx=10, pady=(5, 10))
        
        self.toggle_btn = tk.Button(top_bar, text="◀ Hide Sidebar", bg="#333333", fg="white", 
                                    relief="flat", activebackground="#444444", activeforeground="white",
                                    command=self.toggle_sidebar)
        self.toggle_btn.pack(side="left", padx=(0, 15))

        tk.Label(top_bar, text="Solution Opacity:", bg="#1E1E1E", fg="white").pack(side="left")
        self.opacity_slider = tk.Scale(top_bar, from_=0, to=100, orient="horizontal", 
                                       bg="#1E1E1E", fg="white", highlightthickness=0, 
                                       troughcolor="#333333", activebackground="#094771",
                                       command=self.update_opacity, length=200)
        self.opacity_slider.set(20)
        self.opacity_slider.pack(side="left", padx=10)

        text_frame = tk.Frame(self.right_frame, bg="#1E1E1E")
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self.text_scroll = ttk.Scrollbar(text_frame, orient="vertical")
        self.text_widget = tk.Text(text_frame, bg="#1E1E1E", fg="white", 
                                   font=("Consolas", 14), insertbackground="white", 
                                   borderwidth=0, highlightthickness=0,
                                   yscrollcommand=self.text_scroll.set)
        self.text_scroll.config(command=self.text_widget.yview)

        self.text_scroll.pack(side="right", fill="y")
        self.text_widget.pack(side="left", fill="both", expand=True)
        
        # --- Tag Priority Configuration ---
        # Tags defined later naturally have higher priority when layered.
        self.text_widget.tag_config("space_mark", background="#2A2A2A") # Faint grey for spaces
        self.text_widget.tag_config("tab_mark", background="#1D3B4D")   # Muted deep blue for tabs
        self.text_widget.tag_config("correct", foreground=self.green_color)
        
        # Incorrect is defined last so the red background overrides the whitespace backgrounds
        self.text_widget.tag_config("incorrect", foreground=self.red_color, background=self.red_bg)
        
        self.text_widget.bind("<Key>", self.handle_keypress)

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.left_frame.pack_forget()
            self.toggle_btn.config(text="▶ Show Sidebar")
            self.sidebar_visible = False
        else:
            self.left_frame.pack(side="left", fill="y", before=self.right_frame)
            self.toggle_btn.config(text="◀ Hide Sidebar")
            self.sidebar_visible = True

    def open_folder(self):
        folder_path = filedialog.askdirectory(title="Select Project Folder")
        if folder_path:
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            root_name = os.path.basename(folder_path) or folder_path
            root_node = self.tree.insert("", "end", text=root_name, open=True, values=[folder_path, "directory"])
            self.populate_tree(root_node, folder_path)

    def populate_tree(self, parent, path):
        try:
            entries = os.listdir(path)
        except PermissionError:
            return

        entries.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))

        for entry in entries:
            if entry.startswith('.'):
                continue
                
            full_path = os.path.join(path, entry)
            is_dir = os.path.isdir(full_path)
            
            node = self.tree.insert(parent, "end", text=entry, open=False, 
                                    values=[full_path, "directory" if is_dir else "file"])
            
            if is_dir:
                self.populate_tree(node, full_path)

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = self.tree.item(selected[0])
        values = item.get('values')
        
        if not values:
            return
            
        filepath, item_type = values[0], values[1]
        
        if item_type == 'file':
            self.load_file(filepath)

    def load_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().replace('\r\n', '\n')
        except Exception as e:
            content = f"Error loading file:\n{e}"

        # Reset state for new file
        self.current_filepath = filepath
        self.target_text = content
        self.current_index = 0
        self.has_error = False
        self.is_completed = False
        self.next_file_path = None
        self.skip_intervals = []
        self.close_overlay()
        
        # --- Language Agnostic Comment Parsing ---
        ext = os.path.splitext(filepath)[1].lower()
        basename = os.path.basename(filepath).lower()
        pattern = None

        if ext in ['.c', '.h', '.cpp', '.hpp', '.cc', '.go', '.rs', '.js', '.ts', '.java']:
            pattern = r'/\*[\s\S]*?\*/|//.*'
        elif ext in ['.py']:
            pattern = r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|#.*'
        elif ext in ['.sh', '.rb', '.yml', '.yaml', '.conf'] or basename in ['makefile']:
            pattern = r'#.*'
        elif ext in ['.html', '.xml']:
            pattern = r'<!--[\s\S]*?-->'

        if pattern:
            for match in re.finditer(pattern, self.target_text):
                self.skip_intervals.append((match.start(), match.end()))
        
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", self.target_text)
        self.text_widget.tag_add("ghost", "1.0", tk.END)
        
        # --- Whitespace Background Highlighting ---
        for i, char in enumerate(self.target_text):
            if char == ' ':
                self.text_widget.tag_add("space_mark", f"1.0 + {i} chars")
            elif char == '\t':
                self.text_widget.tag_add("tab_mark", f"1.0 + {i} chars")
        
        self.update_opacity(self.opacity_slider.get())
        self.text_widget.mark_set("insert", "1.0")
        self.text_widget.focus_set()
        
        self.check_auto_skip()

    def check_auto_skip(self):
        """Automatically leaps over detected comment blocks, marking them correct."""
        moved = True
        while moved:
            moved = False
            for start, end in self.skip_intervals:
                if self.current_index == start:
                    pos_start = f"1.0 + {start} chars"
                    pos_end = f"1.0 + {end} chars"
                    
                    self.text_widget.tag_remove("ghost", pos_start, pos_end)
                    self.text_widget.tag_remove("incorrect", pos_start, pos_end)
                    self.text_widget.tag_add("correct", pos_start, pos_end)
                    
                    self.current_index = end
                    self.text_widget.mark_set("insert", f"1.0 + {self.current_index} chars")
                    self.text_widget.see("insert")
                    moved = True
                    break 
                    
        if self.current_index >= len(self.target_text) and not self.is_completed:
            self.current_index = len(self.target_text)
            self.is_completed = True
            self.show_completion_overlay()

    def update_opacity(self, value):
        ratio = float(value) / 100.0
        r = int(self.bg_color[0] + (self.fg_color[0] - self.bg_color[0]) * ratio)
        g = int(self.bg_color[1] + (self.fg_color[1] - self.bg_color[1]) * ratio)
        b = int(self.bg_color[2] + (self.fg_color[2] - self.bg_color[2]) * ratio)
        
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        self.text_widget.tag_config("ghost", foreground=hex_color)

    def get_next_file(self, search_from_path):
        if not search_from_path:
            return None
        
        parent_dir = os.path.dirname(search_from_path)
        try:
            entries = os.listdir(parent_dir)
        except PermissionError:
            return None

        files = []
        for entry in entries:
            if entry.startswith('.'):
                continue
            full_path = os.path.join(parent_dir, entry)
            if os.path.isfile(full_path):
                files.append(entry)
                
        def sort_key(filename):
            base, ext = os.path.splitext(filename.lower())
            is_code_file = 0 if ext in ['.h', '.hpp', '.c', '.cpp'] else 1
            ext_prio = {'.h': 1, '.hpp': 2, '.c': 3, '.cpp': 4}.get(ext, 99)
            return (is_code_file, base, ext_prio, ext)

        files.sort(key=sort_key)
        full_paths = [os.path.join(parent_dir, f) for f in files]
        
        if search_from_path in full_paths:
            idx = full_paths.index(search_from_path)
            if idx + 1 < len(full_paths):
                return full_paths[idx + 1]
        return None

    def show_completion_overlay(self, search_from_path=None):
        if search_from_path is None:
            search_from_path = self.current_filepath
            
        self.next_file_path = self.get_next_file(search_from_path)
        self.close_overlay()
        
        self.overlay_frame = tk.Frame(self.text_widget, bg="#252526", 
                                      highlightbackground="#094771", highlightthickness=2,
                                      padx=40, pady=30)
        self.overlay_frame.place(relx=0.5, rely=0.4, anchor="center")
        
        tk.Label(self.overlay_frame, text="File Complete! 🎉", font=("Consolas", 18, "bold"), 
                 bg="#252526", fg=self.green_color).pack(pady=(0, 15))
        
        if self.next_file_path:
            filename = os.path.basename(self.next_file_path)
            tk.Label(self.overlay_frame, text=f"Next up: {filename}", font=("Consolas", 12), 
                     bg="#252526", fg="white", wraplength=450, justify="center").pack(pady=5)
                     
            tk.Label(self.overlay_frame, text="[Enter] Start  |  [S] Skip  |  [Esc] Close", 
                     font=("Consolas", 10, "bold"), bg="#252526", fg="#888888").pack(pady=(20, 0))
        else:
            tk.Label(self.overlay_frame, text="Folder Complete!", font=("Consolas", 12), 
                     bg="#252526", fg="white").pack(pady=5)
                     
            tk.Label(self.overlay_frame, text="[Esc] Close & Browse Tree", 
                     font=("Consolas", 10, "bold"), bg="#252526", fg="#888888").pack(pady=(20, 0))

    def close_overlay(self):
        if self.overlay_frame:
            self.overlay_frame.destroy()
            self.overlay_frame = None

    def handle_keypress(self, event):
        if self.is_completed:
            if event.keysym == 'Return' and self.next_file_path:
                self.load_file(self.next_file_path)
            elif event.keysym.lower() == 's' and self.next_file_path:
                self.show_completion_overlay(search_from_path=self.next_file_path)
            elif event.keysym == 'Escape':
                self.close_overlay()
            return "break"

        if event.keysym in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Caps_Lock', 'Tab'):
            if event.keysym == 'Tab':
                char = '\t'
            else:
                return "break"
        else:
            char = event.char

        if event.keysym == 'Return':
            char = '\n'

        if event.keysym == 'BackSpace':
            if self.has_error:
                pos = f"1.0 + {self.current_index} chars"
                self.text_widget.tag_remove("incorrect", pos, f"{pos} + 1 char")
                self.text_widget.tag_add("ghost", pos, f"{pos} + 1 char")
                self.has_error = False
            elif self.current_index > 0:
                skipped_block = True
                while skipped_block:
                    skipped_block = False
                    for start, end in self.skip_intervals:
                        if self.current_index == end:
                            pos_start = f"1.0 + {start} chars"
                            pos_end = f"1.0 + {end} chars"
                            
                            self.text_widget.tag_remove("correct", pos_start, pos_end)
                            self.text_widget.tag_add("ghost", pos_start, pos_end)
                            
                            self.current_index = start
                            skipped_block = True
                            break 
                            
                if not skipped_block and self.current_index > 0:
                    self.current_index -= 1
                    pos = f"1.0 + {self.current_index} chars"
                    self.text_widget.tag_remove("correct", pos, f"{pos} + 1 char")
                    self.text_widget.tag_remove("incorrect", pos, f"{pos} + 1 char")
                    self.text_widget.tag_add("ghost", pos, f"{pos} + 1 char")
                
            self.text_widget.mark_set("insert", f"1.0 + {self.current_index} chars")
            self.text_widget.see("insert")
            return "break"

        if self.has_error:
            return "break"

        if self.current_index >= len(self.target_text):
            return "break"

        if not char:
            return "break"

        target_char = self.target_text[self.current_index]
        pos = f"1.0 + {self.current_index} chars"

        if char == target_char:
            self.text_widget.tag_remove("ghost", pos, f"{pos} + 1 char")
            self.text_widget.tag_remove("incorrect", pos, f"{pos} + 1 char")
            self.text_widget.tag_add("correct", pos, f"{pos} + 1 char")
            self.has_error = False
            self.current_index += 1
            
            self.check_auto_skip()
                
        else:
            self.text_widget.tag_remove("ghost", pos, f"{pos} + 1 char")
            self.text_widget.tag_add("incorrect", pos, f"{pos} + 1 char")
            self.has_error = True

        next_pos = f"1.0 + {self.current_index} chars"
        self.text_widget.mark_set("insert", next_pos)
        self.text_widget.see("insert")

        return "break"

if __name__ == "__main__":
    app = CodingTutorApp()
    app.mainloop()
