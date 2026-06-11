"""Handle Agro establishment validation and switching.

Validate the main Agro window and switch to the note establishment when needed.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-08
Version: 1.0.0
"""

from __future__ import annotations

import time

import pyautogui
import pygetwindow as gw


def wait_window_startswith(title: str, timeout_seconds: int = 10) -> bool:
    """Wait until a window starting with the given title appears."""
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        windows = gw.getAllWindows()

        for window in windows:
            if window.title.startswith(title):
                try:
                    window.activate()
                except Exception:
                    pass

                return True

        time.sleep(0.5)

    return False


def switch_establishment(estab: int | str) -> bool:
    """Switch Agro to the requested establishment."""
    agro_opened = wait_window_startswith("AGRO-AG", timeout_seconds=10)

    if not agro_opened:
        print("Tela principal AGRO-AG não encontrada.")
        return False

    estab_value = str(estab).strip()

    if estab_value == "0":
        pyautogui.hotkey("shift", "f12")
    else:
        pyautogui.hotkey("shift", "f12")

    time.sleep(1)

    establishment_opened = wait_window_startswith(
        "Seleção de Estabelecimento para Trabalho",
        timeout_seconds=10,
    )

    if not establishment_opened:
        print("Tela de seleção de estabelecimento não apareceu.")
        return False

    pyautogui.hotkey("ctrl", "tab")
    time.sleep(0.3)

    pyautogui.write(estab_value, interval=0.03)
    time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(0.3)
    pyautogui.press("enter")

    print(f"Estabelecimento alterado para: {estab_value}")
    return True
