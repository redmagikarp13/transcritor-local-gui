"""Wrapper de transcrição local usando faster-whisper (cross-platform).

Gera para cada entrada quatro arquivos em output/:
    <slug>.txt              -> texto corrido
    <slug>.timestamped.txt  -> linhas '[hh:mm:ss] texto' por segmento
    <slug>.srt              -> legenda SubRip (timestamps com vírgula)
    <slug>.vtt              -> legenda WebVTT (timestamps com ponto)
"""

import os
import sys
import toml
from collections import namedtuple
from pathlib import Path

# Registrar DLLs do CUDA no PATH (Windows) antes de importar faster_whisper
def _register_nvidia_dlls():
    """Adiciona as DLLs do NVIDIA CUDA ao PATH e ao carregador de DLLs do Windows para o CTranslate2 encontrar.
    
    Procura em múltiplos locais:
    1. Bibliotecas pip instaladas no ambiente atual ou globalmente (%APPDATA%\\Python, %LOCALAPPDATA%\\Programs\\Python, etc.)
    2. Ambientes virtuais (.venv, venv) próximos ao executável ou workspace
    3. Pastas locais (nvidia/, cuda/, bin/ ou DLLs na mesma pasta)
    4. CUDA Toolkit instalado no sistema (CUDA_PATH e C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\...)
    5. Diretórios já no PATH do sistema
    """
    if sys.platform != "win32":
        return []
    
    nvidia_paths = []
    candidates = []
    
    # 1. Sys paths e site-packages padrão
    try:
        import site
        if hasattr(site, "getsitepackages"):
            for sp in site.getsitepackages():
                candidates.append(Path(sp))
        if hasattr(site, "getusersitepackages"):
            candidates.append(Path(site.getusersitepackages()))
    except Exception:
        pass

    try:
        candidates.append(Path(sys.executable).parent / "Lib" / "site-packages")
        candidates.append(Path(sys.executable).parent.parent / "Lib" / "site-packages")
        candidates.append(Path(sys.prefix) / "Lib" / "site-packages")
        if hasattr(sys, "base_prefix"):
            candidates.append(Path(sys.base_prefix) / "Lib" / "site-packages")
    except Exception:
        pass

    # 2. Caminhos do Python no usuário (AppData / LocalAppData) e TranscritorLocal
    appdata = os.environ.get("APPDATA")
    if appdata:
        try:
            candidates.extend(Path(appdata).glob("Python/Python*/site-packages"))
            candidates.append(Path(appdata) / "TranscritorLocal")
            candidates.append(Path(appdata) / "TranscritorLocal" / "nvidia")
        except Exception:
            pass

    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        try:
            candidates.extend(Path(localappdata).glob("Programs/Python/Python*/Lib/site-packages"))
            candidates.append(Path(localappdata) / "TranscritorLocal")
            candidates.append(Path(localappdata) / "TranscritorLocal" / "nvidia")
        except Exception:
            pass

    # 3. Instalações globais comuns C:\Python*
    try:
        candidates.extend(Path("C:/").glob("Python*/Lib/site-packages"))
    except Exception:
        pass

    # 4. Ambientes virtuais e pastas próximas ao executável / cwd
    base_dirs = [Path.cwd(), Path(sys.executable).parent, Path(sys.executable).parent.parent]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dirs.append(Path(sys._MEIPASS))
    
    for base in base_dirs:
        candidates.append(base / ".venv" / "Lib" / "site-packages")
        candidates.append(base / "venv" / "Lib" / "site-packages")
        candidates.append(base / "nvidia")
        candidates.append(base / "cuda" / "bin")
        candidates.append(base / "bin")
        candidates.append(base)

    # 5. CUDA Toolkit instalado no sistema
    cuda_base_paths = [
        Path(os.environ.get("CUDA_PATH", "")),
        Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA"),
    ]
    for env_k, env_v in os.environ.items():
        if env_k.startswith("CUDA_PATH_") and env_v:
            cuda_base_paths.append(Path(env_v))

    for cuda_base in cuda_base_paths:
        if cuda_base and cuda_base.exists():
            if "Toolkit" in str(cuda_base):
                try:
                    for version_dir in cuda_base.iterdir():
                        if version_dir.is_dir():
                            for sub in ["bin", "bin/x64", "nvvm/bin"]:
                                p = version_dir / sub
                                if p.exists():
                                    nvidia_paths.append(str(p))
                except Exception:
                    pass
            else:
                for sub in ["bin", "bin/x64", "nvvm/bin"]:
                    p = cuda_base / sub
                    if p.exists():
                        nvidia_paths.append(str(p))

    # Processa candidatos
    for c in set(candidates):
        if not c or not c.exists():
            continue
        nvidia_root = c / "nvidia" if (c / "nvidia").exists() else (c if c.name == "nvidia" else None)
        if nvidia_root and nvidia_root.is_dir():
            for pkg in ["cublas", "cudnn", "cuda_nvrtc", "cuda_runtime"]:
                bin_dir = nvidia_root / pkg / "bin"
                if bin_dir.exists():
                    nvidia_paths.append(str(bin_dir))
        try:
            if list(c.glob("cublas*.dll")) or list(c.glob("cudnn*.dll")):
                nvidia_paths.append(str(c))
        except Exception:
            pass

    # 6. PATH do sistema
    current_path = os.environ.get("PATH", "")
    for path_str in current_path.split(os.pathsep):
        if not path_str:
            continue
        p = Path(path_str)
        if p.exists():
            if "nvidia" in str(p).lower():
                nvidia_paths.append(str(p))
            else:
                try:
                    if list(p.glob("cublas*.dll")) or list(p.glob("cudnn*.dll")):
                        nvidia_paths.append(str(p))
                except Exception:
                    pass

    # Remove duplicatas e paths inexistentes
    nvidia_paths = list(set(p for p in nvidia_paths if p and Path(p).is_dir()))

    if nvidia_paths:
        os.environ["PATH"] = os.pathsep.join(nvidia_paths) + os.pathsep + current_path
        if hasattr(os, "add_dll_directory"):
            for p in nvidia_paths:
                try:
                    os.add_dll_directory(p)
                except Exception:
                    pass

    return nvidia_paths

