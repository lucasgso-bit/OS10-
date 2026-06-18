"""Handle Agro login screen automation for the OS11 robot.

Focus the login window and fill credentials before confirming access.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import time

import pyautogui

from config import AGRO_SENHA, AGRO_USUARIO
from robots.robot_OS11.src.agro_alerts import confirmar_todas_atencoes
from robots.robot_OS11.src.window_utils import focar_janela_por_titulo


def login_agro(usuario: str = "RPA.OS11", senha: str = AGRO_SENHA) -> None:
    """Fill Agro login credentials and confirm access."""
    focar_janela_por_titulo("Seleção de Usuário")
    time.sleep(2)

    print("Voltando para o campo de usuário com SHIFT + TAB...")
    pyautogui.hotkey("shift", "tab")
    time.sleep(0.3)

    print("Digitando usuário do Agro...")
    pyautogui.write(usuario, interval=0.03)
    time.sleep(0.3)

    print("Indo para o campo de senha com TAB...")
    pyautogui.press("tab")
    time.sleep(0.3)

    print("Digitando senha do Agro...")
    pyautogui.write(senha, interval=0.03)
    time.sleep(0.3)

    print("Confirmando login com ENTER...")
    pyautogui.press("enter")
    time.sleep(1)

    confirmar_todas_atencoes(timeout_primeira=1.5)

    print("Enviando ENTER adicional após login...")
    pyautogui.press("enter")
    time.sleep(0.8)
