# Transcritor Local

Workspace ICM para transcrever áudios e vídeos **localmente, de graça e sem upload**, usando `faster-whisper` (Whisper sobre CTranslate2) acelerado por GPU pequena ou CPU. Você joga um arquivo na `inbox/`, roda um comando, e recebe a transcrição em PT-BR em múltiplos formatos (`.txt`, `.timestamped.txt`, `.srt`, `.vtt`). Opcionalmente, o Claude entra no Stage 02 para virar a transcrição crua em texto limpo, resumo ou ata.

Casos de uso do Marquito: reuniões (Solunar etc.), entrevistas, aulas, áudios do WhatsApp e gravações longas de formação no Cefor.

## Folder Map

```
transcritor-local/
├── CLAUDE.md                 (você está aqui — identidade + roteamento)
├── CONTEXT.md                (cheatsheet de comandos do dia a dia)
├── SPEC.md                   (design/origem deste workspace — referência, não usado em runtime)
├── setup/
│   └── install.md            (instalação: ffmpeg + Python + whisper-ctranslate2 + CUDA/cuDNN; benchmark cuda vs cpu)
├── inbox/                    (jogue os áudios/vídeos aqui — mp3, mp4, m4a, wav, ogg, flac...)
├── output/                   (transcrições saem aqui: .txt / .timestamped.txt / .srt / .vtt)
├── tools/
│   ├── transcribe.py         (wrapper: batch da inbox + bons defaults + escreve os 4 formatos)
│   ├── config.toml           (model, device, compute_type, language, vad_filter, beam_size — editável sem tocar no código)
│   └── requirements.txt      (faster-whisper + whisper-ctranslate2; libs nvidia-* ficam comentadas, instaladas à mão só p/ GPU)
└── stages/
    ├── 01-transcribe/        (STAGE MECÂNICO: áudio bruto -> transcrição crua; roda script, não gasta token de IA)
    │   ├── CONTEXT.md
    │   └── output/           (espelha a output/ raiz)
    └── 02-postprocess/       (STAGE IA, OPCIONAL: transcrição crua -> limpa / resumo / ata)
        ├── CONTEXT.md
        └── references/
            ├── limpeza.md    (prompt: remove vícios de fala, corrige pontuação — sem mudar conteúdo)
            ├── resumo.md     (prompt: resumo executivo + tópicos)
            └── ata.md        (prompt: vira ata com participantes, decisões, pendências, próximos passos)
```

## Hardware desta máquina (importante para defaults)

| Item | O Windows mostra | Realidade para CUDA/Whisper |
|---|---|---|
| NVIDIA GeForce MX150 | "~10 GB" | **2 GB de VRAM dedicada** (GDDR5, compute capability 6.1). O resto é *shared memory* (RAM via PCIe) — lenta e inútil para Whisper. |
| Intel UHD Graphics | "8 GB" | **0 GB dedicada** — usa RAM compartilhada. Não acelera Whisper na prática. Ignorada nesta versão. |

> **Passo 0:** confirme a VRAM real com `nvidia-smi`. Se for 2 GB, o padrão é `model = "medium"` com `compute_type = "int8"`. Se for uma variante de 4 GB, libera `large-v3`.
>
> **CUDA:** o MX150 (Pascal, sm_61) roda em CUDA 12.x (use até 12.9 — **não** use CUDA 13+, que removeu suporte a Pascal). O CTranslate2 atual (>=4.5) exige **cuBLAS para CUDA 12 + cuDNN 9** (não cuDNN 8). No Windows, as DLLs da NVIDIA **não** entram no PATH sozinhas após o `pip install` — ver troubleshooting em `setup/install.md`.

## Triggers

| Palavra-chave | Ação |
|---|---|
| `setup` | Roda a instalação passo a passo de `setup/install.md` (ffmpeg, Python, engine, CUDA/cuDNN) e o benchmark cuda vs cpu. |
| `transcrever` | Garante a `.venv` ativa e roda `python tools/transcribe.py` (toda a `inbox/`) ou num arquivo específico. Vá para `stages/01-transcribe/CONTEXT.md`. |
| `status` | Mostra o que há na `inbox/` ainda sem transcrição e o que já saiu em `output/` (ver abaixo). |
| `limpa` / `resumo` / `ata` | Aciona o Stage 02 sobre um `output/<slug>.txt`. Vá para `stages/02-postprocess/CONTEXT.md`. |

