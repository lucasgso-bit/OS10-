"""Run the initial WNota 255 workflow steps.

Update robot execution status, search pending notes, and open Agro when needed.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from __future__ import annotations

import time

from config import AGRO_EXE
from robots.robot_OS07.src.agro_alerts import (
    confirm_attention_popup,
    confirm_establishment_selection,
)
from robots.robot_OS07.src.agro_app import kill_agro_process, start_agro
from robots.robot_OS07.src.agro_login import login_agro
from robots.robot_OS07.src.database import (
    buscar_notas_pendentes,
    buscar_U_ROBOT_LOG_EXECUCAO,
    buscar_U_ROBOT_NEXT,
    get_connection,
    marcar_concluido,
    marcar_executando,
)
from robots.robot_OS07.src.nota_router import process_note_by_config
from robots.robot_OS07.src.replacement_estab import (
    switch_establishment,
    wait_window_startswith,
)


_INTERRUPT_CHECK_INTERVAL = 180  # 3 minutos


def _esta_interrompido() -> bool:
    """Retorna True se o robô não está mais EXECUTANDO em U_ROBOT_LOG."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            return buscar_U_ROBOT_LOG_EXECUCAO(cursor) is None


def _reiniciar_agro() -> None:
    """Mata e reinicia o Agro, faz login e confirma popups iniciais."""
    print("Reiniciando Agro...")
    kill_agro_process("Agro3C.exe")
    start_agro(AGRO_EXE)
    time.sleep(5)
    login_agro()
    print("Login realizado.")
    confirm_attention_popup()
    confirm_establishment_selection()
    if not wait_window_startswith("AGRO-AG", timeout_seconds=15):
        raise RuntimeError("Tela AGRO-AG não abriu após reinício.")
    print("Agro pronto para uso.")


def run_once() -> None:
    """Single execution cycle: fetch pending notes and process all of them.

    Called by the platform worker. No loop, no sleep — returns when done.
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            executando = buscar_U_ROBOT_LOG_EXECUCAO(cursor)
            if executando:
                print(f"Robô já em execução (log_id={executando[0]}). Pulando ciclo.")
                return

            proximo = buscar_U_ROBOT_NEXT(cursor)
            if not proximo:
                print("Nenhuma tarefa pendente na fila.")
                return

            log_id = proximo[0]

        marcar_executando(connection, log_id)
        print(f"Tarefa log_id={log_id} marcada como EXECUTANDO.")

    print("\n Buscando notas...")

    with get_connection() as connection:
        notas = buscar_notas_pendentes(connection)

    print(f"Notas encontradas: {len(notas)}")

    if not notas:
        print("Nenhuma nota pendente.")
        with get_connection() as connection:
            marcar_concluido(connection, log_id)
        print(f"Tarefa log_id={log_id} marcada como CONCLUIDO.")
        return

    print("Iniciando Agro...")
    kill_agro_process("Agro3C.exe")
    start_agro(AGRO_EXE)
    time.sleep(5)

    login_agro()
    print("Login realizado.")

    confirm_attention_popup()
    confirm_establishment_selection()

    if not wait_window_startswith("AGRO-AG", timeout_seconds=15):
        raise RuntimeError("Tela AGRO-AG não abriu.")

    print("Agro pronto para uso.")

    ultimo_check = time.time()

    for nota in notas:
        # A cada 3 minutos, consulta U_ROBOT_LOG para ver se o robô foi interrompido
        if time.time() - ultimo_check >= _INTERRUPT_CHECK_INTERVAL:
            if _esta_interrompido():
                print(f"Robô interrompido externamente (log_id={log_id}). Parando processamento.")
                return
            ultimo_check = time.time()

        try:
            id_nota = nota.get("U_FISCAL_IO_CONT_ID")
            estab_nota = int(nota["ESTAB"])

            print(f"\n-> Processando nota ID: {id_nota} | Estab: {estab_nota}")

            switched = switch_establishment(estab_nota)
            if not switched:
                print(f"Tela de seleção de estabelecimento não apareceu para nota {id_nota}. Reiniciando Agro e pulando nota.")
                _reiniciar_agro()
                continue

            print("Troca de estabelecimento realizada.")

            processed = process_note_by_config(nota)

            if processed:
                print("Nota processada com sucesso")
            else:
                print("Falha ao processar nota")

        except Exception as e:
            print(f"Erro na nota {nota.get('U_FISCAL_IO_CONT_ID')}: {e}")

    with get_connection() as connection:
        marcar_concluido(connection, log_id)
    print(f"Tarefa log_id={log_id} marcada como CONCLUIDO.")


def run() -> None:
    """Legacy loop — used only by main.py (direct execution without the platform)."""
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"ERRO GERAL: {e}")
        print("Aguardando 20 segundos...\n")
        time.sleep(20)
