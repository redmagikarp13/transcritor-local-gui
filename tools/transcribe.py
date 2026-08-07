"""Wrapper de transcrição local com faster-whisper.

Uso:
    python tools/transcribe.py            # transcreve TODOS os áudios em inbox/
    python tools/transcribe.py <arquivo>  # transcreve um arquivo específico

Lê os defaults de tools/config.toml (model, device, compute_type, language,
vad_filter, beam_size, chunk_minutes) e gera, para cada entrada, quatro arquivos
em output/:

    <slug>.txt              -> texto corrido
    <slug>.timestamped.txt  -> linhas '[hh:mm:ss] texto' por segmento
    <slug>.srt              -> legenda SubRip (timestamps com vírgula)
    <slug>.vtt              -> legenda WebVTT (timestamps com ponto)

Roda 100% local, sem upload. Faz fallback automático de GPU (cuda) para CPU
(int8) quando o modelo não carrega ou estoura a VRAM.

ÁUDIOS LONGOS: o faster-whisper calcula a STFT do áudio inteiro de uma vez
(feature_extractor / np.fft.rfft), o que estoura a RAM em arquivos de horas
(ver github SYSTRAN/faster-whisper#1206). Para contornar, este wrapper decodifica
o waveform com o decoder do próprio faster-whisper (PyAV, sem precisar de ffmpeg
no PATH) e transcreve em BLOCOS de `chunk_minutes`, somando o offset de tempo de
cada bloco aos timestamps. Assim a STFT nunca processa mais que `chunk_minutes`
por vez, e a memória fica constante independente da duração total.
"""

import os
import sys
import tomllib
from collections import namedtuple
from pathlib import Path


def _ensure_cuda_dlls() -> None:
    """No Windows, registra os diretórios das DLLs do CUDA (cuBLAS/cuDNN/runtime)
    instaladas via pip (pacotes nvidia-*-cu12) para que o CTranslate2 as encontre
    em tempo de execução.

    Sem isto, a GPU falha com 'Library cublas64_12.dll is not found or cannot be
    loaded' ao computar — mesmo com os pacotes instalados —, porque no Windows o pip
    não coloca essas DLLs no PATH nem ao lado do CTranslate2. Usa a API oficial
    os.add_dll_directory (Python 3.8+). É no-op fora do Windows.
    """
    if os.name != "nt":
        return
    import importlib.util
    for pkg in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_runtime", "nvidia.cuda_nvrtc"):
        try:
            spec = importlib.util.find_spec(pkg)
        except (ImportError, ValueError, ModuleNotFoundError):
            continue
        if not spec or not spec.submodule_search_locations:
            continue
        for base in spec.submodule_search_locations:
            dll_dir = os.path.join(base, "bin")
            if os.path.isdir(dll_dir):
                # Prepender ao PATH é o que DE FATO resolve: o CTranslate2 procura o
                # cuBLAS/cuDNN via PATH, e o os.add_dll_directory sozinho não basta
                # (testado: sem o PATH, dá 'Library cublas64_12.dll is not found').
                if dll_dir not in os.environ.get("PATH", "").split(os.pathsep):
                    os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")
                try:
                    os.add_dll_directory(dll_dir)
                except (OSError, AttributeError):
                    pass


# Tem de rodar ANTES de importar o faster_whisper (que carrega o CTranslate2).
_ensure_cuda_dlls()

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

# Taxa de amostragem que o Whisper espera (16 kHz mono).
SAMPLE_RATE = 16000

# Segmento normalizado (start/end em segundos no tempo REAL do áudio, já com offset).
Seg = namedtuple("Seg", ["start", "end", "text"])

# Raiz do workspace (tools/ é parents[0]; a raiz é parents[1]).
ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "inbox"
OUTPUT = ROOT / "output"
CONFIG_PATH = Path(__file__).with_name("config.toml")

# Extensões de áudio/vídeo aceitas (tudo que o PyAV/ffmpeg costuma decodificar).
AUDIO_EXT = {
    ".mp3", ".mp4", ".m4a", ".wav", ".ogg",
    ".flac", ".aac", ".webm", ".mkv", ".mov",
}