### Como `status` funciona

Compara a `inbox/` com a `output/`. Para cada áudio em `inbox/` (extensões de áudio/vídeo, ignorando `.gitkeep`), verifica se existe `output/<slug>.txt`. Renderiza:

```
Transcritor Local — status

  inbox/   N arquivo(s)
  output/  M transcrito(s)

  PENDENTE:    <slugs sem .txt em output/>
  TRANSCRITO:  <slugs com .txt em output/>
```

## Routing

| Tarefa | Vá para |
|---|---|
| Instalar do zero / resolver erro de CUDA/cuDNN | `setup/install.md` |
| Comandos do dia a dia (cheatsheet) | `CONTEXT.md` |
| Transcrever áudio (stage mecânico) | `stages/01-transcribe/CONTEXT.md` |
| Limpar / resumir / virar ata (stage de IA) | `stages/02-postprocess/CONTEXT.md` |
| Mudar modelo, device ou idioma padrão | `tools/config.toml` |

## What to Load

| Tarefa | Carregar | NÃO carregar |
|---|---|---|
| Instalar / configurar | `setup/install.md`, `tools/requirements.txt`, `tools/config.toml` | `stages/02-postprocess/` |
| Transcrever | `stages/01-transcribe/CONTEXT.md`, `CONTEXT.md`, `tools/config.toml` (só para conferir defaults) | `stages/02-postprocess/`, `setup/` |
| Pós-processar (limpa/resumo/ata) | `stages/02-postprocess/CONTEXT.md`, o prompt relevante em `stages/02-postprocess/references/`, o arquivo `output/<slug>.txt` alvo | `tools/`, `setup/`, stage 01 |

## Como funciona o pipeline

1. **Stage 01 (mecânico, determinístico):** `tools/transcribe.py` lê os defaults de `tools/config.toml`, transcreve com `faster-whisper` (VAD filter ligado para áudios longos), e escreve quatro arquivos por entrada em `output/`:
   - `<slug>.txt` — texto corrido
   - `<slug>.timestamped.txt` — `[hh:mm:ss] texto` por segmento
   - `<slug>.srt` e `<slug>.vtt` — legendas
   O script faz fallback automático `cuda -> cpu` se a GPU der OOM. Esse stage **não gasta token de IA**.

2. **Stage 02 (IA, opcional):** o Claude lê `output/<slug>.txt` e aplica um dos prompts de `references/` (limpeza, resumo ou ata). Saída em `output/<slug>.<tipo>.md`, sempre em PT-BR (idioma do conteúdo).

> **Convenção de slug:** o `<slug>` é o nome do arquivo de áudio sem extensão (`reuniao-solunar.m4a` -> `reuniao-solunar`). Ele prefixa todos os artefatos gerados ao longo do pipeline.

## Notas técnicas (engine)

- Engine: **`faster-whisper`** (não o `openai-whisper`). Reimplementa Whisper sobre CTranslate2: mais rápido, suporta quantização `int8` (modelo ocupa ~⅓ da VRAM), não exige PyTorch e tem VAD filter embutido. `large` no Whisper original quer ~10 GB de VRAM — não cabe em 2 GB; por isso `faster-whisper` + `int8`.
- `transcribe()` retorna `(segments, info)` — `segments` é um **gerador** (a transcrição só roda ao iterar; `tools/transcribe.py` materializa com `list(...)`). `info` é um objeto `TranscriptionInfo`: use `info.language` por atributo, nunca `info['language']`.
- `compute_type` por dispositivo: GPU com folga -> `float16`; GPU com pouca VRAM (MX150 2 GB) -> `int8_float16` ou `int8`; CPU -> `int8` (CPU não acelera `float16`).
- **Diarização (quem falou):** módulo opcional, **desligado por padrão**. Quando precisar, usa `pyannote.audio` (modelo `pyannote/speaker-diarization-community-1` em 4.x, ou `3.1` legado) com token gratuito do HuggingFace; em 2 GB de VRAM, rodar a diarização em **CPU** é o mais seguro. Não bloqueia a v1.
