from robots.robot_OS14.src.database.connection import get_connection


def buscar_pedidos_OS14() -> list[dict]:
    sql = """
WITH base AS (
  SELECT
    t.CNPJ,
    t.ESTAB,
    t.NUM_PED,
    t.FORNECEDOR,
    t.CNPJF_FORNECEDOR,
    t.IE_FORNECEDOR,
    t.DTEMISSAO,
    TO_CHAR(TO_DATE(t.DTEMISSAO, 'DD/MM/YYYY'), 'DDMMYY') AS DTEMISSAO_ROBO,
    t.CHAVCHAVENF,
    t.REGRA_NOTACONF,
    t.TIPOPGTO,
    t.CHAVEBOLETO,
    t.BANCO,
    t.VALORTOTAL,
    REGEXP_REPLACE(t.AGENCIA, '[^0-9]', '') AS AGENCIA,
    REGEXP_REPLACE(t.CONTA, '[^0-9]', '') AS CONTA,
    t.PIX,

    CASE
      WHEN INSTR(t.CONFIG, '-') > 0
      THEN SUBSTR(t.CONFIG, 1, INSTR(t.CONFIG, '-') - 1)
      ELSE t.CONFIG
    END AS config_split,

    CASE
      WHEN INSTR(t.PEDIDO, '-') > 0
      THEN SUBSTR(t.PEDIDO, INSTR(t.PEDIDO, '-') + 1)
      ELSE t.PEDIDO
    END AS pedido_split,

    TO_DATE(t.VENCIMENTO, 'DD/MM/YYYY') AS venc_dt

  FROM OS_RPA_PEDIDOS_OS14 t
  WHERE t.TIPOPGTO <> 'ERRO'
),

b AS (
  SELECT
    base.*,

    CASE
      WHEN base.config_split = '799' THEN '01'
      WHEN base.config_split = '67' THEN '06'
      WHEN base.config_split IN ('27', '44', '37', '41') THEN '02'
      WHEN base.config_split IN ('800', '825') THEN '03'
      WHEN base.config_split = '502' THEN '04'
      ELSE 'PRODUTO_INEXISTENTE'
    END AS CENARIO,

    CASE
      WHEN base.config_split = '67' THEN 'NAO'
      WHEN base.venc_dt >= TRUNC(SYSDATE) + 1 THEN 'NAO'
      ELSE 'NAO'
    END AS data_invalida

  FROM base
)

SELECT *
FROM (
  SELECT
    b.*,
    ROW_NUMBER() OVER (
      PARTITION BY b.data_invalida
      ORDER BY b.venc_dt
    ) AS rn
  FROM b
) q
WHERE q.rn <= 500
  AND NOT q.ESTAB LIKE '%802'
  AND (
    LENGTH(TRIM(q.CHAVCHAVENF)) = 44
    OR q.CHAVCHAVENF IS NULL
  )
  AND q.REGRA_NOTACONF = '799'
  AND q.ESTAB <> '1001'

ORDER BY q.ESTAB ASC
"""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)

            columns = [col[0].lower() for col in cursor.description]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
