from robots.robot_OS17.src.database.connection import get_connection
from robots.robot_OS17.src.database.queries import QUERY_CANDIDATOS_CREDITO


QUERY_INSERIR_CONTROLE = """
INSERT INTO U_CREDITO_PRESUMIDO (
    ESTAB,
    IE,
    NUMEROCM,
    STATUS,
    ANO,
    MES,
    VALOR
)
SELECT
    :estab,
    :ins_estad,
    :numerocm,
    'PENDENTE',
    :ano,
    :mes,
    :credito_resumo
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1
    FROM U_CREDITO_PRESUMIDO T
    WHERE T.ESTAB = :estab
      AND T.IE = :ins_estad
      AND T.NUMEROCM = :numerocm
      AND T.ANO = :ano
      AND T.MES = :mes
)
"""


def normalizar_linha(cursor, linha: tuple) -> dict:
    """Convert a database row into a dictionary."""
    colunas = [coluna[0].lower() for coluna in cursor.description]

    return dict(zip(colunas, linha))


def carregar_pendentes_iniciais() -> int:
    """Insert new pending records into the OS-17 control table."""
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(QUERY_CANDIDATOS_CREDITO)
        candidatos = [
            normalizar_linha(cursor, linha)
            for linha in cursor.fetchall()
        ]

        total_inseridos = 0

        for candidato in candidatos:
            cursor.execute(
                QUERY_INSERIR_CONTROLE,
                {
                    "estab": str(candidato["estab"]).strip(),
                    "ins_estad": str(candidato["ins_estad"]).strip(),
                    "numerocm": str(candidato["numerocm"]).strip(),
                    "ano": str(candidato["ano"]).strip(),
                    "mes": str(candidato["mes"]).strip(),
                    "credito_resumo": candidato["credito_resumo"],
                },
            )

            total_inseridos += cursor.rowcount

        connection.commit()

        return total_inseridos
