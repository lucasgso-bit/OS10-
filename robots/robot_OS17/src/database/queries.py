QUERY_BUSCAR_PENDENTES = """
SELECT
    ESTAB,
    IE AS INS_ESTAD,
    NUMEROCM,
    ANO,
    MES,
    VALOR AS CREDITO_RESUMO
FROM U_CREDITO_PRESUMIDO
WHERE STATUS = 'PENDENTE'
ORDER BY ESTAB
"""

QUERY_MARCAR_EM_PROCESSAMENTO = """
UPDATE U_CREDITO_PRESUMIDO
SET
    STATUS = 'EM_PROCESSAMENTO'
WHERE IE = :ins_estad
  AND NUMEROCM = :numerocm
  AND ESTAB = :estab
  AND ANO = :ano
  AND MES = :mes
  AND STATUS = 'PENDENTE'
"""

QUERY_MARCAR_ERRO = """
UPDATE U_CREDITO_PRESUMIDO
SET
    STATUS = 'ERRO',
    DTFINALIZACAO = SYSDATE
WHERE IE = :ins_estad
  AND NUMEROCM = :numerocm
  AND ESTAB = :estab
  AND ANO = :ano
  AND MES = :mes
  AND STATUS IN ('PENDENTE', 'EM_PROCESSAMENTO')
"""

QUERY_MARCAR_CONCLUIDO = """
UPDATE U_CREDITO_PRESUMIDO
SET
    STATUS = 'CONCLUIDO',
    NOTA = REPLACE(:nota, '.', ''),
    SEQNOTA = REPLACE(:seqnota, '.', ''),
    DTFINALIZACAO = SYSDATE
WHERE IE = :ins_estad
  AND NUMEROCM = :numerocm
  AND ESTAB = :estab
  AND ANO = :ano
  AND MES = :mes
  AND STATUS IN ('PENDENTE', 'EM_PROCESSAMENTO')
"""

