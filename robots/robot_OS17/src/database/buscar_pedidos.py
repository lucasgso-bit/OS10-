from robots.robot_OS17.src.database.credito_presumido_repository import buscar_pendentes


def buscar_pedidos_OS17() -> list[dict]:
    """Busca apenas os pendentes."""
    return buscar_pendentes()
