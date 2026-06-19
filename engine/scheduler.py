"""Orchestrator — runs on one machine (or any machine, idempotently).

Reads U_ROBOT every minute and creates PENDENTE entries in U_ROBOT_LOG
when a robot is due to run. Workers pick those entries up automatically.

Scheduling rules (all must pass):
  - ATIVO = 'S'
  - No PENDENTE or EXECUTANDO task already exists for this robot
  - EXECMAXDIA not exceeded today (0 = unlimited)
  - Day of week is in DIAS (ignored when EXECTODOSDIAS = 'S')
  - INTERVALOMINUTOS elapsed since last successful run (0 = run immediately)

Multi-machine robots (EXECNOVAMENTE = 'S'):
  One PENDENTE task is created per online worker that does not already have
  this robot running. OS07 is the primary example: multiple machines process
  notes in parallel, each with its own isolated queue.

Idle monitoring:
  Workers that have not sent a heartbeat for 30+ minutes are marked OFFLINE
  and an alert email is sent to the operations team.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from core.database import (
    cleanup_zombie_tasks,
    count_executions_today,
    create_pending_task,
    create_pending_task_computador,
    get_connection,
    get_last_success,
    get_online_workers,
    get_scheduled_robots,
    get_workers_heartbeat_vencido,
    has_active_task,
    has_active_task_no_computador,
    init_oracle_client,
    marcar_worker_offline_stale,
)
from core.mailer import enviar_alerta_maquinas_paradas

logger = logging.getLogger(__name__)

_CYCLE_INTERVAL = 60        # seconds between scheduler sweeps
_IDLE_ALERT_MINUTES = 30    # minutes without heartbeat before alert


_WEEKDAY_MAP = {
    0: "SEG",
    1: "TER",
    2: "QUA",
    3: "QUI",
    4: "SEX",
    5: "SAB",
    6: "DOM",
}


class Orchestrator:
    def start(self) -> None:
        init_oracle_client()
        logger.info("Orchestrator started")

        while True:
            try:
                self._cycle()
            except Exception:
                logger.exception("Orchestrator cycle error")
            time.sleep(_CYCLE_INTERVAL)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _cycle(self) -> None:
        with get_connection() as conn:
            # 1. Clean up tasks whose worker process died.
            cleaned = cleanup_zombie_tasks(conn, minutos=_IDLE_ALERT_MINUTES)
            if cleaned:
                logger.warning("Zombie tasks encerrados automaticamente: %d", cleaned)

            # 2. Alert and mark OFFLINE workers with stale heartbeats.
            self._check_workers_idle(conn)

            # 3. Schedule pending robots.
            robots = get_scheduled_robots(conn)
            for robot in robots:
                try:
                    if robot.get("EXECNOVAMENTE") == "S":
                        self._schedule_multimachine(robot, conn)
                    elif self._should_schedule(robot, conn):
                        task_id = create_pending_task(conn, robot["U_ROBOT_ID"])
                        logger.info(
                            "Task created: robot='%s' (id=%d) log_id=%d",
                            robot["NOME"],
                            robot["U_ROBOT_ID"],
                            task_id,
                        )
                except Exception:
                    logger.exception("Error evaluating robot '%s'", robot.get("NOME"))

    def _check_workers_idle(self, conn) -> None:
        """Alert and offline workers that have stopped sending heartbeats."""
        stale = get_workers_heartbeat_vencido(conn, minutos=_IDLE_ALERT_MINUTES)
        if not stale:
            return

        maquinas = [w["nome_computador"] for w in stale]
        logger.warning("Workers com heartbeat vencido: %s", maquinas)

        enviar_alerta_maquinas_paradas(maquinas)

        for w in stale:
            marcar_worker_offline_stale(conn, w["nome_computador"])

    def _schedule_multimachine(self, robot: dict, conn) -> None:
        """Create one PENDENTE task per online worker that isn't already running this robot.

        Used for robots marked with EXECNOVAMENTE='S' (e.g. OS07) that are
        allowed — and expected — to run simultaneously on several machines.
        """
        robot_id: int = robot["U_ROBOT_ID"]

        if not self._passes_day_filter(robot):
            return

        max_per_day: int = robot.get("EXECMAXDIA") or 0
        if max_per_day > 0 and count_executions_today(conn, robot_id) >= max_per_day:
            return

        for worker in get_online_workers(conn):
            computador: str = worker["nome_computador"]
            if not has_active_task_no_computador(conn, robot_id, computador):
                task_id = create_pending_task_computador(conn, robot_id, computador)
                logger.info(
                    "Multi-machine task: robot='%s' (id=%d) computador='%s' log_id=%d",
                    robot["NOME"],
                    robot_id,
                    computador,
                    task_id,
                )

    def _should_schedule(self, robot: dict, conn) -> bool:
        robot_id: int = robot["U_ROBOT_ID"]

        if has_active_task(conn, robot_id):
            return False

        max_per_day: int = robot.get("EXECMAXDIA") or 0
        if max_per_day > 0 and count_executions_today(conn, robot_id) >= max_per_day:
            return False

        if not self._passes_day_filter(robot):
            return False

        interval_min: int = robot.get("INTERVALOMINUTOS") or 0
        if interval_min > 0:
            last_run = get_last_success(conn, robot_id)
            if last_run is not None:
                elapsed = (datetime.now() - last_run.replace(tzinfo=None)).total_seconds() / 60
                if elapsed < interval_min:
                    return False

        return True

    @staticmethod
    def _passes_day_filter(robot: dict) -> bool:
        if robot.get("EXECTODOSDIAS") == "S":
            return True
        allowed_days = [d.strip() for d in (robot.get("DIAS") or "").split(",")]
        today = _WEEKDAY_MAP[datetime.now().weekday()]
        return today in allowed_days
