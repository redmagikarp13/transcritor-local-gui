# Contexto do Projeto - Transcritor Local GUI

## Última Atualização
13 de agosto de 2026

## Status Atual
- **Versão:** v1.4.6 (gerenciador completo de DLLs CUDA 12: download direto via PyPI ou pip, atualização, exclusão e verificação em tempo real)
- **Branch:** main
- **Última Release:** v1.4.5

## Problema Resolvido: Gerenciamento de DLLs CUDA 12 (cuBLAS / cuDNN)
- **Contexto:** O faster-whisper/CTranslate2 requer especificamente as bibliotecas do CUDA 12, mesmo quando o usuário tem o CUDA Toolkit 13 instalado no sistema.
- **Solução Completa Implementada:**
  1. **Aba Configurações:** Seção dedicada para *Aceleração por Placa de Vídeo (NVIDIA CUDA 12)* com exibição em tempo real do status da GPU e das bibliotecas.
  2. **Baixar / Atualizar DLLs (~1.3 GB):** Baixa via `pip install --upgrade` ou via download direto das wheels do PyPI (extraindo os binários em `%LOCALAPPDATA%\TranscritorLocal\nvidia`), com barra/percentual de progresso em tempo real.
  3. **Excluir DLLs:** Botão para desinstalar e excluir pastas locais das DLLs, liberando ~1.3 GB de espaço em disco e voltando para a CPU de forma segura.
  4. **Verificar Status:** Botão para re-escanear a disponibilidade de GPU e DLLs cuBLAS/cuDNN a qualquer momento.
  5. **Busca de DLLs Abrangente:** `_register_nvidia_dlls()` varre automaticamente o `%LOCALAPPDATA%\TranscritorLocal\nvidia`, `%APPDATA%\Python`, `.venv`, pastas locais e `CUDA_PATH`.
  6. **Fallback Automático e Resiliente:** Se faltar qualquer biblioteca ou a GPU falhar, `load_model()` e `transcribe_one()` recaem instantaneamente para CPU (`int8`) sem travar a aplicação.

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
