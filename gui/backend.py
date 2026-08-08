import os
import sys
import shutil
import threading
from pathlib import Path

# Adiciona o diretório raiz ao sys.path para importar tools
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from huggingface_hub import snapshot_download, scan_cache_dir

# Lista de modelos comuns do faster-whisper
MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

def get_repo_id(model_size: str) -> str:
    """Retorna o repo_id do HuggingFace para o tamanho do modelo."""
    return f"Systran/faster-whisper-{model_size}"

def get_downloaded_models() -> list:
    """Retorna uma lista de model_sizes que já estão baixados no cache."""
    try:
        hf_cache_info = scan_cache_dir()
    except Exception:
        return []
    
    downloaded = []
    for repo in hf_cache_info.repos:
        repo_id = repo.repo_id
        if repo_id.startswith("Systran/faster-whisper-"):
            model_size = repo_id.replace("Systran/faster-whisper-", "")
            downloaded.append(model_size)
    return downloaded

def download_model(model_size: str, progress_callback=None):
    """Baixa o modelo. O progress_callback(texto) pode ser usado para atualizar a UI."""
    repo_id = get_repo_id(model_size)
    if progress_callback:
        progress_callback(f"Iniciando download de {model_size}...\nIsso pode demorar dependendo da sua conexão.")
    try:
        # Usa snapshot_download direto, que é o que o faster-whisper faz por baixo dos panos.
        snapshot_download(repo_id=repo_id)
        if progress_callback:
            progress_callback(f"Modelo {model_size} baixado com sucesso!")
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"Erro ao baixar modelo: {e}")
        return False

def delete_model(model_size: str) -> bool:
    """Exclui o modelo do cache usando as ferramentas do huggingface_hub."""
    repo_id = get_repo_id(model_size)
    try:
        hf_cache_info = scan_cache_dir()
        for repo in hf_cache_info.repos:
            if repo.repo_id == repo_id:
                # Exclui todas as revisões do repositório
                revisions = [rev.commit_hash for rev in repo.revisions]
                delete_strategy = hf_cache_info.delete_revisions(*revisions)
                delete_strategy.execute()
                return True
        return False
    except Exception as e:
        print(f"Erro ao excluir modelo: {e}")
        return False
