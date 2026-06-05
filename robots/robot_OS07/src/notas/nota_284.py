"""
Process NOTACONF 284 notes.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-02
Version: 2.4.0
"""

from __future__ import annotations

import time
from typing import Any

import pyautogui

from robots.robot_OS07.src.notifier import notify_error
from robots.robot_OS07.src.replacement_estab import wait_window_startswith
from robots.robot_OS07.src.notas.nota_utils import (
    ESTABS_COM_CHAVE_NFE,
    advertencias_tem_erro_critico,
    close_current_windows,
    fill_inscricao_pessoa,
    focus_window,
    focus_window_contains,
    focus_window_startswith,
    format_dtemissao_ddmmyy,
    get_estab,
    get_required_note_value,
    handle_error,
    print_open_windows,
    restart_agro,
    verificar_advertencia_apos_ordemcarga,
)

# =========================
# CONFIGURACOES DE CLIQUE
# =========================

# Botao "Contratos" identificado pelo fluxo FlaUI que funciona.
#
# PowerShell original:
#   $btnContato = $instance.GetElement('/Tab/Pane/Pane/Button[2]', '')
#   $coords = $btnContato.BoundingRectangle.Location
#   $x = $coords.X + 66
#   $y = $coords.Y + 14
#   LeftClick($x, $y)
#
# AutoIt Window Info do botao:
#   Janela: Nota Fiscal / Classe: TFNfCab
#   Controle: [CLASS:TcxButton; INSTANCE:2]
#   Texto: Contratos
#   Position: 784, 112
#   Size: 161 x 25
#
# Calculo equivalente ao PowerShell:
#   X = 784 + 66 = 850
#   Y = 112 + 14 = 126
CONTRATOS_BUTTON_X = 850
CONTRATOS_BUTTON_Y = 126

# Clique usado apenas para dar foco dentro da tela "Consulta contratos".
CONSULTA_CONTRATO_FOCUS_X = 200
CONSULTA_CONTRATO_FOCUS_Y = 200


# =========================
# UTILS LOCAIS
# =========================


def _focus_consulta_contratos_window(timeout: int = 7) -> bool:
    """Foca na tela 'Consulta contratos'."""
    return focus_window_contains("Consulta contratos", timeout_seconds=timeout)


# =========================
# ABERTURA DA TELA CONTRATOS
# =========================


def _open_consulta_contratos(nota: dict[str, Any]) -> bool:
    """Open Consulta contratos by clicking the real Contratos button twice."""
    print("Abrindo Consulta contratos pelo botao Contratos...")

    if not focus_window_contains("Nota Fiscal", timeout_seconds=5):
        return handle_error(
            nota,
            "Tela 'Contrato' nao encontrada antes de clicar em Contratos",
        )

    time.sleep(1)

    for tentativa in range(2):
        print(f"Clique no botao Contratos. Tentativa {tentativa + 1}/2.")
        pyautogui.click(CONTRATOS_BUTTON_X, CONTRATOS_BUTTON_Y)
        time.sleep(1)

        if _focus_consulta_contratos_window(timeout=5):
            print("Tela 'Consulta contratos' encontrada apos clicar em Contratos.")
            return True

    return handle_error(
        nota,
        "Tela 'Consulta contratos' nao apareceu apos clicar no botao Contratos",
    )


# =========================
# PROCESSO PRINCIPAL
# =========================


def process_notaconf_284(nota: dict[str, Any]) -> bool:
    """Run the main NOTACONF 284 flow."""
    print("Processando NOTACONF 284...")

    if not focus_window("AGRO-AG"):
        print("Janela principal do Agro nao encontrada.")
        print_open_windows()
        return handle_error(nota, "Janela principal do Agro nao encontrada")

    pyautogui.hotkey("alt", "n")
    time.sleep(1)

    pyautogui.press("enter")
    time.sleep(1)

    if not (
        wait_window_startswith("Filtrar NF - Cabecalho", 5)
        or wait_window_startswith("Filtrar NF - Cabeçalho", 5)
        or wait_window_startswith("Filtrar NF", 5)
        or wait_window_startswith("Filtrar", 5)
    ):
        print("Tela de filtro nao encontrada.")
        return handle_error(nota, "Tela de filtro nao encontrada")

    pyautogui.hotkey("alt", "v")
    time.sleep(1)

    if not (
        wait_window_startswith("Nota Fiscal", 10) or wait_window_startswith("Nota", 5)
    ):
        print("Tela 'Nota Fiscal' nao carregou.")
        return handle_error(nota, "Tela 'Nota Fiscal' nao carregou")

    pyautogui.hotkey("ctrl", "insert")
    time.sleep(8)

    pyautogui.write("284", interval=0.03)
    pyautogui.press("enter")
    time.sleep(1)
    return process_dados_nfe_recebida(nota)


