"""Robot OS20-specific Oracle queries.

All platform-level operations (connections, task queue, worker registry)
live in core.database. This module contains only the queries and DDL that are
exclusive to the OS20 robot.

Developed by: MATHEUS CORREA
Updated by: MATHEUS CORREA
Last Modified: 2026-06-16
Version: 3.0.0
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Any

import oracledb


@contextmanager
def get_os20_connection():
    """Yield a robot-specific Oracle connection for OS20."""
    conn = oracledb.connect(
        user=os.environ["USUARIO_DB"],
        password=os.environ["SENHA_DB"],
        dsn=os.environ["DSN_DB"],
    )
    try:
        yield conn
    finally:
        conn.close()


def buscar_lotes_completos(conn: oracledb.Connection) -> set[int]:
    """Return the set of CODIGO_LOTE already marked 100% complete."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT CODIGO_LOTE FROM U_TICKETLOG_LOTES_STATUS
            WHERE LOTE_COMPLETO = 'S'
        """)
        return {int(row[0]) for row in cur.fetchall()}  # type: ignore[misc]


def buscar_chaves_lote(conn: oracledb.Connection, codigo_lote: int) -> set[str]:
    """Return the set of CHAVE_ACESSO already imported for a given lot."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT CHAVE_ACESSO FROM U_TICKETLOG_NOTAS_LOTE
            WHERE CODIGO_LOTE = :codigo_lote
              AND CHAVE_ACESSO IS NOT NULL
        """,
            {"codigo_lote": codigo_lote},
        )
        return {row[0] for row in cur.fetchall()}  # type: ignore[misc]


def upsert_status_lote(
    conn: oracledb.Connection,
    codigo_lote: int,
    percentual: Decimal,
    completo: bool,
) -> None:
    """Insert or update the completion status of a lot."""
    with conn.cursor() as cur:
        cur.execute(
            """
            MERGE INTO U_TICKETLOG_LOTES_STATUS t
            USING (SELECT :lote_id AS CODIGO_LOTE FROM DUAL) s
            ON (t.CODIGO_LOTE = s.CODIGO_LOTE)
            WHEN MATCHED THEN UPDATE SET
                PERCENTUAL_RECEBIDO = :percentual,
                LOTE_COMPLETO       = :completo,
                DATA_VERIFICACAO    = SYSDATE
            WHEN NOT MATCHED THEN INSERT (
                CODIGO_LOTE, PERCENTUAL_RECEBIDO, LOTE_COMPLETO, DATA_VERIFICACAO
            ) VALUES (
                :lote_id, :percentual, :completo, SYSDATE
            )
        """,
            {
                "lote_id": codigo_lote,
                "percentual": float(percentual),
                "completo": "S" if completo else "N",
            },
        )


def inserir_nota(
    conn: oracledb.Connection,
    *,
    codigo_lote: int | str,
    codigo_estabelecimento: int | str,
    estabelecimento: str,
    tipo_nota: str,
    nota: dict[str, Any],
    valor_total_lote: Decimal,
    valor_recebido_lote: Decimal,
    percentual_recebido: Decimal,
) -> int:
    """Insert a Ticket Log note header and return the generated ID."""
    with conn.cursor() as cur:
        out_id = cur.var(int)
        cur.execute(
            """
            INSERT INTO U_TICKETLOG_NOTAS_LOTE (
                CODIGO_LOTE,
                CODIGO_ESTABELECIMENTO,
                ESTABELECIMENTO,
                TIPO_NOTA,
                NUMERO_NOTA,
                SERIE,
                CHAVE_ACESSO,
                NATUREZA_OPERACAO,
                RAZAO_SOCIAL,
                CNPJ,
                INSCRICAO_ESTADUAL,
                DATA_EMISSAO,
                VALOR_BASE_ICMS,
                VALOR_ICMS,
                VALOR_BASE_ICMS_ST,
                VALOR_ICMS_ST,
                VALOR_FRETE,
                VALOR_SEGURO,
                VALOR_DESCONTO,
                VALOR_OUTRAS_DESPESAS,
                VALOR_IPI,
                VALOR_TOTAL_PRODUTOS,
                VALOR_TOTAL_NOTA,
                VALOR_TOTAL_LOTE,
                VALOR_RECEBIDO_LOTE,
                PERCENTUAL_RECEBIDO,
                STATUS,
                DATA_IMPORTACAO,
                JSON_NOTA
            ) VALUES (
                :codigo_lote,
                :codigo_estabelecimento,
                :estabelecimento,
                :tipo_nota,
                :numero_nota,
                :serie,
                :chave_acesso,
                :natureza_operacao,
                :razao_social,
                :cnpj,
                :inscricao_estadual,
                :data_emissao,
                :valor_base_icms,
                :valor_icms,
                :valor_base_icms_st,
                :valor_icms_st,
                :valor_frete,
                :valor_seguro,
                :valor_desconto,
                :valor_outras_despesas,
                :valor_ipi,
                :valor_total_produtos,
                :valor_total_nota,
                :valor_total_lote,
                :valor_recebido_lote,
                :percentual_recebido,
                'PENDENTE',
                SYSDATE,
                :json_nota
            ) RETURNING ID INTO :out_id
            """,
            {
                "codigo_lote": int(codigo_lote),
                "codigo_estabelecimento": int(codigo_estabelecimento),
                "estabelecimento": estabelecimento,
                "tipo_nota": tipo_nota,
                "numero_nota": str(nota.get("numero") or ""),
                "serie": str(nota.get("serie") or ""),
                "chave_acesso": nota.get("chaveAcesso"),
                "natureza_operacao": nota.get("naturezaOperacao"),
                "razao_social": nota.get("razaoSocial"),
                "cnpj": nota.get("cnpj"),
                "inscricao_estadual": nota.get("inscricaoEstadual"),
                "data_emissao": nota.get("dataEmissao"),
                "valor_base_icms": _to_float_or_none(nota.get("valorBaseCalculoIcms")),
                "valor_icms": _to_float_or_none(nota.get("valorIcms")),
                "valor_base_icms_st": _to_float_or_none(
                    nota.get("valorBaseCalculoIcmsSubstituto")
                ),
                "valor_icms_st": _to_float_or_none(nota.get("valorIcmsSubstituto")),
                "valor_frete": _to_float_or_none(nota.get("valorFrete")),
                "valor_seguro": _to_float_or_none(nota.get("valorSeguro")),
                "valor_desconto": _to_float_or_none(nota.get("valorDesconto")),
                "valor_outras_despesas": _to_float_or_none(
                    nota.get("valorOutrasDespesasAcessorias")
                ),
                "valor_ipi": _to_float_or_none(nota.get("valorIpi")),
                "valor_total_produtos": _to_float_or_none(
                    nota.get("valorTotalProdutos")
                ),
                "valor_total_nota": _to_float_or_none(nota.get("valorTotalNota")),
                "valor_total_lote": float(valor_total_lote),
                "valor_recebido_lote": float(valor_recebido_lote),
                "percentual_recebido": float(percentual_recebido),
                "json_nota": json.dumps(nota, ensure_ascii=False),
                "out_id": out_id,
            },
        )
        val = out_id.getvalue()
        return int(val[0] if isinstance(val, list) else val)  # type: ignore[index]


def inserir_itens_nota(
    conn: oracledb.Connection,
    nota_id: int,
    itens: list[dict[str, Any]],
    *,
    codigo_lote: int,
    codigo_estabelecimento: int,
    chave_acesso: str | None,
    numero_nota: str | None,
) -> None:
    """Insert all items from a nota into U_TICKETLOG_ITENS_NOTA."""
    if not itens:
        return
    with conn.cursor() as cur:
        rows = [
            {
                "nota_id": nota_id,
                "codigo_lote": codigo_lote,
                "codigo_estabelecimento": codigo_estabelecimento,
                "chave_acesso": chave_acesso,
                "numero_nota": numero_nota,
                "produto": item.get("produto"),
                "ncm": str(item.get("codigoNcm") or "").strip(),
                "cfop": str(item.get("codigoCfop") or "").strip(),
                "unidade": str(item.get("unidade") or "").strip(),
                "quantidade": _to_float_or_none(item.get("quantidade")),
                "valor_unitario": _to_float_or_none(item.get("valorUnitario")),
                "valor_liquido": _to_float_or_none(item.get("valorLiquido")),
                "base_icms": _to_float_or_none(item.get("valorBaseCalculoIcms")),
                "valor_icms": _to_float_or_none(item.get("valorIcms")),
                "cst_icms": str(item.get("codigoCstIcms") or "").strip(),
                "cst_pis": str(item.get("codigoCstPis") or "").strip(),
                "cst_cofins": str(item.get("codigoCstCofins") or "").strip(),
            }
            for item in itens
        ]
        cur.executemany(
            """
            INSERT INTO U_TICKETLOG_ITENS_NOTA (
                NOTA_ID, CODIGO_LOTE, CODIGO_ESTABELECIMENTO,
                CHAVE_ACESSO, NUMERO_NOTA,
                PRODUTO, NCM, CFOP, UNIDADE,
                QUANTIDADE, VALOR_UNITARIO, VALOR_LIQUIDO,
                BASE_ICMS, VALOR_ICMS,
                CST_ICMS, CST_PIS, CST_COFINS
            ) VALUES (
                :nota_id, :codigo_lote, :codigo_estabelecimento,
                :chave_acesso, :numero_nota,
                :produto, :ncm, :cfop, :unidade,
                :quantidade, :valor_unitario, :valor_liquido,
                :base_icms, :valor_icms,
                :cst_icms, :cst_pis, :cst_cofins
            )
            """,
            rows,
        )


def _converter_decimal(valor: Any) -> Decimal:
    """Convert API numeric values to Decimal."""
    if valor is None:
        return Decimal("0")
    texto = str(valor).strip()
    if not texto:
        return Decimal("0")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return Decimal(texto)


def _to_float_or_none(valor: Any) -> float | None:
    """Return float for a numeric API value, or None if absent/empty."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return float(_converter_decimal(valor))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Phase 1 — Agro note launching queries