_register_nvidia_dlls()

from faster_whisper import WhisperModel

# Segmento normalizado
Seg = namedtuple("Seg", ["start", "end", "text"])

# Raiz do workspace (suporte a PyInstaller frozen e execução normal)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BUNDLE_DIR = Path(sys._MEIPASS)
    # Aponta o faster-whisper para o ffmpeg embutido no executável
    _ffmpeg = BUNDLE_DIR / "ffmpeg.exe" if sys.platform == "win32" else BUNDLE_DIR / "ffmpeg"
    if _ffmpeg.exists():
        os.environ["PATH"] = str(BUNDLE_DIR) + os.pathsep + os.environ.get("PATH", "")
    # Em modo compilado, a raiz de trabalho é a pasta onde o executável está
    ROOT = Path(sys.executable).parent
    # Config do usuário tem preferência; fallback para a empacotada no bundle
    USER_CONFIG_PATH = ROOT / "config.toml"
    BUNDLED_CONFIG_PATH = Path(__file__).with_name("config.toml")
    CONFIG_PATH = USER_CONFIG_PATH if USER_CONFIG_PATH.exists() else BUNDLED_CONFIG_PATH
else:
    # core/ -> transcritor/ -> src/ -> raiz do projeto
    ROOT = Path(__file__).resolve().parents[2]
    CONFIG_PATH = Path(__file__).with_name("config.toml")

INBOX = ROOT / "inbox"
OUTPUT = ROOT / "output"

AUDIO_EXT = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".webm", ".mkv", ".mov"}

DEFAULTS = {
    "model": "medium",
    "language": "auto",
    "device": "auto",
    "compute_type": "int8",
}

def load_cfg() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.is_file():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(toml.load(f))
        except Exception:
            pass
    # language pode vir como "auto" -> faster-whisper espera None para detectar.
    if str(cfg.get("language", "")).lower() in ("", "auto", "none"):
        cfg["language"] = None
    return cfg

def fmt_ts(seconds: float, sep: str = ",") -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

def fmt_hms(seconds: float) -> str:
    total_s = int(seconds)
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def load_model(cfg: dict) -> WhisperModel:
    """Carrega o WhisperModel com fallback automático de GPU para CPU.

    Se device='cuda' (ou 'auto') falhar ao carregar ou executar teste — por falta de cuDNN/cuBLAS,
    VRAM insuficiente ou GPU ausente — recai para device='cpu', compute_type='int8'.
    """
    device = cfg.get("device", "auto")
    compute_type = cfg.get("compute_type", "int8")
    threads = os.cpu_count() or 4

    if device != "cpu":
        try:
            model = WhisperModel(cfg["model"], device=device, compute_type=compute_type, cpu_threads=threads)
            
            # Validação imediata (warm-up) para garantir que cuBLAS/cuDNN estão presentes e funcionais
            if device in ("cuda", "auto"):
                import numpy as np
                import ctranslate2
                dummy = ctranslate2.StorageView.from_array(np.zeros((1, 80, 3000), dtype=np.float32))
                model.model.encode(dummy)

            print(f"Modelo '{cfg['model']}' carregado em {device} ({compute_type}) com {threads} threads.")
            return model
        except Exception as e:
            print(f"[aviso] GPU indisponível ou DLLs ausentes: {e}")
            print("[aviso] Para usar GPU, instale as bibliotecas NVIDIA:")
            print("         pip install nvidia-cublas-cu12 \"nvidia-cudnn-cu12==9.*\"")
            print("[aviso] Recaindo automaticamente para device='cpu', compute_type='int8'.")

    model = WhisperModel(cfg["model"], device="cpu", compute_type="int8", cpu_threads=threads)
    print(f"Modelo '{cfg['model']}' carregado em cpu (int8) usando {threads} threads.")
    return model


