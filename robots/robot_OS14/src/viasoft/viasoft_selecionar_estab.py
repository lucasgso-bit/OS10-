import time

import pyautogui

from robots.robot_OS14.src.viasoft.erros.janela_atencao import tratar_tela_atencao
from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def alterar_estabelecimento_trabalho(estab: str) -> None:
    estab = str(estab)

    tratar_tela_atencao()

    focar_janela_por_titulo("AGRO-AG", timeout=60)

    pyautogui.hotkey("shift", "f12")
    time.sleep(2)

    focar_janela_por_titulo(
        "Seleção de Estabelecimento para Trabalho",
        timeout=30,
    )

    pyautogui.hotkey("ctrl", "tab")
    time.sleep(1)

    pyautogui.write(estab, interval=0.03)
    time.sleep(1)

    focar_janela_por_titulo(
        "Seleção de Estabelecimento para Trabalho",
        timeout=30,
    )

    pyautogui.press("enter")
    time.sleep(1)

    pyautogui.press("enter")
    time.sleep(1)
