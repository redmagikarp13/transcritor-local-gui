# Stage 01 — Transcribe (áudio bruto -> transcrição crua)

> Stage **MECÂNICO**: roda um script Python determinístico. **Não gasta token de IA.**
> Não chame o Claude para esta etapa — é só executar `tools/transcribe.py`.

## Propósito

Transformar arquivos de áudio/vídeo brutos em transcrição crua em PT-BR, em
múltiplos formatos. É o coração do workspace: tudo local, gratuito, sem upload.
O resultado é a matéria-prima para o Stage 02 (opcional, por IA).

## Entrada

Arquivos de áudio/vídeo na pasta `inbox/` (na raiz do workspace).

- Qualquer formato que o ffmpeg leia: `mp3`, `mp4`, `m4a`, `wav`, `ogg`, `flac`,
  `aac`, `webm`, `mkv`, `mov`, etc.
- Basta arrastar os arquivos para `inbox/` (pelo Explorer ou copiando).
- O nome do arquivo (sem extensão) vira o `<slug>` que prefixa todas as saídas.
  Ex.: `inbox/reuniao-solunar.m4a` -> `output/reuniao-solunar.txt`, etc.

## Processo

Com o ambiente virtual ativado, rodar o wrapper:

```powershell
.\.venv\Scripts\Activate.ps1

# transcreve TUDO que estiver em inbox/
python tools/transcribe.py

# ou um arquivo específico (não precisa estar em inbox/)
python tools/transcribe.py "caminho/para/audio.m4a"
```

O script carrega os defaults de `tools/config.toml`, materializa os segmentos
(`list(segments)` — é aqui que o trabalho pesado da GPU/CPU acontece) e escreve
os quatro formatos de saída em `output/`. Faz **fallback automático cuda -> cpu**
se a GPU der OOM.

> Instalação e benchmark de device (cuda vs cpu) ficam em `setup/install.md`.
> Este stage assume que o setup já foi feito.

## Saídas

Para cada entrada, em `output/` (prefixadas pelo `<slug>`):

| Arquivo | Conteúdo |
|---|---|
| `output/<slug>.txt` | Texto corrido limpo (sem timestamps). Entrada do Stage 02. |
| `output/<slug>.timestamped.txt` | `[hh:mm:ss] texto` por segmento — leitura humana com marcação de tempo. |
| `output/<slug>.srt` | Legenda SubRip (timestamps `00:00:00,000 --> ...`). |
| `output/<slug>.vtt` | Legenda WebVTT (timestamps com `.` no separador de ms). |

## Parâmetros relevantes (via `tools/config.toml`)

Edite o `config.toml` para mudar o comportamento padrão — sem tocar no código:

| Campo | Valores | Observação |
|---|---|---|
| `model` | `medium` \| `large-v3` \| `small` | `medium` é o padrão para 2 GB de VRAM (MX150). `large-v3` só com 4 GB+. |
| `device` | `cuda` \| `cpu` \| `auto` | Defina pelo benchmark do setup. Em GPU fraca, `cpu` pode ganhar. |
| `compute_type` | `int8` \| `float16` \| `int8_float16` | `int8` para pouca VRAM **ou** CPU (use este na MX150). `int8_float16`/`float16` exigem GPU Turing+ — a MX150 (Pascal) dá `ValueError`. |
| `language` | `pt`, `en`, `es`, `auto`... | Idioma do áudio. `pt` por padrão. |
| `vad_filter` | `true` \| `false` | Silero VAD: pula silêncios. Mantenha `true` (ver nota abaixo). |
| `beam_size` | inteiro | `1` (greedy) é o padrão aqui: faz o `medium` caber em 2 GB e é mais rápido. `5` (beam search) melhora pouco e estoura a VRAM da MX150 com `medium`. |

> `compute_type`: `int8` e `int8_float16` não são equivalentes. Em `int8` as
> camadas não-quantizadas rodam em FP32; em `int8_float16` rodam em float16
> (menos VRAM). Na CPU use `int8` — CPU não acelera float16.

## Nota sobre áudios longos (horas)

**Não precisa cortar o áudio manualmente — o wrapper já fatia internamente.** O
`faster-whisper` calcula a STFT (feature extraction) do áudio **inteiro** de uma só
vez; em arquivos de várias horas isso estoura a **RAM** (erro `Unable to allocate ...
complex128`, ver [issue #1206](https://github.com/SYSTRAN/faster-whisper/issues/1206)).
Para contornar, o `transcribe.py` decodifica o waveform (via PyAV, sem precisar de
ffmpeg no PATH) e transcreve em **blocos de `chunk_minutes`** (padrão 20 min),
somando o offset de tempo de cada bloco aos timestamps. Assim a memória fica
constante, independente da duração total. Se ainda faltar RAM, baixe `chunk_minutes`
para 10 no `config.toml`.

Além disso, `vad_filter=True` (Silero VAD, com `min_silence_duration_ms=500`) pula
os silêncios dentro de cada bloco — o que reduz o tempo de processamento e elimina
as alucinações típicas do Whisper em trechos mudos. Mantenha `vad_filter = true`.

## Próximo stage

O **Stage 02 (`stages/02-postprocess/`) é OPCIONAL** e roda **por IA**. Ele lê de
`output/<slug>.txt` e transforma a transcrição crua em algo útil (limpeza, resumo
ou ata). Só rode quando quiser mais que a transcrição bruta — abra o Claude no
workspace e peça (ex.: "limpa a transcrição output/reuniao-solunar.txt" ou
"faz a ata"). Se editar o `output/<slug>.txt` à mão entre os stages, o Stage 02
pega sua edição.
