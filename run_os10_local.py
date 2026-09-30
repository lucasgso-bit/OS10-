"""Run OS10 manually without U_ROBOT_LOG."""

from __future__ import annotations

from core.database import get_connection, init_oracle_client
from robots.robot_OS10.run import Robot
from robots.robot_OS10.src.database import buscar_notas_pendentes


def main() -> None:
    """Run OS10 manually."""
    init_oracle_client()

    print("[OS10] Buscando notas pendentes pela query do OS10.")

    with get_connection() as conn:
        notas = buscar_notas_pendentes(conn)

    print(f"[OS10] Notas encontradas: {len(notas)}")

    if not notas:
        print("[OS10] Nenhuma nota pendente encontrada pela query.")
        return

    task = {
        "log_id": 0,
        "robot_id": 10,
        "manual": True,
        "notas": notas,
    }

    print("[OS10] Execução manual iniciada.")
    Robot(task).run()
    print("[OS10] Execução manual finalizada.")


if __name__ == "__main__":
    main()


