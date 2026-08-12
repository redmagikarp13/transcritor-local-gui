# SPEC — Transcritor Local (Whisper) · workspace ICM `transcritor-local`

> Spec para criar uma pasta ICM especializada em transcrever áudios longos
> localmente, de graça, com Whisper acelerado por GPU pequena.
> Escopo escolhido: **híbrido** (CLI de transcrição + stage leve de pós-processamento por IA).
> Data: 2026-06-05

---

## 1. Objetivo

Jogar um arquivo de áudio/vídeo numa pasta, rodar um comando, e receber a
transcrição em PT-BR em múltiplos formatos (texto corrido, com timestamps,
legenda `.srt`/`.vtt`) — tudo local, sem custo, sem upload pra nuvem.

Casos de uso do Marquito: reuniões (Solunar etc.), entrevistas, aulas, áudios
do WhatsApp, gravações longas de formação no Cefor.

### Requisitos confirmados
- Formatos de entrada padrão: `mp3`, `mp4`, `m4a`, `wav`, `ogg`, `flac`, etc. (qualquer coisa que o ffmpeg leia).
- Saídas: **texto corrido (`.txt`)**, **com timestamps**, **legenda (`.srt`/`.vtt`)**.
- Diarização (quem falou): **módulo opcional, desligado por padrão**.
- Gratuito e 100% local.
- Áudios **muito longos** (horas) precisam funcionar sem cortar manualmente.

---

## 2. Decisão técnica central (e por que)

### 2.1 Realidade da máquina do Marquito
| Item | O que o Windows mostra | Realidade pra CUDA |
|---|---|---|
| NVIDIA GeForce MX150 | "~10 GB" | **2 GB de VRAM dedicada** (GDDR5). O resto é *shared memory* (RAM via PCIe), inútil/lenta pra Whisper. |
| Intel UHD Graphics | "8 GB" | **0 GB dedicada** — usa RAM compartilhada. Não serve pra acelerar Whisper de forma prática. |

> ⚠️ **Passo 0 da implementação:** confirmar a VRAM real rodando `nvidia-smi`
> (coluna *Memory-Usage*, valor à direita = VRAM total). Se confirmar 2 GB, o
> modelo padrão é `medium`. Se por acaso for uma variante de 4 GB, libera `large-v3`.

### 2.2 Engine: `faster-whisper`, não o Whisper original
O Whisper original da OpenAI (`pip install openai-whisper`) carrega o modelo em
PyTorch e é pesado: `large` quer ~10 GB de VRAM. **Não cabe em 2 GB.**

`faster-whisper` reimplementa o Whisper sobre **CTranslate2**:
- ~4× mais rápido com o mesmo modelo.
- Suporta quantização `int8` → o modelo ocupa ~⅓ da memória.
- **Não precisa de PyTorch** (instalação mais leve no Windows).
- Tem **VAD filter** embutido (Voice Activity Detection) — pula silêncios, o que
  acelera muito áudios longos e elimina as "alucinações" típicas do Whisper em
  trechos mudos.

### 2.3 Interface: `whisper-ctranslate2` (CLI drop-in)
`whisper-ctranslate2` é um CLI que embrulha o `faster-whisper` com **a mesma
sintaxe do Whisper original**. O comando do Colab praticamente não muda:

```bash
# Colab (antes)
whisper "tamara-192.mp3" --model large --language pt

# Local com faster-whisper (agora) — mesma cara, GPU pequena
whisper-ctranslate2 "tamara-192.mp3" --model medium --language pt \
  --device cuda --compute_type int8 --vad_filter True --output_format all
```

`--output_format all` já cospe `.txt`, `.srt`, `.vtt`, `.tsv` e `.json` de uma vez.

### 2.4 Modelo padrão por cenário
| VRAM real | Modelo padrão | `compute_type` | Observação |
|---|---|---|---|
| 2 GB (MX150) | `medium` | `int8` | Bom equilíbrio qualidade/PT-BR. ~1.5 GB. |
| 4 GB | `large-v3` | `int8` | Melhor qualidade. ~3 GB. |
| Sem GPU / OOM | `medium` ou `small` | `int8` (CPU) | Ver 2.5. |

