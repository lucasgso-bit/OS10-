import subprocess
import time

import pyautogui

from config import AGRO_EXE, AGRO_SENHA, AGRO_USUARIO
from robots.robot_OS14.src.viasoft.erros.janela_atencao import tratar_tela_atencao
from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def matar_agro3c() -> None:
    subprocess.run(
        ["taskkill", "/F", "/IM", "agro3c.exe"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def abrir_agro3c() -> None:
    subprocess.Popen(AGRO_EXE)
    time.sleep(2)


def preencher_login() -> None:
    focar_janela_por_titulo(
        "Seleção de Usuário",
        timeout=30,
    )

    time.sleep(0.5)

    for _ in range(5):
        pyautogui.press("tab")
        time.sleep(0.2)

    time.sleep(0.5)

    pyautogui.write(str(AGRO_USUARIO), interval=0.03)
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(0.8)

    print("Preenchendo senha.")
    pyautogui.write(str(AGRO_SENHA), interval=0.03)
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(1)

    tratar_tela_atencao()


def confirmar_estabelecimento_inicial() -> None:
    print("Aguardando seleção de estabelecimento...")

    focar_janela_por_titulo(
        "Seleção de Estabelecimento para Trabalho",
        timeout=30,
    )

    pyautogui.press("enter")
    time.sleep(3)


def login_viasoft() -> None:
    matar_agro3c()
    time.sleep(1)

    abrir_agro3c()
    time.sleep(5)
    preencher_login()
    confirmar_estabelecimento_inicial()
