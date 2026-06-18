"""Robot OS07-specific Oracle queries.

All platform-level operations (connections, task queue, worker registry)
live in core.database. This module contains only the queries that are
exclusive to the OS07 robot.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-18
Version: 2.1.0
"""

from __future__ import annotations

from typing import Any

import oracledb


def buscar_notas_pendentes(connection: oracledb.Connection) -> list[dict[str, Any]]:
    """Fetch pending OS07 records not already claimed in today's queue.

    Notes already present in U_OS07_FILA today (regardless of machine) are
    excluded so two machines never pick up the same note.
    """
    sql = """
        SELECT
  N.U_FISCAL_IO_CONT_ID,
  N.CHAVEACESSO,
  N.DTEMISS,
  N.NUMERONOTA,
  N.SERIE,
  N.CNPJF,
  N.IEEMITENTE,
  N.ESTAB,
  N.CFOP,
  N.PLACA,
  N.NCM,
  N.ITEM,
  N.QUANTIDADE,
  N.UNIDADETRIBUTAVEL,
  N.VALORTOTAL,
  N.ORDEMCARGA,
  N.LOCALESTOQUE,
  N.CONTRATO,
  N.PRODUTOR,
  N.STATUS,
  N.MENSAGEMERRO,
  N.DTPROCESSAMENTO,
  N.REPROCESSADO,
  N.SEQENDERECO,
  N.DIFVIASOFT,
  N.DIFAPP,
  N.ESTABCONTRATO,
  N.VALIDANCM,
  N.NOTACONF,
  N.TIPOBAIXA,
  N.CONTCONF,
  N.STATUS_NOTA,
  N.NOTAFILHA,
  N.CLASSIF_LOCAL,
  N.NUMEROCM,
  N.DTEMISSAO,
  N.DATA_EMISSAO
FROM OS_RPA_NOTA_07 N
INNER JOIN CONCEITOPESSOA C
    ON C.NUMEROCM = N.NUMEROCM
WHERE
  -- N.STATUS = 100
  C.CONCEITO <> 98
  AND (
        (
            TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) < 23
            AND N.NOTACONF IN ('255', '275', '284', '314', '244', '270', '285')
            AND N.IEEMITENTE IS NOT NULL
        )
        OR
        (
            TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) >= 23
            AND N.NOTACONF IN ('225', '232', '255', '275', '284', '314', '244', '270', '285')
        )
      )
  AND NOT EXISTS (
        SELECT 1 FROM U_OS07_FILA F
         WHERE F.CONT_ID = N.U_FISCAL_IO_CONT_ID
           AND TRUNC(F.DT_INCLUSAO) = TRUNC(SYSDATE)
      )
ORDER BY
  N.DTVENCTO_CTR,
  N.DATA_EMISSAO,
  N.NOTACONF ASC
FETCH FIRST 10 ROWS ONLY """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]

        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def buscar_estab_logado(connection: oracledb.Connection) -> int:
    """Fetch the active establishment logged for the robot user."""
    sql = """
        SELECT estab AS establogados
        FROM pmodulolicuso
        WHERE userid = 'RPA.OS071'
          AND status = 'A'

        UNION ALL

        SELECT 0 AS establogados
        FROM dual
        WHERE NOT EXISTS (
            SELECT 1
            FROM pmodulolicuso
            WHERE userid = 'RPA.OS071'
              AND status = 'A'
        )
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

        if not row:
            return 0

        return int(row[0])
