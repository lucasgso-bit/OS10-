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

from config import AGRO_SENHA, AGRO_USUARIO


def login_agro(
    usuario: str = AGRO_USUARIO,
    senha: str = AGRO_SENHA,
) -> None:
    """Fill Agro login credentials."""
    time.sleep(2)

    # A tela já inicia com foco no campo Senha.
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(senha, interval=0.03)

    time.sleep(0.2)

    pyautogui.press("enter")