"""Shared utilities for all nota_XXX RPA scripts.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-02
Version: 1.0.0
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import pyautogui
import pygetwindow as gw

from config import AGRO_EXE
from src.agro_alerts import confirm_attention_popup, confirm_establishment_selection
from src.agro_app import kill_agro_process, start_agro
from src.agro_login import login_agro
from src.notifier import notify_error
from src.replacement_estab import wait_window_startswith

ESTABS_COM_CHAVE_NFE = {"26", "68", "71"}


# =========================
# JANELAS
# =========================


def print_open_windows() -> None:
    """Lista todas as janelas abertas (debug)."""
    print("\n===== JANELAS ABERTAS =====")
    for window in gw.getAllWindows():
        title = window.title.strip()
        if title:
            print(title)
    print("===== FIM =====\n")


def focus_window(title_start: str) -> bool:
    """Foca em uma janela pelo início do título."""
    for window in gw.getAllWindows():
        if window.title.strip().startswith(title_start):
            window.activate()
            time.sleep(1)
            return True
    return False


def focus_window_contains(title_part: str, timeout_seconds: int = 7) -> bool:
    """Foca em uma janela que contenha o texto informado no título."""
    title_part_lower = title_part.lower()

    for _ in range(timeout_seconds):
        for window in gw.getAllWindows():
            title = window.title.strip()
            if title_part_lower in title.lower():
                window.activate()
                time.sleep(1)
                return True

        time.sleep(1)

    print(f"Janela contendo '{title_part}' não encontrada.")
    print_open_windows()
    return False


def focus_window_startswith(title_start: str, timeout_seconds: int = 7) -> bool:
    """Foca em uma janela cujo título inicia com o texto informado."""
    for _ in range(timeout_seconds):
        if focus_window(title_start):
            return True

        time.sleep(1)

    print(f"Janela iniciando com '{title_start}' não encontrada.")
    print_open_windows()
    return False


def click_in_window(title_start: str, rel_x: int, rel_y: int) -> bool:
    """Click at coordinates relative to a window's top-left corner."""
    for window in gw.getAllWindows():
        if window.title.strip().startswith(title_start):
            pyautogui.click(window.left + rel_x, window.top + rel_y)
            return True
    return False


def double_click_in_window(title_start: str, rel_x: int, rel_y: int) -> bool:
    """Double-click at coordinates relative to a window's top-left corner."""
    for window in gw.getAllWindows():
        if window.title.strip().startswith(title_start):
            pyautogui.doubleClick(window.left + rel_x, window.top + rel_y)
            return True
    return False


def grid_has_data(title_start: str, rel_x: int, rel_y: int) -> bool:
    """Return True if the grid row area has content (pixel is not white/near-white)."""
    for window in gw.getAllWindows():
        if window.title.strip().startswith(title_start):
            r, g, b = pyautogui.pixel(window.left + rel_x, window.top + rel_y)
            return not (r > 245 and g > 245 and b > 245)
    return False


def close_current_windows(times: int = 3, delay_seconds: float = 2.0) -> None:
    """Fecha janelas atuais do Agro usando Ctrl+F4 repetidamente."""
    for _ in range(times):
        pyautogui.hotkey("ctrl", "f4")
        time.sleep(delay_seconds)


# =========================
# NOTA / CAMPOS
# =========================


def get_required_note_value(nota: dict[str, Any], key: str) -> str:
    """Return a required note field as stripped text."""
    value = nota.get(key)

    if value is None or str(value).strip() == "":
        raise ValueError(f"Campo obrigatorio ausente na nota: {key}")

    return str(value).strip()


def get_estab(nota: dict[str, Any]) -> str:
    """Retorna o código do estabelecimento a partir dos campos conhecidos da nota."""
    for key in ("ESTAB", "ESTABELECIMENTO", "CODESTAB", "COD_ESTAB", "CD_ESTAB"):
        value = nota.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    return ""
                                                    

def format_dtemissao_ddmmyy(nota: dict[str, Any]) -> str:
    """Format DTEMISSAO from ddmmyyyy to ddmmyy."""
    dtemissao = get_required_note_value(nota, "DTEMISSAO")

    try:
        data = datetime.strptime(dtemissao, "%d%m%Y")
    except ValueError as exc:
        raise ValueError(f"Formato invalido de DTEMISSAO: {dtemissao}") from exc

    return data.strftime("%d%m%y")


def fill_inscricao_pessoa(
    inscricao: str,
    executar_alt_t: bool = True,
) -> None:
    """Preenche a inscrição na tela de seleção de endereço."""
    time.sleep(4)
    pyautogui.press("right", presses=2, interval=0.2)
    time.sleep(0.2)

    pyautogui.press("up")
    time.sleep(0.2)

    pyautogui.write(inscricao, interval=0.03)
    print(f"Inscricao '{inscricao}' selecionada.")

    time.sleep(2)
    pyautogui.press("enter")
    time.sleep(2)

    if executar_alt_t:
        pyautogui.hotkey("alt", "t")


# =========================
# AGRO / ERROS
# =========================


def restart_agro() -> None:
    """Kill Agro, restart and log back in so the next note can run."""
    print("Reiniciando Agro...")
    kill_agro_process("Agro3C.exe")
    start_agro(AGRO_EXE)
    time.sleep(5)
    login_agro()
    confirm_attention_popup()
    confirm_establishment_selection()
    if wait_window_startswith("AGRO-AG", timeout_seconds=15):
        print("Agro pronto após reinício.")
    else:
        print("AVISO: tela AGRO-AG não abriu após reinício.")


def handle_error(nota: dict[str, Any], motivo: str) -> bool:
    """Notify error via screenshot+email, restart Agro, return False."""
    print(f"ERRO: {motivo}")
    notify_error(nota, motivo)
    restart_agro()
    return False


# =========================
# ADVERTÊNCIAS
# =========================


def advertencias_tem_erro_critico() -> bool:
    """Return True if Advertências has a red error row (pixel scan on first list item)."""
    for window in gw.getAllWindows():
        if window.title.strip().startswith(
            "[A]dvertencias"
        ) or window.title.strip().startswith("[A]dvertências"):
            for y_off in range(35, 65):
                r, g, b = pyautogui.pixel(window.left + 50, window.top + y_off)
                if r > 150 and g < 80 and b < 80:
                    return True
    return False


def verificar_advertencia_apos_ordemcarga(nota: dict[str, Any]) -> bool:
    """Verifica linha vermelha em Advertências logo após salvar ORDEMCARGA.

    Retorna False e reinicia o Agro se uma linha vermelha crítica for detectada.
    Retorna True caso contrário (sem janela de advertência ou sem erro crítico).
    """
    print("Verificando advertências após ORDEMCARGA...")
    deadline = time.time() + 2
    while time.time() < deadline:
        for window in gw.getAllWindows():
            t = window.title.strip()
            if t.startswith("[A]dvertencias") or t.startswith("[A]dvertências"):
                time.sleep(1)
                try:
                    window.activate()
                except Exception:
                    pass
                if advertencias_tem_erro_critico():
                    print("ERRO: linha vermelha detectada após ORDEMCARGA.")
                    return handle_error(
                        nota, "Advertência com erro crítico após ORDEMCARGA"
                    )
                return True
        time.sleep(0.5)
    return True
