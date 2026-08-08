import os
import sys
import json
import threading
import subprocess
import signal
import re
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
import toml

# Adiciona o diretório raiz
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import gui.backend as backend

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

CONFIG_PATH = ROOT_DIR / "tools" / "config.toml"

class TranscritorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Transcritor Local (MLX)")
        self.geometry("900x680")

        # Layout principal
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Process control
        self.current_process = None
        self.is_paused = False

        # Barra lateral minimalista
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="transparent")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Transcritor MLX", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Estilo dos botões da sidebar
        btn_kwargs = {"fg_color": "transparent", "text_color": ("gray10", "gray90"), "hover_color": ("gray70", "gray30"), "anchor": "w"}

        self.btn_tab_single = ctk.CTkButton(self.sidebar_frame, text="Arquivo Único", command=lambda: self.select_tab("single"), **btn_kwargs)
        self.btn_tab_single.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.btn_tab_batch = ctk.CTkButton(self.sidebar_frame, text="Fila (Lote)", command=lambda: self.select_tab("batch"), **btn_kwargs)
        self.btn_tab_batch.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.btn_tab_models = ctk.CTkButton(self.sidebar_frame, text="Modelos", command=lambda: self.select_tab("models"), **btn_kwargs)
        self.btn_tab_models.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.btn_tab_settings = ctk.CTkButton(self.sidebar_frame, text="Configurações", command=lambda: self.select_tab("settings"), **btn_kwargs)
        self.btn_tab_settings.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        self.frames = {}
        
        # --- TAB SINGLE ---
        self.frames["single"] = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray95", "gray15"))
        self.frames["single"].grid_columnconfigure(0, weight=1)
        self.frames["single"].grid_rowconfigure(5, weight=1)
        
        ctk.CTkLabel(self.frames["single"], text="Transcrição Única", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=30, pady=(30, 15), sticky="w")
        
        self.single_file_path = ctk.StringVar()
        self.single_out_path = ctk.StringVar(value=str(ROOT_DIR / "output"))

        f1 = ctk.CTkFrame(self.frames["single"], fg_color="transparent")
        f1.grid(row=1, column=0, padx=30, pady=5, sticky="ew")
        f1.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(f1, text="Selecionar Mídia", command=self.browse_single_file, width=120).grid(row=0, column=0, padx=(0, 10), pady=10)
        ctk.CTkEntry(f1, textvariable=self.single_file_path, state="disabled", fg_color="transparent").grid(row=0, column=1, sticky="ew")
        
        ctk.CTkButton(f1, text="Salvar Em", command=self.browse_single_out, width=120).grid(row=1, column=0, padx=(0, 10), pady=10)
        ctk.CTkEntry(f1, textvariable=self.single_out_path, state="disabled", fg_color="transparent").grid(row=1, column=1, sticky="ew")

        # Botões de controle Single
        c1 = ctk.CTkFrame(self.frames["single"], fg_color="transparent")
        c1.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        c1.grid_columnconfigure(0, weight=1)
        c1.grid_columnconfigure(1, weight=1)
        c1.grid_columnconfigure(2, weight=1)

        self.btn_run_single = ctk.CTkButton(c1, text="Iniciar", height=40, command=self.run_single)
        self.btn_run_single.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.btn_pause_single = ctk.CTkButton(c1, text="Pausar", height=40, command=self.toggle_pause, state="disabled", fg_color="transparent", border_width=1)
        self.btn_pause_single.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_stop_single = ctk.CTkButton(c1, text="Parar", height=40, command=self.stop_process, state="disabled", fg_color="transparent", border_width=1, hover_color="darkred")
        self.btn_stop_single.grid(row=0, column=2, padx=5, sticky="ew")

        self.prog_single = ctk.CTkProgressBar(self.frames["single"])
        self.prog_single.grid(row=3, column=0, padx=30, pady=(10, 10), sticky="ew")
        self.prog_single.set(0)

        self.log_single = ctk.CTkTextbox(self.frames["single"], fg_color=("gray90", "gray10"), text_color=("gray20", "gray80"))
        self.log_single.grid(row=4, column=0, padx=30, pady=(0, 30), sticky="nsew")

        # --- TAB BATCH ---
        self.frames["batch"] = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray95", "gray15"))
        self.frames["batch"].grid_columnconfigure(0, weight=1)
        self.frames["batch"].grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self.frames["batch"], text="Fila de Processamento", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=30, pady=(30, 15), sticky="w")

        f2 = ctk.CTkFrame(self.frames["batch"], fg_color="transparent")
        f2.grid(row=1, column=0, padx=30, pady=5, sticky="ew")
        f2.grid_columnconfigure(0, weight=1)

        f2_btns = ctk.CTkFrame(f2, fg_color="transparent")
        f2_btns.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(f2_btns, text="Adicionar", command=self.batch_add_files, width=100).pack(side="left", pady=5)
        ctk.CTkButton(f2_btns, text="Limpar Fila", command=self.batch_clear, width=100, fg_color="transparent", border_width=1).pack(side="right", pady=5)

        self.batch_listbox = ctk.CTkTextbox(f2, height=80, fg_color="transparent", border_width=1)
        self.batch_listbox.grid(row=1, column=0, pady=10, sticky="ew")
        self.batch_files = []

        self.batch_out_path = ctk.StringVar(value=str(ROOT_DIR / "output"))
        f2_out = ctk.CTkFrame(f2, fg_color="transparent")
        f2_out.grid(row=2, column=0, pady=5, sticky="ew")
        f2_out.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(f2_out, text="Salvar Em", command=self.browse_batch_out, width=100).grid(row=0, column=0, padx=(0,10))
        ctk.CTkEntry(f2_out, textvariable=self.batch_out_path, state="disabled", fg_color="transparent").grid(row=0, column=1, sticky="ew")

        # Botões de controle Batch
        c2 = ctk.CTkFrame(self.frames["batch"], fg_color="transparent")
        c2.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        c2.grid_columnconfigure(0, weight=1)
        c2.grid_columnconfigure(1, weight=1)
        c2.grid_columnconfigure(2, weight=1)

        self.btn_run_batch = ctk.CTkButton(c2, text="Processar Fila", height=40, command=self.run_batch)
        self.btn_run_batch.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.btn_pause_batch = ctk.CTkButton(c2, text="Pausar", height=40, command=self.toggle_pause, state="disabled", fg_color="transparent", border_width=1)
        self.btn_pause_batch.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_stop_batch = ctk.CTkButton(c2, text="Parar", height=40, command=self.stop_process, state="disabled", fg_color="transparent", border_width=1, hover_color="darkred")
        self.btn_stop_batch.grid(row=0, column=2, padx=5, sticky="ew")

        self.prog_batch = ctk.CTkProgressBar(self.frames["batch"])
        self.prog_batch.grid(row=3, column=0, padx=30, pady=(10, 10), sticky="ew")
        self.prog_batch.set(0)

        self.log_batch = ctk.CTkTextbox(self.frames["batch"], fg_color=("gray90", "gray10"), text_color=("gray20", "gray80"))
        self.log_batch.grid(row=4, column=0, padx=30, pady=(0, 30), sticky="nsew")

        # --- TAB MODELS ---
        self.frames["models"] = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray95", "gray15"))
        self.frames["models"].grid_columnconfigure(0, weight=1)
        self.frames["models"].grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(self.frames["models"], text="Modelos MLX (Cache)", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=30, pady=(30, 15), sticky="w")
        
        f3 = ctk.CTkFrame(self.frames["models"], fg_color="transparent")
        f3.grid(row=1, column=0, padx=30, pady=5, sticky="ew")
        f3.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(f3, text="Baixados:").grid(row=0, column=0, pady=(0, 5), sticky="w")
        self.models_textbox = ctk.CTkTextbox(f3, height=80, fg_color="transparent", border_width=1)
        self.models_textbox.grid(row=1, column=0, columnspan=3, pady=5, sticky="ew")
        
        self.model_combo = ctk.CTkComboBox(f3, values=backend.MODELS)
        self.model_combo.grid(row=2, column=0, pady=20, sticky="w")
        
        ctk.CTkButton(f3, text="Baixar", command=self.download_model, width=100).grid(row=2, column=1, padx=10, pady=20)
        ctk.CTkButton(f3, text="Excluir", command=self.delete_model, width=100, fg_color="transparent", border_width=1).grid(row=2, column=2, pady=20)

        self.log_models = ctk.CTkTextbox(self.frames["models"], fg_color=("gray90", "gray10"), text_color=("gray20", "gray80"))
        self.log_models.grid(row=3, column=0, padx=30, pady=(0, 30), sticky="nsew")

        # --- TAB SETTINGS ---
        self.frames["settings"] = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray95", "gray15"))
        self.frames["settings"].grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.frames["settings"], text="Configurações", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=30, pady=(30, 15), sticky="w")

        f4 = ctk.CTkFrame(self.frames["settings"], fg_color="transparent")
        f4.grid(row=1, column=0, padx=30, pady=5, sticky="nsew")
        f4.grid_columnconfigure(1, weight=1)
        
        self.cfg_model = ctk.StringVar(value="medium")
        self.cfg_lang = ctk.StringVar(value="auto")

        row_idx = 0
        def add_setting(label, var, values):
            nonlocal row_idx
            ctk.CTkLabel(f4, text=label).grid(row=row_idx, column=0, pady=10, sticky="w")
            ctk.CTkComboBox(f4, variable=var, values=values).grid(row=row_idx, column=1, padx=20, pady=10, sticky="w")
            row_idx += 1

        add_setting("Modelo MLX", self.cfg_model, backend.MODELS)
        add_setting("Idioma Padrão", self.cfg_lang, ["auto", "pt", "en", "es"])

        ctk.CTkButton(f4, text="Salvar", command=self.save_settings, width=150, height=40).grid(row=row_idx, column=0, columnspan=2, pady=30, sticky="w")

        # Initialize
        self.select_tab("single")
        self.load_settings()
        self.refresh_models()

    def select_tab(self, tab_name):
        for frame in self.frames.values():
            frame.grid_forget()
        
        for btn in [self.btn_tab_single, self.btn_tab_batch, self.btn_tab_models, self.btn_tab_settings]:
            btn.configure(fg_color="transparent")
            
        active_btn = {
            "single": self.btn_tab_single,
            "batch": self.btn_tab_batch,
            "models": self.btn_tab_models,
            "settings": self.btn_tab_settings
        }[tab_name]
        active_btn.configure(fg_color=("gray85", "gray25"))
        
        self.frames[tab_name].grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

    # --- Controle de Processos ---
    def toggle_pause(self):
        if not self.current_process: return
        
        try:
            if self.is_paused:
                os.kill(self.current_process.pid, signal.SIGCONT)
                self.is_paused = False
                self.btn_pause_single.configure(text="Pausar")
                self.btn_pause_batch.configure(text="Pausar")
                self.log_single.insert("end", "\n[Transcrição Retomada]\n")
                self.log_batch.insert("end", "\n[Transcrição Retomada]\n")
            else:
                os.kill(self.current_process.pid, signal.SIGSTOP)
                self.is_paused = True
                self.btn_pause_single.configure(text="Retomar")
                self.btn_pause_batch.configure(text="Retomar")
                self.log_single.insert("end", "\n[Transcrição Pausada...]\n")
                self.log_batch.insert("end", "\n[Transcrição Pausada...]\n")
        except Exception as e:
            print(f"Erro ao pausar: {e}")

    def stop_process(self):
        if not self.current_process: return
        try:
            self.current_process.terminate()
            self.log_single.insert("end", "\n[Transcrição Interrompida pelo Usuário]\n")
            self.log_batch.insert("end", "\n[Transcrição Interrompida pelo Usuário]\n")
        except Exception as e:
            print(f"Erro ao parar: {e}")

    # --- Funções Single ---
    def browse_single_file(self):
        f = filedialog.askopenfilename()
        if f: self.single_file_path.set(f)

    def browse_single_out(self):
        d = filedialog.askdirectory()
        if d: self.single_out_path.set(d)

    def run_single(self):
        file_path = self.single_file_path.get()
        if not file_path: return
        
        self.btn_run_single.configure(state="disabled")
        self.btn_pause_single.configure(state="normal", text="Pausar")
        self.btn_stop_single.configure(state="normal")
        
        self.log_single.delete("0.0", "end")
        self.prog_single.set(0)
        self.is_paused = False
        
        args = {"files": [file_path], "output_dir": self.single_out_path.get()}
        self.start_transcription_thread(args, self.log_single, self.btn_run_single, self.prog_single, self.btn_pause_single, self.btn_stop_single)

    # --- Funções Batch ---
    def batch_add_files(self):
        files = filedialog.askopenfilenames()
        for f in files:
            if f not in self.batch_files:
                self.batch_files.append(f)
        self.update_batch_listbox()

    def batch_clear(self):
        self.batch_files = []
        self.update_batch_listbox()

    def update_batch_listbox(self):
        self.batch_listbox.delete("0.0", "end")
        for f in self.batch_files:
            self.batch_listbox.insert("end", f + "\n")

    def browse_batch_out(self):
        d = filedialog.askdirectory()
        if d: self.batch_out_path.set(d)

    def run_batch(self):
        if not self.batch_files: return
        
        self.btn_run_batch.configure(state="disabled")
        self.btn_pause_batch.configure(state="normal", text="Pausar")
        self.btn_stop_batch.configure(state="normal")
        
        self.log_batch.delete("0.0", "end")
        self.prog_batch.set(0)
        self.is_paused = False
        
        args = {"files": self.batch_files, "output_dir": self.batch_out_path.get()}
        self.start_transcription_thread(args, self.log_batch, self.btn_run_batch, self.prog_batch, self.btn_pause_batch, self.btn_stop_batch)

    # --- Subprocesso ---
    def start_transcription_thread(self, args, log_widget, btn_run, prog_widget, btn_pause, btn_stop):
        runner_path = str(ROOT_DIR / "gui" / "transcribe_runner.py")
        
        def run():
            try:
                self.current_process = subprocess.Popen(
                    [sys.executable, "-u", runner_path],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )
                self.current_process.stdin.write(json.dumps(args))
                self.current_process.stdin.close()
                
                buffer = ""
                while True:
                    char = self.current_process.stdout.read(1)
                    if not char: break
                    if char == '\r':
                        self.handle_progress_line(buffer, log_widget, prog_widget, is_cr=True)
                        buffer = ""
                    elif char == '\n':
                        self.handle_progress_line(buffer, log_widget, prog_widget, is_cr=False)
                        buffer = ""
                    else:
                        buffer += char

                self.current_process.wait()
                self.after(0, lambda: log_widget.insert("end", f"\n[Finalizado]\n"))
                self.after(0, log_widget.see, "end")
                self.after(0, lambda: prog_widget.set(1.0))
            except Exception as e:
                self.after(0, lambda: log_widget.insert("end", f"\nErro: {e}\n"))
            finally:
                self.current_process = None
                self.after(0, lambda: btn_run.configure(state="normal"))
                self.after(0, lambda: btn_pause.configure(state="disabled"))
                self.after(0, lambda: btn_stop.configure(state="disabled"))

        threading.Thread(target=run, daemon=True).start()

    def handle_progress_line(self, text, log_widget, prog_widget, is_cr):
        # Em mlx-whisper com verbose=True os prints saem linha por linha normais.
        def update_log():
            if is_cr:
                lines = log_widget.get("0.0", "end").split("\n")
                if len(lines) > 2:
                    log_widget.delete(f"{len(lines)-2}.0", "end")
                    log_widget.insert("end", text + "\n")
            else:
                log_widget.insert("end", text + "\n")
                log_widget.see("end")
        self.after(0, update_log)

        # O mlx-whisper geralmente printa [00:00.000 --> 00:05.000] Algum texto...
        # Podemos tentar parsear o timestamp final de cada linha para o progresso.
        if "-->" in text:
            matches = re.findall(r"(\d{2}):(\d{2})\.(\d{3})", text)
            if matches:
                # Pegar o último timestamp da linha
                try:
                    m, s, ms = map(int, matches[-1])
                    t_sec = m * 60 + s
                    # Como mlx-whisper não nos dá a duração total no print, 
                    # a barra de progresso em transcrição pode ser apenas um indicador visual,
                    # Mas tentaremos estimar se o usuário já souber. Por hora deixamos como indeterminado 
                    # ou subimos aos poucos. Aqui fazemos um bump para mostrar atividade.
                    current = prog_widget.get()
                    if current < 0.95:
                        prog_widget.set(current + 0.01)
                except: pass

    # --- Funções Models e Settings ---
    def refresh_models(self):
        downloaded = backend.get_downloaded_models()
        self.models_textbox.delete("0.0", "end")
        if not downloaded:
            self.models_textbox.insert("end", "Nenhum modelo baixado no cache MLX.\n")
        else:
            for m in downloaded: self.models_textbox.insert("end", f" - {m}\n")

    def download_model(self):
        mod = self.model_combo.get()
        self.log_models.insert("end", f"\nBaixando: {mod}\n")
        def cb(msg):
            self.after(0, lambda m=msg: self.log_models.insert("end", m + "\n"))
            self.after(0, self.log_models.see, "end")
        def run():
            backend.download_model(mod, progress_callback=cb)
            self.after(0, self.refresh_models)
        threading.Thread(target=run, daemon=True).start()

    def delete_model(self):
        mod = self.model_combo.get()
        if messagebox.askyesno("Confirmar", f"Excluir '{mod}'?"):
            success = backend.delete_model(mod)
            self.log_models.insert("end", f"\n{mod} excluído.\n" if success else f"\nFalha. {mod} não encontrado.\n")
            self.refresh_models()

    def load_settings(self):
        if CONFIG_PATH.exists():
            try:
                cfg = toml.load(str(CONFIG_PATH))
                self.cfg_model.set(cfg.get("model", "medium"))
                lang = cfg.get("language", "auto")
                self.cfg_lang.set(lang if lang else "auto")
            except: pass

    def save_settings(self):
        cfg = {}
        if CONFIG_PATH.exists():
            try: cfg = toml.load(str(CONFIG_PATH))
            except: pass
        cfg["model"] = self.cfg_model.get()
        # Removemos os campos inúteis pro mlx (device/compute_type)
        if "device" in cfg: del cfg["device"]
        if "compute_type" in cfg: del cfg["compute_type"]
        
        lang = self.cfg_lang.get()
        cfg["language"] = None if lang == "auto" else lang
        try:
            with open(CONFIG_PATH, "w") as f: toml.dump(cfg, f)
            messagebox.showinfo("Sucesso", "Configurações salvas para MLX!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro: {e}")

if __name__ == "__main__":
    app = TranscritorGUI()
    app.mainloop()
