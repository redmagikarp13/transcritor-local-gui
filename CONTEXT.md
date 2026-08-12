# CONTEXT — Transcritor Local (cheatsheet de uso)

Como usar no dia a dia: ativar o ambiente, jogar áudio na `inbox/`, rodar um
comando ou usar a interface gráfica, e pegar o resultado em `output/`. Opcionalmente,
pedir ao assistente de IA o pós-processamento (Stage 02). Tudo local, de graça, sem upload.

Comandos para **Windows / PowerShell**.

---

## Fluxo rápido — Interface Gráfica

```powershell
# 1. Ativar o ambiente virtual e iniciar a GUI
.\start_gui.bat
```

Na interface:
1. Abra a aba **Arquivo Único** ou **Fila (Lote)**
2. Selecione o(s) arquivo(s) de mídia
3. Escolha a pasta de destino e o idioma
4. Clique em **Iniciar Transcrição**
5. Acompanhe o log em tempo real; os arquivos saem em `output/`

---

## Fluxo rápido — CLI (5 passos)

```powershell
# 1. Ativar o ambiente virtual (uma vez por sessão de terminal)
.\.venv\Scripts\Activate.ps1

# 2. Jogar o(s) áudio(s) na pasta inbox\  (arrastar no Explorer já basta)

# 3. Transcrever TUDO que estiver na inbox\
python src\transcritor\core\transcribe.py

# 4. Pegar o resultado em output\<slug>.txt / .timestamped.txt / .srt / .vtt
#    (<slug> = nome do arquivo de origem, sem extensão)

# 5. (Opcional) Abrir o assistente neste workspace e pedir o Stage 02:
#    "limpa a transcrição output\reuniao-solunar.txt" ou "faz a ata"
```

> Se o prompt do PowerShell passou a mostrar `(.venv)` no início da linha, o
> ambiente está ativo. Para sair: `deactivate`.

---

## Variações do comando de transcrição

```powershell
# Transcrever um arquivo específico (em vez de toda a inbox\)
python src\transcritor\core\transcribe.py "inbox\reuniao-solunar.m4a"

# Arquivo que está em qualquer outro lugar do disco
python src\transcritor\core\transcribe.py "C:\Users\leo\Downloads\entrevista.mp3"
```

Os defaults (modelo, device, idioma, VAD, beam_size) vêm de `src\transcritor\core\config.toml` —
edite lá ou use a aba **Configurações** da GUI para mudar o comportamento sem tocar no código.

---

## Formatos de saída (por arquivo, prefixados pelo `<slug>`)

| Arquivo | O que é | Quando usar |
|---|---|---|
| `<slug>.txt` | Texto corrido, sem timestamps. | Leitura, copiar pro documento, jogar no Stage 02. |
| `<slug>.timestamped.txt` | `[hh:mm:ss] texto` por segmento. | Achar um trecho pelo tempo; revisão com a gravação aberta. |
| `<slug>.srt` | Legenda SubRip (numerada, `00:00:01,000 --> ...`). | Legendar vídeo (YouTube, players, editores). |
| `<slug>.vtt` | Legenda WebVTT (`WEBVTT`, `00:00:01.000 --> ...`). | Legenda na web (HTML5 `<track>`). |

---

## Qual modelo usar (por VRAM real)

Confira a VRAM **dedicada** real com `nvidia-smi` (coluna *Memory-Usage*, valor à
direita = total). A "memória de GPU compartilhada" que o Windows mostra **não**
conta — é RAM via PCIe, lenta demais para Whisper.

| VRAM dedicada | `model` | `compute_type` | Observação |
|---|---|---|---|
| 2 GB (MX150 2GB) | `medium` | `int8` | Padrão. Bom equilíbrio qualidade/PT-BR, ~1.5 GB. |
| 4 GB (MX150 4GB) | `large-v3` | `int8` ou `int8_float16` | Melhor qualidade. |
| Sem GPU / deu OOM | `medium` (ou `small`) | `int8` | CPU não acelera `float16`; use sempre `int8`. |

Regras práticas:
- Em GPU com **pouca** VRAM, `int8` é mais seguro que `float16`.
- Em **CPU**, use `int8`.
- Se a GPU der OOM, o programa já tenta fallback automático GPU → CPU.
- O download do modelo acontece na **primeira** execução e fica em cache local (`medium` ~1.5 GB) em `C:\Users\<usuário>\.cache\huggingface\hub\`.

---

## Stage 02 — pós-processamento por IA (opcional)

Quando a transcrição crua não basta, abra o assistente **neste workspace** e peça um
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

- **Erro de cuBLAS/cuDNN / "Library ... not found"**: faltam as DLLs CUDA no PATH (Windows).
  O `transcribe.py` já tenta resolver isso automaticamente. Se persistir, siga `setup\install.md`.
- **Out of memory na GPU**: baixe o modelo (`large-v3` → `medium` → `small`),
  use `compute_type = "int8"`, ou troque para CPU. O programa faz fallback automático.
- **`(.venv)` não aparece**: você esqueceu o passo 1 (ativar o ambiente).
- **PowerShell bloqueia a ativação**: execute
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ative novamente.
