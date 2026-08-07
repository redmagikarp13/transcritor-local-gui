# CONTEXT — Transcritor Local (cheatsheet de uso)

Como usar no dia a dia: ativar o ambiente, jogar áudio na `inbox/`, rodar um
comando, pegar o resultado em `output/`. Opcionalmente, pedir ao Claude o
pós-processamento (Stage 02). Tudo local, de graça, sem upload.

Comandos para **Windows / PowerShell**.

---

## Fluxo rápido (5 passos)

```powershell
# 1. Ativar o ambiente virtual (uma vez por sessão de terminal)
.\.venv\Scripts\Activate.ps1

# 2. Jogar o(s) áudio(s) na pasta inbox\  (arrastar no Explorer já basta)

# 3. Transcrever TUDO que estiver na inbox\
python tools\transcribe.py

# 4. Pegar o resultado em output\<slug>.txt / .timestamped.txt / .srt / .vtt
#    (<slug> = nome do arquivo de origem, sem extensão)

# 5. (Opcional) Abrir o Claude neste workspace e pedir o Stage 02:
#    "limpa a transcrição output\reuniao-solunar.txt" ou "faz a ata"
```

> Se o prompt do PowerShell passou a mostrar `(.venv)` no início da linha, o
> ambiente está ativo. Para sair: `deactivate`.

---

## Variações do comando de transcrição

```powershell
# Transcrever um arquivo específico (em vez de toda a inbox\)
python tools\transcribe.py "inbox\reuniao-solunar.m4a"

# Arquivo que está em qualquer outro lugar do disco
python tools\transcribe.py "C:\Users\marco\Downloads\entrevista.mp3"
```

Os defaults (modelo, device, idioma, VAD, beam_size) vêm de `tools\config.toml` —
edite lá para mudar o comportamento sem tocar no código.

---

## Equivalente direto via `whisper-ctranslate2` (mesma sintaxe do Colab)