QUERY_CANDIDATOS_CREDITO = """
WITH params AS (
    SELECT
        TRUNC(ADD_MONTHS(SYSDATE, -1), 'MM') AS dt_inicial,
        TRUNC(SYSDATE, 'MM') AS dt_final
    FROM dual
),

devol AS (
    SELECT
        filial.estab,
        contamov.nome,
        nfitem.seqnota,
        nfitem.seqnotaitem,
        nfitem.valorunitario,
        nfitem.valortotal AS vlr_total
    FROM
        nfcab
        CROSS JOIN params
        INNER JOIN contamov ON contamov.numerocm = nfcab.numerocm
        INNER JOIN conceitopessoa ON conceitopessoa.numerocm = contamov.numerocm
        INNER JOIN filial ON filial.estab = nfcab.estab
        INNER JOIN u_tempresa ON u_tempresa.estab = filial.estab
        INNER JOIN cidade ON cidade.cidade = filial.cidade
        INNER JOIN nfitem ON nfitem.estab = nfcab.estab
                          AND nfitem.seqnota = nfcab.seqnota
    WHERE
        cidade.uf = 'MG'
        AND nfitem.cfop IN (5202)
        AND nfcab.chaveacessonfe LIKE '%' || filial.cnpj || '%'
        AND COALESCE(nfcab.status, 'N') <> 'C'
        AND nfcab.DTENTSAI >= params.dt_inicial
        AND nfcab.DTENTSAI < params.dt_final
        AND conceitopessoa.conceito <> 98
    GROUP BY
        filial.estab,
        nfitem.valortotal,
        contamov.nome,
        nfitem.seqnota,
        nfitem.seqnotaitem,
        nfitem.valorunitario
),

base AS (
    SELECT
        filial.estab,
        EXTRACT(YEAR FROM nfcab.DTENTSAI) AS ano,
        EXTRACT(MONTH FROM nfcab.DTENTSAI) AS mes,
        contamov.nome,
        contamov.numerocm,
        contamov.cnpjf AS cnpj_cpf,
        TRIM(COALESCE(endereco.credencialagro, contamov.inscestad)) AS ins_estad,
        itemagro.item || ' - ' || itemagro.descricao AS item,
        nfitem.seqnota,
        nfitem.seqnotaitem,
        nfitem.valortotal - NVL(nfitem.vlrnfant, 0) AS vlr_total,
        COALESCE(devol.vlr_total, 0) AS vlr_devol,
        (
            nfitem.valortotal
            - NVL(nfitem.vlrnfant, 0)
            - COALESCE(devol.vlr_total, 0)
        ) AS vlr_liq,
        (
            nfitem.valortotal
            - NVL(nfitem.vlrnfant, 0)
            - COALESCE(devol.vlr_total, 0)
        ) * 0.024 AS credito_resumo
    FROM
        nfcab
        CROSS JOIN params
        INNER JOIN contamov ON contamov.numerocm = nfcab.numerocm
        LEFT JOIN endereco ON endereco.numerocm = nfcab.numerocm
                          AND endereco.seqendereco = nfcab.seqendereco
        INNER JOIN filial ON filial.estab = nfcab.estab
        INNER JOIN u_tempresa ON u_tempresa.estab = filial.estab
        INNER JOIN cidade ON cidade.cidade = filial.cidade
        INNER JOIN nfitem ON nfitem.estab = nfcab.estab
                         AND nfitem.seqnota = nfcab.seqnota
        INNER JOIN itemagro ON itemagro.item = nfitem.item
        LEFT JOIN nfitemapartirde ON nfitemapartirde.estaborigem = nfcab.estab
                                 AND nfitemapartirde.seqnotaorigem = nfcab.seqnota
                                 AND nfitemapartirde.seqnotaitemorigem = nfitem.seqnotaitem
        LEFT JOIN devol ON nfitemapartirde.estab = devol.estab
                       AND nfitemapartirde.seqnota = devol.seqnota
                       AND nfitemapartirde.seqnotaitem = devol.seqnotaitem
        INNER JOIN conceitopessoa ON conceitopessoa.numerocm = contamov.numerocm
    WHERE
        cidade.uf = 'MG'
        AND nfitem.cfop IN (1102, 1117, 1118)
        AND nfcab.chaveacessonfe LIKE '%' || filial.cnpj || '%'
        AND COALESCE(nfcab.status, 'N') <> 'C'
        AND nfcab.DTENTSAI >= params.dt_inicial
        AND nfcab.DTENTSAI < params.dt_final
        AND u_tempresa.graos = 'S'
        AND conceitopessoa.conceito <> 98
    GROUP BY
        EXTRACT(YEAR FROM nfcab.DTENTSAI),
        EXTRACT(MONTH FROM nfcab.DTENTSAI),
        contamov.numerocm,
        filial.estab,
        nfitem.valortotal,
        contamov.nome,
        itemagro.item,
        itemagro.descricao,
        nfitem.seqnota,
        nfitem.seqnotaitem,
        devol.vlr_total,
        contamov.cnpjf,
        endereco.credencialagro,
        contamov.inscestad,
        nfitem.vlrnfant
),

baseimp AS (
    SELECT
        EXTRACT(YEAR FROM nfcab.DTENTSAI) AS ano,
        EXTRACT(MONTH FROM nfcab.DTENTSAI) AS mes,
        nfcab.estab,
        nfcab.numerocm,
        SUM(valorimposto) AS valorimposto
    FROM
        nfcab
        CROSS JOIN params
        INNER JOIN nfcabimposto i ON i.estab = nfcab.estab
                                  AND i.seqnota = nfcab.seqnota
    WHERE
        nfcab.DTENTSAI >= params.dt_inicial
        AND nfcab.DTENTSAI < params.dt_final
        AND nfcab.notaconf = 616
    GROUP BY
        EXTRACT(YEAR FROM nfcab.DTENTSAI),
        EXTRACT(MONTH FROM nfcab.DTENTSAI),
        nfcab.numerocm,
        nfcab.estab
)

SELECT
    base.estab,
    base.numerocm,
    base.nome,
    base.ins_estad,
    base.ano,
    base.mes,
    arredondar(SUM(base.credito_resumo), 2) AS credito_resumo,
    NVL(b.valorimposto, 0) AS valorimposto
FROM
    base
    LEFT JOIN baseimp b ON b.estab = base.estab
                       AND b.ano = base.ano
                       AND b.mes = base.mes
                       AND b.numerocm = base.numerocm
WHERE
    NVL(b.valorimposto, 0) = 0
    AND base.credito_resumo <> 0
GROUP BY
    base.estab,
    base.numerocm,
    base.nome,
    base.ins_estad,
    base.ano,
    base.mes,
    b.valorimposto
ORDER BY
    base.estab;
"""
