"""Local, user-initiated diagnostics; no arbitrary shell or model-generated commands."""
import os
import shutil
import subprocess
from pathlib import Path

import psutil


def system_summary():
    memory = psutil.virtual_memory()
    drive = Path.home().anchor or "/"
    disk = psutil.disk_usage(drive)
    return ("CPU: %.1f%% | %s threads\nRAM: %.1f / %.1f GB (%.1f%%)\nDisco: %.1f GB livres" %
            (psutil.cpu_percent(interval=0.25), psutil.cpu_count(),
             memory.used / 1e9, memory.total / 1e9, memory.percent, disk.free / 1e9))


def git_summary(directory):
    root = Path(directory).resolve(strict=True)
    git = shutil.which("git")
    if not git:
        raise RuntimeError("Git não instalado ou fora do PATH.")
    if not root.is_dir():
        raise ValueError("Selecione uma pasta.")
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"

    def run(*args):
        result = subprocess.run([git, "-C", str(root), "-c", "core.fsmonitor=false",
                                 "-c", "core.hooksPath=" + os.devnull, *args],
                                capture_output=True, timeout=15, text=True, encoding="utf-8",
                                errors="replace", env=env,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise RuntimeError("Não foi possível ler este repositório Git.")
        return result.stdout[:12000].strip()

    run("rev-parse", "--is-inside-work-tree")
    return "\n\n".join([
        "Estado do repositório:\n" + run("status", "--short", "--branch", "--untracked-files=no"),
        "Últimos commits:\n" + run("log", "-5", "--format=%h %s"),
        "Resumo de alterações:\n" + run("diff", "--stat", "--no-ext-diff", "--no-textconv"),
    ])


def launch_codex(directory):
    """Launch an installed official Codex CLI in a user-selected directory.

    No token sharing, arbitrary commands, or automatic GitHub writes.
    """
    root = Path(directory).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Selecione uma pasta válida.")
    exe = shutil.which("codex.exe") if os.name == "nt" else shutil.which("codex")
    if not exe:
        raise RuntimeError("Codex CLI executável não encontrado. Instale o Codex oficial e entre com ChatGPT.")
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    return subprocess.Popen([exe, "--sandbox", "workspace-write", "--ask-for-approval", "on-request"],
                            cwd=str(root), env=env, creationflags=flags)
