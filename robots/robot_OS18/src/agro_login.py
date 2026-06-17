"""Handle Agro login screen automation.

Fill login credentials and confirm access.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-05-28
Version: 1.1.0
"""

from __future__ import annotations
from config import AGRO_USUARIO as USUARIO_AGRO, AGRO_SENHA as SENHA_AGRO

import time

import pyautogui
import pyperclip


def paste_text(text: str) -> None:
    """Paste text using the clipboard."""
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)


def login_agro(
    usuario: str = USUARIO_AGRO,
    senha: str = SENHA_AGRO,
) -> None:
    """Fill Agro login credentials."""
    time.sleep(2)

    pyautogui.hotkey("shift", "tab")
    time.sleep(0.2)

    paste_text(usuario)
    pyautogui.press("enter")
    time.sleep(0.5)

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)

    paste_text(senha)
    time.sleep(0.2)

    pyautogui.press("enter")
