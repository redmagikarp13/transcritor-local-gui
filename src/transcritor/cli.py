import sys
import os
from pathlib import Path

def main():
    """Entrypoint CLI para o Transcritor Local."""
    # Redireciona a chamada para o script de transcrição principal em core/transcribe.py
    core_dir = Path(__file__).parent / "core"
    transcribe_script = core_dir / "transcribe.py"
    
    if transcribe_script.exists():
        os.execv(sys.executable, [sys.executable, str(transcribe_script)] + sys.argv[1:])
    else:
        print("Erro: Script de transcrição não encontrado.")
        sys.exit(1)

if __name__ == "__main__":
    main()