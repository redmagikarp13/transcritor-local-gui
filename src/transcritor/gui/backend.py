import os
import sys
import subprocess
import shutil
import urllib.request
import json
import zipfile
from pathlib import Path
from huggingface_hub import scan_cache_dir, hf_hub_url
from huggingface_hub.file_download import repo_folder_name

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Tamanhos de modelo disponíveis no faster-whisper
MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# Organização no HuggingFace que hospeda os modelos faster-whisper
_FW_ORG = "Systran"

# Bibliotecas NVIDIA necessárias para GPU CUDA 12
NVIDIA_PACKAGES = [
    "nvidia-cublas-cu12",
    "nvidia-cudnn-cu12==9.*",
    "nvidia-cuda-nvrtc-cu12",
]

NVIDIA_PYPI_NAMES = [
    "nvidia-cublas-cu12",
    "nvidia-cudnn-cu12",
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

def get_local_nvidia_dir() -> Path:
    """Retorna o diretório local para armazenar DLLs baixadas diretamente."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "TranscritorLocal" / "nvidia"
    return Path.home() / ".transcritor_local" / "nvidia"

def _get_system_python() -> str:
    """Retorna o caminho do executável Python disponível no sistema."""
    if not getattr(sys, 'frozen', False):
        return sys.executable
    
    # Procura no PATH
    for name in ["python", "python3", "py"]:
        p = shutil.which(name)
        if p and not p.lower().endswith("transcritorlocal.exe"):
            return p
            
    # Procura em locais comuns de instalação do Python no Windows
    candidates = []
    appdata = os.environ.get("LOCALAPPDATA")
    if appdata:
        try:
            candidates.extend(Path(appdata).glob("Programs/Python/Python*/python.exe"))
        except Exception:
            pass
    try:
        candidates.extend(Path("C:/").glob("Python*/python.exe"))
        candidates.extend(Path("C:/Program Files/Python*").glob("python.exe"))
    except Exception:
        pass
    
    for c in candidates:
        if c.exists():
            return str(c)
            
    return None

def get_gpu_info() -> dict:
    """Verifica se há placa de vídeo NVIDIA disponível no sistema."""
    try:
        import ctranslate2
        count = ctranslate2.get_cuda_device_count()
        if count > 0:
            return {"has_gpu": True, "count": count}
    except Exception:
        pass
    return {"has_gpu": False, "count": 0}

def is_cuda_available() -> bool:
    """Verifica se há dispositivo CUDA e bibliotecas cuBLAS disponíveis."""
    try:
        from transcritor.core.transcribe import _register_nvidia_dlls
        _register_nvidia_dlls()
    except Exception:
        pass
        
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() == 0:
            return False
            
        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.CDLL("cublas64_12.dll")
                return True
            except Exception:
                return False
        return True
    except Exception:
        return False

def get_nvidia_packages_status() -> dict:
    """Retorna o status das bibliotecas NVIDIA / aceleração CUDA instaladas."""
    try:
        from transcritor.core.transcribe import _register_nvidia_dlls
        _register_nvidia_dlls()
    except Exception:
        pass

    cuda_ok = is_cuda_available()
    gpu_info = get_gpu_info()
    is_frozen = getattr(sys, 'frozen', False)
    
    # Verifica pasta local customizada
    local_dir = get_local_nvidia_dir()
    has_local_dlls = local_dir.exists() and (
        list(local_dir.rglob("cublas64_12.dll")) or list(local_dir.rglob("cudnn*.dll"))
    )

    if is_frozen:
        return {
            "has_gpu": gpu_info["has_gpu"],
            "installed": cuda_ok,
            "is_frozen": True,
            "packages": [{"name": "CUDA 12 + cuBLAS + cuDNN", "version": "Ativo"}] if cuda_ok else [],
            "missing": [] if cuda_ok else ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"],
            "total_size": "~1.3 GB" if cuda_ok else "0 MB"
        }
    
    # Modo desenvolvimento: consulta pip
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {
                "has_gpu": gpu_info["has_gpu"],
                "installed": cuda_ok,
                "is_frozen": False,
                "packages": [{"name": "Bibliotecas CUDA 12", "version": "Detectadas"}] if (cuda_ok or has_local_dlls) else [],
                "missing": [] if (cuda_ok or has_local_dlls) else ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"],
                "total_size": "~1.3 GB" if (cuda_ok or has_local_dlls) else "0 MB"
            }
        
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
        
        is_inst = (len(nvidia_missing) == 0 and cuda_ok) or (cuda_ok and has_local_dlls)
        return {
            "has_gpu": gpu_info["has_gpu"],
            "installed": is_inst,
            "is_frozen": False,
            "packages": nvidia_installed if nvidia_installed else ([{"name": "DLLs CUDA 12", "version": "Locais"}] if is_inst else []),
            "missing": [] if is_inst else nvidia_missing,
            "total_size": _estimate_nvidia_size(nvidia_installed) if nvidia_installed else ("~1.3 GB" if is_inst else "0 MB")
        }
    except Exception as e:
        return {
            "has_gpu": gpu_info["has_gpu"],
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

def _get_whl_info(pkg_name: str):
    """Consulta os metadados do PyPI para encontrar a wheel Windows x64."""
    url = f"https://pypi.org/pypi/{pkg_name}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "TranscritorLocal/1.4.6"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for u in data.get("urls", []):
        fn = u.get("filename", "")
        if "win_amd64" in fn and fn.endswith(".whl"):
            return u.get("url"), fn, u.get("size", 0)
    return None, None, 0

def _download_and_extract_wheel(pkg_name: str, target_dir: Path, progress_callback=None) -> bool:
    """Baixa a wheel do PyPI e extrai os binários diretamente no target_dir."""
    url, filename, total_size = _get_whl_info(pkg_name)
    if not url:
        if progress_callback:
            progress_callback(f"Não foi possível localizar pacote {pkg_name} no PyPI.")
        return False
    
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_whl = target_dir / filename

    try:
        size_mb = total_size // (1024 * 1024) if total_size else 0
        if progress_callback:
            progress_callback(f"Baixando {pkg_name} ({size_mb} MB)...")
        
        req = urllib.request.Request(url, headers={"User-Agent": "TranscritorLocal/1.4.6"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(temp_whl, "wb") as out_f:
            downloaded = 0
            block_size = 1024 * 1024
            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                out_f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    pct = int(downloaded * 100 / total_size)
                    cur_mb = downloaded // (1024 * 1024)
                    progress_callback(f"Baixando {pkg_name}: {pct}% ({cur_mb}/{size_mb} MB)")
        
        if progress_callback:
            progress_callback(f"Extraindo {pkg_name}...")
        
        with zipfile.ZipFile(temp_whl, "r") as z:
            z.extractall(target_dir)
            
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"Erro no download de {pkg_name}: {e}")
        return False
    finally:
        if temp_whl.exists():
            try:
                temp_whl.unlink()
            except Exception:
                pass

def install_nvidia_packages(progress_callback=None) -> bool:
    """Instala ou atualiza as bibliotecas NVIDIA necessárias para GPU CUDA 12."""
    python_bin = _get_system_python()
    
    # 1. Tenta instalar via pip se Python estiver disponível
    if python_bin:
        if progress_callback:
            progress_callback("Iniciando instalação das bibliotecas NVIDIA CUDA 12 via pip...")
            progress_callback("Baixando pacotes cuBLAS e cuDNN (~1.3 GB)...")
        
        try:
            cmd = [python_bin, "-m", "pip", "install", "--upgrade"]
            if getattr(sys, 'frozen', False):
                cmd.append("--user")
            cmd.extend(NVIDIA_PACKAGES)

            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=900
            )
            
            if result.returncode == 0:
                try:
                    from transcritor.core.transcribe import _register_nvidia_dlls
                    _register_nvidia_dlls()
                except Exception:
                    pass
                if progress_callback:
                    progress_callback("Bibliotecas NVIDIA CUDA 12 instaladas com sucesso!")
                return True
            else:
                if progress_callback:
                    progress_callback(f"Pip reportou erro. Tentando download direto...\n{result.stderr}")
        except Exception as e:
            if progress_callback:
                progress_callback(f"Falha no pip: {e}. Tentando download direto...")
    
    # 2. Fallback: Download direto e extração das wheels do PyPI
    target_dir = get_local_nvidia_dir()
    if progress_callback:
        progress_callback("Baixando bibliotecas NVIDIA diretamente do PyPI...")
    
    all_ok = True
    for pkg in NVIDIA_PYPI_NAMES:
        ok = _download_and_extract_wheel(pkg, target_dir, progress_callback)
        if not ok:
            all_ok = False
            break
            
    if all_ok:
        try:
            from transcritor.core.transcribe import _register_nvidia_dlls
            _register_nvidia_dlls()
        except Exception:
            pass
        if progress_callback:
            progress_callback("Todas as bibliotecas CUDA 12 foram instaladas com sucesso!")
        return True
    else:
        if progress_callback:
            progress_callback("Falha ao baixar algumas bibliotecas NVIDIA.")
        return False

def uninstall_nvidia_packages(progress_callback=None) -> bool:
    """Desinstala e remove todas as bibliotecas NVIDIA CUDA 12."""
    if progress_callback:
        progress_callback("Excluindo bibliotecas NVIDIA CUDA 12...")
    
    success = True
    
    # 1. Se pip estiver disponível, tenta desinstalar
    python_bin = _get_system_python()
    if python_bin:
        try:
            packages_to_remove = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12", "nvidia-cuda-nvrtc-cu12"]
            subprocess.run(
                [python_bin, "-m", "pip", "uninstall", "-y"] + packages_to_remove,
                capture_output=True, text=True, timeout=120
            )
        except Exception:
            pass
    
    # 2. Remove pastas locais de DLLs
    local_dirs = [
        get_local_nvidia_dir(),
        Path(os.environ.get("APPDATA", "")) / "TranscritorLocal" / "nvidia",
        Path(os.environ.get("LOCALAPPDATA", "")) / "TranscritorLocal" / "nvidia",
        Path(sys.executable).parent / "nvidia" if getattr(sys, 'frozen', False) else None
    ]
    
    for d in local_dirs:
        if d and d.exists():
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception as e:
                print(f"Erro ao remover {d}: {e}")
                success = False

    try:
        from transcritor.core.transcribe import _register_nvidia_dlls
        _register_nvidia_dlls()
    except Exception:
        pass

    if progress_callback:
        progress_callback("Bibliotecas NVIDIA excluídas com sucesso!")
        
    return success
