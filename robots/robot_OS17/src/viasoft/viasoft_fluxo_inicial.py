import time

import pyautogui

from robots.robot_OS17.src.viasoft.viasoft_janela import focar_janela_por_titulo


VIASOFT_WINDOW_TITLE = "AGRO-AG"


def executar_fluxo_inicial_agro() -> None:
    """Navigate to the Nota Fiscal entry screen via ALT+N → Enter → ALT+V."""
    focar_janela_por_titulo(VIASOFT_WINDOW_TITLE)
    time.sleep(1)

    pyautogui.hotkey("alt", "n")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.hotkey("alt", "v")
    time.sleep(2)