# Defaults usados caso falte algum campo no config.toml.
DEFAULTS = {
    "model": "medium",
    "device": "cuda",
    "compute_type": "int8",
    "language": "pt",
    "vad_filter": True,
    "beam_size": 5,
    "chunk_minutes": 20,
}


def load_cfg() -> dict:
    """Carrega o config.toml e preenche os campos ausentes com os defaults."""
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            cfg.update(tomllib.load(f))
    # language pode vir como "auto" -> faster-whisper espera None para detectar.
    if str(cfg.get("language", "")).lower() in ("", "auto", "none"):
        cfg["language"] = None
    return cfg


def fmt_ts(seconds: float, sep: str = ",") -> str:
    """Formata segundos como 'hh:mm:ss<sep>mmm' (sep=',' para SRT, '.' para VTT).

    Trabalha em milissegundos inteiros para evitar a imprecisão de float do
    cálculo ingênuo `(t % 1) * 1000`.
    """
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def fmt_hms(seconds: float) -> str:
    """Formata segundos como 'hh:mm:ss' (sem milissegundos), para o .timestamped.txt."""
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
    device = cfg["device"]
    compute_type = cfg["compute_type"]
    if device != "cpu":
        try:
            model = WhisperModel(cfg["model"], device=device, compute_type=compute_type)
            print(f"Modelo '{cfg['model']}' carregado em {device} ({compute_type}).")
            return model
        except Exception as e:
            print(f"[aviso] GPU indisponível ou falhou ({e}).")
            print("[aviso] Recaindo para device='cpu', compute_type='int8'.")
    model = WhisperModel(cfg["model"], device="cpu", compute_type="int8")
    print(f"Modelo '{cfg['model']}' carregado em cpu (int8).")
    return model


def write_outputs(slug: str, segments: list) -> None:
    """Gera os quatro formatos de saída em output/ para a lista de segmentos."""
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # 1) Texto corrido.
    plain = " ".join(s.text.strip() for s in segments).strip()
    (OUTPUT / f"{slug}.txt").write_text(plain + "\n", encoding="utf-8")

    # 2) Com timestamps legíveis por segmento.
    timestamped = "\n".join(
        f"[{fmt_hms(s.start)}] {s.text.strip()}" for s in segments
    )
    (OUTPUT / f"{slug}.timestamped.txt").write_text(
        timestamped + "\n", encoding="utf-8"
    )

    # 3) Legenda SRT (índice 1-based, timestamps com vírgula, bloco separado por linha em branco).
    srt_blocks = []
    for i, s in enumerate(segments, 1):
        srt_blocks.append(
            f"{i}\n"
            f"{fmt_ts(s.start, sep=',')} --> {fmt_ts(s.end, sep=',')}\n"
            f"{s.text.strip()}\n"
        )
    (OUTPUT / f"{slug}.srt").write_text("\n".join(srt_blocks), encoding="utf-8")

    # 4) Legenda VTT (cabeçalho WEBVTT, timestamps com ponto).
    vtt_blocks = ["WEBVTT\n"]
    for s in segments:
        vtt_blocks.append(
            f"{fmt_ts(s.start, sep='.')} --> {fmt_ts(s.end, sep='.')}\n"
            f"{s.text.strip()}\n"
        )
    (OUTPUT / f"{slug}.vtt").write_text("\n".join(vtt_blocks), encoding="utf-8")


