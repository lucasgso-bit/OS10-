"""Start the WNota 255 robot.

Initialize dependencies and execute the first robot workflow stage.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from src.database import init_oracle_client


from src.workflow import run


def main() -> None:
    """Run the robot entry point."""
    init_oracle_client()
    run()


if __name__ == "__main__":
    main()