# =========================
# PROCESSO NF-e
# =========================


def process_dados_nfe_recebida(nota: dict[str, Any]) -> bool:
    """Process the Dados da NF-e Recebida screen."""
    try:
        numerocm = get_required_note_value(nota, "NUMEROCM")
        inscricao = get_required_note_value(nota, "IEEMITENTE")
        ddmmyy = format_dtemissao_ddmmyy(nota)
    except ValueError as error:
        return handle_error(nota, str(error))

    print("Inserindo pessoa/NUMEROCM...")
    pyautogui.write(numerocm, interval=0.03)
    print(f"NUMEROCM '{numerocm}' preenchido.")

    pyautogui.press("enter")
    time.sleep(1)

    if not wait_window_startswith(
        "Selecao de Endereco", 5
    ) and not wait_window_startswith("Seleção de Endereço", 5):
        print("Tela de endereco nao apareceu.")
        return handle_error(
            nota, "Tela 'Selecao de Endereco' nao apareceu apos inserir pessoa"
        )

    print("Tela de endereco encontrada. Selecionando inscricao...")
    fill_inscricao_pessoa(inscricao)

    if not _open_consulta_contratos(nota):
        return False

    if not process_consulta_contrato_284(nota, ddmmyy):
        print("Falha na etapa de contrato.")
        return False

    print("Processo NOTACONF 284 finalizado com sucesso.")
    return True


# =========================
# PROCESSO CONTRATO 284
# =========================


def process_consulta_contrato_284(nota: dict[str, Any], ddmmyy: str) -> bool:
    """Process contract, quantity, producer tab, classification, and finance."""
    contrato = str(nota.get("CONTRATO") or "").strip()
    chave_acesso = str(nota.get("CHAVEACESSO") or "").strip()
    quantidade = str(nota.get("QUANTIDADE") or "").strip()
    classif_local = str(nota.get("CLASSIF_LOCAL") or "").strip()
    placa = str(nota.get("PLACA") or "").strip()
    ordem_carga = str(nota.get("ORDEMCARGA") or "").strip()

    if not contrato:
        print("CONTRATO nao encontrado.")
        return handle_error(nota, "CONTRATO nao encontrado na nota")

    if not quantidade:
        print("QUANTIDADE nao encontrada.")
        return handle_error(nota, "QUANTIDADE nao encontrada na nota")

    if not _focus_consulta_contratos_window():
        print("Tela 'Consulta contratos' nao encontrada.")
        return handle_error(nota, "Tela 'Consulta contratos' nao encontrada")

    print(f"Tela 'Consulta contratos' encontrada. Contrato: {contrato}")
    time.sleep(1)

    # Clique apenas para garantir foco dentro da tela Consulta contratos.
    pyautogui.click(CONSULTA_CONTRATO_FOCUS_X, CONSULTA_CONTRATO_FOCUS_Y)
    time.sleep(0.5)

    print("Inserindo contrato...")
    time.sleep(0.2)
    pyautogui.press("tab", presses=6, interval=0.05)
    time.sleep(0.2)
    pyautogui.write(contrato, interval=0.03)
    time.sleep(2)
    pyautogui.press("enter")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "p")
    time.sleep(1)

    # Atencao apos Ctrl+P = contrato NAO encontrado.
    if wait_window_startswith("Atencao", timeout_seconds=3) or wait_window_startswith(
        "Atenção", timeout_seconds=3
    ):
        print("Contrato nao encontrado: popup 'Atencao' detectado apos Ctrl+P.")
        return handle_error(nota, f"Contrato '{contrato}' nao encontrado no Agro")

    print("Setando quantidade...")
    pyautogui.press("tab", presses=3, interval=0.05)
    time.sleep(2)
    pyautogui.press("enter")
    time.sleep(2)
    pyautogui.press("enter")
    time.sleep(0.2)
    pyautogui.write(quantidade, interval=0.03)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)

    # Confirmacao de quantidade, se aparecer.
    if wait_window_startswith("Atencao", timeout_seconds=2) or wait_window_startswith(
        "Atenção", timeout_seconds=2
    ):
        pyautogui.hotkey("alt", "s")
        time.sleep(1)

    print(f"Quantidade '{quantidade}' inserida e salva.")

    print("Preenchendo aba Nota Produtor...")
    time.sleep(6)
    pyautogui.hotkey("shift", "tab")
    time.sleep(0.2)
    pyautogui.press("right", presses=6, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("tab", presses=4, interval=0.05)
    time.sleep(0.2)

    if chave_acesso:
        pyautogui.write(chave_acesso, interval=0.03)
        print("Chave de acesso preenchida na aba Nota Produtor.")
    else:
        return handle_error(nota, "CHAVEACESSO nao encontrada para aba Nota Produtor")

    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.2)
    pyautogui.press("up")
    time.sleep(0.2)
    pyautogui.press("right", presses=2, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.2)
    pyautogui.write(ddmmyy, interval=0.03)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.2)
    print(f"Aba Nota Produtor preenchida com data '{ddmmyy}'.")

    print("Inserindo classificacao...")
    if not _process_classificacao_284(nota, classif_local, placa, ordem_carga):
        return False

    if not _process_financeiro_284(nota):
        return False

    if not _process_advertencias_284(nota):
        return False

    if not _process_impressao_transmissao_284(nota):
        return False

    if not _process_chave_por_estab_284(nota, ddmmyy):
        return False

    print("Contrato processado com sucesso.")
    return True


