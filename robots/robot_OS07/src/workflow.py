"""Run the initial WNota 255 workflow steps.

Update robot execution status, search pending notes, and open Agro when needed.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-18
Version: 3.0.0
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
from robots.robot_OS07.src.database import buscar_notas_pendentes, buscar_notas_reclamadas
from robots.robot_OS07.src.nota_router import process_note_by_config
from robots.robot_OS07.src.queue_tracker import (
    claim_next_batch,
    enviar_relatorio_final,
    limpar_fila,
    limpar_fila_pos_execucao,
    marcar_concluido,
    marcar_erro,
    popular_fila,
)
from robots.robot_OS07.src.replacement_estab import (
    switch_establishment,
    wait_window_startswith,
)

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

    Fluxo multi-máquina sem race condition:
      1. limpar_fila()      — libera notas presas de crash desta máquina de volta ao pool.
      2. buscar_notas_pendentes() — busca candidatos na tabela fonte (exclui notas já no pool hoje).
      3. popular_fila()     — insere candidatos no pool compartilhado (USUARIO='OS07_FILA').
      4. claim_next_batch() — reivindica atomicamente N notas com FOR UPDATE SKIP LOCKED.
      5. buscar_notas_reclamadas() — retorna dados completos das notas desta máquina.

    FOR UPDATE SKIP LOCKED garante que dois robôs nunca processem a mesma nota,
    mesmo consultando simultaneamente.

    When log_id is provided (called by the platform worker), task claiming and
    completion are handled by the worker. When log_id is None (legacy main.py
    path), this function claims and completes its own task.
    """
    platform_managed = log_id is not None

    if not platform_managed:
        with get_connection() as connection:
            executando = buscar_executando(connection, COMPUTADOR_ROBO)
            if executando:
                print(
                    f"Robô já em execução (log_id={executando['u_robot_log_id']}). Pulando ciclo."
                )
                return

            proximo = buscar_proximo_pendente(connection, COMPUTADOR_ROBO)
            if not proximo:
                print("Nenhuma tarefa pendente na fila.")
                return

            log_id = proximo["u_robot_log_id"]
            marcar_executando(connection, log_id, COMPUTADOR_ROBO)
            print(f"Tarefa log_id={log_id} marcada como EXECUTANDO.")

    print("\n Buscando notas OS07...")

    # Passo 1: libera notas presas de crash de volta ao pool e busca novos candidatos
    try:
        with get_connection() as connection:
            limpar_fila(connection, COMPUTADOR_ROBO)
            candidatos = buscar_notas_pendentes(connection)

        with get_connection() as connection:
            popular_fila(connection, candidatos, COMPUTADOR_ROBO)
    except Exception as exc:
        print(f"[queue_tracker] Erro ao popular fila (não bloqueia execução): {exc}")

    # Passo 2: reivindica atomicamente as notas para esta máquina (FOR UPDATE SKIP LOCKED)
    # Garante que dois robôs nunca processem a mesma nota, mesmo que consultem ao mesmo tempo.
    with get_connection() as connection:
        claimed = claim_next_batch(connection, COMPUTADOR_ROBO)

    if not claimed:
        print("Nenhuma nota disponível no pool para este robô.")
        if not platform_managed:
            with get_connection() as connection:
                complete_task(connection, log_id, computer_name=COMPUTADOR_ROBO)
            print(f"Tarefa log_id={log_id} marcada como CONCLUIDO.")
        return

    # Passo 3: busca os dados completos das notas reivindicadas por esta máquina
    with get_connection() as connection:
        notas = buscar_notas_reclamadas(connection, COMPUTADOR_ROBO)

    print(f"Notas encontradas 07: {len(notas)}")

    if _esta_interrompido():
        print(f"Robô interrompido externamente (log_id={log_id}). Abortando antes de abrir o Agro.")
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

    for nota in notas:
        if _esta_interrompido():
            print(f"Robô interrompido externamente (log_id={log_id}). Parando processamento.")
            return

        id_nota = nota.get("U_FISCAL_IO_CONT_ID")
        try:
            estab_nota = int(nota["ESTAB"])

            print(f"\n-> Processando nota ID: {id_nota} | Estab: {estab_nota}")

            switched = switch_establishment(estab_nota)
            if not switched:
                msg_err = f"Tela de seleção de estabelecimento não apareceu (nota {id_nota}). Agro reiniciado."
                print(msg_err)
                with get_connection() as connection:
                    marcar_erro(connection, id_nota, COMPUTADOR_ROBO, msg_err)
                _reiniciar_agro()
                continue

            print("Troca de estabelecimento realizada.")

            processed = process_note_by_config(nota)

            if processed:
                print("Nota processada com sucesso")
                try:
                    with get_connection() as connection:
                        marcar_concluido(connection, id_nota, COMPUTADOR_ROBO)
                except Exception as exc:
                    print(f"[queue_tracker] marcar_concluido falhou: {exc}")
            else:
                print("Falha ao processar nota")
                try:
                    with get_connection() as connection:
                        marcar_erro(
                            connection, id_nota, COMPUTADOR_ROBO, "Falha no processamento (sem exceção)"
                        )
                except Exception as exc:
                    print(f"[queue_tracker] marcar_erro falhou: {exc}")

        except Exception as e:
            print(f"Erro na nota {id_nota}: {e}")
            try:
                with get_connection() as connection:
                    marcar_erro(connection, id_nota, COMPUTADOR_ROBO, str(e))
            except Exception as exc:
                print(f"[queue_tracker] marcar_erro falhou: {exc}")

    # Envia relatório final com totais desta máquina hoje
    try:
        with get_connection() as connection:
            enviar_relatorio_final(connection, COMPUTADOR_ROBO)
    except Exception as exc:
        print(f"[queue_tracker] Erro ao enviar relatório final: {exc}")

    # Remove todas as linhas da fila após o relatório ser enviado
    try:
        with get_connection() as connection:
            limpar_fila_pos_execucao(connection, COMPUTADOR_ROBO)
    except Exception as exc:
        print(f"[queue_tracker] Erro ao limpar fila pós-execução: {exc}")

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
