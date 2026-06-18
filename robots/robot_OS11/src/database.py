"""Manage Oracle database access for the OS11 robot.

Fetch establishments eligible for taxa de serviço processing.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import oracledb

from config import DSN_DB, SENHA_DB, USUARIO_DB

_BUSCAR_ESTABELECIMENTOS = """
    SELECT
        u_tempresa.estab
    FROM
        u_tempresa
        INNER JOIN filial
            ON filial.estab = u_tempresa.estab
        INNER JOIN cidade
            ON cidade.cidade = filial.cidade
    WHERE
        u_tempresa.graos = 'S'
        AND u_tempresa.ativo = 'S'
        AND u_tempresa.exvenda = 'N'
        AND cidade.uf = 'SP'
    GROUP BY
        u_tempresa.estab
    ORDER BY
        u_tempresa.estab
"""


def get_connection() -> oracledb.Connection:
    return oracledb.connect(
        user=USUARIO_DB,
        password=SENHA_DB,
        dsn=DSN_DB,
    )


def buscar_estabelecimentos(connection: oracledb.Connection) -> list:
    with connection.cursor() as cursor:
        cursor.execute(_BUSCAR_ESTABELECIMENTOS)
        return [row[0] for row in cursor.fetchall()]