def _process_classificacao_284(
    nota: dict[str, Any],
    classif_local: str,
    placa: str,
    ordem_carga: str,
) -> bool:
    """Fill the classification, plate, and loading order fields."""
    if not classif_local:
        return handle_error(nota, "CLASSIF_LOCAL nao encontrado na nota")

    pyautogui.press("tab", presses=4, interval=0.1)
    time.sleep(0.1)
    pyautogui.press("right", presses=2, interval=0.1)
    time.sleep(0.1)
    pyautogui.press("enter")
    time.sleep(0.5)

    pyautogui.write(classif_local, interval=0.03)
    print(f"CLASSIF_LOCAL '{classif_local}' preenchido.")

    pyautogui.press("enter", presses=7, interval=0.1)
    time.sleep(0.5)

    if placa:
        pyautogui.write(placa, interval=0.03)
        print(f"PLACA '{placa}' preenchida.")
    else:
        print("PLACA nao informada. Seguindo sem preencher.")

    pyautogui.press("enter")
    time.sleep(0.5)

    if ordem_carga:
        pyautogui.write(ordem_carga, interval=0.03)
        print(f"ORDEMCARGA '{ordem_carga}' preenchida.")
    else:
        print("ORDEMCARGA nao informada. Seguindo sem preencher.")

    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)

    if ordem_carga and not verificar_advertencia_apos_ordemcarga(nota):
        return False

    return True


def _process_financeiro_284(nota: dict[str, Any]) -> bool:
    """Save the financial screen when Pagamento com Duplicatas appears."""
    print("Verificando tela financeiro...")

    if wait_window_startswith("Pagamento com Duplicatas", timeout_seconds=5):
        print("Tela financeira encontrada.")
        pyautogui.hotkey("ctrl", "p")
        time.sleep(1)
        pyautogui.hotkey("ctrl", "s")
        time.sleep(1)
        return True

    print("Tela financeira nao apareceu. Seguindo fluxo.")
    return True


def _process_advertencias_284(nota: dict[str, Any]) -> bool:
    """Confirm Advertencias when no critical error is detected."""
    print("Verificando retorno para Nota Fiscal/Advertencias...")

    if not (
        wait_window_startswith("[A]dvertencias", timeout_seconds=5)
        or wait_window_startswith("[A]dvertências", timeout_seconds=5)
    ):
        print("Tela Advertencias/Nota Fiscal nao apareceu.")
        print_open_windows()
        return True

    print("Tela Advertencias encontrada.")
    time.sleep(3)
    if not (focus_window("[A]dvertencias") or focus_window("[A]dvertências")):
        print("Nao foi possivel focar Advertencias.")

    if advertencias_tem_erro_critico():
        print("Advertencias com erro critico: linha vermelha detectada.")
        notify_error(nota, "Advertencia com erro critico na nota fiscal")
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

    return True


