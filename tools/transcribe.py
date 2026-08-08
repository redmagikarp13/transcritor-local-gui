"""Wrapper de transcrição local otimizado para Mac Silicon (MLX).

Gera para cada entrada quatro arquivos em output/:
    <slug>.txt              -> texto corrido
    <slug>.timestamped.txt  -> linhas '[hh:mm:ss] texto' por segmento
    <slug>.srt              -> legenda SubRip (timestamps com vírgula)
    <slug>.vtt              -> legenda WebVTT (timestamps com ponto)
"""

import os
import sys
import tomllib
from collections import namedtuple
from pathlib import Path

try:
    import mlx_whisper
except ImportError:
    print("ERRO: mlx-whisper não instalado. Rode: pip install mlx-whisper")
    sys.exit(1)

# Segmento normalizado
Seg = namedtuple("Seg", ["start", "end", "text"])

# Raiz do workspace
ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "inbox"
OUTPUT = ROOT / "output"
CONFIG_PATH = Path(__file__).with_name("config.toml")

AUDIO_EXT = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".webm", ".mkv", ".mov"}

DEFAULTS = {
    "model": "medium",
    "language": "auto",
}

def load_cfg() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            cfg.update(tomllib.load(f))
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

def transcribe_one(path: Path, cfg: dict) -> None:
    print(f"\nTranscrevendo: {path.name}", flush=True)

    model_repo = f"mlx-community/whisper-{cfg['model']}-mlx"
    kwargs = {"path_or_hf_repo": model_repo, "verbose": True}
    
    if cfg.get("language"):
        kwargs["language"] = cfg["language"]

    print(f"Usando modelo MLX: {model_repo}", flush=True)
    
    # O verbose=True faz o mlx-whisper printar no stdout os segmentos sendo detectados,
    # então a nossa GUI vai capturar esses prints para mostrar o log em tempo real.
    result = mlx_whisper.transcribe(str(path), **kwargs)

    all_segs = [Seg(s["start"], s["end"], s["text"].strip()) for s in result["segments"]]

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

    falhas = 0
    for path in targets:
        try:
            transcribe_one(path, cfg)
        except Exception as e:
            falhas += 1
            print(f"  [erro] falha ao transcrever {path.name}: {e}")

    total = len(targets)
    print(f"\nConcluído: {total - falhas}/{total} arquivo(s) transcrito(s). Saída em: {OUTPUT}")
    return 0 if falhas == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
