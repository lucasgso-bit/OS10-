"""
Generic RPA Agent — deploy the same file on every machine.
Configure AGENT_ID via environment variable or .env file.

Each agent polls for ANY PENDENTE job using SELECT FOR UPDATE SKIP LOCKED
so two agents never claim the same job.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import oracledb

# =============================================================
# CONFIGURATION
# =============================================================

AGENT_ID      = int(os.getenv("AGENT_ID", "1"))          # set on each machine
PYTHON_EXEC   = os.getenv("PYTHON_EXEC", sys.executable)
BASE_DIR      = Path(__file__).resolve().parent

USUARIO_DB    = os.getenv("DB_USER",   "OS_VX")
SENHA_DB      = os.getenv("DB_PASS",   "8@*M-*Y.yAfFuo_kLK8E")
DSN_DB        = os.getenv("DB_DSN",    "10.200.0.231:1521/prod.db.ocilan.oraclevcn.com")
CLIENT_PATH   = os.getenv("DB_CLIENT", r"C:\instantclient_23_0")

POLL_INTERVAL          = 5    # seconds between polls when idle
HEARTBEAT_INTERVAL     = 30   # seconds between heartbeat updates
CANCEL_CHECK_INTERVAL  = 10   # seconds between cancellation checks
TIMEOUT_MINUTES        = 60   # mark as TIMEOUT if heartbeat is this old

# =============================================================
# ROBOT DISPATCH
# Add new robots here — no other code changes needed.
# =============================================================

ROBOTS: dict[int, Path] = {
    4: BASE_DIR / "AutomationEdge" / "OS11_COBSERVICO_30.py",
    6: BASE_DIR / "AutomationEdge" / "OS13_COBSERVICO_31.py",
    7: BASE_DIR / "AutomationEdge" / "OS14_NOTA_DE_ACERTO.py",
    8: BASE_DIR / "AutomationEdge" / "OS15_CARTA_CORRECAO.py",
    # OS07 — fiscal notes robot
    9: BASE_DIR / "OS07_255" / "main.py",
}

# =============================================================
# LOGGING
# =============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | AGENT-%(agent_id)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

class _AgentFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.agent_id = AGENT_ID
        return True

for handler in logging.root.handlers:
    handler.addFilter(_AgentFilter())

log = logging.getLogger(__name__)

# =============================================================
# DATABASE
# =============================================================

def _get_conn() -> oracledb.Connection:
    oracledb.init_oracle_client(lib_dir=CLIENT_PATH)
    return oracledb.connect(user=USUARIO_DB, password=SENHA_DB, dsn=DSN_DB)


def _claim_next_job(conn: oracledb.Connection) -> tuple[int, int] | None:
    """
    Atomically claim the oldest PENDENTE job.

    Uses SELECT FOR UPDATE SKIP LOCKED so two agents running in parallel
    can never pick the same row — Oracle skips rows already locked by
    another agent and returns the next available one.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT u_log.u_robot_log_id, u_log.u_robot_id
            FROM   u_robot_log u_log
            WHERE  u_log.status = 'PENDENTE'
            ORDER  BY u_log.dtinicializacao
            FETCH  FIRST 1 ROW ONLY
            FOR UPDATE SKIP LOCKED
        """)
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return None

        log_id, robot_id = row

        cur.execute("""
            UPDATE u_robot_log
            SET    status       = 'EXECUTANDO',
                   computador   = :agent_id,
                   dt_inicio    = SYSDATE,
                   dt_heartbeat = SYSDATE
            WHERE  u_robot_log_id = :log_id
        """, agent_id=AGENT_ID, log_id=log_id)
        conn.commit()
        return log_id, robot_id


def _store_pid(conn: oracledb.Connection, log_id: int, pid: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE u_robot_log SET pid = :pid WHERE u_robot_log_id = :log_id",
            pid=pid, log_id=log_id,
        )
        conn.commit()


def _send_heartbeat(conn: oracledb.Connection, log_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE u_robot_log SET dt_heartbeat = SYSDATE WHERE u_robot_log_id = :log_id",
            log_id=log_id,
        )
        conn.commit()


def _check_status(conn: oracledb.Connection, log_id: int) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM u_robot_log WHERE u_robot_log_id = :log_id",
            log_id=log_id,
        )
        row = cur.fetchone()
        return row[0] if row else "DESCONHECIDO"


def _finish_job(conn: oracledb.Connection, log_id: int, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE u_robot_log
            SET    status  = :status,
                   dt_fim  = SYSDATE,
                   pid     = NULL
            WHERE  u_robot_log_id = :log_id
        """, status=status, log_id=log_id)
        conn.commit()


