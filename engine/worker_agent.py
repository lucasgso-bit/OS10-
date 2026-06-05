"""Worker agent — runs on every machine.

On startup it registers itself in U_ROBOT_WORKER using the machine's real
hostname (no hardcoded computer name). It then loops:

  1. Send heartbeat to U_ROBOT_WORKER
  2. Try to claim one PENDENTE task via SELECT FOR UPDATE SKIP LOCKED
  3. If a task was claimed, load the matching robot module and call run()
  4. Mark the task SUCESSO or ERRO
  5. If no task was found, sleep and retry

Because the claim is atomic at the database level, four machines can call
this simultaneously and each will get a different task — no duplicates,
no coordination needed between machines.
"""

from __future__ import annotations

import importlib
import logging
import signal
import socket
import time

from core.database import (
    claim_task,
    complete_task,
    fail_task,
    get_connection,
    heartbeat,
    init_oracle_client,
    register_worker,
    set_worker_offline,
)

logger = logging.getLogger(__name__)

_SLEEP_IDLE = 30      # seconds to wait when queue is empty
_SLEEP_ERROR = 10     # seconds to wait after an unexpected error
_HEARTBEAT_EVERY = 30 # seconds between heartbeat updates


class WorkerAgent:
    def __init__(self) -> None:
        self.name = socket.gethostname()
        self._running = True
        self._last_heartbeat: float = 0.0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def start(self) -> None:
        init_oracle_client()

        with get_connection() as conn:
            register_worker(conn, self.name)

        logger.info("Worker '%s' online", self.name)

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        while self._running:
            try:
                self._cycle()
            except Exception:
                logger.exception("Unexpected error in worker cycle")
                time.sleep(_SLEEP_ERROR)

        self._go_offline()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _cycle(self) -> None:
        now = time.monotonic()

        with get_connection() as conn:
            if now - self._last_heartbeat >= _HEARTBEAT_EVERY:
                heartbeat(conn, self.name)
                self._last_heartbeat = now

            task = claim_task(conn, self.name)

        if not task:
            time.sleep(_SLEEP_IDLE)
            return

        self._execute(task)

    def _execute(self, task: dict) -> None:
        robot_id: int = task["robot_id"]
        log_id: int = task["log_id"]

        logger.info("Starting robot_id=%d log_id=%d", robot_id, log_id)

        try:
            module = importlib.import_module(f"robots.robot_{robot_id:03d}.run")
            robot = module.Robot(task)
            robot.run()

            with get_connection() as conn:
                complete_task(conn, log_id)

            logger.info("robot_id=%d log_id=%d finished OK", robot_id, log_id)

        except Exception as exc:
            logger.exception("robot_id=%d log_id=%d FAILED", robot_id, log_id)
            with get_connection() as conn:
                fail_task(conn, log_id, str(exc))

    def _go_offline(self) -> None:
        try:
            with get_connection() as conn:
                set_worker_offline(conn, self.name)
        except Exception:
            logger.warning("Could not set worker offline in database")
        logger.info("Worker '%s' offline", self.name)

    def _handle_shutdown(self, *_) -> None:
        logger.info("Shutdown signal received")
        self._running = False
