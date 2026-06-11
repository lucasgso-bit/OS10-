"""Robot OS16-specific Oracle queries.

All platform-level operations (connections, task queue, worker registry)
live in core.database. This module contains only the queries that are
exclusive to the OS16 robot.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-08
Version: 1.0.0
"""

from __future__ import annotations

from typing import Any

import oracledb


def buscar_notas_pendentes(connection: oracledb.Connection) -> list[dict[str, Any]]:
    """Fetch pending OS16 records from Oracle."""
    sql = """
        SELECT DISTINCT NFCAB.ESTAB  
        FROM NFCAB  
        INNER JOIN NFITEM ON NFITEM.ESTAB = NFCAB.ESTAB AND NFITEM.SEQNOTA = NFCAB.SEQNOTA  
        INNER JOIN U_TEMPRESA ON U_TEMPRESA.ESTAB = NFCAB.ESTAB  
            AND U_TEMPRESA.GRAOS = 'S'  
            AND U_TEMPRESA.EXVENDA = 'S'  
            AND U_TEMPRESA.ATIVO = 'S'  
        INNER JOIN CONTAMOV ON CONTAMOV.NUMEROCM = NFCAB.NUMEROCM  
        INNER JOIN FILIAL ON FILIAL.ESTAB = NFCAB.ESTAB  
        INNER JOIN NFCFG ON NFCFG.NOTACONF = NFCAB.NOTACONF  
        INNER JOIN CONTRATONFITE ON CONTRATONFITE.ESTAB = NFCAB.ESTAB  
            AND CONTRATONFITE.SEQNOTA = NFCAB.SEQNOTA  
        LEFT JOIN NFCFGESTAB ON NFCFGESTAB.ESTAB = NFCAB.ESTAB  
            AND NFCFGESTAB.NOTACONF = NFCAB.NOTACONF  
            AND NFCFGESTAB.SEQ = NFCAB.SEQ_NFCFGESTAB  
        LEFT JOIN NFCABSERIE ON NFCFGESTAB.ESTAB = NFCABSERIE.ESTAB  
            AND NFCFGESTAB.SERIE = NFCABSERIE.SERIE  
        WHERE NFCAB.DTEMISSAO >= TO_DATE('01/01/2026','DD/MM/YYYY')  
        AND NFCAB.NPROTAUTORIZA IS NULL  
        AND NFCAB.STATUS <> 'C'  
        AND NFCFG.EMITENFE = 'S'  
        AND NFCAB.NOTACONF IN (209,210,211,229,230,241,303,342,343,394)  
        ORDER BY NFCAB.ESTAB """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]

        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def buscar_estab_logado(connection: oracledb.Connection) -> int:
    """Fetch the active establishment logged for the robot user."""
    sql = """
        SELECT estab AS establogados
        FROM pmodulolicuso
        WHERE userid = 'RPA.OS161'
          AND status = 'A'

        UNION ALL

        SELECT 0 AS establogados
        FROM dual
        WHERE NOT EXISTS (
            SELECT 1
            FROM pmodulolicuso
            WHERE userid = 'RPA.OS161'
              AND status = 'A'
        )
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

        if not row:
            return 0

        return int(row[0])
