"""Manage Oracle database access for the WNota 255 robot.

Create database connections and execute the initial robot queries.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from __future__ import annotations

from typing import Any

import oracledb

from config import CLIENT_PATH, COMPUTADOR_ROBO, DSN_DB, SENHA_DB, USUARIO_DB

ROBOT_ID = 11


def init_oracle_client() -> None:
    """Initialize the Oracle Instant Client."""
    if CLIENT_PATH:
        oracledb.init_oracle_client(lib_dir=CLIENT_PATH)


def get_connection() -> oracledb.Connection:
    """Create an Oracle database connection."""
    return oracledb.connect(
        user=USUARIO_DB,
        password=SENHA_DB,
        dsn=DSN_DB,
    )


def buscar_notas_pendentes(connection: oracledb.Connection) -> list[dict[str, Any]]:
    """Fetch pending WNota 255 records from Oracle."""
    sql = """
        SELECT
  OS_RPA_NOTA_07.U_FISCAL_IO_CONT_ID,
  OS_RPA_NOTA_07.CHAVEACESSO,
  OS_RPA_NOTA_07.DTEMISS,
  OS_RPA_NOTA_07.NUMERONOTA,
  OS_RPA_NOTA_07.SERIE,
  OS_RPA_NOTA_07.CNPJF,
  OS_RPA_NOTA_07.IEEMITENTE,
  OS_RPA_NOTA_07.ESTAB,
  OS_RPA_NOTA_07.CFOP,
  OS_RPA_NOTA_07.PLACA,
  OS_RPA_NOTA_07.NCM,
  OS_RPA_NOTA_07.ITEM,
  OS_RPA_NOTA_07.QUANTIDADE,
  OS_RPA_NOTA_07.UNIDADETRIBUTAVEL,
  OS_RPA_NOTA_07.VALORTOTAL,
  OS_RPA_NOTA_07.ORDEMCARGA,
  OS_RPA_NOTA_07.LOCALESTOQUE,
  OS_RPA_NOTA_07.CONTRATO,
  OS_RPA_NOTA_07.PRODUTOR,
  OS_RPA_NOTA_07.STATUS,
  OS_RPA_NOTA_07.MENSAGEMERRO,
  OS_RPA_NOTA_07.DTPROCESSAMENTO,
  OS_RPA_NOTA_07.REPROCESSADO,
  OS_RPA_NOTA_07.SEQENDERECO,
  OS_RPA_NOTA_07.DIFVIASOFT,
  OS_RPA_NOTA_07.DIFAPP,
  OS_RPA_NOTA_07.ESTABCONTRATO,
  OS_RPA_NOTA_07.VALIDANCM,
  OS_RPA_NOTA_07.NOTACONF,
  OS_RPA_NOTA_07.TIPOBAIXA,
  OS_RPA_NOTA_07.CONTCONF,
  OS_RPA_NOTA_07.STATUS_NOTA,
  OS_RPA_NOTA_07.NOTAFILHA,
  OS_RPA_NOTA_07.CLASSIF_LOCAL,
  OS_RPA_NOTA_07.NUMEROCM,
  OS_RPA_NOTA_07.DTEMISSAO,
  DATA_EMISSAO
FROM OS_RPA_NOTA_07
INNER JOIN CONCEITOPESSOA
    ON CONCEITOPESSOA.NUMEROCM = OS_RPA_NOTA_07.NUMEROCM
WHERE OS_RPA_NOTA_07.STATUS = 100
  AND CONCEITOPESSOA.CONCEITO <> 98
  AND (
        (
           -- estab <> 67 and
            TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) < 21
           -- and notaconf in ('255','270','232','314', '275', '285', '284')
            AND   notaconf in ('225','232')
            and ieemitente is not null
           -- and chaveacesso ='35260608032953000143550010000004221860859264'
        )
        OR
        (
            TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) >= 23 
            and notaconf in ('225','232') 
        )
      )
ORDER BY
  DTVENCTO_CTR,
  DATA_EMISSAO,
  OS_RPA_NOTA_07.NOTACONF ASC """

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


def buscar_U_ROBOT_LOG_EXECUCAO(cursor: Any) -> tuple[Any, ...] | None:
    """Retorna um robô que esteja EXECUTANDO no computador informado."""
    cursor.execute(
        """
        SELECT
            u_log.u_robot_log_id,
            u_log.u_robot_id,
            u_log.status,
            u.nome,
            u.descricao,
            u.prioridade,
            u_log.dtinicializacao
        FROM u_robot_log u_log
        INNER JOIN u_robot u
            ON u.u_robot_id = u_log.u_robot_id
        WHERE u_log.status = 'EXECUTANDO'
          AND u_log.computador = :comp
        """,
        {"comp": COMPUTADOR_ROBO},
    )
    return cursor.fetchone()


def buscar_U_ROBOT_NEXT(cursor: Any) -> tuple[Any, ...] | None:
    """Retorna o primeiro robô PENDENTE da fila (somente leitura)."""
    cursor.execute(
        """
        SELECT
            u_log.u_robot_log_id,
            u_log.u_robot_id,
            u_log.status,
            u.nome,
            u.descricao,
            u.prioridade,
            u_log.dtinicializacao
        FROM u_robot_log u_log
        INNER JOIN u_robot u
            ON u.u_robot_id = u_log.u_robot_id
        WHERE u_log.status = 'PENDENTE'
          -- AND u_log.computador = :comp
        ORDER BY u_log.dtinicializacao
        FETCH FIRST 1 ROW ONLY
        """,
        #  {"comp": COMPUTADOR_ROBO},
    )
    return cursor.fetchone()


def marcar_executando(connection: oracledb.Connection, log_id: int) -> None:
    """Muda o status da tarefa de PENDENTE para EXECUTANDO."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE u_robot_log
               SET status          = 'EXECUTANDO',
                   COMPUTADOR       = :comp,
                   dtinicializacao = SYSTIMESTAMP
             WHERE u_robot_log_id  = :id
               AND status          = 'PENDENTE'
            """,
            {"id": log_id, "comp": COMPUTADOR_ROBO},
        )
        connection.commit()
