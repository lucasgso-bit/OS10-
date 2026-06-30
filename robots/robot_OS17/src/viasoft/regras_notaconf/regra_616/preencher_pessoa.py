import time

import pyautogui
import pygetwindow as gw

from robots.robot_OS17.src.viasoft.erros.janela_atencao import tratar_tela_atencao


VIASOFT_WINDOW_TITLE = "AGRO-AG"
CONCEITO_POPUP_TITLE = "Conceito"


def focar_janela_viasoft() -> None:
    janelas = [j for j in gw.getAllTitles() if j.startswith(VIASOFT_WINDOW_TITLE)]
    if janelas:
        gw.getWindowsWithTitle(janelas[0])[0].activate()
        time.sleep(0.5)


def preencher_pessoa(pedido: dict) -> None:
    """Fill the NumeroCM (pessoa) field, handle address selection and Conceito popup."""
    focar_janela_viasoft()
    time.sleep(0.5)

    numerocm = str(pedido.get("numerocm", "")).strip()

    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(numerocm, interval=0.05)
    pyautogui.press("enter")
    time.sleep(1)

    # Handle address selection if it appears
    tratar_tela_atencao(timeout=3)

    # Confirm address with Enter if needed
    pyautogui.press("enter")
    time.sleep(0.5)

    # Dismiss Conceito popup if it appears
    inicio = time.time()
    while time.time() - inicio < 5:
        janelas = [j for j in gw.getAllTitles() if CONCEITO_POPUP_TITLE in j]
        if janelas:
            gw.getWindowsWithTitle(janelas[0])[0].activate()
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(0.5)
            break
        time.sleep(0.3)