def transcribe_one(path: Path, model: WhisperModel, cfg: dict) -> None:
    """Transcreve um único arquivo em blocos e escreve os outputs."""
    print(f"\nTranscrevendo: {path.name}")

    # Decodifica o áudio inteiro para waveform 16 kHz mono (float32). Usa PyAV, que
    # vem com o faster-whisper — não exige ffmpeg no PATH. O waveform é linear na
    # duração (~460 MB para 2 h); o que estourava a RAM era a STFT do todo, não isto.
    audio = decode_audio(str(path), sampling_rate=SAMPLE_RATE)
    total_s = len(audio) / SAMPLE_RATE

    chunk_min = max(1, int(cfg.get("chunk_minutes", 20)))
    chunk_samples = chunk_min * 60 * SAMPLE_RATE
    n_chunks = max(1, (len(audio) + chunk_samples - 1) // chunk_samples)
    print(f"  duração: {fmt_hms(total_s)} | {n_chunks} bloco(s) de até {chunk_min} min")

    vad_filter = bool(cfg.get("vad_filter", True))
    tkwargs = dict(
        language=cfg["language"],
        beam_size=cfg["beam_size"],
        vad_filter=vad_filter,
    )
    # min_silence_duration_ms ajuda em áudios longos a cortar silêncios curtos.
    if vad_filter:
        tkwargs["vad_parameters"] = dict(min_silence_duration_ms=500)

    all_segs = []
    for idx in range(n_chunks):
        start_sample = idx * chunk_samples
        end_sample = min(len(audio), start_sample + chunk_samples)
        chunk = audio[start_sample:end_sample]
        offset = start_sample / SAMPLE_RATE

        if n_chunks > 1:
            print(f"  bloco {idx + 1}/{n_chunks} (offset {fmt_hms(offset)})", flush=True)

        # transcribe() retorna (generator, info); iterar é o que dispara o trabalho.
        # Os timestamps voltam relativos ao bloco -> somamos o offset do bloco.
        segments_gen, _info = model.transcribe(chunk, **tkwargs)
        got = False
        for s in segments_gen:
            all_segs.append(Seg(s.start + offset, s.end + offset, s.text.strip()))
            got = True
            # Sinal de vida em tempo real (tempo absoluto já transcrito).
            print(f"\r    transcrito até {fmt_hms(s.end + offset)} / {fmt_hms(total_s)}",
                  end="", flush=True)
        if got:
            print()  # quebra a linha do progresso ao fim do bloco

    if not all_segs:
        print("  [aviso] nenhum segmento de fala detectado (áudio mudo ou só silêncio?).")
        return

    slug = path.stem
    write_outputs(slug, all_segs)
    print(f"  OK -> {slug} (.txt / .timestamped.txt / .srt / .vtt)")


def collect_targets() -> list:
    """Resolve os arquivos-alvo: argumento da linha de comando ou toda a inbox/."""
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.exists():
            print(f"[erro] arquivo não encontrado: {target}")
            return []
        return [target]
    if not INBOX.exists():
        print(f"[erro] pasta inbox não encontrada: {INBOX}")
        return []
    return sorted(
        p for p in INBOX.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXT
    )


def main() -> int:
    cfg = load_cfg()

    targets = collect_targets()
    if not targets:
        print("Nada para transcrever (inbox vazia ou arquivo inválido).")
        return 1

    print(f"Arquivos para transcrever: {len(targets)}")
    model = load_model(cfg)
    on_cpu = cfg["device"] == "cpu"

    falhas = 0
    for path in targets:
        try:
            transcribe_one(path, model, cfg)
        except Exception as e:
            msg = str(e).lower()
            gpu_err = any(k in msg for k in ("out of memory", "cuda failed", "cublas", "cudnn"))
            if gpu_err and not on_cpu:
                # Erro de GPU (OOM de VRAM etc.) DURANTE a transcrição: recarrega o
                # modelo em CPU e refaz este arquivo (e segue os próximos em CPU).
                print(f"  [aviso] erro de GPU ({e}).")
                print("  [aviso] Recarregando o modelo em CPU (int8) e tentando de novo...")
                cfg = dict(cfg, device="cpu", compute_type="int8")
                model = load_model(cfg)
                on_cpu = True
                try:
                    transcribe_one(path, model, cfg)
                except Exception as e2:
                    falhas += 1
                    print(f"  [erro] falha mesmo em CPU: {e2}")
            else:
                falhas += 1
                print(f"  [erro] falha ao transcrever {path.name}: {e}")

    total = len(targets)
    print(f"\nConcluído: {total - falhas}/{total} arquivo(s) transcrito(s). Saída em: {OUTPUT}")
    return 0 if falhas == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
