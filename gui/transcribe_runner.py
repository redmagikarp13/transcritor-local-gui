import sys
import json
import traceback
from pathlib import Path

# Adiciona o diretório raiz
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Força o tqdm a exibir a barra de progresso (engana o isatty)
class FakeTTY:
    def __init__(self, stream):
        self._stream = stream
    def __getattr__(self, name):
        return getattr(self._stream, name)
    def isatty(self):
        return True

sys.stderr = FakeTTY(sys.stderr)

# Importa o módulo do projeto original, agora adaptado para MLX
import tools.transcribe as tr

def run_transcription(files, output_dir, config_override=None):
    if config_override is None:
        config_override = {}
        
    cfg = tr.load_cfg()
    cfg.update(config_override)

    # Redireciona o OUTPUT
    if output_dir:
        tr.OUTPUT = Path(output_dir)

    print(f"[{len(files)} arquivo(s) na fila para processamento (faster-whisper)]", flush=True)
    print(f"Carregando modelo '{cfg.get('model')}'... (Se for a primeira vez, o download automático pode demorar vários minutos)", flush=True)

    try:
        model = tr.load_model(cfg)
    except Exception as e:
        print(f"ERRO ao carregar o modelo: {e}", flush=True)
        return

    falhas = 0

    for path_str in files:
        path = Path(path_str)
        if not path.exists():
            print(f"ERRO: Arquivo não encontrado: {path}", flush=True)
            falhas += 1
            continue
            
        try:
            tr.transcribe_one(path, model, cfg)
        except Exception as e:
            falhas += 1
            print(f"  [erro] falha ao transcrever {path.name}: {e}\n{traceback.format_exc()}", flush=True)

    print(f"\nCONCLUIDO: {len(files) - falhas}/{len(files)} arquivo(s) transcrito(s).", flush=True)

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