# ---------------------------------------------------------------------------


def buscar_notas_para_lancar(conn: oracledb.Connection) -> list[dict[str, Any]]:
    """Return all pending TicketLog notes not yet launched in Agro.

    Uses STATUS_VALIDADO (checked against NFCAB) to filter out notes already
    posted. Results are ordered CODIGO_LOTE ASC so the first batch is processed
    first. Multiple rows per NUMERO_NOTA are expected when a note has items with
    different NCM codes — group by NUMERO_NOTA + SERIE on the caller side.
    """
    sql = """
WITH UTL_PENDENTES AS (
    SELECT
        UTL.CODIGO_LOTE,
        UTL.NUMERO_NOTA,
        UTL.SERIE,
        UTL.CHAVE_ACESSO,
        UTL.STATUS,
        UTL.CNPJ,
        UTL.INSCRICAO_ESTADUAL,
        TRIM(UTL.CHAVE_ACESSO) AS CHAVE,
        REGEXP_REPLACE(TRIM(UTL.CNPJ), '[^0-9]', '') AS CNPJ_UTL,
        REGEXP_REPLACE(UPPER(TRIM(UTL.INSCRICAO_ESTADUAL)), '[^0-9A-Z]', '') AS IE_NORMALIZADA
    FROM U_TICKETLOG_NOTAS_LOTE UTL
    WHERE TRIM(UPPER(UTL.STATUS)) = 'PENDENTE'
),
 
MAPA_ITEM AS (
    SELECT 27101259 AS NCM, 77606 AS ITEM, 1653 AS CFOP_DENTRO_UF, 2653 AS CFOP_FORA_UF FROM DUAL
    UNION ALL
    SELECT 27101921 AS NCM, 77607 AS ITEM, 1653 AS CFOP_DENTRO_UF, 2653 AS CFOP_FORA_UF FROM DUAL
    UNION ALL
    SELECT 22071090 AS NCM, 77608 AS ITEM, 1653 AS CFOP_DENTRO_UF, 2653 AS CFOP_FORA_UF FROM DUAL
    UNION ALL
    SELECT 31021010 AS NCM, 77609 AS ITEM, 1556 AS CFOP_DENTRO_UF, 2556 AS CFOP_FORA_UF FROM DUAL
),
 
NOTASSIEG AS (
    SELECT
        TRIM(N.CHAVEACESSONFE) AS CHAVE,
        MAX(N.DTEMISSAO) AS DATA_EMISSAO,
        MAX(REGEXP_REPLACE(TRIM(N.CNPJ_TOMADOR), '[^0-9]', '')) AS CNPJ_SIEG
    FROM U_NOTASSIEG N
    WHERE EXISTS (
        SELECT 1
          FROM UTL_PENDENTES UTL
         WHERE UTL.CHAVE = TRIM(N.CHAVEACESSONFE)
    )
    GROUP BY
        TRIM(N.CHAVEACESSONFE)
),
 
SIEG_ITENS AS (
    SELECT
        TRIM(SI.CHAVE) AS CHAVE,
        SI.NCM,
        ROUND(SI.VLRUNITARIO, 4) AS VALOR_UNITARIO,
        SUM(SI.QUANTIDADE) AS QUANTIDADE_CORRETA
    FROM U_NOTASSIEG_ITENS SI
    WHERE EXISTS (
        SELECT 1
          FROM UTL_PENDENTES UTL
         WHERE UTL.CHAVE = TRIM(SI.CHAVE)
    )
    GROUP BY
        TRIM(SI.CHAVE),
        SI.NCM,
        ROUND(SI.VLRUNITARIO, 4)
),
 
TICKETLOG_ITEM_REF AS (
    SELECT
        TIR.CODIGO_LOTE,
        TRIM(TIR.CHAVE_ACESSO) AS CHAVE,
        TIR.NUMERO_NOTA,
        TIR.NCM,
        ROUND(TIR.VALOR_UNITARIO, 4) AS VALOR_UNITARIO
    FROM U_TICKETLOG_ITENS_NOTA TIR
    WHERE EXISTS (
        SELECT 1
          FROM UTL_PENDENTES UTL
         WHERE UTL.CODIGO_LOTE = TIR.CODIGO_LOTE
           AND UTL.CHAVE = TRIM(TIR.CHAVE_ACESSO)
           AND UTL.NUMERO_NOTA = TIR.NUMERO_NOTA
    )
    GROUP BY
        TIR.CODIGO_LOTE,
        TRIM(TIR.CHAVE_ACESSO),
        TIR.NUMERO_NOTA,
        TIR.NCM,
        ROUND(TIR.VALOR_UNITARIO, 4)
),
 
IE_CONTAMOV AS (
    SELECT
        X.IE_NORMALIZADA,
        MIN(X.NUMEROCM) AS NUMEROCM
    FROM (
        SELECT
            REGEXP_REPLACE(UPPER(TRIM(C.INSCESTAD)), '[^0-9A-Z]', '') AS IE_NORMALIZADA,
            C.NUMEROCM
        FROM CONTAMOV C
        WHERE C.INSCESTAD IS NOT NULL
    ) X
    WHERE X.IE_NORMALIZADA IS NOT NULL
      AND EXISTS (
          SELECT 1
            FROM UTL_PENDENTES UTL
           WHERE UTL.IE_NORMALIZADA = X.IE_NORMALIZADA
      )
    GROUP BY
        X.IE_NORMALIZADA
),
 
IE_ENDERECO AS (
    SELECT
        X.IE_NORMALIZADA,
        MIN(X.NUMEROCM) AS NUMEROCM
    FROM (
        SELECT
            REGEXP_REPLACE(UPPER(TRIM(E.CREDENCIALAGRO)), '[^0-9A-Z]', '') AS IE_NORMALIZADA,
            E.NUMEROCM
        FROM ENDERECO E
        WHERE E.CREDENCIALAGRO IS NOT NULL
    ) X
    WHERE X.IE_NORMALIZADA IS NOT NULL
      AND EXISTS (
          SELECT 1
            FROM UTL_PENDENTES UTL
           WHERE UTL.IE_NORMALIZADA = X.IE_NORMALIZADA
      )
    GROUP BY
        X.IE_NORMALIZADA
),
 
FILIAL_NORMALIZADA AS (
    SELECT
        REGEXP_REPLACE(TRIM(F.CNPJ), '[^0-9]', '') AS CNPJ_NORMALIZADO,
        MIN(F.ESTAB) AS ESTAB,
        MIN(F.CIDADE) AS CIDADE
    FROM FILIAL F
    WHERE F.CNPJ IS NOT NULL
    GROUP BY
        REGEXP_REPLACE(TRIM(F.CNPJ), '[^0-9]', '')
),
 
BASE AS (
    SELECT
        UTL.CODIGO_LOTE,
        CONTAMOV.NUMEROCM,
        TIR.NCM,
        MAPA_ITEM.ITEM,
        ITEMAGRO.DESCRICAO,
        UTL.NUMERO_NOTA,
        UTL.SERIE,
        NOTASSIEG.DATA_EMISSAO,
        SI.QUANTIDADE_CORRETA AS QUANTIDADE,
        TIR.VALOR_UNITARIO,
        UTL.CHAVE_ACESSO,
 
        COALESCE(FILIAL_UTL.ESTAB, FILIAL_SIEG.ESTAB) AS ESTAB,
 
        CIDADE_FILIAL.UF AS UF_ESTAB,
        CIDADE_CLIENTE.UF AS UF_CLIENTE,
 
        CASE
            WHEN TRIM(UPPER(CIDADE_FILIAL.UF)) = TRIM(UPPER(CIDADE_CLIENTE.UF))
                THEN MAPA_ITEM.CFOP_DENTRO_UF
            ELSE MAPA_ITEM.CFOP_FORA_UF
        END AS CFOP,
 
        162 AS NOTACONF,
 
        CASE
            WHEN EXISTS (
                SELECT 1
                  FROM NFCAB NF
                 WHERE NF.ESTAB = COALESCE(FILIAL_UTL.ESTAB, FILIAL_SIEG.ESTAB)
                   AND NF.NUMEROCM = CONTAMOV.NUMEROCM
                   AND NF.NOTA = UTL.NUMERO_NOTA
                   AND TRIM(NF.SERIE) = TRIM(UTL.SERIE)
            ) THEN 'LANCADA'
            ELSE 'PENDENTE'
        END AS STATUS_VALIDADO
 
    FROM UTL_PENDENTES UTL
 
    INNER JOIN TICKETLOG_ITEM_REF TIR
            ON TIR.CODIGO_LOTE = UTL.CODIGO_LOTE
           AND TIR.CHAVE = UTL.CHAVE
           AND TIR.NUMERO_NOTA = UTL.NUMERO_NOTA
 
    INNER JOIN SIEG_ITENS SI
            ON SI.CHAVE = UTL.CHAVE
           AND SI.NCM = TIR.NCM
           AND SI.VALOR_UNITARIO = TIR.VALOR_UNITARIO
 
    INNER JOIN MAPA_ITEM
            ON MAPA_ITEM.NCM = TIR.NCM
 
    INNER JOIN ITEMAGRO
            ON ITEMAGRO.ITEM = MAPA_ITEM.ITEM
 
    LEFT JOIN NOTASSIEG
            ON NOTASSIEG.CHAVE = UTL.CHAVE
 
    LEFT JOIN IE_CONTAMOV
            ON IE_CONTAMOV.IE_NORMALIZADA = UTL.IE_NORMALIZADA
 
    LEFT JOIN IE_ENDERECO
            ON IE_CONTAMOV.NUMEROCM IS NULL
           AND IE_ENDERECO.IE_NORMALIZADA = UTL.IE_NORMALIZADA
 
    INNER JOIN CONTAMOV
            ON CONTAMOV.NUMEROCM = COALESCE(IE_CONTAMOV.NUMEROCM, IE_ENDERECO.NUMEROCM)
 
    LEFT JOIN FILIAL_NORMALIZADA FILIAL_UTL
            ON FILIAL_UTL.CNPJ_NORMALIZADO = UTL.CNPJ_UTL
 
    LEFT JOIN FILIAL_NORMALIZADA FILIAL_SIEG
            ON FILIAL_UTL.ESTAB IS NULL
           AND FILIAL_SIEG.CNPJ_NORMALIZADO = NOTASSIEG.CNPJ_SIEG
 
    INNER JOIN CIDADE CIDADE_FILIAL
            ON CIDADE_FILIAL.CIDADE = COALESCE(FILIAL_UTL.CIDADE, FILIAL_SIEG.CIDADE)
 
    INNER JOIN CIDADE CIDADE_CLIENTE
            ON CIDADE_CLIENTE.CIDADE = CONTAMOV.CIDADE
 
    WHERE COALESCE(FILIAL_UTL.ESTAB, FILIAL_SIEG.ESTAB) IS NOT NULL
 
      AND EXISTS (
          SELECT 1
            FROM CONCEITOPESSOA CP
           WHERE CP.NUMEROCM = CONTAMOV.NUMEROCM
             AND CP.CONCEITO <> 98
      )
)
 
SELECT
    BASE.CODIGO_LOTE,
    BASE.NUMEROCM,
    BASE.NCM,
    BASE.ITEM,
    BASE.DESCRICAO,
    BASE.NUMERO_NOTA,
    BASE.SERIE,
    BASE.DATA_EMISSAO,
    TRUNC(SUM(BASE.QUANTIDADE), 4) AS QUANTIDADE,
    BASE.VALOR_UNITARIO,
    ROUND(TRUNC(SUM(BASE.QUANTIDADE), 4) * BASE.VALOR_UNITARIO, 3) AS VALOR_TOTAL,
    BASE.CHAVE_ACESSO,
    BASE.ESTAB,
    BASE.UF_ESTAB,
    BASE.UF_CLIENTE,
    BASE.CFOP,
    BASE.NOTACONF,
    'PENDENTE' AS STATUS
FROM BASE
WHERE BASE.STATUS_VALIDADO = 'PENDENTE'
GROUP BY
    BASE.CODIGO_LOTE,
    BASE.NUMEROCM,
    BASE.NCM,
    BASE.ITEM,
    BASE.DESCRICAO,
    BASE.NUMERO_NOTA,
    BASE.SERIE,
    BASE.DATA_EMISSAO,
    BASE.CHAVE_ACESSO,
    BASE.ESTAB,
    BASE.UF_ESTAB,
    BASE.UF_CLIENTE,
    BASE.CFOP,
    BASE.NOTACONF,
    BASE.VALOR_UNITARIO
ORDER BY
    BASE.ESTAB ASC,
    BASE.CODIGO_LOTE ASC,
    BASE.NUMERO_NOTA ASC,
    BASE.ITEM ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


def marcar_nota_lancada(
    conn: oracledb.Connection,
    numero_nota: str,
    serie: str,
    codigo_lote: int,
) -> None:
    """Mark a note as LANCADA in U_TICKETLOG_NOTAS_LOTE after posting in Agro."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE U_TICKETLOG_NOTAS_LOTE
               SET STATUS = 'LANCADA'
             WHERE NUMERO_NOTA  = :num
               AND TRIM(SERIE)  = TRIM(:serie)
               AND CODIGO_LOTE  = :lote
               AND STATUS       = 'PENDENTE'
            """,
            {"num": numero_nota, "serie": serie, "lote": codigo_lote},
        )
    conn.commit()


def tem_notas_pendentes(conn: oracledb.Connection) -> bool:
    """Return True if at least one note with STATUS = 'PENDENTE' exists."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM DUAL WHERE EXISTS "
            "(SELECT 1 FROM U_TICKETLOG_NOTAS_LOTE WHERE STATUS = 'PENDENTE')"
        )
        return cur.fetchone() is not None


def atualizar_notas_lancadas_diferente(conn: oracledb.Connection) -> int:
    """Mark as LANCADO DIFERENTE RPA.OS02 notes already in NFCAB but still PENDENTE.

    These notes exist in NFCAB but were not launched by this RPA — launched
    manually or by another process. Must run before buscar_notas_para_lancar
    so they are excluded from the launch queue.
    """
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE U_TICKETLOG_NOTAS_LOTE UTL
               SET UTL.STATUS = 'LANCADO DIFERENTE RPA.OS02'
             WHERE UTL.STATUS = 'PENDENTE'
               AND EXISTS (
                   SELECT 1
                     FROM NFCAB NF
                    INNER JOIN CONTAMOV C ON C.INSCESTAD = UTL.INSCRICAO_ESTADUAL
                    WHERE NF.NUMEROCM = C.NUMEROCM
                      AND NF.NOTA     = UTL.NUMERO_NOTA
                      AND TRIM(NF.SERIE) = TRIM(UTL.SERIE)
               )
        """)
        updated = cur.rowcount
    conn.commit()
    return updated
