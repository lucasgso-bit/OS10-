"""Window and control utilities for the OS11 robot.

Focus windows, interact with controls, and normalize text for comparisons.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import time
import unicodedata

import pyautogui
import pygetwindow as gw
import win32com.client
import win32con
import win32gui


def normalizar_texto(texto: str) -> str:
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(char for char in texto if unicodedata.category(char) != "Mn")


def focar_janela_por_titulo(titulo: str, timeout: int = 30) -> None:
    for _ in range(timeout):
        janelas = gw.getWindowsWithTitle(titulo)
        if janelas:
            print(f"Focando na tela {titulo}")
            janela = janelas[-1]
            if janela.isMinimized:
                janela.restore()
            janela.activate()
            time.sleep(1)
            return
        time.sleep(1)
    raise RuntimeError(f"Janela não encontrada: {titulo}")


def janela_esta_visivel(hwnd: int) -> bool:
    return bool(hwnd and win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd))


def aguardar_janela_sumir(hwnd: int, timeout: float = 1.5) -> bool:
    inicio = time.time()
    while time.time() - inicio < timeout:
        if not janela_esta_visivel(hwnd):
            return True
        time.sleep(0.1)
    return False


def focar_hwnd(hwnd: int) -> bool:
    if not hwnd:
        return False
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys("%")
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)
        return True
    except Exception:
        return False


def obter_titulo_janela_ativa() -> tuple[str, str]:
    hwnd = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(hwnd), win32gui.GetClassName(hwnd)


def listar_controles_filhos(hwnd_pai: int) -> list[int]:
    controles: list[int] = []

    def procurar(hwnd: int, _: None) -> None:
        controles.append(hwnd)

    win32gui.EnumChildWindows(hwnd_pai, procurar, None)
    return controles


def obter_texto_janela(hwnd: int) -> str:
    textos: list[str] = []
    try:
        texto_pai = win32gui.GetWindowText(hwnd).strip()
        if texto_pai:
            textos.append(texto_pai)

        def procurar_filho(hwnd_filho: int, _: None) -> None:
            texto = win32gui.GetWindowText(hwnd_filho).strip()
            if texto:
                textos.append(texto)

        win32gui.EnumChildWindows(hwnd, procurar_filho, None)
    except Exception:
        pass
    textos_limpos: list[str] = []
    for texto in textos:
        if texto not in textos_limpos:
            textos_limpos.append(texto)
    return " | ".join(textos_limpos)


def encontrar_controle_por_classe_instancia(
    hwnd_pai: int,
    classe_controle: str,
    instancia: int,
) -> int | None:
    controles = listar_controles_filhos(hwnd_pai)
    encontrados = [hwnd for hwnd in controles if win32gui.GetClassName(hwnd) == classe_controle]
    if len(encontrados) < instancia:
        return None
    return encontrados[instancia - 1]


def clicar_controle(hwnd_controle: int) -> bool:
    if not hwnd_controle:
        return False
    left, top, right, bottom = win32gui.GetWindowRect(hwnd_controle)
    x = left + ((right - left) // 2)
    y = top + ((bottom - top) // 2)
    pyautogui.click(x, y)
    return True


def setar_texto_controle(hwnd_controle: int, texto: str) -> bool:
    if not hwnd_controle:
        return False
    win32gui.SendMessage(hwnd_controle, win32con.WM_SETTEXT, 0, str(texto))
    return True
