"""Platform-level Oracle database operations.

Worker registration, heartbeat, atomic task claiming, and status updates.
All robot-specific queries stay inside each robot's own module.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import oracledb

from config import CLIENT_PATH, DSN_DB, SENHA_DB, USUARIO_DB


def init_oracle_client() -> None:
    if CLIENT_PATH:
        oracledb.init_oracle_client(lib_dir=CLIENT_PATH)


@contextmanager
def get_connection() -> Generator[oracledb.Connection, None, None]:
    conn = oracledb.connect(user=USUARIO_DB, password=SENHA_DB, dsn=DSN_DB)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Worker registry
# ---------------------------------------------------------------------------

def register_worker(conn: oracledb.Connection, computer_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            MERGE INTO U_ROBOT_WORKER t
            USING (SELECT :nome AS nome FROM DUAL) s
               ON (t.NOME_COMPUTADOR = s.nome)
             WHEN MATCHED THEN
                  UPDATE SET STATUS       = 'ONLINE',
                             DT_HEARTBEAT = SYSTIMESTAMP,
                             DT_INICIO    = SYSTIMESTAMP
             WHEN NOT MATCHED THEN
                  INSERT (NOME_COMPUTADOR, STATUS, DT_HEARTBEAT, DT_INICIO)
                  VALUES (s.nome, 'ONLINE', SYSTIMESTAMP, SYSTIMESTAMP)
            """,
            {"nome": computer_name},
        )
        conn.commit()


def heartbeat(conn: oracledb.Connection, computer_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE U_ROBOT_WORKER
               SET DT_HEARTBEAT = SYSTIMESTAMP,
                   STATUS       = 'ONLINE'
             WHERE NOME_COMPUTADOR = :nome
            """,
            {"nome": computer_name},
        )
        conn.commit()


def set_worker_offline(conn: oracledb.Connection, computer_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE U_ROBOT_WORKER SET STATUS = 'OFFLINE' WHERE NOME_COMPUTADOR = :nome",
            {"nome": computer_name},
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Task queue — claim is atomic via SELECT FOR UPDATE SKIP LOCKED
# Multiple workers can call this simultaneously without conflict.
# ---------------------------------------------------------------------------

def buscar_executando(conn: oracledb.Connection, computer_name: str) -> dict[str, Any] | None:
    """Return the robot currently EXECUTANDO on this machine, or None."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                u_log.U_ROBOT_LOG_ID,
                u_log.U_ROBOT_ID,
                u_log.STATUS,
                u.NOME,
                u.DESCRICAO,
                u.PRIORIDADE,
                u_log.DTINICIALIZACAO
            FROM U_ROBOT_LOG u_log
            INNER JOIN U_ROBOT u
                ON u.U_ROBOT_ID = u_log.U_ROBOT_ID
            WHERE u_log.STATUS = 'EXECUTANDO'
              AND u_log.COMPUTADOR = :comp
            """,
            {"comp": computer_name},
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [c[0].lower() for c in cur.description]
        return dict(zip(cols, row, strict=False))


def buscar_proximo_pendente(conn: oracledb.Connection, computer_name: str) -> dict[str, Any] | None:
    """Return the next PENDENTE robot in queue for this machine (read-only)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                u_log.U_ROBOT_LOG_ID,
                u_log.U_ROBOT_ID,
                u_log.STATUS,
                u.NOME,
                u.DESCRICAO,
                u.PRIORIDADE,
                u_log.DTINICIALIZACAO
            FROM U_ROBOT_LOG u_log
            INNER JOIN U_ROBOT u
                ON u.U_ROBOT_ID = u_log.U_ROBOT_ID
            WHERE u_log.STATUS = 'PENDENTE'
              AND u_log.COMPUTADOR = :comp
            ORDER BY u_log.DTINICIALIZACAO
            FETCH FIRST 1 ROW ONLY
            """,
            {"comp": computer_name},
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [c[0].lower() for c in cur.description]
        return dict(zip(cols, row, strict=False))


def claim_task(conn: oracledb.Connection, computer_name: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT U_ROBOT_LOG_ID, U_ROBOT_ID
              FROM U_ROBOT_LOG
             WHERE STATUS    = 'PENDENTE'
               AND COMPUTADOR = :comp
               AND ROWNUM    = 1
               FOR UPDATE SKIP LOCKED
            """,
            {"comp": computer_name},
        )
        row = cur.fetchone()

        if not row:
            return None

        log_id, robot_id = row

        cur.execute(
            """
            UPDATE U_ROBOT_LOG
               SET STATUS          = 'EXECUTANDO',
                   DTINICIALIZACAO = SYSTIMESTAMP
             WHERE U_ROBOT_LOG_ID  = :id
            """,
            {"id": log_id},
        )
        conn.commit()

    return {"log_id": int(log_id), "robot_id": int(robot_id)}


def complete_task(conn: oracledb.Connection, log_id: int, mensagem: str = "Executado com sucesso") -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE U_ROBOT_LOG
               SET STATUS        = 'SUCESSO',
                   DTFINALIZACAO = SYSTIMESTAMP,
                   MENSAGEM      = :msg
             WHERE U_ROBOT_LOG_ID = :id
            """,
            {"msg": mensagem[:4000], "id": log_id},
        )
        conn.commit()


def fail_task(conn: oracledb.Connection, log_id: int, mensagem: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE U_ROBOT_LOG
               SET STATUS        = 'ERRO',
                   DTFINALIZACAO = SYSTIMESTAMP,
                   MENSAGEM      = :msg
             WHERE U_ROBOT_LOG_ID = :id
            """,
            {"msg": mensagem[:4000], "id": log_id},
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Scheduler helpers — used by the orchestrator
# ---------------------------------------------------------------------------

def get_scheduled_robots(conn: oracledb.Connection) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT U_ROBOT_ID, NOME, INTERVALOMINUTOS, EXECMAXDIA,
                   EXECTODOSDIAS, DIAS, EXECNOVAMENTE
              FROM U_ROBOT
             WHERE ATIVO = 'S'
            """
        )
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]


def has_active_task(conn: oracledb.Connection, robot_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM U_ROBOT_LOG
             WHERE U_ROBOT_ID = :id
               AND STATUS IN ('PENDENTE', 'EXECUTANDO')
            """,
            {"id": robot_id},
        )
        return cur.fetchone()[0] > 0


def count_executions_today(conn: oracledb.Connection, robot_id: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM U_ROBOT_LOG
             WHERE U_ROBOT_ID = :id
               AND TRUNC(DTINCLUSAO) = TRUNC(SYSDATE)
               AND STATUS IN ('SUCESSO', 'EXECUTANDO', 'PENDENTE')
            """,
            {"id": robot_id},
        )
        return cur.fetchone()[0]


def get_last_success(conn: oracledb.Connection, robot_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT MAX(DTFINALIZACAO) FROM U_ROBOT_LOG
             WHERE U_ROBOT_ID = :id AND STATUS = 'SUCESSO'
            """,
            {"id": robot_id},
        )
        return cur.fetchone()[0]


def create_pending_task(conn: oracledb.Connection, robot_id: int) -> int:
    with conn.cursor() as cur:
        out_var = cur.var(oracledb.NUMBER)
        cur.execute(
            """
            INSERT INTO U_ROBOT_LOG (U_ROBOT_ID, STATUS, DTINCLUSAO)
            VALUES (:robot_id, 'PENDENTE', SYSTIMESTAMP)
            RETURNING U_ROBOT_LOG_ID INTO :log_id
            """,
            {"robot_id": robot_id, "log_id": out_var},
        )
        conn.commit()
        return int(out_var.getvalue()[0])
