import time

import pyautogui
import pygetwindow as gw


VIASOFT_WINDOW_TITLE = "AGRO-AG"


def focar_janela_viasoft() -> None:
    janelas = [j for j in gw.getAllTitles() if j.startswith(VIASOFT_WINDOW_TITLE)]
    if janelas:
        gw.getWindowsWithTitle(janelas[0])[0].activate()
        time.sleep(0.5)


def finalizar_parte_1() -> None:
    """Save the first part of the NF: CTRL+S then ALT+O."""
    focar_janela_viasoft()
    time.sleep(0.5)

    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)

    pyautogui.hotkey("alt", "o")
    time.sleep(1)