O wrapper `transcribe.py` é o caminho recomendado (gera o `.timestamped.txt`
custom e organiza tudo em `output\`). Mas se quiser rodar a engine na mão — com a
**mesma cara do comando do Colab** — é assim:

```powershell
# Colab (antes):  whisper "tamara-192.mp3" --model large --language pt

# Local, GPU pequena (MX150 2GB) — modelo medium + int8 + VAD, todos os formatos:
whisper-ctranslate2 "inbox\tamara-192.mp3" `
  --model medium --language pt `
  --device cuda --compute_type int8 `
  --vad_filter True `
  --output_format all --output_dir output
```

Notas sobre essas flags (confirmadas):
- `--output_format all` gera `txt`, `srt`, `vtt`, `tsv` e `json` de uma vez. Se
  você omitir `--output_format`, ele já produz todos por padrão (herdado do
  Whisper original).
- Booleanos seguem a sintaxe do Whisper original: escreva o valor explícito
  (`--vad_filter True`), não a flag sozinha.
- Em GPU com 4GB você pode trocar para `--model large-v3` (e, com folga de VRAM,
  `--compute_type float16`).
- Inferência em lote (mais rápida): adicione `--batched True --batch_size 16`. No
  modo batched o VAD já vem habilitado.

A continuação de linha no PowerShell é a **crase** (`` ` ``) no fim de cada linha —
não a barra invertida `\` do bash. Ou escreva tudo numa linha só.

---

## Formatos de saída (por arquivo, prefixados pelo `<slug>`)

| Arquivo | O que é | Quando usar |
|---|---|---|
| `<slug>.txt` | Texto corrido, sem timestamps. | Leitura, copiar pro documento, jogar no Stage 02. |
| `<slug>.timestamped.txt` | `[hh:mm:ss] texto` por segmento. | Achar um trecho pelo tempo; revisão com a gravação aberta. |
| `<slug>.srt` | Legenda SubRip (numerada, `00:00:01,000 --> ...`). | Legendar vídeo (YouTube, players, editores). |
| `<slug>.vtt` | Legenda WebVTT (`WEBVTT`, `00:00:01.000 --> ...`). | Legenda na web (HTML5 `<track>`). |

> `.txt` e `.timestamped.txt` saem do wrapper `transcribe.py`. Rodando a CLI
> `whisper-ctranslate2 --output_format all` direto, você também ganha `.tsv` e
> `.json` (e o `.txt`/`.srt`/`.vtt`), mas o `.timestamped.txt` legível é específico
> do wrapper.

---

## Qual modelo usar (por VRAM real)

Confira a VRAM **dedicada** real com `nvidia-smi` (coluna *Memory-Usage*, valor à
direita = total). A "memória de GPU compartilhada" que o Windows mostra **não**
conta — é RAM via PCIe, lenta demais para Whisper.

| VRAM dedicada | `model` | `compute_type` | Observação |
|---|---|---|---|
| 2 GB (MX150 2GB) | `medium` | `int8` | Padrão. Bom equilíbrio qualidade/PT-BR, ~1.5 GB. |
| 4 GB (MX150 4GB) | `large-v3` | `int8` ou `int8_float16` | Melhor qualidade; `int8_float16` economiza VRAM na GPU. |
| Sem GPU / deu OOM | `medium` (ou `small`) | `int8` | CPU não acelera `float16`; use sempre `int8`. |

Regras práticas:
- Em GPU com **pouca** VRAM, `int8_float16` ou `int8` são mais seguros que
  `float16` (que pode dar aviso/fallback em hardware antigo como o MX150).
- Em **CPU**, use `int8` (CPU não tira proveito de `float16`).
- Se a GPU der OOM ou ficar abaixo de ~1× realtime, mude `device = "cpu"` no
  `config.toml`. O `transcribe.py` já tenta fallback automático GPU → CPU.
- O download do modelo acontece na **primeira** execução e fica em cache local
  (`medium` ~1.5 GB).

---

## Stage 02 — pós-processamento por IA (opcional)

Quando a transcrição crua não basta, abra o Claude **neste workspace** e peça um
dos tratamentos. Ele lê `output\<slug>.txt` e aplica o prompt correspondente em
`stages\02-postprocess\references\`:

| Peça por... | Prompt | Resultado |
|---|---|---|
| "limpa a transcrição" | `limpeza.md` | Remove vícios de fala ("né", "tipo", repetições), corrige pontuação e parágrafos, sem mudar o conteúdo. |
| "faz um resumo" | `resumo.md` | Resumo executivo + bullets dos tópicos principais. |
| "faz a ata" | `ata.md` | Ata: participantes, decisões, pendências, próximos passos. |

Saída do Stage 02 em `output\<slug>.<tipo>.md` (ex.: `reuniao-solunar.ata.md`),
em PT-BR (idioma do conteúdo).

---

## Se algo der errado

- **Erro de cuBLAS/cuDNN / "Library ... not found" / `cublas64_12.dll` /
  `cudnn_ops*_9.dll`**: faltam as DLLs CUDA no PATH (Windows). **O `transcribe.py`
  já resolve isso sozinho** ao iniciar (registra as DLLs dos pacotes `nvidia-*-cu12`
  no PATH). Se ainda assim aparecer, você provavelmente está rodando a CLI
  `whisper-ctranslate2` direta — siga `setup\install.md` (copiar as DLLs / ajustar o
  PATH) ou use CPU (`--device cpu`).
- **`ffmpeg` não encontrado** / formato não decodifica: instale com
  `winget install -e --id Gyan.FFmpeg` e confira com `ffmpeg -version`.
- **Out of memory na GPU**: baixe o modelo (`large-v3` → `medium` → `small`),
  use `compute_type = "int8"`, ou troque para CPU.
- **`(.venv)` não aparece**: você esqueceu o passo 1 (ativar o ambiente).
