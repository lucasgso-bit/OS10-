import time

import pyautogui

from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def preencher_regra_notaconf(pedido: dict) -> None:
    regra_notaconf = str(pedido["regra_notaconf"])

    time.sleep(6)

    focar_janela_por_titulo("Nota Fiscal", timeout=30)

    print("Pressionando CTRL + INS")

    pyautogui.keyDown("ctrl")
    time.sleep(0.2)
    pyautogui.press("insert")
    time.sleep(0.2)
    pyautogui.keyUp("ctrl")

    time.sleep(3)

    focar_janela_por_titulo("Nota Fiscal", timeout=30)

    print("Digitando a notaconf")
    time.sleep(0.5)

    pyautogui.write(regra_notaconf, interval=0.03)
    time.sleep(0.5)

    pyautogui.press("enter")

    print(f"Escrevi a regra_notaconf: {regra_notaconf}")
