"""
Process NOTACONF 285 notes.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-11
Version: 2.2.0
"""

from __future__ import annotations

import time
from typing import Any

import pyautogui
import pygetwindow as gw

from robots.robot_OS07.src.notifier import notify_error
from robots.robot_OS07.src.replacement_estab import wait_window_startswith
from robots.robot_OS07.src.notas.nota_utils import (
    ESTABS_COM_CHAVE_NFE,
    advertencias_tem_erro_critico,
    click_in_window,
    close_current_windows,
    double_click_in_window,
    fill_inscricao_pessoa,
    focus_window,
    focus_window_contains,
    focus_window_startswith,
    format_dtemissao_ddmmyy,
    get_estab,
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


def process_notaconf_285(nota: dict[str, Any]) -> bool:
    """Fluxo principal NOTACONF 285."""
    print("Processando NOTACONF 285...")

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

    _write("285", interval=0.03)
    _press("enter")
    _sleep_and_handle(3)

    return process_dados_nfe_recebida(nota)


# =========================
# PROCESSO NF-e
# =========================


def process_dados_nfe_recebida(nota: dict[str, Any]) -> bool:
    """Processa tela de NF-e recebida."""
    numerocm = str(nota.get("NUMEROCM") or "").strip()
    inscricao = str(nota.get("IEEMITENTE") or "").strip()
    ddmmyy = format_dtemissao_ddmmyy(nota)

    if not numerocm:
        return handle_error(nota, "NUMEROCM não encontrado na nota")

    print("Inserindo NUMEROCM...")
    _write(numerocm, interval=0.03)
    print(f"NUMEROCM '{numerocm}' preenchido.")
    _sleep_and_handle(1)
    _press("enter")
    _sleep_and_handle(1)

    # =========================
    # ENDEREÇO (OPCIONAL)
    # =========================
    if _wait_window_startswith("Seleção de Endereço", 10):
        print("Tela de endereço encontrada.")

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

    _sleep_and_handle(2)

    # =========================
    # NOTA FILHA
    # =========================
    if not process_nota_filha(nota, ddmmyy):
        print("Falha na etapa de nota filha.")
        return False

    print("Processo finalizado com sucesso.")
    return True


# =========================
# PROCESSO NOTA FILHA
# =========================


def process_nota_filha(nota: dict[str, Any], ddmmyy: str) -> bool:
    """Processa nota filha + quantidade + classificação + placa + ordem + financeiro."""

    notafilha = str(nota.get("NOTAFILHA") or "").strip()
    quantidade = str(nota.get("QUANTIDADE") or "").strip()
    classif_local = str(nota.get("CLASSIF_LOCAL") or "").strip()
    ordem_carga = str(nota.get("ORDEMCARGA") or "").strip()
    chave_nf = str(nota.get("CHAVEACESSO") or "").strip()

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
        print("passei no erro!")
        return handle_error(
            nota, "Nenhuma linha encontrada na grid sgNota — NOTAFILHA não encontrada"
        )

    print(f"NOTAFILHA '{notafilha}' preenchida.")

    # =========================
    # QUANTIDADE: Tab×19 → Enter×2 → quantidade → Enter → Ctrl+S
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
    #  ABA PRODUTOR
    # =========================
    _hotkey("alt", "i")
    _sleep_and_handle(1)

    _hotkey("shift", "tab")
    _sleep_and_handle(0.3)

    _hotkey("shift", "tab")
    _sleep_and_handle(0.3)

    _press("right", presses=4, interval=0.1)
    _sleep_and_handle(0.5)

    _press("tab")
    _sleep_and_handle(0.5)

    _press("enter")
    _press("enter")
    _press("enter")
    _press("enter")
    _sleep_and_handle(0.5)

    _write(chave_nf, interval=0.03)
    _sleep_and_handle(0.5)

    _press("enter")
    _sleep_and_handle(0.5)

    _press("up")
    _sleep_and_handle(0.3)

    _press("right", presses=2, interval=0.1)
    _sleep_and_handle(0.5)

    _press("enter")
    _sleep_and_handle(0.5)

    _write(ddmmyy, interval=0.03)
    _sleep_and_handle(0.5)

    _press("enter")
    _sleep_and_handle(0.5)

    _press("enter")
    _sleep_and_handle(0.5)

    # =========================
    # CLASSIFICAÇÃO
    # =========================
    _hotkey("alt", "o")
    _sleep_and_handle(1)
    _hotkey("shift", "tab")

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
    #  VOLTA NOTA FISCAL / ADVERTÊNCIAS
    # =========================
    print("Verificando retorno para Nota Fiscal...")

    if not (
        _wait_window_startswith("[A]dvertencias", timeout_seconds=5)
        or _wait_window_startswith("[A]dvertências", timeout_seconds=5)
    ):
        print("Tela Advertências/Nota Fiscal não apareceu.")
        print_open_windows()
    else:
        print("Tela Advertências/Nota Fiscal encontrada.")
        _sleep_and_handle(3)
        if not (focus_window("[A]dvertencias") or focus_window("[A]dvertências")):
            print("Não foi possível focar Advertências.")

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

    _sleep_and_handle(5)

    # =========================
    #  IMPRESSÃO / TRANSMISSÃO
    # =========================
    if not _process_impressao_transmissao_285(nota):
        return False

    # =========================
    #  PÓS-TRANSMISSÃO POR ESTAB
    # =========================
    if not _process_chave_por_estab_285(nota, ddmmyy):
        return False

    return True


# =========================
# IMPRESSAO / TRANSMISSAO
# =========================


def _process_impressao_transmissao_285(nota: dict[str, Any]) -> bool:
    """Valida tela de impressão, trata mensagem da nota, transmite NF-e e fecha telas."""
    print("Verificando tela 'Impressao de Nota Fiscal Eletronica'...")

    if not (
        focus_window_contains("Impressao de Nota Fiscal Eletronica", timeout_seconds=5)
        or focus_window_contains(
            "Impressão de Nota Fiscal Eletrônica", timeout_seconds=5
        )
    ):
        return handle_error(
            nota,
            "Tela 'Impressao de Nota Fiscal Eletronica' nao apareceu",
        )

    _sleep_and_handle(0.3)

    print("Verificando tela 'Mensagem da Nota - Nota (0)' antes do Ctrl+E...")

    if focus_window_contains("Mensagem da Nota - Nota (0)", timeout_seconds=3):
        print("Tela 'Mensagem da Nota - Nota (0)' encontrada. Enviando Ctrl+S...")
        _hotkey("ctrl", "s")
        _sleep_and_handle(2)
    else:
        print("Tela 'Mensagem da Nota - Nota (0)' nao apareceu. Seguindo para Ctrl+E.")

    print("Tela de impressao encontrada. Enviando Ctrl+E para transmitir...")
    _sleep_and_handle(1)
    _hotkey("ctrl", "e")

    print("Verificando popup de transmissao 'Agro'...")
    if not focus_window_startswith("Agro", timeout_seconds=10):
        return handle_error(
            nota,
            "Popup 'Agro' de transmissao nao apareceu apos Ctrl+E",
        )

    print("Popup 'Agro' detectado. Confirmando transmissao...")
    _press("enter")
    _sleep_and_handle(10)

    _hotkey("alt", "o")
    _sleep_and_handle(1)

    # pyautogui.press("enter")
    _sleep_and_handle(1)

    print("Fechando telas apos transmissao...")
    close_current_windows(times=3, delay_seconds=2)

    return True


# =========================
# POS-TRANSMISSAO POR ESTAB
# =========================


def _process_chave_por_estab_285(nota: dict[str, Any], ddmmyy: str) -> bool:
    """Fluxo pós-transmissão de chave para estabelecimentos 26, 68 e 71."""
    estab = get_estab(nota)

    if estab not in ESTABS_COM_CHAVE_NFE:
        print(
            f"Estabelecimento '{estab or 'NAO INFORMADO'}' nao exige fluxo de chave. "
            "Fechando telas e seguindo para o proximo.",
        )
        close_current_windows(times=1, delay_seconds=1)
        return True

    print(f"Estabelecimento '{estab}' exige fluxo de chave pos-transmissao.")

    chave_nf = str(nota.get("CHAVEACESSO") or "").strip()
    inscricao = str(nota.get("IEEMITENTE") or "").strip()

    if not chave_nf:
        return handle_error(
            nota, "CHAVEACESSO nao encontrada para fluxo pos-transmissao"
        )

    print("Verificando tela 'Dados da NF-e Recebida' para inserir chave...")
    if not focus_window("Dados da NF-e Recebida"):
        return handle_error(
            nota,
            "Tela 'Dados da NF-e Recebida' nao apareceu para inserir chave",
        )

    print("Inserindo chave da NF-e...")
    _sleep_and_handle(1)
    _write(chave_nf, interval=0.03)
    _sleep_and_handle(1)
    _press("enter")
    _sleep_and_handle(1)
    _press("enter")
    _sleep_and_handle(1)
    _press("enter")
    _sleep_and_handle(1)
    _hotkey("alt", "n")
    _sleep_and_handle(1)

    print("Verificando tela de endereco apos inserir chave...")
    if _wait_window_startswith("Selecao de Endereco", 5) or _wait_window_startswith(
        "Seleção de Endereço", 5
    ):
        if inscricao:
            print("Tela de endereco encontrada. Inserindo IE.")
            fill_inscricao_pessoa(inscricao)
        else:
            print("IEEMITENTE nao informada. Seguindo para alteracao de data.")
    else:
        print("Tela de endereco nao apareceu. Seguindo direto para alteracao de data.")

    _alterar_data_nota_285(ddmmyy)

    if not _salvar_final_285():
        return False

    return True


def _alterar_data_nota_285(ddmmyy: str) -> bool:
    """Altera a data da NF pela mesma sequência de teclado usada no PowerShell."""
    print(f"Alterando data para '{ddmmyy}'...")

    _sleep_and_handle(2)
    _hotkey("alt", "o")
    _sleep_and_handle(1)
    _hotkey("alt", "o")
    _sleep_and_handle(1)
    _hotkey("alt", "p")
    _sleep_and_handle(1)
    _press("enter")
    _sleep_and_handle(1)
    _write(ddmmyy, interval=0.03)
    _sleep_and_handle(2)
    _press("enter")
    _sleep_and_handle(1)

    return True


def _salvar_final_285() -> bool:
    """Executa o salvamento final após ajustes de data/chave."""
    print("Executando salvamento final...")
    print("ctrl salvamento final...")
    _sleep_and_handle(5)
    _hotkey("ctrl", "s")
    _sleep_and_handle(3)
    print("ctrl o")
    _hotkey("alt", "o")
    _sleep_and_handle(1)
    print("enter")
    _sleep_and_handle(5)
    _press("enter")
    _sleep_and_handle(1)
    _press("enter")
    _sleep_and_handle(8)
    _hotkey("ctrl", "s")
    _sleep_and_handle(1)
    close_current_windows(times=3, delay_seconds=2)
    _sleep_and_handle(5)
    print("Salvamento final executado.")
    return True
