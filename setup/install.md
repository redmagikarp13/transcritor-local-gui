# Instalação — Transcritor Local (Windows + PowerShell)

Passo a passo para deixar o `transcritor-local` rodando do zero no Windows via
PowerShell. As orientações de GPU usam uma NVIDIA GeForce MX150 como exemplo de
hardware com pouca VRAM; adapte o modelo e o `device` à sua máquina.

> Resumo do caminho: `ffmpeg` → `Python 3.12` → venv → engine de transcrição →
> (só se a GPU passar no teste) libs CUDA → confirmar VRAM real → benchmark
> `cuda` vs `cpu` → fixar o `device` vencedor no `config.toml`.

Antes de começar, crie sua configuração local a partir do exemplo na raiz do
projeto:

```powershell
Copy-Item tools\config.example.toml tools\config.toml
```

---

## 0. Pré-requisitos de sistema

### 0.1 ffmpeg (obrigatório)

O `faster-whisper` decodifica o áudio com `ffmpeg`/`libav`. Sem ele, nada funciona.

```powershell
winget install -e --id Gyan.FFmpeg
```

> Use o **id exato** `Gyan.FFmpeg` (build *full* do gyan.dev). Não use
> `winget install ffmpeg` por nome — o id correto evita pegar o pacote errado.
> O build *full* inclui mais bibliotecas que o *essentials*. Se quiser um pacote
> menor e não se importar com as libs extras, existe `Gyan.FFmpeg.Essentials`.

Depois de instalar, **feche e reabra o PowerShell** (para o PATH atualizar) e confirme:

```powershell
ffmpeg -version
```

