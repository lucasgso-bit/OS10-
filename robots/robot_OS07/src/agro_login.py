"""Handle Agro login screen automation.

Fill login credentials and confirm access.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from __future__ import annotations

import time

import pyautogui


def login_agro(
    usuario: str = "RPA.OS07",
    senha: str = "12345678",
) -> None:
    """Fill Agro login credentials."""
    time.sleep(2)

    # A tela já inicia com foco no campo Senha.
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(senha, interval=0.03)

    time.sleep(0.2)

    pyautogui.press("enter")