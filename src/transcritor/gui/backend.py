import os
import sys
from pathlib import Path
from huggingface_hub import scan_cache_dir, hf_hub_url
from huggingface_hub.file_download import repo_folder_name

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Tamanhos de modelo disponíveis no faster-whisper
MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Organização no HuggingFace que hospeda os modelos faster-whisper
_FW_ORG = "Systran"

def get_repo_id(model_size: str) -> str:
    """Retorna o repo_id do HuggingFace para o modelo faster-whisper."""
    return f"{_FW_ORG}/faster-whisper-{model_size}"

def get_downloaded_models() -> list:
    """Retorna uma lista de model_sizes já baixados no cache do HuggingFace."""
    try:
        hf_cache_info = scan_cache_dir()
    except Exception:
        return []

    downloaded = []
    for repo in hf_cache_info.repos:
        repo_id = repo.repo_id
        if repo_id.startswith(f"{_FW_ORG}/faster-whisper-"):
            model_size = repo_id.replace(f"{_FW_ORG}/faster-whisper-", "")
            downloaded.append(model_size)
    return downloaded

def download_model(model_size: str, progress_callback=None):
    """Baixa o modelo faster-whisper via HuggingFace Hub (forçando o download)."""
    from huggingface_hub import snapshot_download
    repo_id = get_repo_id(model_size)
    if progress_callback:
        progress_callback(f"Iniciando download de {model_size}...\nIsso pode demorar dependendo da sua conexão.")
    try:
        snapshot_download(repo_id=repo_id)
        if progress_callback:
            progress_callback(f"Modelo {model_size} baixado com sucesso!")
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"Erro ao baixar modelo: {e}")
        return False

def delete_model(model_size: str) -> bool:
    """Exclui o modelo do cache local."""
    repo_id = get_repo_id(model_size)
    try:
        hf_cache_info = scan_cache_dir()
        for repo in hf_cache_info.repos:
            if repo.repo_id == repo_id:
                revisions = [rev.commit_hash for rev in repo.revisions]
                delete_strategy = hf_cache_info.delete_revisions(*revisions)
                delete_strategy.execute()
                return True
        return False
    except Exception as e:
        print(f"Erro ao excluir modelo: {e}")
        return False
