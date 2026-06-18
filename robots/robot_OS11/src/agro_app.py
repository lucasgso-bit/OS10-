"""Control the Agro desktop application process for the OS11 robot.

Close existing Agro instances and start a clean application session.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from pathlib import Path

import psutil


def get_process_session_id(pid: int) -> int | None:
    session_id = ctypes.c_ulong()
    success = ctypes.windll.kernel32.ProcessIdToSessionId(
        ctypes.c_ulong(pid),
        ctypes.byref(session_id),
    )
    if not success:
        return None
    return int(session_id.value)


def kill_agro_process(process_name: str = "Agro3C.exe") -> int:
    """Terminate Agro processes running in the current Windows session."""
    killed = 0
    current_session_id = get_process_session_id(os.getpid())

    if current_session_id is None:
        raise RuntimeError("Não foi possível identificar a sessão atual do Python.")

    for process in psutil.process_iter(["pid", "name"]):
        try:
            name = process.info.get("name")
            pid = process.info.get("pid")

            if not name or not pid:
                continue

            if name.lower() != process_name.lower():
                continue

            process_session_id = get_process_session_id(pid)

            if process_session_id != current_session_id:
                continue

            process.kill()
            process.wait(timeout=5)
            killed += 1
            print(f"Processo finalizado: {name} PID={pid}")

        except psutil.NoSuchProcess:
            continue

        except psutil.AccessDenied:
            print(f"Sem permissão para finalizar {process_name} PID={process.pid}")

        except psutil.TimeoutExpired:
            print(f"Timeout ao finalizar {process_name} PID={process.pid}")

    if killed:
        time.sleep(2)

    return killed


def start_agro(agro_exe: str) -> subprocess.Popen:
    """Start the Agro application."""
    agro_path = Path(agro_exe)

    if not agro_path.exists():
        raise FileNotFoundError(f"Executável do Agro não encontrado: {agro_exe}")

    return subprocess.Popen(
        [str(agro_path)],
        cwd=str(agro_path.parent),
    )
