"""Handle Agro login screen automation.

Fill login credentials by detecting the user and password fields in the Agro
login window before confirming access.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-09
Version: 1.0.0
"""

from __future__ import annotations

import time

import pyautogui
from pywinauto import Desktop

from config import AGRO_SENHA, AGRO_USUARIO

_LOGIN_WINDOW_TITLE = "Seleção de Usuário"
_LOGIN_WINDOW_CLASS = "TFSelUsu"
_LOGIN_FIELD_CLASS = "Edit"
_PASSWORD_FIELD_CLASS = "TEdit"
_LOGIN_TIMEOUT_SECONDS = 20


def _wait_login_window(timeout_seconds: int = _LOGIN_TIMEOUT_SECONDS):
    """Wait for the Agro user selection window to be available."""
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            window = Desktop(backend="win32").window(
                title=_LOGIN_WINDOW_TITLE,
                class_name=_LOGIN_WINDOW_CLASS,
            )

            if window.exists(timeout=1):
                window.set_focus()
                return window
        except Exception:
            pass

        time.sleep(0.5)

    raise RuntimeError("Tela 'Seleção de Usuário' não apareceu no login do Agro.")


def _fill_control(window, class_name: str, value: str, field_name: str) -> None:
    """Fill an edit control when it is visible and enabled."""
    try:
        control = window.child_window(class_name=class_name, found_index=0)

        if not control.exists(timeout=5):
            raise RuntimeError(f"Campo {field_name} não apareceu.")

        control.wait("visible enabled", timeout=5)
        control.click_input()
        time.sleep(0.2)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.write(value, interval=0.03)

    except Exception as exc:
        raise RuntimeError(f"Não foi possível preencher o campo {field_name}.") from exc


def login_agro(
    usuario: str = "RPA.OS16",
    senha: str = AGRO_SENHA,
) -> None:
    """Fill Agro login credentials."""
    window = _wait_login_window()

    _fill_control(
        window=window,
        class_name=_LOGIN_FIELD_CLASS,
        value=usuario,
        field_name="Usuário",
    )

    _fill_control(
        window=window,
        class_name=_PASSWORD_FIELD_CLASS,
        value=senha,
        field_name="Senha",
    )

    time.sleep(0.2)
    pyautogui.press("enter")