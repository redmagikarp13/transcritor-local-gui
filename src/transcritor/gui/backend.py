import os
import sys
import subprocess
import shutil
from pathlib import Path
from huggingface_hub import scan_cache_dir, hf_hub_url
from huggingface_hub.file_download import repo_folder_name

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Tamanhos de modelo disponíveis no faster-whisper
MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Organização no HuggingFace que hospeda os modelos faster-whisper
_FW_ORG = "Systran"

# Bibliotecas NVIDIA necessárias para GPU
NVIDIA_PACKAGES = [
    "nvidia-cublas-cu12",
    "nvidia-cudnn-cu12==9.*",
    "nvidia-cuda-nvrtc-cu12",
]

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


# --- Gerenciamento de Bibliotecas NVIDIA ---

def is_cuda_available() -> bool:
    """Verifica se há dispositivo CUDA e bibliotecas disponíveis via CTranslate2."""
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False

def get_nvidia_packages_status() -> dict:
    """Retorna o status das bibliotecas NVIDIA / aceleração CUDA instaladas."""
    is_frozen = getattr(sys, 'frozen', False)
    
    if is_frozen:
        # No executável compilado, não executa pip (sys.executable é o próprio .exe).
        # Verifica diretamente se a GPU NVIDIA e o suporte a CUDA estão ativos.
        cuda_ok = is_cuda_available()
        return {
            "installed": cuda_ok,
            "is_frozen": True,
            "packages": [{"name": "CUDA GPU", "version": "Disponível"}] if cuda_ok else [],
            "missing": [] if cuda_ok else ["CUDA Toolkit 12 / DLLs NVIDIA"],
            "total_size": "Integrado/Sistema"
        }
    
    # Modo desenvolvimento: consulta o ambiente Python local via pip
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            cuda_ok = is_cuda_available()
            return {
                "installed": cuda_ok,
                "is_frozen": False,
                "packages": [],
                "missing": [] if cuda_ok else ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"],
                "total_size": "0 MB"
            }
        
        import json
        installed_packages = json.loads(result.stdout)
        nvidia_installed = []
        nvidia_missing = []
        
        for pkg in NVIDIA_PACKAGES:
            pkg_name = pkg.split("==")[0].replace("*", "")
            norm_pkg_name = pkg_name.lower().replace("-", "").replace("_", "")
            found = False
            for installed in installed_packages:
                norm_installed_name = installed["name"].lower().replace("-", "").replace("_", "")
                if norm_installed_name == norm_pkg_name or norm_installed_name.startswith(norm_pkg_name):
                    nvidia_installed.append({
                        "name": installed["name"],
                        "version": installed["version"]
                    })
                    found = True
                    break
            if not found:
                nvidia_missing.append(pkg)
        
        return {
            "installed": len(nvidia_missing) == 0,
            "is_frozen": False,
            "packages": nvidia_installed,
            "missing": nvidia_missing,
            "total_size": _estimate_nvidia_size(nvidia_installed)
        }
    except Exception as e:
        cuda_ok = is_cuda_available()
        return {
            "installed": cuda_ok,
            "is_frozen": False,
            "packages": [],
            "missing": [] if cuda_ok else ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"],
            "total_size": "0 MB",
            "error": str(e)
        }

def _estimate_nvidia_size(packages: list) -> str:
    """Estima o tamanho total das bibliotecas NVIDIA instaladas."""
    sizes = {
        "nvidia-cublas-cu12": 553,
        "nvidia-cudnn-cu12": 737,
        "nvidia-cuda-nvrtc-cu12": 76,
    }
    total_mb = 0
    for pkg in packages:
        for key, size in sizes.items():
            if key in pkg["name"].lower():
                total_mb += size
                break
    if total_mb == 0:
        return "0 MB"
    return f"~{total_mb} MB"

def install_nvidia_packages(progress_callback=None) -> bool:
    """Instala as bibliotecas NVIDIA necessárias para GPU."""
    if getattr(sys, 'frozen', False):
        if progress_callback:
            progress_callback("No executável compilado, instale o NVIDIA CUDA Toolkit 12 no sistema.")
        return False

    if progress_callback:
        progress_callback("Iniciando instalação das bibliotecas NVIDIA CUDA 12...")
        progress_callback("Isso pode demorar alguns minutos (~1.3 GB)...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + NVIDIA_PACKAGES,
            capture_output=True, text=True, timeout=600
        )
        
        if result.returncode == 0:
            if progress_callback:
                progress_callback("Bibliotecas NVIDIA instaladas com sucesso!")
                progress_callback("Reinicie o aplicativo para usar a GPU.")
            return True
        else:
            if progress_callback:
                progress_callback(f"Erro na instalação: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        if progress_callback:
            progress_callback("Timeout na instalação. Tente novamente.")
        return False
    except Exception as e:
        if progress_callback:
            progress_callback(f"Erro: {e}")
        return False

def uninstall_nvidia_packages(progress_callback=None) -> bool:
    """Desinstala as bibliotecas NVIDIA."""
    if getattr(sys, 'frozen', False):
        if progress_callback:
            progress_callback("Operação não suportada no executável compilado.")
        return False

    if progress_callback:
        progress_callback("Desinstalando bibliotecas NVIDIA...")
    
    try:
        status = get_nvidia_packages_status()
        if not status.get("packages"):
            if progress_callback:
                progress_callback("Nenhuma biblioteca NVIDIA encontrada.")
            return True
        
        packages_to_remove = [p["name"] for p in status["packages"]]
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y"] + packages_to_remove,
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            if progress_callback:
                progress_callback("Bibliotecas NVIDIA desinstaladas com sucesso!")
            return True
        else:
            if progress_callback:
                progress_callback(f"Erro na desinstalação: {result.stderr}")
            return False
    except Exception as e:
        if progress_callback:
            progress_callback(f"Erro: {e}")
        return False