### 2.5 GPU vs CPU — benchmarkar, não assumir
A MX150 é fraca (384 CUDA cores, TDP ~10-25W). Numa CPU moderna de 8 threads, o
`faster-whisper` em `int8` na **CPU** pode chegar perto ou até superar essa GPU.
O spec inclui um passo de benchmark (ver §6) pra escolher `--device` por padrão.
Regra prática: se a GPU der OOM ou ficar abaixo de ~1× realtime, usar CPU.

### 2.6 Intel UHD
Ignorada nesta versão. Acelerar Whisper nela exigiria `whisper.cpp` com
Vulkan/OpenVINO — esforço alto, ganho incerto. Fica como nota de "experimento futuro".

---

## 3. Estrutura da pasta ICM (híbrida)

```
transcritor-local/
├── CLAUDE.md                 # identidade + roteamento do workspace
├── CONTEXT.md                # como usar (cheatsheet de comandos)
├── setup/
│   └── install.md            # instalação passo a passo (Win + CUDA + ffmpeg)
├── inbox/                    # joga os áudios/vídeos aqui
│   └── .gitkeep
├── output/                   # transcrições saem aqui (.txt/.srt/.vtt/.timestamped.txt)
│   └── .gitkeep
├── tools/
│   ├── transcribe.py         # wrapper: batch + defaults bons + multi-output organizado
│   ├── requirements.txt
│   └── config.toml           # modelo, device, idioma padrão (editável sem mexer no código)
└── stages/
    ├── 01-transcribe/        # STAGE MECÂNICO: áudio bruto -> transcrição crua
    │   ├── CONTEXT.md
    │   └── output/           # = pasta output/ raiz (ou symlink lógico)
    └── 02-postprocess/       # STAGE IA (opcional): transcrição crua -> limpa/resumo/ata
        ├── CONTEXT.md
        └── references/
            ├── limpeza.md    # prompt: remove vícios de fala, corrige pontuação
            ├── resumo.md     # prompt: resumo executivo + tópicos
            └── ata.md        # prompt: vira ata de reunião com decisões/ações
```

**Por que híbrido:** o Stage 01 é determinístico (roda script, não gasta token de
IA). O Stage 02 é onde o Claude entra pra transformar a transcrição crua em algo
útil (ata, resumo, post) — e é **opcional**, só roda quando você quiser.

---

## 4. Setup (`setup/install.md`)

Pré-requisitos no Windows:

```powershell
# 1. ffmpeg (decodifica qualquer formato de áudio/vídeo)
winget install --id Gyan.FFmpeg -e
#   confirmar: ffmpeg -version

# 2. Python 3.10–3.12 (se ainda não tiver)
winget install --id Python.Python.3.12 -e

# 3. Ambiente virtual dedicado ao transcritor
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 4. Engine de transcrição
pip install whisper-ctranslate2

# 5. Bibliotecas CUDA pro faster-whisper (CTranslate2 usa cuBLAS + cuDNN 9)
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

# 6. Verificar GPU e VRAM real
nvidia-smi
```

Notas:
- `faster-whisper`/CTranslate2 trabalha com **CUDA 12 + cuDNN 9**. Os pacotes pip
  `nvidia-cublas-cu12` e `nvidia-cudnn-cu12` resolvem isso sem instalar o CUDA Toolkit inteiro.
- O download do modelo (`medium` ~1.5 GB) acontece na primeira execução e fica em cache local.
- Se `--device cuda` der erro de cuDNN/`Library not found`, ver troubleshooting no §8.

---

## 5. O wrapper `tools/transcribe.py`

Objetivo: rodar a transcrição com bons defaults, em lote (toda a `inbox/`) ou num
arquivo específico, e organizar as saídas com nome `<slug>` na pasta `output/`.

### Comportamento esperado
- `python tools/transcribe.py` → transcreve **tudo** que estiver em `inbox/`.
- `python tools/transcribe.py "caminho/audio.m4a"` → transcreve um arquivo.
- Lê defaults de `config.toml` (modelo, device, idioma) — sobrescrevíveis por flag.
- Para cada entrada, gera em `output/`:
  - `<slug>.txt` — texto corrido limpo
  - `<slug>.timestamped.txt` — `[hh:mm:ss] texto` por segmento (o "com timestamps")
  - `<slug>.srt` e `<slug>.vtt` — legendas
