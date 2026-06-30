import time

import pygetwindow as gw
import pyautogui


def tratar_tela_atencao(timeout: int = 3) -> bool:
    """Dismiss an 'Atenção' popup if it appears within the timeout. Returns True if found."""
    inicio = time.time()

    while time.time() - inicio < timeout:
        janelas = [j for j in gw.getAllTitles() if "atenção" in j.lower() or "atencao" in j.lower()]

        if janelas:
            janela = gw.getWindowsWithTitle(janelas[0])[0]
            janela.activate()
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(0.5)
            return True

        time.sleep(0.3)

    return False
