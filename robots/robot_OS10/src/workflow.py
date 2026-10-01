from __future__ import annotations

import time
from typing import Any

from config import AGRO_EXE, COMPUTADOR_ROBO
from core.database import complete_task, fail_task, get_connection

from .agro_alerts import (
    confirm_attention_popup,
    confirm_establishment_selection,
)
from .agro_app import kill_agro_process, start_agro
from .agro_estab import wait_window_startswith
from .agro_login import login_agro
from .database import buscar_notas_pendentes
from .lancamento import executar_lancamento

AGRO_PROCESS_NAME = "Agro3C.exe"
AGRO_MAIN_TITLE = "AGRO-"

START_DELAY_SECONDS = 5


def run_once(
    log_id: int,
    task: dict[str, Any] | None = None,
) -> None:
    """Run one OS10 execution cycle."""

    task_data = task or {"log_id": log_id}
    manual = bool(task_data.get("manual"))

    try:
        _run_body(
            log_id=log_id,
            task=task_data,
        )

        if not manual:
            with get_connection() as conn:
                complete_task(
                    conn,
                    log_id,
                    "Execução concluída.",
                    computer_name=COMPUTADOR_ROBO,
                )

            print(f"[OS10] U_ROBOT_LOG {log_id} -> CONCLUIDO")

        else:
            print("[OS10] Execução manual concluída. " "U_ROBOT_LOG não atualizado.")

    except Exception as exc:
        if not manual:
            with get_connection() as conn:
                fail_task(
                    conn,
                    log_id,
                    f"Erro: {str(exc)[:3990]}",
                )

            print(f"[OS10] U_ROBOT_LOG {log_id} -> ERRO")

        else:
            print("[OS10] Execução manual com erro. " "U_ROBOT_LOG não atualizado.")

        raise


def _run_body(
    log_id: int,
    task: dict[str, Any],
) -> None:
    """Run OS10 process."""

    print(f"[OS10] Iniciando execução | " f"log_id={log_id}")

    notas = _obter_notas(task)

    if not notas:
        print("[OS10] Nenhuma nota encontrada para processar.")
        return

    print(f"[OS10] Total de notas: {len(notas)}")

    _executar_lancamento(
        notas=notas,
        task=task,
        log_id=log_id,
    )

    print("[OS10] Execução finalizada com sucesso.")


def _obter_notas(
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    """Use supplied notes or fetch pending OS10 notes from the database."""

    notas = task.get("notas")

    if isinstance(notas, list):
        return notas

    print("[OS10] Buscando notas pendentes pela query do OS10.")

    with get_connection() as conn:
        return buscar_notas_pendentes(conn)


def _executar_lancamento(
    notas: list[dict[str, Any]],
    task: dict[str, Any],
    log_id: int,
) -> None:
    """Open Agro test environment and launch notes."""

    print("[OS10] Abrindo Agro teste para lançamento | " f"notas={len(notas)}")

    try:
        _abrir_sistema(
            exe_path=AGRO_EXE,
            process_name=AGRO_PROCESS_NAME,
            main_title=AGRO_MAIN_TITLE,
        )

        executar_lancamento(
            notas=notas,
            task=task,
            log_id=log_id,
        )

    finally:
        # kill_agro_process(
        #     AGRO_PROCESS_NAME
        # )

        print("[OS10] Agro teste encerrado.")


def _abrir_sistema(
    exe_path: str,
    process_name: str,
    main_title: str,
) -> None:
    """Open Agro, login, and validate the main screen."""

    print(f"[OS10] Abrindo sistema: {exe_path}")

    # ============================================
    # GARANTE QUE NÃO EXISTE AGRO ANTIGO ABERTO
    # ============================================

    print("[OS10] Encerrando possíveis processos " "anteriores do Agro.")

    kill_agro_process(process_name)

    time.sleep(1)

    # ============================================
    # ABRE O AGRO
    # ============================================

    print("[OS10] Inicializando Agro.")

    start_agro(exe_path)

    print(f"[OS10] Aguardando {START_DELAY_SECONDS}s " "para inicialização inicial.")

    time.sleep(START_DELAY_SECONDS)

    # ============================================
    # LOGIN
    # ============================================

    print("[OS10] Executando login.")

    login_agro()

    print("[OS10] Login executado.")

    # ============================================
    # TRATA TELAS INTERMEDIÁRIAS
    # ============================================

    print("[OS10] Verificando tela Atenção.")

    confirm_attention_popup()

    print("[OS10] Verificando seleção de estabelecimento.")

    confirm_establishment_selection()

    # ============================================
    # PRIMEIRA TENTATIVA
    # ============================================

    print("[OS10] Aguardando tela principal do Agro | " f"prefixo={main_title}")

    encontrou_agro = wait_window_startswith(
        main_title,
        timeout_seconds=30,
    )

    # ============================================
    # SEGUNDA TENTATIVA
    # ============================================

    if not encontrou_agro:
        print("[OS10] Tela principal ainda não apareceu.")

        print("[OS10] Verificando novamente possíveis " "telas intermediárias.")

        confirm_attention_popup()

        confirm_establishment_selection()

        print("[OS10] Aguardando novamente a tela " "principal do Agro.")

        encontrou_agro = wait_window_startswith(
            main_title,
            timeout_seconds=30,
        )

    # ============================================
    # VALIDA RESULTADO
    # ============================================

    if not encontrou_agro:
        raise RuntimeError(
            f"Tela {main_title} não abriu após login " "em até 60 segundos."
        )

    print("[OS10] Sistema aberto com sucesso | " f"prefixo={main_title}")