- Liga `--vad_filter` por padrão (áudios longos).
- Mostra progresso (segmentos / duração processada).
- Faz fallback automático cuda → cpu se a GPU der OOM.

### `config.toml` (exemplo)
```toml
model = "medium"        # medium (2GB) | large-v3 (4GB+)
device = "cuda"         # cuda | cpu | auto
compute_type = "int8"   # int8 (pouca VRAM) | float16 (mais VRAM) | int8 (CPU)
language = "pt"
vad_filter = true
```

### Esboço de implementação (referência — usa a lib `faster_whisper` direto pra controlar os writers)
```python
import sys, tomllib
from pathlib import Path
from datetime import timedelta
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
INBOX, OUTPUT = ROOT / "inbox", ROOT / "output"
AUDIO_EXT = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".webm", ".mkv", ".mov"}

def load_cfg():
    with open(Path(__file__).with_name("config.toml"), "rb") as f:
        return tomllib.load(f)

def ts(seconds, sep=",", hms_only=False):
    td = timedelta(seconds=seconds)
    h, rem = divmod(int(td.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    ms = int((td.total_seconds() % 1) * 1000)
    if hms_only:
        return f"{h:02}:{m:02}:{s:02}"
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"

def transcribe(path, model, cfg):
    segments, info = model.transcribe(
        str(path),
        language=cfg["language"],
        vad_filter=cfg.get("vad_filter", True),
        beam_size=5,
    )
    segments = list(segments)  # materializa (faz o trabalho pesado)
    slug = path.stem
    # .txt corrido
    (OUTPUT / f"{slug}.txt").write_text(
        " ".join(s.text.strip() for s in segments), encoding="utf-8")
    # .timestamped.txt
    (OUTPUT / f"{slug}.timestamped.txt").write_text(
        "\n".join(f"[{ts(s.start, hms_only=True)}] {s.text.strip()}" for s in segments),
        encoding="utf-8")
    # .srt
    srt = "\n".join(
        f"{i}\n{ts(s.start)} --> {ts(s.end)}\n{s.text.strip()}\n"
        for i, s in enumerate(segments, 1))
    (OUTPUT / f"{slug}.srt").write_text(srt, encoding="utf-8")
    # .vtt
    vtt = "WEBVTT\n\n" + "\n".join(
        f"{ts(s.start, sep='.')} --> {ts(s.end, sep='.')}\n{s.text.strip()}\n"
        for s in segments)
    (OUTPUT / f"{slug}.vtt").write_text(vtt, encoding="utf-8")
    print(f"  OK -> {slug} (.txt/.timestamped.txt/.srt/.vtt)")

def main():
    cfg = load_cfg()
    try:
        model = WhisperModel(cfg["model"], device=cfg["device"], compute_type=cfg["compute_type"])
    except Exception as e:                      # fallback GPU -> CPU
        print(f"GPU falhou ({e}); usando CPU.")
        model = WhisperModel(cfg["model"], device="cpu", compute_type="int8")
    targets = [Path(sys.argv[1])] if len(sys.argv) > 1 else \
              [p for p in INBOX.iterdir() if p.suffix.lower() in AUDIO_EXT]
    if not targets:
        print("Nada pra transcrever (inbox vazia)."); return
    OUTPUT.mkdir(exist_ok=True)
    for p in targets:
        print(f"Transcrevendo: {p.name}")
        transcribe(p, model, cfg)

if __name__ == "__main__":
    main()
```

> Nota: o esboço acima usa a lib `faster_whisper` direto (controle total dos
> writers, incl. o `.timestamped.txt` custom). Alternativa mais simples de manter:
> o wrapper só chama `whisper-ctranslate2 ... --output_format all` por baixo e
> renomeia/organiza. Decidir na implementação — recomendo a lib direto pelo
> controle do formato com timestamps legíveis.

### `requirements.txt`
```
whisper-ctranslate2
faster-whisper
nvidia-cublas-cu12
nvidia-cudnn-cu12
```

---

## 6. Passo de benchmark (decidir device padrão)

Na primeira instalação, rodar um áudio de ~2 min em `cuda` e em `cpu`, medir
tempo, e gravar o vencedor em `config.toml`. Documentar em `setup/install.md`:

