import os
import sys
import json
import threading
import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
import toml

# Adiciona o diretório raiz
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import gui.backend as backend

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

CONFIG_PATH = ROOT_DIR / "tools" / "config.toml"

class TranscritorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Transcritor Local")
        self.geometry("900x600")

        # grid layout 1x2
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Configuração da barra lateral
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Transcritor Local", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_tab_single = ctk.CTkButton(self.sidebar_frame, text="Arquivo Único", command=lambda: self.select_tab("single"))
        self.btn_tab_single.grid(row=1, column=0, padx=20, pady=10)

        self.btn_tab_batch = ctk.CTkButton(self.sidebar_frame, text="Fila (Lote)", command=lambda: self.select_tab("batch"))
        self.btn_tab_batch.grid(row=2, column=0, padx=20, pady=10)

        self.btn_tab_models = ctk.CTkButton(self.sidebar_frame, text="Modelos", command=lambda: self.select_tab("models"))
        self.btn_tab_models.grid(row=3, column=0, padx=20, pady=10)

        self.btn_tab_settings = ctk.CTkButton(self.sidebar_frame, text="Configurações", command=lambda: self.select_tab("settings"))
        self.btn_tab_settings.grid(row=4, column=0, padx=20, pady=10)

        # Tabs Frames
        self.frames = {}
        
        # --- TAB SINGLE ---
        self.frames["single"] = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["single"].grid_columnconfigure(0, weight=1)
        self.frames["single"].grid_rowconfigure(3, weight=1)
        
        ctk.CTkLabel(self.frames["single"], text="Transcrever Arquivo Único", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.single_file_path = ctk.StringVar()
        self.single_out_path = ctk.StringVar(value=str(ROOT_DIR / "output"))

        f1 = ctk.CTkFrame(self.frames["single"])
        f1.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        f1.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(f1, text="Selecionar Áudio/Vídeo", command=self.browse_single_file).grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkEntry(f1, textvariable=self.single_file_path, state="disabled").grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(f1, text="Pasta de Destino", command=self.browse_single_out).grid(row=1, column=0, padx=10, pady=10)
        ctk.CTkEntry(f1, textvariable=self.single_out_path, state="disabled").grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.btn_run_single = ctk.CTkButton(self.frames["single"], text="INICIAR TRANSCRIÇÃO", height=50, command=self.run_single, fg_color="green", hover_color="darkgreen")
        self.btn_run_single.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        self.log_single = ctk.CTkTextbox(self.frames["single"])
        self.log_single.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

        # --- TAB BATCH ---
        self.frames["batch"] = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["batch"].grid_columnconfigure(0, weight=1)
        self.frames["batch"].grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self.frames["batch"], text="Fila de Transcrição", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=20, pady=20, sticky="w")

        f2 = ctk.CTkFrame(self.frames["batch"])
        f2.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        f2.grid_columnconfigure(0, weight=1)

        f2_btns = ctk.CTkFrame(f2, fg_color="transparent")
        f2_btns.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(f2_btns, text="Adicionar Arquivo(s)", command=self.batch_add_files).pack(side="left", padx=5)
        ctk.CTkButton(f2_btns, text="Limpar Fila", command=self.batch_clear, fg_color="red", hover_color="darkred").pack(side="right", padx=5)

        self.batch_listbox = ctk.CTkTextbox(f2, height=100)
        self.batch_listbox.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.batch_files = []

        self.batch_out_path = ctk.StringVar(value=str(ROOT_DIR / "output"))
        f2_out = ctk.CTkFrame(f2, fg_color="transparent")
        f2_out.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        f2_out.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(f2_out, text="Pasta de Destino", command=self.browse_batch_out).grid(row=0, column=0, padx=5)
        ctk.CTkEntry(f2_out, textvariable=self.batch_out_path, state="disabled").grid(row=0, column=1, padx=5, sticky="ew")

        self.btn_run_batch = ctk.CTkButton(f2, text="PROCESSAR FILA", height=50, command=self.run_batch, fg_color="green", hover_color="darkgreen")
        self.btn_run_batch.grid(row=3, column=0, padx=10, pady=20, sticky="ew")

        self.log_batch = ctk.CTkTextbox(self.frames["batch"])
        self.log_batch.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        # --- TAB MODELS ---
        self.frames["models"] = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["models"].grid_columnconfigure(0, weight=1)
        self.frames["models"].grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(self.frames["models"], text="Gerenciador de Modelos", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        f3 = ctk.CTkFrame(self.frames["models"])
        f3.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(f3, text="Modelos Baixados (Cache Local):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.models_textbox = ctk.CTkTextbox(f3, height=100)
        self.models_textbox.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.model_combo = ctk.CTkComboBox(f3, values=backend.MODELS)
        self.model_combo.grid(row=2, column=0, padx=10, pady=20, sticky="w")
        
        ctk.CTkButton(f3, text="Baixar Modelo", command=self.download_model).grid(row=2, column=1, padx=10, pady=20, sticky="w")
        ctk.CTkButton(f3, text="Excluir Modelo", command=self.delete_model, fg_color="red", hover_color="darkred").grid(row=2, column=2, padx=10, pady=20, sticky="w")

        self.log_models = ctk.CTkTextbox(self.frames["models"])
        self.log_models.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        # --- TAB SETTINGS ---
        self.frames["settings"] = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frames["settings"].grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.frames["settings"], text="Configurações", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=20, pady=20, sticky="w")

        f4 = ctk.CTkFrame(self.frames["settings"])
        f4.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Variáveis
        self.cfg_model = ctk.StringVar(value="medium")
        self.cfg_device = ctk.StringVar(value="cpu")
        self.cfg_compute = ctk.StringVar(value="int8")
        self.cfg_lang = ctk.StringVar(value="auto")

        row_idx = 0
        def add_setting(label, var, values):
            nonlocal row_idx
            ctk.CTkLabel(f4, text=label).grid(row=row_idx, column=0, padx=20, pady=10, sticky="w")
            ctk.CTkComboBox(f4, variable=var, values=values).grid(row=row_idx, column=1, padx=20, pady=10, sticky="w")
            row_idx += 1

        add_setting("Modelo (Model)", self.cfg_model, backend.MODELS)
        add_setting("Dispositivo (Device)", self.cfg_device, ["cpu", "cuda", "auto"])
        add_setting("Precisão (Compute Type)", self.cfg_compute, ["int8", "float16", "float32", "int8_float16"])
        add_setting("Idioma Padrão", self.cfg_lang, ["auto", "pt", "en", "es"])

        ctk.CTkButton(f4, text="Salvar Configurações", command=self.save_settings, fg_color="green", hover_color="darkgreen").grid(row=row_idx, column=0, columnspan=2, pady=30)

        # Initialize
        self.select_tab("single")
        self.load_settings()
        self.refresh_models()
        self.transcription_process = None

    def select_tab(self, tab_name):
        # Esconde todos
        for frame in self.frames.values():
            frame.grid_forget()
        # Mostra o selecionado
        self.frames[tab_name].grid(row=0, column=1, sticky="nsew")

    # --- Funções Single ---
    def browse_single_file(self):
        f = filedialog.askopenfilename(title="Selecione o áudio/vídeo")
        if f:
            self.single_file_path.set(f)

    def browse_single_out(self):
        d = filedialog.askdirectory(title="Selecione a pasta de saída")
        if d:
            self.single_out_path.set(d)

    def run_single(self):
        file_path = self.single_file_path.get()
        if not file_path:
            messagebox.showwarning("Aviso", "Selecione um arquivo!")
            return
        
        self.btn_run_single.configure(state="disabled")
        self.log_single.delete("0.0", "end")
        
        args = {
            "files": [file_path],
            "output_dir": self.single_out_path.get()
        }
        self.start_transcription_thread(args, self.log_single, self.btn_run_single)

    # --- Funções Batch ---
    def batch_add_files(self):
        files = filedialog.askopenfilenames(title="Selecione os arquivos")
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
        d = filedialog.askdirectory(title="Selecione a pasta de saída")
        if d:
            self.batch_out_path.set(d)

    def run_batch(self):
        if not self.batch_files:
            messagebox.showwarning("Aviso", "Adicione arquivos na fila!")
            return
            
        self.btn_run_batch.configure(state="disabled")
        self.log_batch.delete("0.0", "end")
        
        args = {
            "files": self.batch_files,
            "output_dir": self.batch_out_path.get()
        }
        self.start_transcription_thread(args, self.log_batch, self.btn_run_batch)

    # --- Subprocesso de Transcrição ---
    def start_transcription_thread(self, args, log_widget, btn_widget):
        runner_path = str(ROOT_DIR / "gui" / "transcribe_runner.py")
        
        def run():
            try:
                # Inicia o subprocesso lendo json via stdin
                # usa unbuffered (-u) para updates instantâneos
                proc = subprocess.Popen(
                    [sys.executable, "-u", runner_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                # envia args via stdin e fecha
                proc.stdin.write(json.dumps(args))
                proc.stdin.close()
                
                # Lemos stdout linha por linha char por char pra tratar \r
                # Como o faster-whisper usa \r para barra de progresso
                buffer = ""
                while True:
                    char = proc.stdout.read(1)
                    if not char:
                        break
                    if char == '\r':
                        # Se for carriage return, apagamos a última linha do log_widget e colocamos o buffer
                        def update_progress(text):
                            lines = log_widget.get("0.0", "end").split("\n")
                            # remove last empty line from split
                            if len(lines) > 2:
                                log_widget.delete(f"{len(lines)-2}.0", "end")
                                log_widget.insert("end", text + "\n")
                        self.after(0, update_progress, buffer)
                        buffer = ""
                    elif char == '\n':
                        self.after(0, lambda t=buffer: log_widget.insert("end", t + "\n"))
                        self.after(0, log_widget.see, "end")
                        buffer = ""
                    else:
                        buffer += char

                proc.wait()
                self.after(0, lambda: log_widget.insert("end", f"\n[Processo finalizado com código {proc.returncode}]\n"))
                self.after(0, log_widget.see, "end")
                
            except Exception as e:
                self.after(0, lambda err=e: log_widget.insert("end", f"\nErro ao iniciar processo: {err}\n"))
            finally:
                self.after(0, lambda: btn_widget.configure(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    # --- Funções Models ---
    def refresh_models(self):
        downloaded = backend.get_downloaded_models()
        self.models_textbox.delete("0.0", "end")
        if not downloaded:
            self.models_textbox.insert("end", "Nenhum modelo baixado ainda no cache do HuggingFace.\n")
        else:
            for m in downloaded:
                self.models_textbox.insert("end", f" - {m}\n")

    def download_model(self):
        mod = self.model_combo.get()
        self.log_models.insert("end", f"\nSolicitando download: {mod}\n")
        
        def cb(msg):
            self.after(0, lambda m=msg: self.log_models.insert("end", m + "\n"))
            self.after(0, self.log_models.see, "end")

        def run():
            backend.download_model(mod, progress_callback=cb)
            self.after(0, self.refresh_models)
            
        threading.Thread(target=run, daemon=True).start()

    def delete_model(self):
        mod = self.model_combo.get()
        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja excluir o modelo '{mod}'?"):
            success = backend.delete_model(mod)
            if success:
                self.log_models.insert("end", f"\nModelo {mod} excluído com sucesso.\n")
            else:
                self.log_models.insert("end", f"\nFalha ao excluir {mod}. Talvez não esteja baixado.\n")
            self.refresh_models()

    # --- Funções Settings ---
    def load_settings(self):
        if CONFIG_PATH.exists():
            try:
                cfg = toml.load(str(CONFIG_PATH))
                self.cfg_model.set(cfg.get("model", "medium"))
                self.cfg_device.set(cfg.get("device", "cpu"))
                self.cfg_compute.set(cfg.get("compute_type", "int8"))
                
                lang = cfg.get("language", "auto")
                if not lang: lang = "auto"
                self.cfg_lang.set(lang)
            except Exception as e:
                print(f"Erro ao ler config: {e}")

    def save_settings(self):
        cfg = {}
        if CONFIG_PATH.exists():
            try:
                cfg = toml.load(str(CONFIG_PATH))
            except:
                pass
        
        cfg["model"] = self.cfg_model.get()
        cfg["device"] = self.cfg_device.get()
        cfg["compute_type"] = self.cfg_compute.get()
        
        lang = self.cfg_lang.get()
        if lang == "auto":
            cfg["language"] = None
        else:
            cfg["language"] = lang

        try:
            with open(CONFIG_PATH, "w") as f:
                toml.dump(cfg, f)
            messagebox.showinfo("Sucesso", "Configurações salvas!")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar: {e}")

if __name__ == "__main__":
    app = TranscritorGUI()
    app.mainloop()
