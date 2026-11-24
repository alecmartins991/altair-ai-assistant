import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT)).resolve()
ALT_DIR = RESOURCE_ROOT / "src" / "altair"
CORE_DIR = ALT_DIR / "core"
APP_DIR = ALT_DIR / "app"

for p in (str(ALT_DIR), str(CORE_DIR), str(APP_DIR), str(RESOURCE_ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

USER_ROOT = (
    Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Altair"
    if getattr(sys, "frozen", False)
    else ROOT
)
USER_ROOT = Path(os.environ.get("ALTAIR_USER_DATA_DIR", USER_ROOT))
DATA_ROOT = Path(os.environ.get("ALTAIR_DATA_DIR", USER_ROOT / "data"))
CONFIG_ROOT = Path(os.environ.get("ALTAIR_CONFIG_DIR", USER_ROOT / "configs"))
for directory in (DATA_ROOT, CONFIG_ROOT, DATA_ROOT / "json"):
    directory.mkdir(parents=True, exist_ok=True)

# Prevent concurrent refresh-token rotation and competing microphone loops.
# Hold the OS lock until process exit; Windows releases it even on a crash.
if os.name == "nt":
    import msvcrt
    lock_path = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Altair" / "runtime.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _runtime_lock = open(lock_path, "a+b")
    if lock_path.stat().st_size == 0:
        _runtime_lock.write(b"0")
        _runtime_lock.flush()
    _runtime_lock.seek(0)
    try:
        msvcrt.locking(_runtime_lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, "Feche a outra instância do Altair antes de abrir esta versão.", "Altair", 0x30)
        sys.exit(1)

os.environ.setdefault("ALTAIR_USER_DATA_DIR", str(USER_ROOT))
os.environ.setdefault("ALTAIR_CONFIG_DIR", str(CONFIG_ROOT))
os.environ.setdefault("ALTAIR_WWEBJS_DIR", str(RESOURCE_ROOT / "scripts" / "whatsapp"))
os.environ.setdefault("ALTAIR_CHROME_PROFILE_DIR", str(DATA_ROOT / "chrome_profile"))
os.environ.setdefault("ALTAIR_DATA_DIR", str(DATA_ROOT))
node = RESOURCE_ROOT / "tools" / "node" / "node.exe"
if node.is_file():
    os.environ.setdefault("ALTAIR_NODE_PATH", str(node))
os.environ.setdefault("PUPPETEER_CACHE_DIR", str(RESOURCE_ROOT / "browser"))
if (RESOURCE_ROOT / "support.json").is_file():
    os.environ.setdefault("ALTAIR_STORE_PACKAGE", "1")

from altair.core.privacy import external_services_allowed

os.environ.setdefault(
    "ALTAIR_EXTERNAL_SERVICES_ALLOWED",
    "1" if external_services_allowed() else "0",
)

from altair import main  # noqa: E402, F401

