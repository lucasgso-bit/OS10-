import time

import pyautogui
import pygetwindow as gw


VIASOFT_WINDOW_TITLE = "AGRO-AG"
ITEM_VALUE = "43"
CFOP_VALUE = "1949"


def focar_janela_viasoft() -> None:
    janelas = [j for j in gw.getAllTitles() if j.startswith(VIASOFT_WINDOW_TITLE)]
    if janelas:
        gw.getWindowsWithTitle(janelas[0])[0].activate()
        time.sleep(0.5)


def preencher_item_cfop_valorimposto(pedido: dict) -> None:
    """Fill item = 43, CFOP = 1949, and the credito_resumo value."""
    focar_janela_viasoft()
    time.sleep(0.5)

    credito_resumo = str(pedido.get("credito_resumo", "0")).strip()

    # Item
    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(ITEM_VALUE, interval=0.05)
    pyautogui.press("tab")
    time.sleep(0.5)

    # CFOP
    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(CFOP_VALUE, interval=0.05)
    pyautogui.press("tab")
    time.sleep(0.5)

    # Valor (credito_resumo)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(credito_resumo, interval=0.05)
    pyautogui.press("tab")
    time.sleep(0.5)
