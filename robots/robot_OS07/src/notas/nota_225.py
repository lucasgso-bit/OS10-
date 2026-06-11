"""
Process NOTACONF 225 notes.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-11
Version: 1.2.0
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import pyautogui
import pygetwindow as gw

from robots.robot_OS07.src.notifier import notify_error
from robots.robot_OS07.src.replacement_estab import wait_window_startswith
from robots.robot_OS07.src.notas.nota_utils import (
    advertencias_tem_erro_critico,
    click_in_window,
    double_click_in_window,
    focus_window,
    grid_has_data,
    handle_error,
    print_open_windows,
    restart_agro,
    verificar_advertencia_apos_ordemcarga,
)

# =========================
# UTILS LOCAIS
# =========================


def _get_window_by_title_start(title: str) -> gw.Win32Window | None:
    """Return the first visible window whose title starts with the provided text."""
    title_normalized = title.strip().lower()

    for window in gw.getAllWindows():
        window_title = (window.title or "").strip().lower()

        if window_title.startswith(title_normalized):
            return window

    return None


def _handle_conceito_popup(timeout_seconds: float = 0.0) -> bool:
    """Dismiss the transient 'Conceito' dialog when it appears."""
    handled = False
    deadline = time.time() + max(timeout_seconds, 0.0)
    attempts = 0
    max_attempts = 4

    while True:
        conceito_window = _get_window_by_title_start("Conceito")

        if conceito_window is not None:
            attempts += 1

            try:
                conceito_window.activate()
            except Exception as exc:
                print(f"AVISO: Não foi possível focar popup 'Conceito': {exc}")

            time.sleep(0.2)
            pyautogui.press("enter")
            time.sleep(0.4)

            handled = True
            print("Popup 'Conceito' detectado e confirmado com OK.")

            if attempts >= max_attempts:
                return handled

            continue

        if time.time() >= deadline:
            return handled

        time.sleep(0.2)


def _sleep_and_handle(seconds: float, check_interval: float = 0.25) -> None:
    """Wait while continuously dismissing the transient 'Conceito' dialog."""
    _handle_conceito_popup()

    deadline = time.time() + max(seconds, 0.0)

    while time.time() < deadline:
        time.sleep(min(check_interval, max(deadline - time.time(), 0.0)))
        _handle_conceito_popup()

    _handle_conceito_popup()


def _wait_window_startswith(title: str, timeout_seconds: int = 5) -> bool:
    """Wait for a window while keeping the 'Conceito' dialog dismissed."""
    deadline = time.time() + max(timeout_seconds, 0)

    while time.time() <= deadline:
        _handle_conceito_popup()

        if wait_window_startswith(title, timeout_seconds=1):
            _handle_conceito_popup()
            return True

        _handle_conceito_popup()

    return False


def _press(*args: Any, **kwargs: Any) -> None:
    """Press keys while guarding against the transient 'Conceito' dialog."""
    _handle_conceito_popup()
    pyautogui.press(*args, **kwargs)
    _handle_conceito_popup()


def _hotkey(*args: Any, **kwargs: Any) -> None:
    """Send a hotkey while guarding against the transient 'Conceito' dialog."""
    _handle_conceito_popup()
    pyautogui.hotkey(*args, **kwargs)
    _handle_conceito_popup()


def _write(*args: Any, **kwargs: Any) -> None:
    """Write text while guarding against the transient 'Conceito' dialog."""
    _handle_conceito_popup()
    pyautogui.write(*args, **kwargs)
    _handle_conceito_popup()


def _click(*args: Any, **kwargs: Any) -> None:
    """Click while guarding against the transient 'Conceito' dialog."""
    _handle_conceito_popup()
    pyautogui.click(*args, **kwargs)
    _handle_conceito_popup()


def _click_in_window_and_handle(title: str, x: int, y: int) -> None:
    """Click inside a window and dismiss 'Conceito' before and after the action."""
    _handle_conceito_popup()
    click_in_window(title, x, y)
    _handle_conceito_popup()


def _double_click_in_window_and_handle(title: str, x: int, y: int) -> None:
    """Double-click inside a window and dismiss 'Conceito' before and after the action."""
    _handle_conceito_popup()
    double_click_in_window(title, x, y)
    _handle_conceito_popup()


# =========================
# PROCESSO PRINCIPAL
# =========================


def process_notaconf_225(nota: dict[str, Any]) -> bool:
    """Fluxo principal NOTACONF 225."""
    print("Processando NOTACONF 225...")

    if not focus_window("AGRO-AG"):
        print("Janela principal do Agro não encontrada.")
        print_open_windows()
        return handle_error(nota, "Janela principal do Agro não encontrada")

    _hotkey("alt", "n")
    _sleep_and_handle(1)

    _press("enter")
    _sleep_and_handle(1)

    # Tela filtro
    if not (
        _wait_window_startswith("Filtrar NF - Cabeçalho", 5)
        or _wait_window_startswith("Filtrar NF", 5)
        or _wait_window_startswith("Filtrar", 5)
    ):
        print("Tela de filtro não encontrada.")
        return handle_error(nota, "Tela de filtro não encontrada")

    _hotkey("alt", "v")
    _sleep_and_handle(1)

    # Tela Nota
    if not (
        _wait_window_startswith("Nota Fiscal", 10) or _wait_window_startswith("Nota", 5)
    ):
        print("Tela 'Nota Fiscal' não carregou.")
        return handle_error(nota, "Tela 'Nota Fiscal' não carregou")

    _hotkey("ctrl", "insert")
    _sleep_and_handle(8)

    _write("225", interval=0.03)
    _press("enter")
    _sleep_and_handle(3)

    if _wait_window_startswith("Dados da NF-e Recebida", 10):
        return process_dados_nfe_recebida(nota)

    print("Tela 'Dados da NF-e Recebida' não apareceu.")
    return True


# =========================
# PROCESSO NF-e
# =========================


def process_dados_nfe_recebida(nota: dict[str, Any]) -> bool:
    """Processa tela de NF-e recebida."""
    chave_acesso = str(nota.get("CHAVEACESSO") or "").strip()

    if not chave_acesso:
        print("CHAVEACESSO não encontrada.")
        return handle_error(nota, "CHAVEACESSO não encontrada")

    if not focus_window("Dados da NF-e Recebida"):
        print("Erro ao focar janela NF-e.")
        return handle_error(nota, "Janela 'Dados da NF-e Recebida' não encontrada")

    # Preenche chave
    _write(chave_acesso, interval=0.03)
    _sleep_and_handle(1)

    _press("tab")
    _sleep_and_handle(1)

    # Clica em "Carregar na NF"
    _click_in_window_and_handle("Dados da NF-e Recebida", 412, 48)
    _sleep_and_handle(2)

    if grid_has_data("Dados da NF-e Recebida", 258, 157):
        print("Grid com endereços detectado. Selecionando primeira linha...")
        _double_click_in_window_and_handle("Dados da NF-e Recebida", 258, 157)
        _sleep_and_handle(1)
        _press("tab", presses=3, interval=0.1)
    else:
        _sleep_and_handle(1)
        _press("tab", presses=2, interval=0.1)

    _sleep_and_handle(1)

    _press("enter")
    _sleep_and_handle(1)

    _hotkey("alt", "n")
    _sleep_and_handle(1)

    # =========================
    # ENDEREÇO (OPCIONAL)
    # =========================
    if _wait_window_startswith("Seleção de Endereço", 10):
        print("Tela de endereço encontrada.")

        inscricao = str(nota.get("IEEMITENTE") or "").strip()

        if inscricao:
            _press("right", presses=2)
            _press("up")
            _write(inscricao, interval=0.03)
            _press("enter")

            print(f"Inscrição '{inscricao}' selecionada.")
        else:
            print("IEEMITENTE não encontrada, pulando.")
    else:
        print("Tela de endereço não apareceu, seguindo fluxo...")

    # =========================
    # DATA EMISSÃO
    # =========================
    dtemissao = str(nota.get("DTEMISSAO") or "").strip()

    if not dtemissao:
        print("DTEMISSAO não encontrada.")
        return handle_error(nota, "DTEMISSAO não encontrada na nota")

    try:
        data = datetime.strptime(dtemissao, "%d%m%Y")
        ddmmyy = data.strftime("%d%m%y")
    except ValueError:
        print(f"Formato inválido: {dtemissao}")
        return handle_error(nota, f"Formato inválido de DTEMISSAO: {dtemissao}")

    _sleep_and_handle(2)

    _hotkey("alt", "o")
    _sleep_and_handle(1)
    _hotkey("alt", "o")
    _sleep_and_handle(1)
    _hotkey("alt", "p")
    _sleep_and_handle(1)

    _press("enter")
    _write(ddmmyy, interval=0.03)
    _sleep_and_handle(2)
    _press("enter")

    print(f"Data '{ddmmyy}' preenchida.")

    # =========================
    # NOTA FILHA
    # =========================
    if not process_nota_filha(nota):
        print("Falha na etapa de nota filha.")
        return False

    print("Processo finalizado com sucesso.")
    return True


# =========================
# PROCESSO NOTA FILHA
# =========================


def process_nota_filha(nota: dict[str, Any]) -> bool:
    """Processa nota filha + quantidade + classificação + placa + ordem + financeiro."""

    notafilha = str(nota.get("NOTAFILHA") or "").strip()
    quantidade = str(nota.get("QUANTIDADE") or "").strip()
    classif_local = str(nota.get("CLASSIF_LOCAL") or "").strip()
    ordem_carga = str(nota.get("ORDEMCARGA") or "").strip()

    if not notafilha:
        print("NOTAFILHA não encontrada.")
        return handle_error(nota, "NOTAFILHA não encontrada na nota")

    if not focus_window("Nota Fiscal"):
        print("Tela 'Nota Fiscal' não encontrada.")
        return handle_error(nota, "Tela 'Nota Fiscal' não encontrada")

    print(f"Tela encontrada. NOTAFILHA: {notafilha}")

    _sleep_and_handle(1)

    # =========================
    # ABRE TELA "A PARTIR DE NF"
    # =========================
    _double_click_in_window_and_handle("Nota Fiscal", 697, 120)
    _sleep_and_handle(2)

    # =========================
    # NOTA FILHA: Tab×13 → escreve → Enter → Ctrl+P
    # =========================
    for _ in range(13):
        _press("tab")
        _sleep_and_handle(0.1)

    _write(notafilha, interval=0.03)
    _press("enter")
    _sleep_and_handle(1)

    agro_count_before = sum(1 for w in gw.getAllWindows() if w.title.strip() == "Agro")

    _hotkey("ctrl", "p")

    popup_detectado = False
    for _ in range(3):
        _sleep_and_handle(1)
        if (
            sum(1 for w in gw.getAllWindows() if w.title.strip() == "Agro")
            > agro_count_before
        ):
            popup_detectado = True
            break

    if popup_detectado:
        print("Popup 'Agro' detectado — Nenhuma linha encontrada na grid sgNota.")
        focus_window("Agro")
        _sleep_and_handle(0.5)
        _click_in_window_and_handle("Agro", 130, 61)
        _sleep_and_handle(1)
        return handle_error(
            nota, "Nenhuma linha encontrada na grid sgNota — NOTAFILHA não encontrada"
        )

    print(f"NOTAFILHA '{notafilha}' preenchida.")

    # =========================
    # QUANTIDADE: Tab×20 → Enter×2 → quantidade → Enter → Ctrl+S
    # =========================
    if quantidade:
        _sleep_and_handle(2)

        for _ in range(19):
            _press("tab")
            _sleep_and_handle(0.1)

        _press("enter")
        _press("enter")

        _write(quantidade, interval=0.03)
        _press("enter")

        _hotkey("ctrl", "s")
        _sleep_and_handle(1)

        print(f"Quantidade '{quantidade}' inserida e salva.")
    else:
        print("QUANTIDADE não informada.")

    # =========================
    #  TRATA POPUP ATENÇÃO (erro de quantidade)
    # =========================
    print("Verificando popup 'Atenção'...")

    if _wait_window_startswith("Atenção", timeout_seconds=3):
        print("Popup 'Atenção' detectado — Quantidade a fixar maior que o saldo.")
        _press("enter")
        _sleep_and_handle(1)
        return handle_error(nota, "Quantidade a fixar maior que o saldo")

    print("Popup 'Atenção' não apareceu.")

    # =========================
    # CLASSIFICAÇÃO
    # =========================
    _hotkey("alt", "o")
    _sleep_and_handle(1)

    _press("right")
    _press("down")

    if classif_local:
        _write(classif_local, interval=0.03)
        _press("enter")
        print(f"CLASSIF_LOCAL '{classif_local}' preenchido.")

    # =========================
    # PLACA (Tab×7 para posicionar)
    # =========================
    for _ in range(7):
        _press("tab")
        _sleep_and_handle(0.1)

    # =========================
    # ORDEM DE CARGA
    # =========================
    if ordem_carga:
        _sleep_and_handle(1)
        _write(ordem_carga, interval=0.03)
        _press("enter")

        _hotkey("ctrl", "s")
        _sleep_and_handle(1)

        print(f"ORDEMCARGA '{ordem_carga}' preenchida.")

        if not verificar_advertencia_apos_ordemcarga(nota):
            return False

    # =========================
    #  FINANCEIRO
    # =========================
    print("Verificando tela financeiro...")

    if _wait_window_startswith("Pagamento com Duplicatas", timeout_seconds=5):
        print("Tela financeira encontrada.")

        _hotkey("ctrl", "p")
        _sleep_and_handle(1)

        _hotkey("ctrl", "s")
        _sleep_and_handle(1)

    else:
        print("Tela financeira não apareceu.")

    # =========================
    #  VOLTA NOTA FISCAL
    # =========================
    print("Verificando retorno para Nota Fiscal...")

    if _wait_window_startswith("[A]dvertências", timeout_seconds=10):
        print("Tela Advertências/Nota Fiscal encontrada.")
        _sleep_and_handle(3)
        focus_window("[A]dvertências")

        if advertencias_tem_erro_critico():
            print("Advertências com erro crítico — linha vermelha detectada.")
            notify_error(nota, "Advertência com erro crítico na nota fiscal")
            _press("escape")
            _sleep_and_handle(1)
            restart_agro()
            return False

        _hotkey("alt", "o")
        _sleep_and_handle(1)

        _press("enter")
        _sleep_and_handle(1)
        _press("enter")
        _sleep_and_handle(1)
        _press("enter")
        _sleep_and_handle(1)

    else:
        print("Tela Advertências/Nota Fiscal não apareceu.")
        print_open_windows()

    _sleep_and_handle(5)
    # =========================
    # FECHAR TELAS
    # =========================
    _hotkey("ctrl", "f4")
    _sleep_and_handle(1)

    print("Nota filha processada com sucesso.")
    return True
