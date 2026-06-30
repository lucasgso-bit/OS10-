import subprocess
import time

import psutil
import pyautogui

from config import AGRO_EXE, AGRO_SENHA, AGRO_USUARIO
from robots.robot_OS17.src.viasoft.viasoft_janela import focar_janela_por_titulo


VIASOFT_WINDOW_TITLE = "AGRO-AG"


def matar_agro3c() -> None:
    """Kill any running AGRO-AG process."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and "agro" in proc.info["name"].lower():
            proc.kill()
    time.sleep(2)


def abrir_agro3c() -> None:
    """Launch the Viasoft/AGRO-AG application."""
    subprocess.Popen(AGRO_EXE)
    time.sleep(8)


def preencher_login() -> None:
    """Fill in username and password on the login screen."""
    focar_janela_por_titulo(VIASOFT_WINDOW_TITLE)
    time.sleep(1)

    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(AGRO_USUARIO, interval=0.05)
    pyautogui.press("tab")
    pyautogui.typewrite(AGRO_SENHA, interval=0.05)
    pyautogui.press("enter")
    time.sleep(5)


def confirmar_estabelecimento_inicial() -> None:
    """Dismiss the initial establishment selection dialog."""
    focar_janela_por_titulo(VIASOFT_WINDOW_TITLE)
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(2)


def login_viasoft() -> None:
    """Full login flow: kill → open → login → confirm establishment."""
    matar_agro3c()
    abrir_agro3c()
    preencher_login()
    confirmar_estabelecimento_inicial()