def write_outputs(slug: str, segments: list) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    plain = " ".join(s.text.strip() for s in segments).strip()
    (OUTPUT / f"{slug}.txt").write_text(plain + "\n", encoding="utf-8")

    timestamped = "\n".join(f"[{fmt_hms(s.start)}] {s.text.strip()}" for s in segments)
    (OUTPUT / f"{slug}.timestamped.txt").write_text(timestamped + "\n", encoding="utf-8")

    srt_blocks = []
    for i, s in enumerate(segments, 1):
        srt_blocks.append(f"{i}\n{fmt_ts(s.start, sep=',')} --> {fmt_ts(s.end, sep=',')}\n{s.text.strip()}\n")
    (OUTPUT / f"{slug}.srt").write_text("\n".join(srt_blocks), encoding="utf-8")

    vtt_blocks = ["WEBVTT\n"]
    for s in segments:
        vtt_blocks.append(f"{fmt_ts(s.start, sep='.')} --> {fmt_ts(s.end, sep='.')}\n{s.text.strip()}\n")
    (OUTPUT / f"{slug}.vtt").write_text("\n".join(vtt_blocks), encoding="utf-8")

def transcribe_one(path: Path, cfg: dict, model: WhisperModel = None) -> None:
    print(f"\nTranscrevendo: {path.name}", flush=True)

    if model is None:
        model = load_model(cfg)

    kwargs = {"beam_size": 5, "vad_filter": True}
    if cfg.get("language"):
        kwargs["language"] = cfg["language"]

    print(f"Usando modelo faster-whisper: {cfg['model']}", flush=True)

    def _execute_transcribe(active_model):
        segments_iter, info = active_model.transcribe(str(path), **kwargs)
        print(f"Idioma detectado: {info.language} (prob {info.language_probability:.2f})", flush=True)
        all_segs = []
        for seg in segments_iter:
            all_segs.append(Seg(seg.start, seg.end, seg.text.strip()))
            print(f"  [{fmt_hms(seg.start)} --> {fmt_hms(seg.end)}] {seg.text.strip()}", flush=True)
        return all_segs

    try:
        all_segs = _execute_transcribe(model)
    except Exception as e:
        err_msg = str(e).lower()
        if any(k in err_msg for k in ["cublas", "cudnn", "cuda", "out of memory", "driver", "failed to load", "not found"]):
            print(f"  [aviso] Falha na execução via GPU ({e}). Alternando para CPU...", flush=True)
            threads = os.cpu_count() or 4
            cpu_model = WhisperModel(cfg["model"], device="cpu", compute_type="int8", cpu_threads=threads)
            all_segs = _execute_transcribe(cpu_model)
        else:
            raise

    if not all_segs:
        print("  [aviso] nenhum segmento de fala detectado.")
        return

    slug = path.stem
    write_outputs(slug, all_segs)
    print(f"  OK -> {slug} (.txt / .timestamped.txt / .srt / .vtt)", flush=True)

def collect_targets() -> list:
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.exists():
            return []
        return [target]
    if not INBOX.exists():
        return []
    return sorted(p for p in INBOX.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXT)

def main() -> int:
    cfg = load_cfg()
    targets = collect_targets()
    if not targets:
        print("Nada para transcrever.")
        return 1

    model = load_model(cfg)

    falhas = 0
    for path in targets:
        try:
            transcribe_one(path, cfg, model)
        except Exception as e:
            falhas += 1
            print(f"  [erro] falha ao transcrever {path.name}: {e}")

    total = len(targets)
    print(f"\nConcluído: {total - falhas}/{total} arquivo(s) transcrito(s). Saída em: {OUTPUT}")
    return 0 if falhas == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
