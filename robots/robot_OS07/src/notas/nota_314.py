"""
Process NOTACONF 314 notes.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-02
Version: 1.6.0
"""

from __future__ import annotations

import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pyautogui
import pygetwindow as gw
import pyperclip

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


def _focus_consulta_contratos_window(timeout: int = 7) -> bool:
    """Foca na tela 'Consulta contratos'."""
    for _ in range(timeout):
        for window in gw.getAllWindows():
            title = window.title.strip().lower()

            if "consulta contratos" in title:
                window.activate()
                time.sleep(1)
                return True

        time.sleep(1)

    print("DEBUG - Janelas disponíveis:")
    print_open_windows()
    return False


# =========================
# PROCESSO PRINCIPAL
# =========================


def process_notaconf_314(nota: dict[str, Any]) -> bool:
    """Fluxo principal NOTACONF 314."""
    print("Processando NOTACONF 314...")

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

    pyautogui.write("314", interval=0.03)
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
            pyautogui.press("enter")
            pyautogui.press("enter")
            pyautogui.press("enter")
            pyautogui.press("enter")
            pyautogui.press("enter")
            pyautogui.press("enter")
    else:
        print("Tela de endereço não apareceu. Continuando sem selecionar endereço.")
        time.sleep(0.5)
        for _ in range(6):
            pyautogui.press("enter")
            time.sleep(0.3)

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
    # CONTRATO
    # =========================
    if not process_consulta_contrato(nota):
        print("Falha na etapa de contrato.")
        return False

    print("Processo finalizado com sucesso.")
    return True


# =========================
# PROCESSO CONTRATO
# =========================


def process_consulta_contrato(nota: dict[str, Any]) -> bool:
    """Processa contrato + quantidade + classificação + placa + ordem + financeiro."""

    contrato = str(nota.get("CONTRATO") or "").strip()
    quantidade = str(nota.get("QUANTIDADE") or "").strip()
    classif_local = str(nota.get("CLASSIF_LOCAL") or "").strip()
    ordem_carga = str(nota.get("ORDEMCARGA") or "").strip()

    if not contrato:
        print("CONTRATO não encontrado.")
        return handle_error(nota, "CONTRATO não encontrado na nota")

    if not _focus_consulta_contratos_window():
        print("Tela 'Consulta contratos' não encontrada.")
        return handle_error(nota, "Tela 'Consulta contratos' não encontrada")

    print(f"Tela encontrada. Contrato: {contrato}")

    time.sleep(1)

    # =========================
    # FOCO
    # =========================
    pyautogui.click(200, 200)
    time.sleep(0.5)

    # =========================
    # CONTRATO
    # =========================
    time.sleep(2)
    for _ in range(6):
        pyautogui.press("tab")
        time.sleep(0.1)

    pyautogui.write(contrato, interval=0.03)
    pyautogui.press("enter")
    time.sleep(1)

    pyautogui.hotkey("ctrl", "p")
    time.sleep(2)

    # =========================
    # VERIFICA SE CONTRATO FOI ENCONTRADO
    # =========================
    if wait_window_startswith("Atenção", timeout_seconds=3):
        print("Popup 'Atenção' após busca de contrato — contrato não encontrado.")
        pyautogui.press("enter")
        time.sleep(0.5)
        return handle_error(nota, f"Contrato '{contrato}' não encontrado no Agro")

    if wait_window_startswith("Erro!", timeout_seconds=3):
        print("Popup 'Erro!' após busca de contrato.")
        focus_window("Erro!")
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.5)
        return handle_error(nota, f"Erro ao buscar contrato '{contrato}' no Agro")

    # =========================
    # QUANTIDADE
    # =========================
    if quantidade:
        time.sleep(2)

        for _ in range(3):
            pyautogui.press("tab")
            time.sleep(0.1)

        pyautogui.press("enter")
        pyautogui.press("enter")
        time.sleep(1)

        pyautogui.write(quantidade, interval=0.03)
        pyautogui.press("enter")
        time.sleep(1)

        # =========================
        # VOLTA NO CAMPO
        # =========================
        pyautogui.press("enter")
        time.sleep(1)

        # Garante foco na janela correta antes de copiar o campo
        _focus_consulta_contratos_window()
        time.sleep(0.3)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.5)

        valor_campo = pyperclip.paste().strip()
        print(f"Valor retornado pelo Agro: '{valor_campo[:80]}'")

        # =========================
        # NORMALIZA CORRETAMENTE
        # =========================
        def _to_decimal(valor: str) -> Decimal:
            valor = valor.strip()

            if "," in valor:
                valor = valor.replace(".", "").replace(",", ".")
            return Decimal(valor)

        try:
            valor_campo_dec = _to_decimal(valor_campo)
            quantidade_dec = _to_decimal(quantidade)

            print(f"Comparação: campo={valor_campo_dec} | digitado={quantidade_dec}")

            # =========================
            # VALIDAÇÃO REAL
            # =========================
            if valor_campo_dec < quantidade_dec:
                print("ERRO: Agro reduziu a quantidade (contrato insuficiente).")

                return handle_error(
                    nota,
                    f"Quantidade ajustada menor que informada. Retorno: {valor_campo} | Digitado: {quantidade}",
                )

        except (InvalidOperation, Exception):
            print(
                f"AVISO: Não foi possível validar quantidade via clipboard. "
                f"Campo='{valor_campo[:80]}' | Digitado='{quantidade}' — continuando."
            )

        pyautogui.press("enter")
        time.sleep(0.5)

        pyautogui.hotkey("ctrl", "s")
        time.sleep(1)

        print(f"Quantidade '{quantidade}' validada e salva.")

    else:
        print("QUANTIDADE não informada.")

    # =========================
    #  TRATA POPUP ATENÇÃO
    # =========================
    print("Verificando popup 'Atenção'...")

    if wait_window_startswith("Atenção", timeout_seconds=3):
        print("Popup 'Atenção' detectado.")
        pyautogui.hotkey("ctrl", "s")

    else:
        print("Popup 'Atenção' não apareceu.")

    # =========================
    #  TRATA ERRO IMPOSTO 1
    # =========================
    print("Verificando popup 'Erro'...")

    if wait_window_startswith("Erro!", timeout_seconds=3):
        print("Popup 'Erro!' detectado — erro no imposto.")

        focus_window("Erro!")
        time.sleep(0.5)

        pyautogui.press("enter")
        time.sleep(1)

        return handle_error(nota, "Erro no imposto ao processar a nota")

    else:
        print("Popup 'Erro!' não apareceu.")

    # =========================
    # CLASSIFICAÇÃO
    # =========================
    pyautogui.hotkey("alt", "o")
    time.sleep(1)

    pyautogui.hotkey("shift", "tab")
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

    print("Contrato processado com sucesso.")
    return True
