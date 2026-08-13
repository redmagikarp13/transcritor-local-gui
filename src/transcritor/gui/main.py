import os
import sys
import json
import threading
import subprocess
import signal
import re
import webbrowser
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
import toml

# Raiz do projeto: gui/ -> transcritor/ -> src/ -> raiz
ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

# Suporte a PyInstaller frozen
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    ROOT_DIR = Path(sys._MEIPASS)
    SRC_DIR = ROOT_DIR

sys.path.insert(0, str(SRC_DIR))

from transcritor.gui import backend as backend

# Tema escuro
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_PATH = Path(__file__).resolve().parents[1] / "core" / "config.toml"

class TranscritorLocalGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Transcritor Local")
        self.geometry("950x650")
        
        self.configure(fg_color="#1E1E1E")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.current_process = None
        self.is_paused = False

        # --- SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#252525")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Transcritor Local",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20), sticky="w")

        self.tabs = {}
        self.tab_buttons = {}

        self.create_sidebar_button("single", "Arquivo Único", 1)
        self.create_sidebar_button("batch", "Fila (Lote)", 2)
        self.create_sidebar_button("models", "Modelos", 3)
        self.create_sidebar_button("settings", "Configurações", 4)
        self.create_sidebar_button("credits", "Créditos", 5)

        # --- ÁREA PRINCIPAL ---
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        # === TAB SINGLE ===
        self.frames["single"] = self.create_card_frame()
        self.frames["single"].grid_rowconfigure(5, weight=1)

        self.create_header(self.frames["single"], "Transcrição Única", 0)

        self.single_file_path = ctk.StringVar()
        self.single_out_path = ctk.StringVar(value=str(ROOT_DIR / "output"))

        # Grupo de Seleção
        g1 = self.create_group(self.frames["single"], 1)
        g1.grid_columnconfigure(0, weight=0)
        g1.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(g1, text="Selecionar Mídia", command=self.browse_single_file, width=120, fg_color="#3A3A3C", hover_color="#4A4A4C").grid(row=0, column=0, padx=15, pady=15, sticky="w")
        ctk.CTkEntry(g1, textvariable=self.single_file_path, state="disabled", fg_color="transparent", border_width=0, text_color="gray80").grid(row=0, column=1, sticky="ew", padx=(0,15))

        ctk.CTkButton(g1, text="Salvar Em", command=self.browse_single_out, width=120, fg_color="#3A3A3C", hover_color="#4A4A4C").grid(row=1, column=0, padx=15, pady=(0,15), sticky="w")
        ctk.CTkEntry(g1, textvariable=self.single_out_path, state="disabled", fg_color="transparent", border_width=0, text_color="gray80").grid(row=1, column=1, sticky="ew", padx=(0,15))

        # Seletor de Idioma para transcrição única
        self.single_lang = ctk.StringVar(value="auto")
        opt1 = ctk.CTkFrame(self.frames["single"], fg_color="transparent")
        opt1.grid(row=2, column=0, padx=20, pady=(0,5), sticky="w")
        ctk.CTkLabel(opt1, text="Idioma do Áudio:").pack(side="left", padx=(0,10))
        ctk.CTkComboBox(opt1, variable=self.single_lang, values=["auto", "pt", "en", "es"], width=100, fg_color="#2C2C2E", border_width=0).pack(side="left")

        # Grupo de Controles
        c1 = ctk.CTkFrame(self.frames["single"], fg_color="transparent")
        c1.grid(row=3, column=0, padx=20, pady=10, sticky="w")

        self.btn_run_single = ctk.CTkButton(c1, text="Iniciar Transcrição", height=35, command=self.run_single, fg_color="#0066CC", hover_color="#005BB5")
        self.btn_run_single.grid(row=0, column=0, padx=(0,5), sticky="w")

        self.btn_pause_single = ctk.CTkButton(c1, text="Pausar", height=35, command=self.toggle_pause, state="disabled", fg_color="#3A3A3C", hover_color="#4A4A4C")
        self.btn_pause_single.grid(row=0, column=1, padx=5, sticky="w")

        self.btn_stop_single = ctk.CTkButton(c1, text="Parar", height=35, command=self.stop_process, state="disabled", fg_color="#3A3A3C", hover_color="#4A4A4C")
        self.btn_stop_single.grid(row=0, column=2, padx=(5,0), sticky="w")

        # Progresso
        self.prog_single = ctk.CTkProgressBar(self.frames["single"], height=10, progress_color="#007AFF", fg_color="#2C2C2E")
        self.prog_single.grid(row=4, column=0, padx=20, pady=(15, 5), sticky="ew")
        self.prog_single.set(0)

        # Log
        self.log_single = ctk.CTkTextbox(self.frames["single"], fg_color="#1C1C1E", text_color="gray80", border_width=1, border_color="#2C2C2E", corner_radius=8)
        self.log_single.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="nsew")

        # === TAB BATCH ===
        self.frames["batch"] = self.create_card_frame()
        self.frames["batch"].grid_rowconfigure(5, weight=1)

        self.create_header(self.frames["batch"], "Fila de Processamento", 0)

        g2 = self.create_group(self.frames["batch"], 1)

        f2_btns = ctk.CTkFrame(g2, fg_color="transparent")
        f2_btns.grid(row=0, column=0, sticky="ew", padx=15, pady=(15,5))
        ctk.CTkButton(f2_btns, text="Adicionar", command=self.batch_add_files, width=100, fg_color="#3A3A3C", hover_color="#4A4A4C").pack(side="left")
        ctk.CTkButton(f2_btns, text="Limpar", command=self.batch_clear, width=100, fg_color="transparent", border_width=1, border_color="#4A4A4C", hover_color="#3A3A3C").pack(side="right")

        self.batch_listbox = ctk.CTkTextbox(g2, height=80, fg_color="#1C1C1E", border_width=0, corner_radius=6)
        self.batch_listbox.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.batch_files = []

        self.batch_out_path = ctk.StringVar(value=str(ROOT_DIR / "output"))
        f2_out = ctk.CTkFrame(g2, fg_color="transparent")
        f2_out.grid(row=2, column=0, pady=(5,15), padx=15, sticky="ew")
        f2_out.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(f2_out, text="Salvar Em", command=self.browse_batch_out, width=100, fg_color="#3A3A3C", hover_color="#4A4A4C").grid(row=0, column=0, padx=(0,10))
        ctk.CTkEntry(f2_out, textvariable=self.batch_out_path, state="disabled", fg_color="transparent", border_width=0).grid(row=0, column=1, sticky="ew")

        # Botões de controle Batch
        c2 = ctk.CTkFrame(self.frames["batch"], fg_color="transparent")
        c2.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        self.btn_run_batch = ctk.CTkButton(c2, text="Processar Fila", height=35, command=self.run_batch, fg_color="#0066CC", hover_color="#005BB5")
        self.btn_run_batch.grid(row=0, column=0, padx=(0,5), sticky="w")

        self.btn_pause_batch = ctk.CTkButton(c2, text="Pausar", height=35, command=self.toggle_pause, state="disabled", fg_color="#3A3A3C", hover_color="#4A4A4C")
        self.btn_pause_batch.grid(row=0, column=1, padx=5, sticky="w")

        self.btn_stop_batch = ctk.CTkButton(c2, text="Parar", height=35, command=self.stop_process, state="disabled", fg_color="#3A3A3C", hover_color="#4A4A4C")
        self.btn_stop_batch.grid(row=0, column=2, padx=(5,0), sticky="w")

        self.prog_batch = ctk.CTkProgressBar(self.frames["batch"], height=10, progress_color="#007AFF", fg_color="#2C2C2E")
        self.prog_batch.grid(row=3, column=0, padx=20, pady=(15, 5), sticky="ew")
        self.prog_batch.set(0)

        self.log_batch = ctk.CTkTextbox(self.frames["batch"], fg_color="#1C1C1E", text_color="gray80", border_width=1, border_color="#2C2C2E", corner_radius=8)
        self.log_batch.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="nsew")

        # === TAB MODELS ===
        self.frames["models"] = self.create_card_frame()
        self.frames["models"].grid_rowconfigure(3, weight=1)

        self.create_header(self.frames["models"], "Modelos de IA", 0)

        g3 = self.create_group(self.frames["models"], 1)

        from huggingface_hub import constants as hf_constants
        cache_path = hf_constants.HF_HUB_CACHE
        ctk.CTkLabel(g3, text="Modelos Baixados no Sistema:", text_color="gray70").grid(row=0, column=0, pady=(15, 5), padx=15, sticky="w")
        ctk.CTkLabel(g3, text=f"Cache: {cache_path}", text_color="gray50", font=ctk.CTkFont(size=11)).grid(row=0, column=1, columnspan=3, pady=(15, 5), padx=(0,15), sticky="e")
        self.models_textbox = ctk.CTkTextbox(g3, height=100, fg_color="#1C1C1E", border_width=0, corner_radius=6)
        self.models_textbox.grid(row=1, column=0, columnspan=4, pady=(0,15), padx=15, sticky="ew")

        self.model_combo = ctk.CTkComboBox(g3, values=backend.MODELS, fg_color="#2C2C2E", border_width=0)
        self.model_combo.grid(row=2, column=0, pady=(0,15), padx=15, sticky="w")

        ctk.CTkButton(g3, text="Baixar", command=self.download_model, width=80, fg_color="#3A3A3C", hover_color="#4A4A4C").grid(row=2, column=1, padx=(10, 5), pady=(0,15))
        ctk.CTkButton(g3, text="Excluir", command=self.delete_model, width=80, fg_color="transparent", border_width=1, border_color="#4A4A4C").grid(row=2, column=2, pady=(0,15), padx=5)
        ctk.CTkButton(g3, text="Definir Padrão", command=self.set_default_model, width=110, fg_color="#0066CC", hover_color="#005BB5").grid(row=2, column=3, pady=(0,15), padx=(5,15))

        self.log_models = ctk.CTkTextbox(self.frames["models"], fg_color="#1C1C1E", text_color="gray80", border_width=1, border_color="#2C2C2E", corner_radius=8)
        self.log_models.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")

        # === TAB SETTINGS ===
        self.frames["settings"] = self.create_card_frame()
        self.frames["settings"].grid_rowconfigure(3, weight=1)

        self.create_header(self.frames["settings"], "Configurações", 0)

        g4 = self.create_group(self.frames["settings"], 1)

        self.cfg_model = ctk.StringVar(value="medium")
        self.cfg_lang = ctk.StringVar(value="auto")
        self.cfg_device = ctk.StringVar(value="auto")
        self.cfg_compute = ctk.StringVar(value="int8")

        ctk.CTkLabel(g4, text="Modelo Padrão:").grid(row=0, column=0, pady=15, padx=20, sticky="w")
        ctk.CTkComboBox(g4, variable=self.cfg_model, values=backend.MODELS, fg_color="#2C2C2E", border_width=0).grid(row=0, column=1, padx=20, pady=15, sticky="e")

        ctk.CTkLabel(g4, text="Idioma Padrão:").grid(row=1, column=0, pady=(0,15), padx=20, sticky="w")
        ctk.CTkComboBox(g4, variable=self.cfg_lang, values=["auto", "pt", "en", "es"], fg_color="#2C2C2E", border_width=0).grid(row=1, column=1, padx=20, pady=(0,15), sticky="e")

        ctk.CTkLabel(g4, text="Processador (Device):").grid(row=2, column=0, pady=(0,15), padx=20, sticky="w")
        ctk.CTkComboBox(g4, variable=self.cfg_device, values=["auto", "cpu", "cuda"], fg_color="#2C2C2E", border_width=0).grid(row=2, column=1, padx=20, pady=(0,15), sticky="e")

        ctk.CTkLabel(g4, text="Precisão (Compute):").grid(row=3, column=0, pady=(0,15), padx=20, sticky="w")
        ctk.CTkComboBox(g4, variable=self.cfg_compute, values=["int8", "float16", "float32"], fg_color="#2C2C2E", border_width=0).grid(row=3, column=1, padx=20, pady=(0,15), sticky="e")

        # Grupo CUDA
        g_cuda = self.create_group(self.frames["settings"], 2)
        ctk.CTkLabel(g_cuda, text="Aceleração por Placa de Vídeo (NVIDIA)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(15, 5), padx=20, sticky="w")
        ctk.CTkLabel(g_cuda, text="Para usar a GPU, você precisa ter o CUDA Toolkit 12 instalado no Windows.\nO programa usará a CPU automaticamente se as bibliotecas não forem encontradas.", text_color="gray60", justify="left").grid(row=1, column=0, pady=(0, 15), padx=20, sticky="w")
        ctk.CTkButton(g_cuda, text="Baixar CUDA Toolkit", command=lambda: webbrowser.open("https://developer.nvidia.com/cuda-downloads"), fg_color="#3A3A3C", hover_color="#4A4A4C").grid(row=1, column=1, padx=20, pady=(0,15), sticky="e")

        ctk.CTkButton(self.frames["settings"], text="Salvar Configurações", command=self.save_settings, width=150, height=35, fg_color="#0066CC", hover_color="#005BB5").grid(row=3, column=0, pady=20, padx=20, sticky="sw")

        # === TAB CREDITS ===
        self.frames["credits"] = self.create_card_frame()
        self.frames["credits"].grid_rowconfigure(2, weight=1)

        self.create_header(self.frames["credits"], "Créditos", 0)

        g5 = self.create_group(self.frames["credits"], 1)

        ctk.CTkLabel(g5, text="Transcritor Local", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(g5, text="Uma interface gráfica multiplataforma para o transcritor-local.", text_color="gray70").pack(pady=(0, 20))

        credits_text = (
            "Desenvolvido por Leonardo e Marcos Accioly.\n\n"
            "Tecnologias utilizadas:\n"
            "- Python & CustomTkinter\n"
            "- Faster-Whisper (CTranslate2)\n"
            "- HuggingFace Hub"
        )
        ctk.CTkLabel(g5, text=credits_text, justify="center").pack(pady=10)

        ctk.CTkLabel(g5, text="© 2026", text_color="gray50", font=ctk.CTkFont(size=10)).pack(pady=(20, 10))

        # Initialize
        self.select_tab("single")
        self.load_settings()
        self.refresh_models()

    # --- FUNÇÕES DE LAYOUT ---
    def create_sidebar_button(self, tab_id, text, row):
        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            command=lambda: self.select_tab(tab_id),
            fg_color="transparent",
            text_color="gray80",
            hover_color="#3A3A3C",
            anchor="w",
            corner_radius=6,
            height=32,
            font=ctk.CTkFont(size=13)
        )
        btn.grid(row=row, column=0, padx=10, pady=2, sticky="ew")
        self.tab_buttons[tab_id] = btn

    def create_card_frame(self):
        f = ctk.CTkFrame(self.main_container, corner_radius=10, fg_color="#2C2C2E")
        f.grid_columnconfigure(0, weight=1)
        return f

    def create_group(self, parent, row):
        g = ctk.CTkFrame(parent, corner_radius=8, fg_color="#1C1C1E")
        g.grid(row=row, column=0, padx=20, pady=10, sticky="ew")
        g.grid_columnconfigure(0, weight=1)
        return g

    def create_header(self, parent, title, row):
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=22, weight="bold"), text_color="white").grid(row=row, column=0, padx=20, pady=(20, 10), sticky="w")

    def select_tab(self, tab_name):
        for frame in self.frames.values():
            frame.grid_forget()
        for btn in self.tab_buttons.values():
            btn.configure(fg_color="transparent", text_color="gray80")
        active_btn = self.tab_buttons[tab_name]
        active_btn.configure(fg_color="#0066CC", text_color="white")
        self.frames[tab_name].grid(row=0, column=0, sticky="nsew")

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
            self.log_single.insert("end", "\n[Transcrição Cancelada pelo Usuário]\n")
            self.log_batch.insert("end", "\n[Transcrição Cancelada pelo Usuário]\n")
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

        lang = self.single_lang.get()
        config_override = {"language": None if lang == "auto" else lang}
        args = {"files": [file_path], "output_dir": self.single_out_path.get(), "config": config_override}
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
        runner_path = str(Path(__file__).resolve().parent / "transcribe_runner.py")

        def log_to_widget(msg):
            """Callback para enviar logs para o widget de log da GUI."""
            self.after(0, lambda m=msg: log_widget.insert("end", m + "\n"))
            self.after(0, log_widget.see, "end")

        def run():
            try:
                # Se estiver rodando como executável compilado, executa o runner diretamente
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    # Importa e executa o runner no mesmo processo
                    sys.path.insert(0, str(Path(__file__).resolve().parent))
                    import transcribe_runner as runner
                    runner.run_transcription(
                        files=args.get("files", []),
                        output_dir=args.get("output_dir"),
                        config_override=args.get("config", {}),
                        log_callback=log_to_widget
                    )
                    self.after(0, lambda: log_widget.insert("end", f"\n[Finalizado]\n"))
                    self.after(0, log_widget.see, "end")
                    self.after(0, lambda: prog_widget.set(1.0))
                else:
                    # Modo desenvolvimento: usa subprocess
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

        if "-->" in text:
            matches = re.findall(r"(\d{2}):(\d{2})\.(\d{3})", text)
            if matches:
                try:
                    current = prog_widget.get()
                    if current < 0.95:
                        prog_widget.set(current + 0.02)
                except: pass

    # --- Funções Models e Settings ---
    def refresh_models(self):
        downloaded = backend.get_downloaded_models()
        self.models_textbox.delete("0.0", "end")
        if not downloaded:
            self.models_textbox.insert("end", "Nenhum modelo baixado localmente.\n")
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
            self.log_models.insert("end", f"\nExcluindo modelo {mod}...\n")
            try:
                success = backend.delete_model(mod)
                self.log_models.insert("end", f"Modelo {mod} excluído com sucesso!\n" if success else f"Modelo {mod} não encontrado.\n")
                self.refresh_models()
            except Exception as e:
                self.log_models.insert("end", f"Erro ao excluir modelo: {e}\n")

    def set_default_model(self):
        model_size = self.model_combo.get()
        self.cfg_model.set(model_size)
        self.save_settings()
        self.log_models.insert("end", f"\nModelo '{model_size}' definido como padrão!\n")
        self.log_models.see("end")

    def load_settings(self):
        if CONFIG_PATH.exists():
            try:
                cfg = toml.load(str(CONFIG_PATH))
                self.cfg_model.set(cfg.get("model", "medium"))
                lang = cfg.get("language", "auto")
                self.cfg_lang.set(lang if lang else "auto")
                self.cfg_device.set(cfg.get("device", "auto"))
                self.cfg_compute.set(cfg.get("compute_type", "int8"))
            except: pass

    def save_settings(self):
        cfg = {}
        if CONFIG_PATH.exists():
            try: cfg = toml.load(str(CONFIG_PATH))
            except: pass
        cfg["model"] = self.cfg_model.get()
        lang = self.cfg_lang.get()
        cfg["language"] = None if lang == "auto" else lang
        cfg["device"] = self.cfg_device.get()
        cfg["compute_type"] = self.cfg_compute.get()
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH, "w") as f: toml.dump(cfg, f)
            messagebox.showinfo("Sucesso", "Configurações salvas!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro: {e}")

if __name__ == "__main__":
    app = TranscritorLocalGUI()
    app.mainloop()
