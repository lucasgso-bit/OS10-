import time

import pyautogui

from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def abrir_fluxo_nota_acerto() -> None:
    print("Aguardando tela principal do AGRO...")

    time.sleep(2)

    focar_janela_por_titulo(
        "AGRO-AG",
        timeout=60,
    )

    time.sleep(1)

    pyautogui.hotkey("alt", "n")
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(0.5)

    pyautogui.hotkey("alt", "v")
    time.sleep(0.5)


def executar_fluxo_inicial_agro() -> None:
    abrir_fluxo_nota_acerto()
