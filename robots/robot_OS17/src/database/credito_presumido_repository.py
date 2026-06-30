from robots.robot_OS17.src.database.connection import get_connection
from robots.robot_OS17.src.database.queries import (
    QUERY_BUSCAR_PENDENTES,
    QUERY_MARCAR_CONCLUIDO,
    QUERY_MARCAR_EM_PROCESSAMENTO,
    QUERY_MARCAR_ERRO,
)


def normalizar_linha(cursor, linha: tuple) -> dict:
    """Converte os dados do database em dicionário."""
    colunas = [coluna[0].lower() for coluna in cursor.description]

    return dict(zip(colunas, linha))


def montar_parametros_chave(pedido: dict) -> dict:
    """Cria uma chave única para cada pedido."""
    return {
        "estab": str(pedido["estab"]).strip(),
        "ins_estad": str(pedido["ins_estad"]).strip(),
        "numerocm": str(pedido["numerocm"]).strip(),
        "ano": str(pedido["ano"]).strip(),
        "mes": str(pedido["mes"]).strip(),
    }


def buscar_pendentes() -> list[dict]:
    """Busca os itens com STATUS = 'PENDENTE'."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(QUERY_BUSCAR_PENDENTES)

        return [normalizar_linha(cursor, linha) for linha in cursor.fetchall()]


def marcar_em_processamento(pedido: dict) -> None:
    """Atualiza o STATUS para 'EM_PROCESSAMENTO'."""
    parametros = montar_parametros_chave(pedido)

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(QUERY_MARCAR_EM_PROCESSAMENTO, parametros)
        connection.commit()


def marcar_erro(pedido: dict) -> None:
    """Atualiza o STATUS para 'ERRO'."""
    parametros = montar_parametros_chave(pedido)

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(QUERY_MARCAR_ERRO, parametros)
        connection.commit()


def marcar_concluido(pedido: dict, nota: str, seqnota: str) -> None:
    """Atualiza o STATUS para 'CONCLUIDO'."""
    parametros = montar_parametros_chave(pedido)
    parametros.update(
        {
            "nota": str(nota).strip(),
            "seqnota": str(seqnota).strip(),
        }
    )

    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(QUERY_MARCAR_CONCLUIDO, parametros)
        connection.commit()
