"""Agro establishment switching for OS20."""

from __future__ import annotations

import time

import pyautogui
import pygetwindow as gw


def wait_window_startswith(title: str, timeout_seconds: int = 10) -> bool:
    """Wait until a window starting with the given title appears."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for window in gw.getAllWindows():
            if window.title.startswith(title):
                try:
                    window.activate()
                except Exception:
                    pass
                return True
        time.sleep(0.5)
    return False


def focus_window(title_prefix: str) -> bool:
    """Focus the first window whose title starts with the given prefix."""
    for window in gw.getAllWindows():
        if window.title.startswith(title_prefix):
            try:
                window.activate()
                time.sleep(0.3)
                return True
            except Exception:
                pass
    return False


def switch_establishment(estab: int | str) -> bool:
    """Switch Agro to the requested establishment."""
    if not wait_window_startswith("AGRO-AG", timeout_seconds=10):
        print("Tela principal AGRO-AG não encontrada.")
        return False

    pyautogui.hotkey("shift", "f12")
    time.sleep(1)

    if not wait_window_startswith("Seleção de Estabelecimento para Trabalho", timeout_seconds=10):
        print("Tela de seleção de estabelecimento não apareceu.")
        return False

    pyautogui.hotkey("ctrl", "tab")
    time.sleep(0.3)
    pyautogui.write(str(estab).strip(), interval=0.03)
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(0.3)
    pyautogui.press("enter")

    print(f"Estabelecimento alterado para: {estab}")
    return True