def _mark_stale_timeouts(conn: oracledb.Connection) -> None:
    """Mark EXECUTANDO jobs with an old heartbeat as TIMEOUT."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE u_robot_log
            SET    status = 'TIMEOUT', dt_fim = SYSDATE
            WHERE  status        = 'EXECUTANDO'
            AND    computador    = :agent_id
            AND    dt_heartbeat  < SYSDATE - INTERVAL ':mins' MINUTE
        """.replace(":mins", str(TIMEOUT_MINUTES)), agent_id=AGENT_ID)
        if cur.rowcount:
            log.warning("Marcou %d job(s) como TIMEOUT.", cur.rowcount)
        conn.commit()


# =============================================================
# EXECUTION
# =============================================================

def _run_robot(log_id: int, robot_id: int) -> None:
    """
    Spawn the robot script as a subprocess, then:
      - update PID in DB
      - send heartbeat every HEARTBEAT_INTERVAL seconds
      - check for CANCELADO every CANCEL_CHECK_INTERVAL seconds
      - kill process if CANCELADO
      - update final status when done
    """
    script = ROBOTS.get(robot_id)
    if not script or not script.exists():
        log.error("Script não encontrado para robot_id=%s", robot_id)
        conn = _get_conn()
        try:
            _finish_job(conn, log_id, "ERRO")
        finally:
            conn.close()
        return

    log.info("Iniciando robot_id=%s | script=%s", robot_id, script)

    conn = _get_conn()
    process = subprocess.Popen([PYTHON_EXEC, str(script)])
    _store_pid(conn, log_id, process.pid)
    log.info("PID=%s", process.pid)

    cancelled = threading.Event()
    finished  = threading.Event()

    # ---------- heartbeat thread ----------
    def heartbeat_loop() -> None:
        while not finished.wait(HEARTBEAT_INTERVAL):
            try:
                _send_heartbeat(conn, log_id)
            except Exception as exc:
                log.warning("Heartbeat falhou: %s", exc)

    # ---------- cancel-check thread ----------
    def cancel_loop() -> None:
        while not finished.wait(CANCEL_CHECK_INTERVAL):
            try:
                status = _check_status(conn, log_id)
            except Exception:
                continue
            if status == "CANCELADO":
                log.info("Cancelamento solicitado. Encerrando PID=%s...", process.pid)
                process.terminate()
                time.sleep(3)
                if process.poll() is None:
                    process.kill()
                cancelled.set()
                break

    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    cc_thread = threading.Thread(target=cancel_loop,    daemon=True)
    hb_thread.start()
    cc_thread.start()

    try:
        process.wait()
    finally:
        finished.set()
        hb_thread.join(timeout=5)
        cc_thread.join(timeout=5)

    if cancelled.is_set():
        final_status = "CANCELADO"
    elif process.returncode == 0:
        final_status = "CONCLUIDO"
    else:
        log.error("Robot terminou com código %s", process.returncode)
        final_status = "ERRO"

    try:
        _finish_job(conn, log_id, final_status)
    finally:
        conn.close()

    log.info("Job %s finalizado como %s.", log_id, final_status)


# =============================================================
# MAIN LOOP
# =============================================================

def main() -> None:
    log.info("Agente iniciado | AGENT_ID=%s", AGENT_ID)

    while True:
        try:
            conn = _get_conn()
            try:
                _mark_stale_timeouts(conn)
                job = _claim_next_job(conn)
            finally:
                conn.close()

            if job is None:
                time.sleep(POLL_INTERVAL)
                continue

            log_id, robot_id = job
            log.info("Job %s capturado | robot_id=%s", log_id, robot_id)
            _run_robot(log_id, robot_id)

        except Exception as exc:
            log.exception("Erro no loop principal: %s", exc)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
