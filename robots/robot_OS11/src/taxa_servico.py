"""Handle the Cobrança de Taxas de Serviço screen for the OS11 robot.

Find the screen, fill the SERVICO field, and process until the final warning.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import time

import pyautogui
import win32gui

from robots.robot_OS11.src.agro_alerts import (
    aguardar_alerta_32770,
    aviso_eh_final,
    confirmar_alerta_somente_enter,
    confirmar_todas_atencoes,
)
from robots.robot_OS11.src.window_utils import (
    aguardar_janela_sumir,
    clicar_controle,
    encontrar_controle_por_classe_instancia,
    focar_hwnd,
    focar_janela_por_titulo,
    obter_texto_janela,
    obter_titulo_janela_ativa,
    setar_texto_controle,
)

_TAXA_TITULO = "Cobrança de Taxas de Serviço"
_TAXA_CLASSE = "TFCobTxServico"


def encontrar_tela_taxa_servico() -> int | None:
    hwnd_encontrado = None

    def procurar(hwnd: int, _: None) -> None:
        nonlocal hwnd_encontrado
        if hwnd_encontrado:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return
        titulo = win32gui.GetWindowText(hwnd).strip()
        classe = win32gui.GetClassName(hwnd).strip()
        if titulo == _TAXA_TITULO and classe == _TAXA_CLASSE:
            hwnd_encontrado = hwnd

    win32gui.EnumWindows(procurar, None)
    return hwnd_encontrado


def focar_tela_taxa_servico(timeout: float = 5.0) -> int | None:
    inicio = time.time()
    while time.time() - inicio < timeout:
        hwnd = encontrar_tela_taxa_servico()
        if hwnd:
            if focar_hwnd(hwnd):
                time.sleep(0.25)
                return hwnd
        time.sleep(0.2)
    return None


def aguardar_tela_taxa_ativa(timeout: float = 30.0) -> bool:
    inicio = time.time()
    while time.time() - inicio < timeout:
        hwnd = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(hwnd).strip()
        classe = win32gui.GetClassName(hwnd).strip()
        if titulo == _TAXA_TITULO and classe == _TAXA_CLASSE:
            time.sleep(0.5)
            return True
        hwnd_taxa = encontrar_tela_taxa_servico()
        if hwnd_taxa:
            focar_hwnd(hwnd_taxa)
            time.sleep(0.3)
            hwnd_ativo = win32gui.GetForegroundWindow()
            titulo_ativo = win32gui.GetWindowText(hwnd_ativo).strip()
            classe_ativo = win32gui.GetClassName(hwnd_ativo).strip()
            if titulo_ativo == _TAXA_TITULO and classe_ativo == _TAXA_CLASSE:
                time.sleep(0.5)
                return True
        time.sleep(0.2)
    return False


def fechar_tela_taxa_servico_ctrl_f4(timeout: float = 2.0) -> bool:
    hwnd_taxa = focar_tela_taxa_servico(timeout=timeout)
    if not hwnd_taxa:
        print("Tela Cobrança de Taxas de Serviço não está aberta. Nada para fechar.")
        return True
    print("Fechando Cobrança de Taxas de Serviço com CTRL + F4...")
    pyautogui.hotkey("ctrl", "f4")
    time.sleep(0.8)
    confirmar_todas_atencoes(timeout_primeira=1.2)
    if aguardar_janela_sumir(hwnd_taxa, timeout=2):
        print("Tela Cobrança de Taxas de Serviço fechada.")
        return True
    print("A tela Cobrança de Taxas de Serviço continuou aberta após CTRL + F4.")
    return False


def _formatar_valor_tela(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _preencher_campo(
    hwnd_janela: int,
    nome_campo: str,
    valor: object,
    classe_controle: str,
    instancia: int,
    pressionar_enter: bool = True,
) -> bool:
    valor_texto = _formatar_valor_tela(valor)
    if valor_texto == "":
        print(f"{nome_campo} não foi preenchido.")
        return False
    hwnd_controle = encontrar_controle_por_classe_instancia(
        hwnd_janela, classe_controle, instancia
    )
    if not hwnd_controle:
        print(f"Controle do campo {nome_campo} não encontrado.")
        return False
    clicar_controle(hwnd_controle)
    time.sleep(0.15)
    setar_texto_controle(hwnd_controle, valor_texto)
    time.sleep(0.25)
    if pressionar_enter:
        pyautogui.press("enter")
        time.sleep(0.35)
        confirmar_todas_atencoes(timeout_primeira=0.8)
    return True


def _preparar_consulta_servico() -> bool:
    print("Executando navegação após digitar SERVICO...")
    print("Sequência segura: 5x SHIFT + TAB, RIGHT, CTRL + P, 2x TAB")

    if not focar_tela_taxa_servico(timeout=5):
        print("Não foi possível focar a tela Cobrança de Taxas de Serviço.")
        return False

    time.sleep(0.5)

    for tentativa in range(5):
        print(f"Enviando SHIFT + TAB antes do RIGHT {tentativa + 1}/5...")
        pyautogui.hotkey("shift", "tab")
        time.sleep(0.25)

    print("Enviando RIGHT...")
    pyautogui.press("right")
    time.sleep(0.5)

    print("Enviando CTRL + P...")
    pyautogui.hotkey("ctrl", "p")

    print("Aguardando 3 segundos após CTRL + P...")
    time.sleep(3)

    confirmar_todas_atencoes(timeout_primeira=1.5)

    if not aguardar_tela_taxa_ativa(timeout=30):
        print("Tela Cobrança de Taxas de Serviço não ficou ativa após CTRL + P.")
        return False

    if not focar_tela_taxa_servico(timeout=5):
        print("Perdeu o foco da tela Cobrança de Taxas de Serviço após CTRL + P.")
        return False

    print("Aguardando estabilização antes dos TABs...")
    time.sleep(1)

    print("Enviando TAB 1 depois do CTRL + P...")
    pyautogui.keyDown("tab")
    time.sleep(0.2)
    pyautogui.keyUp("tab")
    time.sleep(0.6)

    print("Enviando TAB 2 depois do CTRL + P...")
    pyautogui.keyDown("tab")
    time.sleep(0.2)
    pyautogui.keyUp("tab")
    time.sleep(0.6)

    print("TABs enviados. Aguardando antes do CTRL + ESPAÇO...")
    time.sleep(2)

    return True


def _processar_servico_ate_aviso(max_tentativas: int = 300) -> bool:
    for tentativa in range(1, max_tentativas + 1):
        print(f"Tentativa {tentativa}/{max_tentativas} no ESTAB atual.")

        if tentativa == 1:
            print("Primeira tentativa após os TABs. Não vou refocar antes do CTRL + ESPAÇO.")
            time.sleep(1)
        else:
            print("Tentativa após alerta. Focando a tela de taxa antes de repetir.")
            hwnd_taxa = focar_tela_taxa_servico(timeout=5)
            if not hwnd_taxa:
                print("Não conseguiu focar a tela de taxa. Vou continuar mesmo assim.")
            time.sleep(1)

        print("Enviando CTRL + ESPAÇO...")
        pyautogui.keyDown("ctrl")
        time.sleep(0.2)
        pyautogui.press("space")
        time.sleep(0.2)
        pyautogui.keyUp("ctrl")

        print("Aguardando marcação da linha antes do ALT + G...")
        time.sleep(1.5)

        print("Enviando ALT + G...")
        pyautogui.keyDown("alt")
        time.sleep(0.2)
        pyautogui.press("g")
        time.sleep(0.2)
        pyautogui.keyUp("alt")

        print("Aguardando tela após ALT + G...")
        time.sleep(1)

        hwnd_alerta, titulo_alerta, classe_alerta = aguardar_alerta_32770(timeout=8)

        if not hwnd_alerta:
            print("Nenhuma tela apareceu após ALT + G.")
            print("Vai focar a tela e repetir CTRL + ESPAÇO e ALT + G no mesmo ESTAB.")
            hwnd_taxa = focar_tela_taxa_servico(timeout=5)
            if not hwnd_taxa:
                print("Não conseguiu focar a tela de taxa, mas vai repetir mesmo assim.")
            time.sleep(1)
            continue

        print("Tela encontrada:")
        print("Título:", titulo_alerta)
        print("Classe:", classe_alerta)
        print("HWND:", hwnd_alerta)

        texto_alerta = obter_texto_janela(hwnd_alerta)
        print("Texto:", texto_alerta)

        if aviso_eh_final(hwnd_alerta, titulo_alerta, classe_alerta):
            print("Aviso final encontrado.")
            print("Esse aviso indica que não há mais nota no ESTAB atual.")
            print("Confirmando com ENTER e trocando para o próximo ESTAB.")

            confirmar_alerta_somente_enter(hwnd_alerta)
            time.sleep(1)

            hwnd_taxa = focar_tela_taxa_servico(timeout=5)
            if not hwnd_taxa:
                print("Não conseguiu focar Cobrança de Taxas de Serviço antes do CTRL + F4.")
                print("Tentando fechar com CTRL + F4 mesmo assim.")

            time.sleep(0.5)

            print("Fechando Cobrança de Taxas de Serviço com CTRL + F4...")
            pyautogui.hotkey("ctrl", "f4")
            time.sleep(1.2)

            confirmar_todas_atencoes(timeout_primeira=1.2)

            print("ESTAB finalizado. Próximo ESTAB será processado.")
            return True

        print("Tela diferente do aviso final.")
        print("Confirmando com ENTER.")

        confirmar_alerta_somente_enter(hwnd_alerta)

        print("Esperando 1 segundo após ENTER.")
        time.sleep(1)

        print("Focando de volta na tela Cobrança de Taxas de Serviço.")
        hwnd_taxa = focar_tela_taxa_servico(timeout=5)
        if not hwnd_taxa:
            print("Não conseguiu focar a tela de taxa, mas vai repetir mesmo assim.")

        time.sleep(0.5)

    print("Limite de tentativas atingido sem aparecer o aviso final.")
    return False


def preencher_cobranca_taxa_servico(servico: int) -> bool:
    """Fill the SERVICO field and process all entries until the final warning."""
    hwnd_janela = encontrar_tela_taxa_servico()
    if not hwnd_janela:
        hwnd_janela = focar_tela_taxa_servico(timeout=10)

    if not hwnd_janela:
        print("Janela TFCobTxServico não encontrada.")
        return False

    focar_hwnd(hwnd_janela)
    time.sleep(0.5)

    print("Preenchendo janela TFCobTxServico somente com SERVICO...")

    if not _preencher_campo(
        hwnd_janela=hwnd_janela,
        nome_campo="SERVICO",
        valor=servico,
        classe_controle="TVsNumRight",
        instancia=12,
        pressionar_enter=False,
    ):
        return False

    print("SERVICO preenchido:", servico)

    if not _preparar_consulta_servico():
        print("Falha ao preparar consulta depois do SERVICO.")
        return False

    sucesso = _processar_servico_ate_aviso()

    if not sucesso:
        print("Falha no processamento do ESTAB atual.")
        return False

    print("ESTAB finalizado com aviso e tela fechada.")
    return True


def abrir_tela_taxa_servico() -> bool:
    """Open or focus the Cobrança de Taxas de Serviço screen."""
    if focar_tela_taxa_servico(timeout=1):
        print("Tela de taxa de serviço já está aberta. Reutilizando tela focada.")
        return True

    focar_janela_por_titulo("AGRO-AG")
    time.sleep(0.6)

    print("Abrindo tela de taxa de serviço...")

    pyautogui.hotkey("alt", "a")
    time.sleep(0.3)

    pyautogui.press("right")
    time.sleep(0.2)

    for _ in range(3):
        pyautogui.press("down")
        time.sleep(0.2)

    pyautogui.press("right")
    time.sleep(0.2)

    pyautogui.press("enter")
    time.sleep(1)

    if confirmar_todas_atencoes(timeout_primeira=1.2):
        print("Atenção/Erro/Aviso apareceu ao abrir taxa de serviço.")

    return bool(focar_tela_taxa_servico(timeout=6))
