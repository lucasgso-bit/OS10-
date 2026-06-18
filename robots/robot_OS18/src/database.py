"""Manage Oracle database access for the OS18 robot.

Create database connections and execute the initial robot queries.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-05-15
Version: 1.0.0
"""

from __future__ import annotations

from typing import Any

import oracledb

from config import CLIENT_PATH, DSN_DB, SENHA_DB, USUARIO_DB


def init_oracle_client() -> None:
    """Initialize the Oracle Instant Client."""
    if CLIENT_PATH:
        oracledb.init_oracle_client(lib_dir=CLIENT_PATH)


def get_connection() -> oracledb.Connection:
    return oracledb.connect(
        user=USUARIO_DB,
        password=SENHA_DB,
        dsn=DSN_DB,
    )


def update_robot_log_executando(
    connection: oracledb.Connection, computador: str
) -> int:
    """Update pending robot log records to executing status."""
    sql = """
        UPDATE U_ROBOT_LOG
           SET STATUS = 'EXECUTANDO'
         WHERE STATUS = 'PENDENTE'
           AND COMPUTADOR = :computador
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, {"computador": computador})
        affected_rows = cursor.rowcount

    connection.commit()
    return affected_rows


def buscar_notas_pendentes(connection: oracledb.Connection) -> list[dict[str, Any]]:
    """Fetch pending from Oracle."""
    sql = """
        SELECT *
        FROM (
            SELECT
                p.*,
                COUNT(*) OVER (PARTITION BY p.FORNECEDOR) AS qtd_fornecedor,
                ROW_NUMBER() OVER (ORDER BY p.DTVENCTO, p.FATURA) AS rn
            FROM PDUPPAGA p
            WHERE p.QUITADA = 'N'
            AND TRUNC(p.DTVENCTO) = TRUNC(SYSDATE)
            AND LENGTH(p.FATURA) = 11
            AND p.FATURA LIKE ('%2026%')
        )
        WHERE qtd_fornecedor > 1
        --AND rn BETWEEN 1 AND 4
        ORDER BY rn
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]

        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def buscar_estab_logado(connection: oracledb.Connection) -> int:
    sql = """
        SELECT estab AS establogados
        FROM pmodulolicuso
        WHERE userid = 'RPA.OS18'
          AND status = 'A'

        UNION ALL

        SELECT 0 AS establogados
        FROM dual
        WHERE NOT EXISTS (
            SELECT 1
            FROM pmodulolicuso
            WHERE userid = 'RPA.OS18'
              AND status = 'A'
        )
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

        if not row:
            return 0

        return int(row[0])