Se aparecer a versão (ex.: `ffmpeg version 8.1.1`), está no PATH. Se der
"comando não reconhecido", veja [Troubleshooting → ffmpeg fora do PATH](#ffmpeg-fora-do-path).

### 0.2 Python 3.10–3.12

```powershell
# Confira se já tem uma versão compatível:
python --version

# Se não tiver (ou for < 3.10), instale o 3.12:
winget install -e --id Python.Python.3.12
```

> `pyannote.audio` (diarização opcional) exige Python >= 3.10. Fique na faixa
> 3.10–3.12 para máxima compatibilidade com as wheels do CTranslate2.

---

## 1. Ambiente virtual (venv)

Crie o venv **na raiz do workspace** `transcritor-local/` (um nível acima de `tools/`).
Abra o PowerShell nessa pasta:

```powershell
# Estando em ...\workspaces\transcritor-local\
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> Se a ativação falhar com erro de *execution policy*, libere só para a sessão atual:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

Com o venv ativo, o prompt mostra `(.venv)` no início. Atualize o `pip`:

```powershell
python -m pip install --upgrade pip
```

---

## 2. Engine de transcrição

Instale tudo a partir do `requirements.txt` (que já vive em `tools/`):

```powershell
pip install -r tools\requirements.txt
```

Isso instala o `faster-whisper` (lib usada diretamente pelo `transcribe.py`) e o
CLI `whisper-ctranslate2` (atalho drop-in compatível com o Whisper original).

> **Importante:** o `requirements.txt` **não** lista as libs NVIDIA de propósito.
> Elas só são necessárias se você for usar a GPU — e nem sempre são. Instale-as no
> passo 3, e só se o teste de GPU pedir.

---

## 3. Suporte a GPU (CUDA) — instale SÓ se for usar `device = cuda`

A MX150 é uma GPU Pascal (compute capability 6.1) e **funciona com CUDA 12**.
Mas as bibliotecas NVIDIA **não vêm automaticamente** com o `pip install faster-whisper` —
o `requirements.txt` do faster-whisper lista apenas `ctranslate2`, `tokenizers`,
`onnxruntime`, `av`, etc., **nenhum pacote `nvidia-*`**. Você precisa instalá-las à mão.

### 3.1 Faça o teste rápido primeiro

Antes de instalar 500+ MB de DLLs, veja se a GPU está visível:

```powershell
nvidia-smi
```

- Se o comando **não existe** ou não lista a MX150 → o driver NVIDIA não está
  instalado/ativo. Pule a GPU, use `device = cpu` e siga para o passo 4.
- Se lista a MX150 → vale a pena tentar a GPU. Continue em 3.2.

### 3.2 Instalar as libs CUDA (cuBLAS + cuDNN 9)

O CTranslate2 atual (>= 4.5, que vem com o faster-whisper recente) exige
**cuBLAS + cuDNN 9 sobre CUDA >= 12.3**. A *major version* do cuDNN é **9**,
não 8 (o senso comum de "CUDA 12 + cuDNN 8" está desatualizado). Atenção ao piso:
o cuDNN 9 do CTranslate2 >= 4.5 pede **CUDA >= 12.3** no runtime/driver — em
máquinas com CUDA 12.0–12.2 a combinação pode falhar. A MX150 com driver 12.x
recente atende; só não fique abaixo de 12.3.

```powershell
pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
```

> Note o pin `==9.*` no cuDNN. A série 8.x **não** funciona com o CTranslate2 atual.
> Se mais tarde aparecer um erro mencionando `cudnn_ops_infer64_8.dll`, é sinal de
> versão antiga — em cuDNN 9 o nome do arquivo passa a ser `cudnn_ops64_9.dll`.

### 3.3 Detalhe Windows: as DLLs não entram no PATH sozinhas

No **Windows**, instalar esses pacotes pip **não** coloca as DLLs no PATH
automaticamente (o truque do `LD_LIBRARY_PATH` é só Linux). Daí o erro clássico
`Library cublas64_12.dll is not found or cannot be loaded` ao rodar na GPU.

> **Na prática você não precisa fazer nada disto:** o `transcribe.py` já registra
> essas DLLs sozinho ao iniciar (função `_ensure_cuda_dlls` — detecta os pacotes
> `nvidia-*-cu12` e **prepende as pastas `bin` ao PATH do processo**, que é o que o
> CTranslate2 consulta). As opções abaixo são *fallback*: só valem se você rodar a
> CLI `whisper-ctranslate2` direto, ou se, mesmo com o wrapper, o erro persistir.

1. **Copiar as DLLs para a pasta do CTranslate2** dentro do venv (mais simples):
   copie o conteúdo de `nvidia\cublas\bin` e `nvidia\cudnn\bin`
   (em `site-packages`) para `site-packages\ctranslate2\`.
   ```powershell
   $sp = python -c "import site; print(site.getsitepackages()[0])"
   Copy-Item "$sp\nvidia\cublas\bin\*.dll" "$sp\ctranslate2\" -Force
   Copy-Item "$sp\nvidia\cudnn\bin\*.dll"  "$sp\ctranslate2\" -Force
   ```
2. **Usar o bundle do Purfview** `whisper-standalone-win`
   (`cuBLAS.and.cuDNN_CUDA12_win`): baixe e ponha as DLLs ao lado do executável /
   no PATH.

> Importante sobre versão do CUDA Toolkit: **não use CUDA 13+** no MX150.
> O CUDA 13.0 removeu suporte a arquiteturas anteriores a Turing (sm < 7.5),
> e a MX150 é sm_61. A linha CUDA 12.x (de preferência até 12.9) é a última que
> roda nessa GPU. Os pacotes pip `nvidia-*-cu12` acima já são da linha 12, então
> está coberto — só não instale Toolkit/PyTorch `cu13x`.

### 3.4 Fallback de versões (caso você esteja preso a cuDNN 8)

Só se, por algum motivo, sua máquina tiver cuDNN 8 e não puder atualizar:

```powershell
# CUDA 12 + cuDNN 8:
pip install --force-reinstall ctranslate2==4.4.0
# CUDA 11 + cuDNN 8:
pip install --force-reinstall ctranslate2==3.24.0
```

> O `--force-reinstall` é necessário: o `faster-whisper` já puxa um `ctranslate2`
> 4.5+, e sem forçar o pip consideraria o requisito satisfeito e não faria o
> downgrade de fato.

---

## 4. Confirmar a VRAM real (Passo 0 do spec)

O Windows mostra "memória de GPU compartilhada" somada à VRAM (pode parecer ~10 GB),
mas isso **não é VRAM utilizável** para Whisper — é RAM do sistema emprestada via
PCIe, ordens de magnitude mais lenta. O que importa é a **VRAM dedicada**.

```powershell
nvidia-smi
```

Olhe a coluna **Memory-Usage**: o valor à direita (ex.: `2048MiB`) é a VRAM total
dedicada.

| VRAM dedicada real | Modelo padrão | `compute_type` | Onde fica no `config.toml` |
|---|---|---|---|
| 2 GB (MX150 2GB) | `medium` | `int8` | `model = "medium"` |
| 4 GB (MX150 4GB) | `large-v3` | `int8` ou `int8_float16` | `model = "large-v3"` |
| Sem GPU / OOM | `medium` (ou `small`) | `int8` (CPU) | `device = "cpu"` |

> A MX150 existe em variantes de **2 GB e 4 GB** — confirme a sua antes de assumir.
> Em 2 GB, `large-v3` em `int8` cabe apertado (~2.5 GB) e tende a dar OOM; por isso
> o padrão seguro é `medium`. Em 2 GB, `int8` economiza mais VRAM que `float16`.

Quer confirmar que o PyTorch/sistema enxerga a capability certa? (opcional)

```powershell
python -c "import torch; print(torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))"
# Esperado para a MX150: ('NVIDIA GeForce MX150', (6, 1))
```

> Esse check só funciona se `torch` estiver instalado (ele **não** é dependência do
> faster-whisper). Pule se não tiver torch — não é necessário para transcrever.

---

## 5. Benchmark: `cuda` vs `cpu` (decide o device padrão)

A MX150 é fraca (384 CUDA cores, TDP ~10–25W). Numa CPU moderna de vários threads,
o `faster-whisper` em `int8` na **CPU** pode empatar ou até superar essa GPU. Não
assuma — **meça** com um áudio curto e fixe o vencedor no `config.toml`.

### 5.1 Prepare um áudio de teste

Coloque um arquivo de ~2 minutos em `inbox/` (ex.: `inbox\teste-2min.mp3`).

### 5.2 Medir com a GPU

Garanta que `config.toml` tem `device = "cuda"` e rode:

```powershell
Measure-Command { python tools\transcribe.py "inbox\teste-2min.mp3" } | Select-Object TotalSeconds
```

### 5.3 Medir com a CPU

Edite `config.toml` e troque para `device = "cpu"` (mantenha `compute_type = "int8"`),
depois rode de novo:

```powershell
Measure-Command { python tools\transcribe.py "inbox\teste-2min.mp3" } | Select-Object TotalSeconds
```

### 5.4 Fixar o vencedor

Deixe no `config.toml` o `device` que foi **mais rápido e estável**. Regra prática:

- Se a GPU deu **OOM** ou ficou **abaixo de ~1× realtime** (levou mais que a duração
  do áudio para um trecho com fala), use `device = "cpu"`.
- Se a GPU foi claramente mais rápida e não deu erro, use `device = "cuda"`.

> Dica: para comparar limpo, apague os arquivos gerados em `output/` entre as duas
> medições, já que o segundo run sobrescreveria os mesmos `<slug>.*`.

---

## 6. Primeiro uso (sanity check)

```powershell
# venv ativo, áudio na inbox\
python tools\transcribe.py
```

Resultados aparecem em `output\<slug>.txt`, `.timestamped.txt`, `.srt`, `.vtt`.
O download do modelo (`medium` ~1.5 GB) acontece **na primeira execução** e fica em
cache local (`%USERPROFILE%\.cache\huggingface`); execuções seguintes não rebaixam.

---

## Troubleshooting

### Erro de cuDNN / "Library ... not found" / `cudnn_ops*.dll`

Sintoma: ao usar `device = "cuda"`, erro tipo `Could not load library cudnn_ops...`,
`Library cublas... not found`, ou falha de inicialização do CTranslate2.

Causa quase sempre: as DLLs do cuBLAS/cuDNN não estão no PATH (no Windows, os
pacotes pip não as expõem automaticamente). **O `transcribe.py` já contorna isto
sozinho** (prepende as pastas das DLLs ao PATH ao iniciar); este troubleshooting
vale para a CLI `whisper-ctranslate2` direta, ou se o erro persistir mesmo assim.

> **Caso especial (só se você tiver `torch` instalado, ex.: por usar a diarização
> via `pyannote.audio`):** o erro `Could not locate cudnn_ops64_9.dll` pode aparecer
> **mesmo com as DLLs no lugar** quando `torch <= 2.3.1` convive com `ctranslate2 >= 4.5`.
> Nesse caso a correção é atualizar o PyTorch: `pip install "torch>=2.4.0"`. Se você
> **não** tem `torch` instalado, ignore — a causa é mesmo PATH/DLL (abaixo).

Correções, em ordem:

1. Confirme que instalou o cuDNN **9** (não 8):
   ```powershell
   pip show nvidia-cudnn-cu12   # Version deve começar com 9.
   ```
   Se for 8.x: `pip install "nvidia-cudnn-cu12==9.*"`.
   Mensagens citando `cudnn_ops_infer64_8.dll` = versão antiga; em cuDNN 9 o nome é
   `cudnn_ops64_9.dll`.
2. Copie as DLLs para a pasta do CTranslate2 (ver [3.3](#33-detalhe-windows-as-dlls-não-entram-no-path-sozinhas)):
   ```powershell
   $sp = python -c "import site; print(site.getsitepackages()[0])"
   Copy-Item "$sp\nvidia\cublas\bin\*.dll" "$sp\ctranslate2\" -Force
   Copy-Item "$sp\nvidia\cudnn\bin\*.dll"  "$sp\ctranslate2\" -Force
   ```
3. Alternativa robusta: bundle do Purfview `whisper-standalone-win`
   (`cuBLAS.and.cuDNN_CUDA12_win`) — coloque as DLLs no PATH.
4. Se nada resolver rápido: use `device = "cpu"` em `config.toml`. A CPU em `int8`
   é totalmente funcional e, nessa GPU fraca, muitas vezes nem fica para trás.

### OOM (Out Of Memory) na GPU

Sintoma: erro de memória CUDA, ou o processo morre logo ao carregar/transcrever em
`device = "cuda"`. Em 2 GB de VRAM isso é comum se o modelo for grande demais.

Correções, da mais leve para a mais drástica:

1. **Reduza `beam_size` para `1`** (greedy) no `config.toml` — é o que mais corta a
   VRAM das ativações e já faz o `medium` caber nos 2 GB da MX150 (testado: `medium` +
   `int8` + `beam_size=1` roda estável; com `beam_size=5` estoura). Mantenha
   `compute_type = "int8"`. Obs.: `int8_float16` **não** funciona na MX150 (Pascal não
   tem int8_float16 eficiente — dá `ValueError`); use `int8`.
2. Baixe o modelo: `large-v3` → `medium` → `small`. Em 2 GB, `medium` + `beam_size=1`
   cabe; se ainda estourar, `small` resolve com folga.
3. Feche programas que consomem VRAM (navegador com muitas abas, jogos, apps de
   vídeo) e tente de novo — a Intel UHD usa RAM, mas outros apps disputam a MX150.
4. O `transcribe.py` já tem **fallback automático GPU → CPU**: se a GPU falhar ao
   carregar, ele cai para `device = "cpu"` sozinho. Para tornar permanente, fixe
   `device = "cpu"` no `config.toml`.

> Lembrete: a "memória compartilhada" do Windows **não** vira VRAM útil. Estourar a
> VRAM dedicada causa *performance cliff* (queda abrupta) ou OOM, não degradação
> suave. Conte só os 2 GB (ou 4 GB) dedicados ao dimensionar o modelo.

### ffmpeg fora do PATH

Sintoma: `ffmpeg : O termo 'ffmpeg' não é reconhecido...`, ou o `transcribe.py`
falha ao abrir o áudio.

Correções:

1. **Feche e reabra** o PowerShell após o `winget install` — o PATH só atualiza em
   sessões novas.
2. Confirme a instalação:
   ```powershell
   winget list --id Gyan.FFmpeg
   (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
   ```
3. Se instalou mas não está no PATH, localize o `ffmpeg.exe` (geralmente em
   `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg...\...\bin`) e adicione
   essa pasta `bin` ao PATH do usuário (Configurações → Variáveis de ambiente), ou
   reinstale:
   ```powershell
   winget install -e --id Gyan.FFmpeg
   ```
4. Reabra o PowerShell e teste `ffmpeg -version`.

### A transcrição "trava" / não imprime nada

No `faster-whisper`, `transcribe()` retorna um **gerador** — o trabalho pesado só
roda quando você itera sobre os segmentos. O `transcribe.py` já materializa com
`list(segments)`, então o uso normal funciona. Se ver um silêncio longo no início,
é o modelo sendo baixado (primeira execução) ou o áudio sendo decodificado — espere.
