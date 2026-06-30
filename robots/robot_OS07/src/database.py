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
  N.STATUS = 100
  AND C.CONCEITO <> 98
  AND (
        -- Antes das 23h: configuração principal (exige IEEMITENTE)
        (
            TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) < 23
            AND N.NOTACONF IN ('244', '255', '270', '275', '284', '314', '285')
            AND N.IEEMITENTE IS NOT NULL
           -- AND N.CHAVEACESSO = '31260620499489000103550010011483081234763795'
        )
        OR
        -- Antes das 23h: fallback 225/232 — só entra se a configuração principal não tiver nada
        (
            TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) < 23
            AND N.NOTACONF IN ('225', '232')
            AND NOT EXISTS (
                SELECT 1
                  FROM OS_RPA_NOTA_07 N2
                 INNER JOIN CONCEITOPESSOA C2 ON C2.NUMEROCM = N2.NUMEROCM
                 WHERE N2.STATUS     = 100
                   AND C2.CONCEITO  <> 98
                   AND N2.NOTACONF  IN ('244', '255', '270', '275', '284', '314', '285')
                   AND N2.IEEMITENTE IS NOT NULL
                   AND NOT EXISTS (
                         SELECT 1 FROM U_OS07_FILA F2
                          WHERE F2.CONT_ID     = N2.U_FISCAL_IO_CONT_ID
                            AND F2.DT_INCLUSAO >= TRUNC(SYSDATE)
                       )
            )
        )
        OR
        -- A partir das 23h: todas, incluindo 225 e 232
        (
            TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) >= 23
            AND N.NOTACONF IN ('225', '232', '244', '255', '270', '275', '284', '285', '314')
        )
      )
  AND NOT EXISTS (
        SELECT 1 FROM U_OS07_FILA F
         WHERE F.CONT_ID = N.U_FISCAL_IO_CONT_ID
           AND F.DT_INCLUSAO >= TRUNC(SYSDATE)
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


def buscar_notas_reclamadas(
    connection: oracledb.Connection, computador: str
) -> list[dict[str, Any]]:
    """Retorna os dados completos das notas reivindicadas por esta máquina hoje.

    Chamada após claim_next_batch() para obter o dict completo de cada nota
    necessário para o processamento (mesmas colunas de buscar_notas_pendentes).
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
        FROM U_OS07_FILA F
        INNER JOIN OS_RPA_NOTA_07 N ON N.U_FISCAL_IO_CONT_ID = F.CONT_ID
        WHERE F.USUARIO     = :comp
          AND F.STATUS      = 'PENDENTE'
          AND F.DT_INCLUSAO >= TRUNC(SYSDATE)
        ORDER BY F.POSICAO ASC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, {"comp": computador})
        assert cursor.description is not None
        columns = [col[0] for col in cursor.description]
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
