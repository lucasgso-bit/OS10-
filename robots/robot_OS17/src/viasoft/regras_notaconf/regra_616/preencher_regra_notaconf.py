import time

import pyautogui
import pygetwindow as gw


NOTACONF_FIELD_VALUE = "616"
VIASOFT_WINDOW_TITLE = "AGRO-AG"


def focar_janela_viasoft() -> None:
    janelas = [j for j in gw.getAllTitles() if j.startswith(VIASOFT_WINDOW_TITLE)]
    if janelas:
        gw.getWindowsWithTitle(janelas[0])[0].activate()
        time.sleep(0.5)


def preencher_regra_notaconf() -> None:
    """Create a new NF entry and fill NOTACONF = 616."""
    focar_janela_viasoft()
    time.sleep(0.5)

    pyautogui.hotkey("ctrl", "insert")
    time.sleep(1)

    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(NOTACONF_FIELD_VALUE, interval=0.05)
    pyautogui.press("enter")
    time.sleep(1)
