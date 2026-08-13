import sys
import json
import traceback
import io
from pathlib import Path

# Adiciona src/ ao sys.path para importar os módulos do pacote
SRC_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SRC_DIR))

# Importa o módulo de transcrição
from transcritor.core import transcribe as tr

class LogRedirector:
    """Redireciona stdout para um callback."""
    def __init__(self, callback):
        self.callback = callback
        self.buffer = ""
    
    def write(self, text):
        if text.strip():
            self.callback(text.rstrip())
    
    def flush(self):
        pass

def run_transcription(files, output_dir, config_override=None, log_callback=None):
    """Executa a transcrição.
    
    Args:
        files: Lista de arquivos para transcrever
        output_dir: Diretório de saída
        config_override: Configurações sobrescritas
        log_callback: Função callback para receber logs (opcional)
    """
    if config_override is None:
        config_override = {}

    # Redireciona stdout se houver callback
    original_stdout = sys.stdout
    if log_callback:
        sys.stdout = LogRedirector(log_callback)

    try:
        cfg = tr.load_cfg()
        cfg.update(config_override)

        # Redireciona o OUTPUT
        if output_dir:
            tr.OUTPUT = Path(output_dir)

        print(f"[{len(files)} arquivo(s) na fila para processamento]")

        # Carrega o modelo uma única vez para todos os arquivos
        model = tr.load_model(cfg)

        falhas = 0

        for path_str in files:
            path = Path(path_str)
            if not path.exists():
                print(f"ERRO: Arquivo não encontrado: {path}")
                falhas += 1
                continue

            try:
                tr.transcribe_one(path, cfg, model)
            except Exception as e:
                falhas += 1
                print(f"  [erro] falha ao transcrever {path.name}: {e}\n{traceback.format_exc()}")

        print(f"\nCONCLUIDO: {len(files) - falhas}/{len(files)} arquivo(s) transcrito(s).")
    finally:
        # Restaura stdout
        sys.stdout = original_stdout

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        args = json.loads(input_data)
        run_transcription(
            files=args.get("files", []),
            output_dir=args.get("output_dir"),
            config_override=args.get("config", {})
        )
    except Exception as e:
        print(f"ERRO FATAL NO RUNNER: {e}\n{traceback.format_exc()}", flush=True)