```powershell
Measure-Command { python tools/transcribe.py "inbox/teste-2min.mp3" }  # com device=cuda
# trocar config.toml device=cpu e repetir
```

Regra: usar o que for mais rápido e estável. Se GPU < 1× realtime ou der OOM → `cpu`.

---

## 7. Stage 02 — pós-processamento por IA (opcional)

Quando você quiser mais que a transcrição crua, o Claude lê `output/<slug>.txt` e
aplica um dos prompts de `stages/02-postprocess/references/`:

| Prompt | Faz |
|---|---|
| `limpeza.md` | Remove vícios de fala ("né", "tipo", repetições), corrige pontuação e parágrafos, **sem mudar o conteúdo**. |
| `resumo.md` | Resumo executivo + bullets dos tópicos principais. |
| `ata.md` | Vira ata: participantes, decisões, pendências, próximos passos. |

Saída do Stage 02 em `output/<slug>.<tipo>.md`. Tudo em PT-BR (idioma do conteúdo).

---

## 8. Diarização — módulo opcional (quem falou)

Desligado por padrão. Quando precisar separar falantes (entrevistas, reuniões):
- Engine: `pyannote.audio` 3.x.
- Requer **token gratuito do HuggingFace** e aceitar os termos do modelo
  `pyannote/speaker-diarization-3.1` no site.
- Fluxo: pyannote gera os intervalos por falante → cruza com os segmentos do
  Whisper → marca `Falante 1 / Falante 2` no `.timestamped.txt`.
- Custo: mais pesado (puxa PyTorch), ~mais 1-2 GB. Em 2 GB de VRAM, rodar a
  diarização em **CPU** é o mais seguro.
- Validar na implementação se a flag nativa de diarização do `whisper-ctranslate2`
  já resolve, evitando montar o pipeline manual.

Fica como `stages/01-transcribe/` com flag `--diarize` ou script separado
`tools/diarize.py`. Não bloqueia a v1.

---

## 9. Fluxo de uso típico (dia a dia)

```powershell
# 1. ativar ambiente
.\.venv\Scripts\Activate.ps1

# 2. jogar o(s) áudio(s) na inbox/  (arrastar no Explorer)

# 3. transcrever tudo
python tools/transcribe.py

# 4. pegar resultado em output/<slug>.txt / .srt / .vtt / .timestamped.txt

# 5. (opcional) abrir o Claude no workspace e pedir Stage 02:
#    "limpa a transcrição output/reuniao-solunar.txt" ou "faz a ata"
```

---

## 10. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| MX150 com 2 GB dá OOM no modelo | Padrão `medium`+`int8`; fallback automático pra CPU no script. |
| GPU mais lenta que CPU | Benchmark no setup (§6) define o device padrão. |
| Erro de cuDNN no Windows | Instalar `nvidia-cudnn-cu12` via pip; documentar no troubleshooting. |
| Alucinação em trechos de silêncio | `vad_filter=True` por padrão. |
| Áudio muito longo (horas) | faster-whisper processa em streaming + VAD; não precisa cortar manual. |
| Qualidade de PT-BR no `small` | Padrão é `medium`; subir pra `large-v3` se a VRAM permitir. |

---

## 11. Checklist para criar a pasta

- [ ] Criar `workspaces/transcritor-local/` com a estrutura do §3.
- [ ] Escrever `CLAUDE.md` (identidade + roteamento) e `CONTEXT.md` (cheatsheet).
- [ ] Escrever `setup/install.md` (§4) e rodar `nvidia-smi` pra confirmar VRAM.
- [ ] Implementar `tools/transcribe.py` + `config.toml` + `requirements.txt` (§5).
- [ ] Rodar benchmark cuda vs cpu (§6) e fixar device em `config.toml`.
- [ ] Testar com 1 áudio curto e 1 áudio longo real.
- [ ] (Opcional) Escrever os 3 prompts do Stage 02 (§7).
- [ ] (Futuro) Avaliar módulo de diarização (§8).

---

## Anexo — Como isso vira a pasta ICM

Esta pasta segue as convenções ICM do projeto (CLAUDE.md por workspace, CONTEXT.md
de roteamento, stages numerados, `output/` por stage). Para criar, dá pra usar o
`workspace-builder` apontando pra este spec, ou criar manualmente com o Claude Code
seguindo o §11.
