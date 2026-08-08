import os
import sys
import json
import traceback
from pathlib import Path

# Adiciona o diretório raiz
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Importa o módulo original do projeto
import tools.transcribe as tr

def run_transcription(files, output_dir, config_override=None):
    """
    Roda a transcrição para uma lista de arquivos.
    """
    if config_override is None:
        config_override = {}
        
    cfg = tr.load_cfg()
    cfg.update(config_override)

    # Redireciona o OUTPUT para a pasta escolhida pelo usuário
    if output_dir:
        tr.OUTPUT = Path(output_dir)

    print(f"[{len(files)} arquivo(s) na fila]", flush=True)

    try:
        model = tr.load_model(cfg)
    except Exception as e:
        print(f"ERRO FATAL: Falha ao carregar modelo: {e}", flush=True)
        return

    on_cpu = cfg.get("device", "cpu") == "cpu"
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
            msg = str(e).lower()
            gpu_err = any(k in msg for k in ("out of memory", "cuda failed", "cublas", "cudnn"))
            if gpu_err and not on_cpu:
                print(f"  [aviso] erro de GPU ({e}).", flush=True)
                print("  [aviso] Recarregando o modelo em CPU (int8) e tentando de novo...", flush=True)
                cfg = dict(cfg, device="cpu", compute_type="int8")
                try:
                    model = tr.load_model(cfg)
                except Exception as e2:
                    print(f"  [erro] falha ao carregar modelo em CPU: {e2}", flush=True)
                    falhas += 1
                    continue
                on_cpu = True
                try:
                    tr.transcribe_one(path, model, cfg)
                except Exception as e3:
                    falhas += 1
                    print(f"  [erro] falha mesmo em CPU: {e3}", flush=True)
            else:
                falhas += 1
                print(f"  [erro] falha ao transcrever {path.name}: {e}\n{traceback.format_exc()}", flush=True)

    print(f"\nCONCLUIDO: {len(files) - falhas}/{len(files)} arquivo(s) transcrito(s).", flush=True)

if __name__ == "__main__":
    # Lê os argumentos JSON passados via sys.stdin
    # Formato: {"files": ["/caminho/a.mp3"], "output_dir": "/caminho/dest", "config": {"model": "medium"}}
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