# =========================
# IMPRESSAO / TRANSMISSAO
# =========================


def _process_impressao_transmissao_284(nota: dict[str, Any]) -> bool:
    """Validate print screen, handle note message, transmit the NF-e, and close screens."""
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

    time.sleep(0.3)

    print("Verificando tela 'Mensagem da Nota - Nota (0)' antes do Ctrl+E...")

    if focus_window_contains("Mensagem da Nota - Nota (0)", timeout_seconds=3):
        print("Tela 'Mensagem da Nota - Nota (0)' encontrada. Enviando Ctrl+S...")
        pyautogui.hotkey("ctrl", "s")
        time.sleep(2)
    else:
        print("Tela 'Mensagem da Nota - Nota (0)' nao apareceu. Seguindo para Ctrl+E.")

    print("Tela de impressao encontrada. Enviando Ctrl+E para transmitir...")
    time.sleep(1)
    pyautogui.hotkey("ctrl", "e")

    print("Verificando popup de transmissao 'Agro'...")
    if not focus_window_startswith("Agro", timeout_seconds=10):
        return handle_error(
            nota,
            "Popup 'Agro' de transmissao nao apareceu apos Ctrl+E",
        )

    print("Popup 'Agro' detectado. Confirmando transmissao...")
    pyautogui.press("enter")
    time.sleep(10)

    pyautogui.hotkey("alt", "o")
    time.sleep(1)

    pyautogui.press("enter")
    time.sleep(6)
    pyautogui.press("enter")

    print("Fechando telas apos transmissao...")
    close_current_windows(times=3, delay_seconds=2)
    close_current_windows(times=3, delay_seconds=2)
    return True


# =========================
# POS-TRANSMISSAO POR ESTAB
# =========================


def _process_chave_por_estab_284(nota: dict[str, Any], ddmmyy: str) -> bool:
    """Handle the post-transmission key flow for establishments 26, 68, and 71."""
    estab = get_estab(nota)

    if estab not in ESTABS_COM_CHAVE_NFE:
        print(
            f"Estabelecimento '{estab or 'NAO INFORMADO'}' nao exige fluxo de chave. "
            "Fechando telas e seguindo para o proximo.",
        )
        restart_agro()
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
    time.sleep(1)
    pyautogui.write(chave_nf, interval=0.03)
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.hotkey("alt", "n")
    time.sleep(1)

    print("Verificando tela de endereco apos inserir chave...")
    if wait_window_startswith("Selecao de Endereco", 5) or wait_window_startswith(
        "Seleção de Endereço", 5
    ):
        if inscricao:
            print("Tela de endereco encontrada. Inserindo IE.")
            fill_inscricao_pessoa(inscricao, executar_alt_t=False)
            print("IE preenchida na tela de endereco.")
        else:
            print("IEEMITENTE nao informada. Seguindo para alteracao de data.")
    else:
        print("Tela de endereco nao apareceu. Seguindo direto para alteracao de data.")

    _alterar_data_nota_284(ddmmyy)

    if not _salvar_final_284():
        return False

    return True


def _alterar_data_nota_284(ddmmyy: str) -> bool:
    """Alter the NF date through the same keyboard sequence used in PowerShell."""
    print(f"Alterando data para '{ddmmyy}'...")
    print("Pressing Alt+O...")
    time.sleep(2)
    pyautogui.hotkey("alt", "o")
    print("Pressing Alt+O...")
    time.sleep(10)
    pyautogui.hotkey("alt", "o")
    time.sleep(1)
    print("Pressing Alt+P...")
    pyautogui.hotkey("alt", "p")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.write(ddmmyy, interval=0.03)
    time.sleep(2)
    pyautogui.press("enter")
    time.sleep(1)

    return True


def _salvar_final_284() -> bool:
    """Run the final save sequence after date/key adjustments."""
    print("Executando salvamento final...")

    time.sleep(5)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(10)
    pyautogui.hotkey("alt", "o")
    time.sleep(1)

    time.sleep(5)
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(8)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)

    time.sleep(1)
    close_current_windows(times=3, delay_seconds=2)

    print("Salvamento final executado.")
    return True
