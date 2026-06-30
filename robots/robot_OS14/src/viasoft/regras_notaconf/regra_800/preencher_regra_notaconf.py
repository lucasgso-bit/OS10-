import time

import pyautogui

from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def preencher_regra_notaconf(pedido: dict) -> None:
    regra_notaconf = str(pedido["regra_notaconf"])

    time.sleep(6)

    focar_janela_por_titulo("Nota Fiscal", timeout=30)

    print("Vou pressionar ctrl + ins")

    pyautogui.keyDown("ctrl")
    time.sleep(0.2)
    pyautogui.press("insert")
    time.sleep(0.2)
    pyautogui.keyUp("ctrl")

    print("Pressionei ctrl + ins")
    time.sleep(3)

    focar_janela_por_titulo("Nota Fiscal", timeout=30)

    print(f"Colocando a regra_notaconf: {regra_notaconf}")
    time.sleep(0.5)

    pyautogui.write(regra_notaconf, interval=0.03)
    time.sleep(0.5)

    pyautogui.press("enter")
