# Contexto do Projeto - Transcritor Local GUI

## Última Atualização
13 de agosto de 2026

## Status Atual
- **Versão:** v1.4.5 (problema de múltiplas janelas, detecção de CUDA e empacotamento PyInstaller resolvidos)
- **Branch:** main
- **Última Release:** v1.4.4 (antiga com problema)

## Problema Resolvido: Múltiplas Janelas no Executável
- **Causa Real Identificada:**
  1. No executável compilado (`sys.frozen`), `backend.get_nvidia_packages_status()` tentava rodar `subprocess.run([sys.executable, "-m", "pip", ...])`. Como `sys.executable` no PyInstaller é o próprio `TranscritorLocal.exe`, o programa chamava a si mesmo recursivamente em background, abrindo janelas infinitas no startup.
  2. Falta de `multiprocessing.freeze_support()` no início de `if __name__ == "__main__":`.
  3. No modo compilado, `ROOT_DIR` apontava para `%TEMP%/_MEIPASS` temporário, perdendo arquivos de saída e arquivos `config.toml` salvos.
- **Solução Aplicada:**
  1. `backend.py` agora detecta disponibilidade de CUDA via `ctranslate2.get_cuda_device_count()` e DLLs diretas quando `sys.frozen == True`, sem chamar `pip` via subprocess.
  2. Adicionado `multiprocessing.freeze_support()` em `main.py`.
  3. `ROOT_DIR` e `CONFIG_PATH` agora apontam para `Path(sys.executable).parent` quando congelado, garantindo que `output/` e configurações fiquem persistentes ao lado do `.exe`.
  4. Workflows e scripts de build atualizados com `--collect-all customtkinter --collect-all faster_whisper --collect-all huggingface_hub`.

### 2. CUDA 13 vs CUDA 12
- **Problema:** faster-whisper/CTranslate2 precisa de CUDA 12, mas usuário pode ter CUDA 13
- **Solução:** Instalar bibliotecas pip do NVIDIA (CUDA 12) que funcionam junto com CUDA 13
- **Comando:** `pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"`

## Estrutura do Código

### Arquivos Principais
```
src/transcritor/
├── core/
│   ├── transcribe.py          # Lógica de transcrição, registro de DLLs CUDA
│   ├── config.toml            # Configuração padrão
│   └── requirements.txt       # Dependências
├── gui/
│   ├── main.py                # Interface CustomTkinter
│   ├── backend.py             # Funções de backend (modelos, bibliotecas NVIDIA)
│   └── transcribe_runner.py   # Runner para subprocess/execução direta
└── cli.py                     # Interface de linha de comando
```

### Fluxo da GUI
1. Usuário clica em "Transcrever"
2. `start_transcription_thread()` é chamado
3. **Se frozen (executável):** Importa e executa `transcribe_runner` diretamente
4. **Se desenvolvimento:** Usa subprocess com `transcribe_runner.py`
5. Runner carrega modelo faster-whisper e transcreve
6. Logs são enviados para o widget de log

## Configurações de Build

### PyInstaller (Windows)
```bash
pyinstaller --noconfirm --onefile --windowed --name "TranscritorLocal" \
  --hidden-import=faster_whisper \
  --hidden-import=ctranslate2 \
  --hidden-import=tokenizers \
  --hidden-import=transcritor.gui.transcribe_runner \
  --collect-data faster_whisper \
  --add-data "src/transcritor/core;transcritor/core/" \
  --add-data "src/transcritor/gui;transcritor/gui/" \
  --add-binary "ffmpeg.exe;." \
  "src/transcritor/gui/main.py"
```

### GitHub Actions
- Disparado por tags `v*`
- Builds para Windows e macOS
- Upload de artefatos e criação de release automático

## Comandos Úteis

### Executar GUI (desenvolvimento)
```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe src\transcritor\gui\main.py
```

### Instalar Bibliotecas NVIDIA
```powershell
.\.venv\Scripts\python.exe -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
```

### Criar Tag e Gerar Build
```bash
git tag v1.X.X
git push origin v1.X.X
```

## Decisões Tomadas

### 1. Bibliotecas NVIDIA Sob Demanda
- **Decisão:** Não incluir bibliotecas NVIDIA no executável compilado
- **Motivo:** Reduzir tamanho do executável de ~1.5GB para ~200MB
- **Implementação:** Botões na aba Configurações para baixar/excluir

### 2. Execução Direta no Frozen
- **Decisão:** Executar `transcribe_runner` no mesmo processo quando frozen
- **Motivo:** Evitar abrir nova janela do executável
- **Problema:** Não está funcionando corretamente (múltiplas janelas)

### 3. Compatibilidade CUDA
- **Decisão:** Usar bibliotecas pip (CUDA 12) em vez de exigir CUDA 12 do sistema
- **Motivo:** Usuários podem ter CUDA 13+ instalado
- **Implementação:** Detecção automática de CUDA do sistema ou bibliotecas pip

## Próximos Passos
1. Analisar logs do v1.4.2 para diagnosticar problema de múltiplas janelas
2. Corrigir import do `transcribe_runner` no modo frozen
3. Testar transcrição no executável compilado
4. Remover logs de debug após resolução

## Links
- **Repositório:** https://github.com/redmagikarp13/transcritor-local-gui
- **Releases:** https://github.com/redmagikarp13/transcritor-local-gui/releases
- **Actions:** https://github.com/redmagikarp13/transcritor-local-gui/actions
