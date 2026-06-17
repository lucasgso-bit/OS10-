"""Run the financial robot workflow.

Update robot execution status, search pending suppliers, open FinAgro when needed,
and process all rows through process_1 in a single grouped execution.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-06-03
Version: 1.3.0
"""

from __future__ import annotations

import ctypes
import time

import psutil
import pyautogui
import pygetwindow as gw

from config import FINAGRO_EXE, COMPUTADOR_ROBO
from robots.robot_OS18.src.agro_alerts import (
    confirm_attention_popup,
    confirm_establishment_selection,
)
from robots.robot_OS18.src.agro_app import kill_agro_process, start_agro
from robots.robot_OS18.src.agro_login import login_agro
from robots.robot_OS18.src.database import (
    buscar_notas_pendentes,
    get_connection,
    update_robot_log_executando,
)
from robots.robot_OS18.src.notas.process_1 import process_1
from robots.robot_OS18.src.replacement_estab import wait_window_startswith

AGRO_EXE = FINAGRO_EXE
MAIN_AGRO_TITLE = "FINAGRO-"
FINAGRO_PROCESS_NAME = "FinAgro3C.exe"


def get_window_process_id(window) -> int | None:
    """Return the process ID that owns a window."""
    hwnd = getattr(window, "_hWnd", None)

    if not hwnd:
        return None

    process_id = ctypes.c_ulong()

    ctypes.windll.user32.GetWindowThreadProcessId(
        ctypes.c_void_p(hwnd),
        ctypes.byref(process_id),
    )

    return int(process_id.value)


def is_finagro_window(window) -> bool:
    """Check whether a window belongs to the FinAgro process."""
    process_id = get_window_process_id(window)

    if not process_id:
        return False

    try:
        process = psutil.Process(process_id)

        return process.name().lower() == FINAGRO_PROCESS_NAME.lower()

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def get_finagro_windows() -> list:
    """Return only visible windows that belong to FinAgro."""
    windows = []

    for window in gw.getAllWindows():
        title = window.title.strip()

        if not title:
            continue

        if is_finagro_window(window):
            windows.append(window)

    return windows


def get_open_finagro_window_titles() -> list[str]:
    """Return titles of visible FinAgro windows only."""
    return [window.title.strip() for window in get_finagro_windows()]


def print_open_finagro_windows() -> None:
    """Print only visible FinAgro windows for debugging."""
    print("\n===== JANELAS FINAGRO ABERTAS =====")

    for title in get_open_finagro_window_titles():
        print(f" - {title}")

    print("===== FIM JANELAS FINAGRO =====\n")


def focus_finagro_window_by_prefix(
    title_prefix: str,
    timeout_seconds: int = 2,
) -> bool:
    """Focus a FinAgro window by title prefix."""
    start = time.time()

    while time.time() - start < timeout_seconds:
        for window in get_finagro_windows():
            title = window.title.strip()

            if title.startswith(title_prefix):
                try:
                    window.activate()
                    time.sleep(0.5)
                    return True
                except Exception:
                    pass

        time.sleep(0.2)

    return False


def close_finagro_dialog_if_exists(title_prefix: str) -> bool:
    """Close a FinAgro modal dialog with Enter if it exists."""
    if not focus_finagro_window_by_prefix(title_prefix, timeout_seconds=1):
        return False

    print(f"Fechando popup do FinAgro: {title_prefix}")

    pyautogui.press("enter")
    time.sleep(1)

    return True


def close_known_finagro_window_if_exists() -> bool:
    """Close known FinAgro internal windows until the main window is reachable."""
    finagro_window_markers = [
        "Pagamentos/Exclusões de Títulos e Contas",
        "Pagamentos",
        "Exclusões",
        "Títulos",
        "Contas",
        "Consulta",
        "Filtrar",
        "Nota Fiscal",
        "Pagamento com Duplicatas",
        "Seleção",
        "Acerto Individual de Conta Movimento",
        "Conta Movimento - Lançamento",
        "Recibo",
    ]

    for window in get_finagro_windows():
        title = window.title.strip()

        if not title:
            continue

        if title.startswith(MAIN_AGRO_TITLE):
            continue

        if any(marker in title for marker in finagro_window_markers):
            print(f"Fechando janela interna do FinAgro: {title}")

            try:
                window.activate()
                time.sleep(0.5)

                pyautogui.hotkey("ctrl", "f4")
                time.sleep(1)

                return True

            except Exception as error:
                print(f"Erro ao tentar fechar janela '{title}': {error}")

    return False


def return_to_main_agro_window(max_attempts: int = 8) -> bool:
    """Close FinAgro dialogs/internal windows until the main window is active."""
    print("Garantindo retorno para a tela principal FINAGRO-...")

    for attempt in range(1, max_attempts + 1):
        print(f"Tentativa {attempt}/{max_attempts}")
        print_open_finagro_windows()

        if close_finagro_dialog_if_exists("Atenção"):
            continue

        if close_finagro_dialog_if_exists("Erro"):
            continue

        if close_finagro_dialog_if_exists("Conceito"):
            continue

        if close_known_finagro_window_if_exists():
            continue

        if focus_finagro_window_by_prefix(MAIN_AGRO_TITLE, timeout_seconds=2):
            print("Tela principal FINAGRO- ativa.")
            return True

        print("Tela principal ainda não encontrada. Enviando ESC...")
        pyautogui.press("esc")
        time.sleep(1)

    print("Não foi possível retornar para a tela principal FINAGRO-.")
    print_open_finagro_windows()

    return False


def start_agro_once() -> None:
    """Start Agro and prepare the main window."""
    print("Iniciando Agro...")
    print(f"AGRO_EXE usado: {AGRO_EXE}")

    kill_agro_process(FINAGRO_PROCESS_NAME)
    start_agro(AGRO_EXE)

    time.sleep(5)

    login_agro()
    print("Login realizado.")

    confirm_attention_popup()
    confirm_establishment_selection()

    if not wait_window_startswith(MAIN_AGRO_TITLE, timeout_seconds=15):
        raise RuntimeError("Tela FINAGRO- não abriu.")

    print("Agro pronto para uso.")


def run_process_1_grouped(notas: list[dict]) -> bool:
    """Run process_1 once with all rows from the query."""
    total_notas = len(notas)

    print("\n==============================")
    print("Iniciando process_1 agrupado")
    print(f"Total de linhas recebidas: {total_notas}")
    print("==============================")

    if not return_to_main_agro_window():
        print("Não foi possível garantir a tela principal antes do process_1.")
        return False

    processed = process_1(notas)

    if processed:
        print("process_1 agrupado finalizado com sucesso.")
        return True

    print("process_1 agrupado falhou.")
    return False


def run() -> None:
    """Run process_1 once for all pending rows and finish."""
    print("\nBuscando fornecedores...")

    try:
        with get_connection() as connection:
            update_robot_log_executando(connection, COMPUTADOR_ROBO)
            notas = buscar_notas_pendentes(connection)

        print(f"Fornecedores encontrados: {len(notas)}")

        if not notas:
            print("Nenhum fornecedor encontrado. Processo finalizado!")
            return

        start_agro_once()

        if not run_process_1_grouped(notas):
            print("Falha ao executar process_1.")
            return

        print("Fluxo completo finalizado.")

    except Exception as error:
        print(f"ERRO GERAL: {error}")
