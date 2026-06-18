"""Run the OS11 taxa de serviço workflow.

Fetch eligible establishments from Oracle, open Agro, and process each
establishment through the Cobrança de Taxas de Serviço screen.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import time

import pyautogui

from config import AGRO_EXE, OS11_SERVICO_FIXO
from robots.robot_OS11.src.agro_alerts import confirmar_todas_atencoes
from robots.robot_OS11.src.agro_app import kill_agro_process, start_agro
from robots.robot_OS11.src.agro_login import login_agro
from robots.robot_OS11.src.database import buscar_estabelecimentos, get_connection
from robots.robot_OS11.src.replacement_estab import trocar_estabelecimento
from robots.robot_OS11.src.taxa_servico import (
    abrir_tela_taxa_servico,
    preencher_cobranca_taxa_servico,
)
from robots.robot_OS11.src.window_utils import focar_janela_por_titulo


def _iniciar_agro() -> None:
    """Kill Agro, start it, log in, and wait for the main AGRO-AG window."""
    print("Iniciando Agro...")

    kill_agro_process("Agro3C.exe")
    start_agro(AGRO_EXE)

    time.sleep(5)

    login_agro()
    print("Login realizado.")

    confirmar_todas_atencoes(timeout_primeira=1.5)

    try:
        focar_janela_por_titulo("Seleção de Estabelecimento para Trabalho", timeout=10)
        time.sleep(0.8)

        print("Tela de estabelecimento apareceu. Confirmando com ENTERs.")
        for _ in range(2):
            pyautogui.press("enter")
            time.sleep(0.8)
            confirmar_todas_atencoes(timeout_primeira=1.2)

        print("Tela de estabelecimento confirmada.")
    except RuntimeError:
        print("Tela de estabelecimento não apareceu. Continuando para AGRO-AG.")

    confirmar_todas_atencoes(timeout_primeira=1.5)

    focar_janela_por_titulo("AGRO-AG")
    time.sleep(1)

    print("Agro pronto para uso.")


def run() -> None:
    """Fetch establishments and process each one through taxa de serviço."""
    print("Conectando ao Oracle para buscar estabelecimentos...")

    with get_connection() as connection:
        estabelecimentos = buscar_estabelecimentos(connection)

    print(f"Estabelecimentos encontrados: {len(estabelecimentos)}")

    if not estabelecimentos:
        print("Nenhum estabelecimento encontrado. Processo finalizado.")
        return

    for estab in estabelecimentos:
        print("ESTAB encontrado:", estab)

    _iniciar_agro()

    print(f"Será preenchido somente o SERVICO: {OS11_SERVICO_FIXO}")

    for indice, estab in enumerate(estabelecimentos, start=1):
        try:
            print("-" * 50)
            print(f"Processando ESTAB {indice} de {len(estabelecimentos)}: {estab}")

            if not trocar_estabelecimento(estab):
                print("Erro ao trocar estabelecimento. Indo para o próximo ESTAB.")
                continue

            print("Abrindo/focando tela de taxa de serviço...")

            if not abrir_tela_taxa_servico():
                print("Erro ao abrir tela de taxa de serviço. Indo para o próximo ESTAB.")
                continue

            sucesso = preencher_cobranca_taxa_servico(servico=OS11_SERVICO_FIXO)

            if not sucesso:
                print("Erro no processamento da taxa de serviço. Indo para o próximo ESTAB.")
                continue

            print("ESTAB processado com sucesso:", estab)

        except Exception as erro:
            print("Erro inesperado ao processar este ESTAB.")
            print(erro)
            print("Indo para o próximo ESTAB.")
            continue

    print("Fluxo finalizado.")
