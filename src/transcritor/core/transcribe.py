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

from faster_whisper import WhisperModel

# Segmento normalizado
Seg = namedtuple("Seg", ["start", "end", "text"])

# Raiz do workspace (suporte a PyInstaller frozen e execução normal)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    ROOT = Path(sys._MEIPASS)
else:
    # core/ -> transcritor/ -> src/ -> raiz do projeto
    ROOT = Path(__file__).resolve().parents[2]

INBOX = ROOT / "inbox"
OUTPUT = ROOT / "output"
CONFIG_PATH = Path(__file__).with_name("config.toml")

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
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(toml.load(f))
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

    Se device='cuda' (ou 'auto') falhar ao carregar — por falta de cuDNN/cuBLAS,
    VRAM insuficiente ou GPU ausente — recai para device='cpu', compute_type='int8'.
    """
    device = cfg.get("device", "auto")
    compute_type = cfg.get("compute_type", "int8")
    threads = os.cpu_count() or 4

    if device != "cpu":
        try:
            model = WhisperModel(cfg["model"], device=device, compute_type=compute_type, cpu_threads=threads)
            print(f"Modelo '{cfg['model']}' carregado em {device} ({compute_type}) com {threads} threads.")
            return model
        except Exception as e:
            print(f"[aviso] GPU indisponível ou falhou ({e}).")
            print("[aviso] Recaindo para device='cpu', compute_type='int8'.")

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

    segments_iter, info = model.transcribe(str(path), **kwargs)
    print(f"Idioma detectado: {info.language} (prob {info.language_probability:.2f})", flush=True)

    all_segs = []
    for seg in segments_iter:
        all_segs.append(Seg(seg.start, seg.end, seg.text.strip()))
        # Print em tempo real para a GUI capturar
        print(f"  [{fmt_hms(seg.start)} --> {fmt_hms(seg.end)}] {seg.text.strip()}", flush=True)

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
