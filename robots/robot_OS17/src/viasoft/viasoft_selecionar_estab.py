import time

import pyautogui

from robots.robot_OS17.src.viasoft.viasoft_janela import focar_janela_por_titulo


VIASOFT_WINDOW_TITLE = "AGRO-AG"


def alterar_estabelecimento_trabalho(estab: str) -> None:
    """Switch working establishment via SHIFT+F12."""
    focar_janela_por_titulo(VIASOFT_WINDOW_TITLE)
    time.sleep(0.5)

    pyautogui.hotkey("shift", "f12")
    time.sleep(1)

    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(str(estab), interval=0.05)
    pyautogui.press("enter")
    time.sleep(2)
