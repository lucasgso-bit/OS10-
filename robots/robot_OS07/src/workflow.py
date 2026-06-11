"""Run the initial WNota 255 workflow steps.

Update robot execution status, search pending notes, and open Agro when needed.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-05
Version: 2.0.0
"""

from __future__ import annotations

import time

from config import AGRO_EXE, COMPUTADOR_ROBO
from core.database import (
    buscar_executando,
    buscar_proximo_pendente,
    complete_task,
    get_connection,
    marcar_executando,
)
from robots.robot_OS07.src.agro_alerts import (
    confirm_attention_popup,
    confirm_establishment_selection,
)
from robots.robot_OS07.src.agro_app import kill_agro_process, start_agro
from robots.robot_OS07.src.agro_login import login_agro
from robots.robot_OS07.src.database import buscar_notas_pendentes
from robots.robot_OS07.src.nota_router import process_note_by_config
from robots.robot_OS07.src.queue_tracker import (
    enviar_relatorio_final,
    limpar_fila,
    marcar_concluido,
    marcar_erro,
    popular_fila,
)
from robots.robot_OS07.src.replacement_estab import (
    switch_establishment,
    wait_window_startswith,
)


_INTERRUPT_CHECK_INTERVAL = 180  # 3 minutos


def _esta_interrompido() -> bool:
    """Retorna True se o robô não está mais EXECUTANDO em U_ROBOT_LOG."""
    with get_connection() as conn:
        return buscar_executando(conn, COMPUTADOR_ROBO) is None


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


def run_once(log_id: int | None = None) -> None:
    """Single execution cycle: fetch pending notes and process all of them.

    When log_id is provided (called by the platform worker), task claiming and
    completion are handled by the worker — this function only runs the business
    logic. When log_id is None (legacy main.py path), this function claims and
    completes its own task.
    """
    platform_managed = log_id is not None

    if not platform_managed:
        with get_connection() as connection:
            executando = buscar_executando(connection, COMPUTADOR_ROBO)
            if executando:
                print(f"Robô já em execução (log_id={executando['u_robot_log_id']}). Pulando ciclo.")
                return

            proximo = buscar_proximo_pendente(connection, COMPUTADOR_ROBO)
            if not proximo:
                print("Nenhuma tarefa pendente na fila.")
                return

            log_id = proximo["u_robot_log_id"]
            marcar_executando(connection, log_id, COMPUTADOR_ROBO)
            print(f"Tarefa log_id={log_id} marcada como EXECUTANDO.")

    print("\n Buscando notas...")

    with get_connection() as connection:
        notas = buscar_notas_pendentes(connection)

    print(f"Notas encontradas 07: {len(notas)}")

    if not notas:
        print("Nenhuma nota pendente.")
        if not platform_managed:
            with get_connection() as connection:
                complete_task(connection, log_id, computer_name=COMPUTADOR_ROBO)
            print(f"Tarefa log_id={log_id} marcada como CONCLUIDO.")
        return

    # Limpa fila anterior deste usuário e popula com estimativas de tempo
    try:
        with get_connection() as connection:
            limpar_fila(connection)
            popular_fila(connection, notas)
    except Exception as exc:
        print(f"[queue_tracker] Erro ao popular fila (não bloqueia execução): {exc}")

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

        id_nota = nota.get("U_FISCAL_IO_CONT_ID")
        try:
            estab_nota = int(nota["ESTAB"])

            print(f"\n-> Processando nota ID: {id_nota} | Estab: {estab_nota}")

            switched = switch_establishment(estab_nota)
            if not switched:
                msg_err = f"Tela de seleção de estabelecimento não apareceu (nota {id_nota}). Agro reiniciado."
                print(msg_err)
                with get_connection() as connection:
                    marcar_erro(connection, id_nota, msg_err)
                _reiniciar_agro()
                continue

            print("Troca de estabelecimento realizada.")

            processed = process_note_by_config(nota)

            if processed:
                print("Nota processada com sucesso")
                try:
                    with get_connection() as connection:
                        marcar_concluido(connection, id_nota)
                except Exception as exc:
                    print(f"[queue_tracker] marcar_concluido falhou: {exc}")
            else:
                print("Falha ao processar nota")
                try:
                    with get_connection() as connection:
                        marcar_erro(connection, id_nota, "Falha no processamento (sem exceção)")
                except Exception as exc:
                    print(f"[queue_tracker] marcar_erro falhou: {exc}")

        except Exception as e:
            print(f"Erro na nota {id_nota}: {e}")
            try:
                with get_connection() as connection:
                    marcar_erro(connection, id_nota, str(e))
            except Exception as exc:
                print(f"[queue_tracker] marcar_erro falhou: {exc}")

    # Envia relatório final com totais de tentativas, sucesso e erro
    try:
        with get_connection() as connection:
            enviar_relatorio_final(connection)
    except Exception as exc:
        print(f"[queue_tracker] Erro ao enviar relatório final: {exc}")

    if not platform_managed:
        with get_connection() as connection:
            complete_task(connection, log_id, computer_name=COMPUTADOR_ROBO)
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
