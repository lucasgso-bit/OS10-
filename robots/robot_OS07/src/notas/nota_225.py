"""
Process NOTACONF 225 notes.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-02
Version: 1.1.0
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
# PROCESSO PRINCIPAL
# =========================


def process_notaconf_225(nota: dict[str, Any]) -> bool:
    """Fluxo principal NOTACONF 225."""
    print("Processando NOTACONF 225...")

    if not focus_window("AGRO-AG"):
        print("Janela principal do Agro não encontrada.")
        print_open_windows()
        return handle_error(nota, "Janela principal do Agro não encontrada")

    pyautogui.hotkey("alt", "n")
    time.sleep(1)

    pyautogui.press("enter")
    time.sleep(1)

    # Tela filtro
    if not (
        wait_window_startswith("Filtrar NF - Cabeçalho", 5)
        or wait_window_startswith("Filtrar NF", 5)
        or wait_window_startswith("Filtrar", 5)
    ):
        print("Tela de filtro não encontrada.")
        return handle_error(nota, "Tela de filtro não encontrada")

    pyautogui.hotkey("alt", "v")
    time.sleep(1)

    # Tela Nota
    if not (
        wait_window_startswith("Nota Fiscal", 10) or wait_window_startswith("Nota", 5)
    ):
        print("Tela 'Nota Fiscal' não carregou.")
        return handle_error(nota, "Tela 'Nota Fiscal' não carregou")

    pyautogui.hotkey("ctrl", "insert")
    time.sleep(8)

    pyautogui.write("225", interval=0.03)
    pyautogui.press("enter")
    time.sleep(3)

    if wait_window_startswith("Dados da NF-e Recebida", 10):
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
    pyautogui.write(chave_acesso, interval=0.03)
    time.sleep(1)

    pyautogui.press("tab")
    time.sleep(1)

    # Clica em "Carregar na NF"
    click_in_window("Dados da NF-e Recebida", 412, 48)
    time.sleep(2)

    if grid_has_data("Dados da NF-e Recebida", 258, 157):
        print("Grid com endereços detectado. Selecionando primeira linha...")
        double_click_in_window("Dados da NF-e Recebida", 258, 157)
        time.sleep(1)
        pyautogui.press("tab", presses=3, interval=0.1)
    else:
        time.sleep(1)
        pyautogui.press("tab", presses=2, interval=0.1)

    time.sleep(1)

    pyautogui.press("enter")
    time.sleep(1)

    pyautogui.hotkey("alt", "n")
    time.sleep(1)

    # =========================
    # ENDEREÇO (OPCIONAL)
    # =========================
    if wait_window_startswith("Seleção de Endereço", 10):
        print("Tela de endereço encontrada.")

        inscricao = str(nota.get("IEEMITENTE") or "").strip()

        if inscricao:
            pyautogui.press("right", presses=2)
            pyautogui.press("up")
            pyautogui.write(inscricao, interval=0.03)
            pyautogui.press("enter")

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

    time.sleep(2)

    pyautogui.hotkey("alt", "o")
    time.sleep(1)
    pyautogui.hotkey("alt", "o")
    time.sleep(1)
    pyautogui.hotkey("alt", "p")
    time.sleep(1)

    pyautogui.press("enter")
    pyautogui.write(ddmmyy, interval=0.03)
    time.sleep(2)
    pyautogui.press("enter")

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

    time.sleep(1)

    # =========================
    # ABRE TELA "A PARTIR DE NF"
    # =========================
    double_click_in_window("Nota Fiscal", 697, 120)
    time.sleep(2)

    # =========================
    # NOTA FILHA: Tab×13 → escreve → Enter → Ctrl+P
    # =========================
    for _ in range(13):
        pyautogui.press("tab")
        time.sleep(0.1)

    pyautogui.write(notafilha, interval=0.03)
    pyautogui.press("enter")
    time.sleep(1)

    agro_count_before = sum(1 for w in gw.getAllWindows() if w.title.strip() == "Agro")

    pyautogui.hotkey("ctrl", "p")

    popup_detectado = False
    for _ in range(3):
        time.sleep(1)
        if (
            sum(1 for w in gw.getAllWindows() if w.title.strip() == "Agro")
            > agro_count_before
        ):
            popup_detectado = True
            break

    if popup_detectado:
        print("Popup 'Agro' detectado — Nenhuma linha encontrada na grid sgNota.")
        focus_window("Agro")
        time.sleep(0.5)
        click_in_window("Agro", 130, 61)
        time.sleep(1)
        return handle_error(
            nota, "Nenhuma linha encontrada na grid sgNota — NOTAFILHA não encontrada"
        )

    print(f"NOTAFILHA '{notafilha}' preenchida.")

    # =========================
    # QUANTIDADE: Tab×20 → Enter×2 → quantidade → Enter → Ctrl+S
    # =========================
    if quantidade:
        time.sleep(2)

        for _ in range(19):
            pyautogui.press("tab")
            time.sleep(0.1)

        pyautogui.press("enter")
        pyautogui.press("enter")

        pyautogui.write(quantidade, interval=0.03)
        pyautogui.press("enter")

        pyautogui.hotkey("ctrl", "s")
        time.sleep(1)

        print(f"Quantidade '{quantidade}' inserida e salva.")
    else:
        print("QUANTIDADE não informada.")

    # =========================
    #  TRATA POPUP ATENÇÃO (erro de quantidade)
    # =========================
    print("Verificando popup 'Atenção'...")

    if wait_window_startswith("Atenção", timeout_seconds=3):
        print("Popup 'Atenção' detectado — Quantidade a fixar maior que o saldo.")
        pyautogui.press("enter")
        time.sleep(1)
        return handle_error(nota, "Quantidade a fixar maior que o saldo")

    print("Popup 'Atenção' não apareceu.")

    # =========================
    # CLASSIFICAÇÃO
    # =========================
    pyautogui.hotkey("alt", "o")
    time.sleep(1)

    pyautogui.press("right")
    pyautogui.press("down")

    if classif_local:
        pyautogui.write(classif_local, interval=0.03)
        pyautogui.press("enter")
        print(f"CLASSIF_LOCAL '{classif_local}' preenchido.")

    # =========================
    # PLACA (Tab×7 para posicionar)
    # =========================
    for _ in range(7):
        pyautogui.press("tab")
        time.sleep(0.1)

    # =========================
    # ORDEM DE CARGA
    # =========================
    if ordem_carga:
        time.sleep(1)
        pyautogui.write(ordem_carga, interval=0.03)
        pyautogui.press("enter")

        pyautogui.hotkey("ctrl", "s")
        time.sleep(1)

        print(f"ORDEMCARGA '{ordem_carga}' preenchida.")

        if not verificar_advertencia_apos_ordemcarga(nota):
            return False

    # =========================
    #  FINANCEIRO
    # =========================
    print("Verificando tela financeiro...")

    if wait_window_startswith("Pagamento com Duplicatas", timeout_seconds=5):
        print("Tela financeira encontrada.")

        pyautogui.hotkey("ctrl", "p")
        time.sleep(1)

        pyautogui.hotkey("ctrl", "s")
        time.sleep(1)

    else:
        print("Tela financeira não apareceu.")

    # =========================
    #  VOLTA NOTA FISCAL
    # =========================
    print("Verificando retorno para Nota Fiscal...")

    if wait_window_startswith("[A]dvertências", timeout_seconds=10):
        print("Tela Advertências/Nota Fiscal encontrada.")
        time.sleep(3)
        focus_window("[A]dvertências")

        if advertencias_tem_erro_critico():
            print("Advertências com erro crítico — linha vermelha detectada.")
            notify_error(nota, "Advertência com erro crítico na nota fiscal")
            pyautogui.press("escape")
            time.sleep(1)
            restart_agro()
            return False

        pyautogui.hotkey("alt", "o")
        time.sleep(1)

        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("enter")
        time.sleep(1)

    else:
        print("Tela Advertências/Nota Fiscal não apareceu.")
        print_open_windows()

    time.sleep(5)
    # =========================
    # FECHAR TELAS
    # =========================
    pyautogui.hotkey("ctrl", "f4")
    time.sleep(1)

    print("Nota filha processada com sucesso.")
    return True
