"""Handle Agro alert windows for the OS11 robot.

Detect warning dialogs and confirm them automatically.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import time

import pyautogui
import win32gui

from robots.robot_OS11.src.window_utils import (
    aguardar_janela_sumir,
    focar_hwnd,
    normalizar_texto,
)


def aviso_eh_final(hwnd_alerta: int, titulo_alerta: str, classe_alerta: str) -> bool:
    titulo_normalizado = normalizar_texto(titulo_alerta)
    classe_normalizada = str(classe_alerta or "").strip()
    if titulo_normalizado == "aviso" and classe_normalizada == "#32770":
        print("Aviso final identificado por título e classe.")
        print("Título:", titulo_alerta)
        print("Classe:", classe_alerta)
        print("HWND:", hwnd_alerta)
        return True
    return False


def aguardar_alerta_32770(timeout: float = 2.0) -> tuple[int | None, str, str]:
    inicio = time.time()
    while time.time() - inicio < timeout:
        hwnd_encontrado = None
        titulo_encontrado = ""
        classe_encontrada = ""

        def procurar(hwnd: int, _: None) -> None:
            nonlocal hwnd_encontrado, titulo_encontrado, classe_encontrada
            if hwnd_encontrado:
                return
            if not win32gui.IsWindowVisible(hwnd):
                return
            titulo = win32gui.GetWindowText(hwnd).strip()
            classe = win32gui.GetClassName(hwnd).strip()
            titulo_normalizado = normalizar_texto(titulo)
            titulo_eh_alerta = titulo_normalizado in ("atencao", "aviso", "erro")
            classe_eh_alerta = classe in ("#32770", "TMessageForm")
            if titulo_eh_alerta and classe_eh_alerta:
                hwnd_encontrado = hwnd
                titulo_encontrado = titulo
                classe_encontrada = classe

        win32gui.EnumWindows(procurar, None)

        if hwnd_encontrado:
            return hwnd_encontrado, titulo_encontrado, classe_encontrada

        time.sleep(0.1)

    return None, "", ""


def confirmar_alerta_somente_enter(hwnd_alerta: int) -> bool:
    if not hwnd_alerta:
        return False
    titulo = win32gui.GetWindowText(hwnd_alerta).strip()
    classe = win32gui.GetClassName(hwnd_alerta).strip()
    print("Confirmando alerta com ENTER:", titulo, "| Classe:", classe)
    focar_hwnd(hwnd_alerta)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.6)
    return aguardar_janela_sumir(hwnd_alerta, timeout=2)


def confirmar_alerta_enter_ou_alt_o(hwnd_alerta: int) -> bool:
    if not hwnd_alerta:
        return False
    titulo = win32gui.GetWindowText(hwnd_alerta).strip()
    classe = win32gui.GetClassName(hwnd_alerta).strip()
    print("Confirmando alerta:", titulo, "| Classe:", classe)
    focar_hwnd(hwnd_alerta)
    time.sleep(0.15)
    for acao in ["enter", "alt_o", "enter", "alt_o"]:
        if acao == "enter":
            print("Tentando confirmar com ENTER...")
            pyautogui.press("enter")
        else:
            print("Tentando confirmar com ALT + O...")
            pyautogui.hotkey("alt", "o")
        time.sleep(0.45)
        if aguardar_janela_sumir(hwnd_alerta, timeout=1.2):
            return True
        focar_hwnd(hwnd_alerta)
        time.sleep(0.15)
    return False


def confirmar_todas_atencoes(timeout_primeira: float = 1.5, max_tentativas: int = 3) -> bool:
    encontrou = False
    for tentativa in range(max_tentativas):
        timeout = timeout_primeira if tentativa == 0 else 0.5
        hwnd_alerta, _, _ = aguardar_alerta_32770(timeout=timeout)
        if not hwnd_alerta:
            break
        confirmar_alerta_enter_ou_alt_o(hwnd_alerta)
        encontrou = True
        time.sleep(0.2)
    return encontrou
