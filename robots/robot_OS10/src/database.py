from __future__ import annotations

from typing import Any

import oracledb


def buscar_notas_pendentes(connection: oracledb.Connection) -> list[dict[str, Any]]:
    sql = """
        SELECT
            t.ESTAB,
            t.CNPJ,
            t.TOMADOR_CNPJ,
            t.REDUZIDO,
            t.SERIE,
            t.NUM_PED,
            t.PEDIDO,
            t.CONCEITO,
            t.FORNECEDOR,
            t.CNPJ_PED,
            t.CNPJF_FORNECEDOR,
            t.EMITENTE_CNPJ,
            t.IE_FORNECEDOR,
            t.COD_CONFIG,
            t.CONFIG,
            TO_CHAR(t.DTEMISSAO, 'DD/MM/YYYY') AS DTEMISSAO,
            t.VENCIMENTO,
            TO_CHAR(NVL(t.VALORTOTAL, 0), 'FM9999999990.00') AS VALORTOTAL,
            TO_CHAR(NVL(t.VALOR_TOTAL_NF, 0), 'FM9999999990.00') AS VALOR_TOTAL_NF,
            t.USERID,
            t.PLACA,
            t.DESCRICAO,
            t.TIPO_PROD,
            t.ERROCHAVENFE,
            t.REGRA_NOTACONF,
            t.CHAVCHAVENF,
            t.TIPOPGTO,
            t.CHAVEBOLETO,
            t.BANCO,
            t.AGENCIA,
            t.CONTA,
            t.PIX,
            t.NOTATERC,
            t.ARQUIVO_XML,
            TO_CHAR(NVL(t.DESC_INCOND, 0), 'FM9999999990.00') AS DESC_INCOND,
            TO_CHAR(NVL(t.DESC_COND, 0), 'FM9999999990.00') AS DESC_COND,
            TO_CHAR(NVL(t.VALOR_LIQUIDO, 0), 'FM9999999990.00') AS VALOR_LIQUIDO,
            TO_CHAR(NVL(t.VALOR_RETENCAO, 0), 'FM9999999990.00') AS VALOR_RETENCAO,
            TO_CHAR(NVL(t.PISBASE, 0), 'FM9999999990.00') AS PISBASE,
            TO_CHAR(NVL(t.COFINSBASE, 0), 'FM9999999990.00') AS COFINSBASE,
            TO_CHAR(NVL(t.ALIQPIS, 0), 'FM9999999990.00') AS ALIQPIS,
            TO_CHAR(NVL(t.ALIQCOFINS, 0), 'FM9999999990.00') AS ALIQCOFINS,
            TO_CHAR(NVL(t.VALOR_PIS, 0), 'FM9999999990.00') AS VALOR_PIS,
            TO_CHAR(NVL(t.VALOR_COFINS, 0), 'FM9999999990.00') AS VALOR_COFINS,
            TO_CHAR(NVL(t.VALOR_IRRF, 0), 'FM9999999990.00') AS VALOR_IRRF,
            TO_CHAR(NVL(t.VALOR_CSLL, 0), 'FM9999999990.00') AS VALOR_CSLL,
            TO_CHAR(NVL(t.VALOR_INSS, 0), 'FM9999999990.00') AS VALOR_INSS,
            TO_CHAR(NVL(t.BCISSQN, 0), 'FM9999999990.00') AS BCISSQN,
            TO_CHAR(NVL(t.ALIQISSQN, 0), 'FM9999999990.00') AS ALIQISSQN,
            TO_CHAR(NVL(t.VALOR_ISSQN, 0), 'FM9999999990.00') AS VALOR_ISSQN,
            t.RETPISCOFINS,
            t.RETISSQN,
            t.LOCALNF,
            t.NUMERO_NF,
            t.VAL_VALOR,
            t.VAL_CHAVE_BOLETO,
            t.VAL_RET_MES,
            t.VAL_CNPJ_DEST,
            t.VAL_CNPJ_FORNEC,
            t.VAL_SERVICO_ITEM,
            t.VAL_VENCIMENTO,
            t.SERVICO_CODIGO,
            t.ITEM_DESC,
            t.ITEM
        FROM OS_RPA_PEDIDOS_OS10 t
        WHERE t.CONCEITO = 'OK' 
        AND t.VAL_VALOR = 'OK'
        AND t.VAL_CHAVE_BOLETO = 'OK'
        AND t.VAL_RET_MES = 'OK'
        AND t.VAL_CNPJ_DEST = 'OK'
        AND t.VAL_CNPJ_FORNEC = 'OK'
        AND t.VAL_SERVICO_ITEM = 'OK'
        AND t.VAL_VENCIMENTO = 'OK'
        AND t.TIPOPGTO <> 'E'
        AND (
            NVL(t.VALOR_RETENCAO, 0) = 0
            OR (
                NVL(t.VALOR_RETENCAO, 0) <> 0
                AND t.RETPISCOFINS IS NOT NULL
            )
        )

        AND t.ESTAB <> '104'
        AND t.ESTAB <> '29'
        AND LENGTH(REGEXP_REPLACE(TRIM(t.CNPJF_FORNECEDOR),'[^0-9]','')) = 14  --OK somente se for CNPJ e não permite CPF (Solicitação da Julia)

        AND TO_DATE(t.VENCIMENTO, 'DD/MM/YYYY') <> TRUNC(SYSDATE) -- OK somente se o vencimento é diferente dia de hoje (Solicitação da Julia)

        --AND t.VALOR_RETENCAO = 0
         AND NUM_PED = 1040

        ORDER BY
            CASE
                WHEN NVL(t.VALOR_RETENCAO, 0) > 0 THEN 0
                ELSE 1
            END,
            TO_DATE(t.VENCIMENTO, 'DD/MM/YYYY') ASC NULLS LAST

 """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]

        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]


def buscar_estab_logado(connection: oracledb.Connection) -> int:
    """Fetch the active establishment logged for the robot user."""
    sql = """
        SELECT estab AS establogados
        FROM pmodulolicuso
        WHERE userid = 'RPA.OS10'
          AND status = 'A'

        UNION ALL

        SELECT 0 AS establogados
        FROM dual
        WHERE NOT EXISTS (
            SELECT 1
            FROM pmodulolicuso
            WHERE userid = 'RPA.OS10'
              AND status = 'A'
        )
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

        if not row:
            return 0

        return int(row[0])
 