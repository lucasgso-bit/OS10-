"""Handle Agro alert windows.

Detect warning dialogs and confirm them automatically.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from __future__ import annotations

import time

import pyautogui
import pygetwindow as gw


def confirm_attention_popup(timeout_seconds: int = 10) -> bool:
    """Confirm the 'Atenção!' popup if it appears."""
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        windows = gw.getWindowsWithTitle("Atenção!")

        if windows:
            time.sleep(0.5)

            pyautogui.press("enter")
            print("Popup 'Atenção!' confirmado.")

            return True

        time.sleep(0.5)

    return False


def confirm_establishment_selection(timeout_seconds: int = 10) -> bool:
    """Confirm the establishment selection window if it appears."""
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        windows = gw.getWindowsWithTitle(
            "Seleção de Estabelecimento para Trabalho"
        )

        if windows:
            time.sleep(0.5)

            for _ in range(4):
                pyautogui.press("enter")
                time.sleep(0.2)

            print(
                "Tela 'Seleção de Estabelecimento para Trabalho' confirmada."
            )

            return True

        time.sleep(0.5)

    return False
