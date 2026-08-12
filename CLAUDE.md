# Transcritor Local

Workspace para transcrever áudios e vídeos **localmente, de graça e sem upload**, usando `faster-whisper` (Whisper sobre CTranslate2) acelerado por GPU NVIDIA ou CPU. Jogue um arquivo na `inbox/`, rode um comando ou use a interface gráfica, e receba a transcrição em múltiplos formatos (`.txt`, `.timestamped.txt`, `.srt`, `.vtt`). Opcionalmente, use um assistente de IA no Stage 02 para transformar a transcrição crua em texto limpo, resumo ou ata.

## Folder Map

```
transcritor-local-gui/
├── CLAUDE.md                       (você está aqui — identidade + roteamento)
├── CONTEXT.md                      (cheatsheet de comandos do dia a dia)
├── SPEC.md                         (design/origem deste workspace — referência)
├── setup/
│   └── install.md                  (instalação: Python + CUDA/cuDNN; benchmark cuda vs cpu)
├── inbox/                          (jogue os áudios/vídeos aqui)
├── output/                         (transcrições saem aqui: .txt / .timestamped.txt / .srt / .vtt)
├── src/transcritor/
│   ├── core/
│   │   ├── transcribe.py           (engine: batch da inbox + fallback GPU→CPU + escreve os 4 formatos)
│   │   ├── config.toml             (model, device, compute_type, language — editável sem tocar no código)
│   │   └── requirements.txt        (faster-whisper + whisper-ctranslate2; nvidia-* instaladas à mão p/ GPU)
│   └── gui/
│       ├── main.py                 (interface gráfica CustomTkinter)
│       ├── backend.py              (gerenciamento de modelos via HuggingFace Hub)
│       └── transcribe_runner.py    (subprocesso da GUI que chama a engine)
├── gui_requirements.txt            (dependências da interface gráfica)
├── start_gui.bat                   (inicia a GUI no Windows)
├── start_gui.sh                    (inicia a GUI no Linux/macOS)
└── stages/
    ├── 01-transcribe/              (STAGE MECÂNICO: áudio bruto → transcrição crua)
    │   ├── CONTEXT.md
    │   └── output/
    └── 02-postprocess/             (STAGE IA, OPCIONAL: transcrição crua → limpa / resumo / ata)
        ├── CONTEXT.md
        └── references/
            ├── limpeza.md          (prompt: remove vícios de fala, corrige pontuação)
            ├── resumo.md           (prompt: resumo executivo + tópicos)
            └── ata.md              (prompt: ata com participantes, decisões, pendências)
```

## Hardware (importante para defaults)

| Item | O Windows mostra | Realidade para CUDA/Whisper |
|---|---|---|
| NVIDIA GeForce MX150 | "~10 GB" | **2 GB de VRAM dedicada** (GDDR5, compute capability 6.1). O resto é *shared memory* (RAM via PCIe) — lenta e inútil para Whisper. |
| Intel UHD Graphics | "8 GB" | **0 GB dedicada** — usa RAM compartilhada. Não acelera Whisper. Ignorada. |

> **Passo 0:** confirme a VRAM real com `nvidia-smi`. Se for 2 GB, o padrão é `model = "medium"` com `compute_type = "int8"`. Se for 4 GB, libera `large-v3`.
>
> **CUDA:** o MX150 (Pascal, sm_61) roda em CUDA 12.x (use até 12.9 — **não** use CUDA 13+, que removeu suporte a Pascal). O CTranslate2 atual (>=4.5) exige **cuBLAS para CUDA 12 + cuDNN 9** (não cuDNN 8). No Windows, as DLLs da NVIDIA **não** entram no PATH sozinhas após o `pip install` — ver `setup/install.md`.

## Triggers

| Palavra-chave | Ação |
|---|---|
| `setup` | Roda a instalação passo a passo de `setup/install.md` (Python, engine, CUDA/cuDNN) e o benchmark cuda vs cpu. |
| `transcrever` | Garante a `.venv` ativa e roda `python src/transcritor/core/transcribe.py` (toda a `inbox/`) ou num arquivo específico. Vá para `stages/01-transcribe/CONTEXT.md`. |
| `status` | Mostra o que há na `inbox/` ainda sem transcrição e o que já saiu em `output/`. |
| `limpa` / `resumo` / `ata` | Aciona o Stage 02 sobre um `output/<slug>.txt`. Vá para `stages/02-postprocess/CONTEXT.md`. |

### Como `status` funciona

Compara a `inbox/` com a `output/`. Para cada áudio em `inbox/`, verifica se existe `output/<slug>.txt`. Renderiza:

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
| Mudar modelo, device ou idioma padrão | `src/transcritor/core/config.toml` ou aba Configurações da GUI |

## What to Load

| Tarefa | Carregar | NÃO carregar |
|---|---|---|
| Instalar / configurar | `setup/install.md`, `src/transcritor/core/requirements.txt`, `src/transcritor/core/config.toml` | `stages/02-postprocess/` |
| Transcrever | `stages/01-transcribe/CONTEXT.md`, `CONTEXT.md`, `src/transcritor/core/config.toml` | `stages/02-postprocess/`, `setup/` |
| Pós-processar (limpa/resumo/ata) | `stages/02-postprocess/CONTEXT.md`, o prompt relevante em `stages/02-postprocess/references/`, o arquivo `output/<slug>.txt` alvo | `src/`, `setup/`, stage 01 |

## Como funciona o pipeline

1. **Stage 01 (mecânico, determinístico):** `src/transcritor/core/transcribe.py` lê os defaults de `src/transcritor/core/config.toml`, transcreve com `faster-whisper` (VAD filter ligado para áudios longos), e escreve quatro arquivos por entrada em `output/`:
   - `<slug>.txt` — texto corrido
   - `<slug>.timestamped.txt` — `[hh:mm:ss] texto` por segmento
   - `<slug>.srt` e `<slug>.vtt` — legendas
   O script faz fallback automático `cuda → cpu` se a GPU der OOM. Esse stage **não gasta token de IA**.

2. **Stage 02 (IA, opcional):** o assistente lê `output/<slug>.txt` e aplica um dos prompts de `references/` (limpeza, resumo ou ata). Saída em `output/<slug>.<tipo>.md`, sempre em PT-BR.

> **Convenção de slug:** o `<slug>` é o nome do arquivo de áudio sem extensão (`reuniao-solunar.m4a` → `reuniao-solunar`). Ele prefixa todos os artefatos gerados ao longo do pipeline.

## Notas técnicas (engine)

- Engine: **`faster-whisper`** (não o `openai-whisper`). Reimplementa Whisper sobre CTranslate2: mais rápido, suporta quantização `int8` (modelo ocupa ~⅓ da VRAM), não exige PyTorch e tem VAD filter embutido.
- `transcribe()` retorna `(segments, info)` — `segments` é um **gerador** (a transcrição só roda ao iterar). `info` é um objeto `TranscriptionInfo`: use `info.language` por atributo, nunca `info['language']`.
- `compute_type` por dispositivo: GPU com folga → `float16`; GPU com pouca VRAM → `int8`; CPU → `int8` (CPU não acelera `float16`).
- **Modelos ficam em cache:** `C:\Users\<usuário>\.cache\huggingface\hub\` (Windows). Para mudar, defina a variável de ambiente `HF_HUB_CACHE`.
- **Diarização (quem falou):** módulo opcional, desligado por padrão. Quando precisar, usa `pyannote.audio` com token gratuito do HuggingFace.
