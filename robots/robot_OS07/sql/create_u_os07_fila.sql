-- Tabela de fila de execução do robô OS07 por usuário Windows
-- Execute uma única vez no banco Oracle

CREATE TABLE U_OS07_FILA (
    U_OS07_FILA_ID    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    USUARIO           VARCHAR2(100)  NOT NULL,        -- login Windows (ex: rpa.dev1)
    CONT_ID           NUMBER,                          -- U_FISCAL_IO_CONT_ID da nota
    NUMERONOTA        VARCHAR2(50),
    NOTACONF          VARCHAR2(10),
    ESTAB             VARCHAR2(10),
    POSICAO           NUMBER         NOT NULL,         -- posição na fila (1, 2, 3...)
    STATUS            VARCHAR2(20)   DEFAULT 'PENDENTE' NOT NULL,  -- PENDENTE / CONCLUIDO / ERRO
    DT_INCLUSAO       TIMESTAMP      DEFAULT SYSTIMESTAMP NOT NULL,
    DT_PREVISAO       TIMESTAMP,                       -- horário estimado de conclusão
    DT_PROCESSAMENTO  TIMESTAMP,                       -- horário real de conclusão
    MENSAGEM          VARCHAR2(4000)                   -- motivo do erro (quando STATUS = ERRO)
);

COMMENT ON TABLE  U_OS07_FILA                    IS 'Fila de execução do robô OS07 por usuário Windows';
COMMENT ON COLUMN U_OS07_FILA.USUARIO            IS 'Login Windows da máquina que processa (ex: rpa.dev1)';
COMMENT ON COLUMN U_OS07_FILA.POSICAO            IS 'Posição na fila; usado para calcular DT_PREVISAO (base: 2,5 min/nota)';
COMMENT ON COLUMN U_OS07_FILA.DT_PREVISAO        IS 'DT_INCLUSAO + (POSICAO * 2,5 min) — estimativa de quando a nota será processada';
COMMENT ON COLUMN U_OS07_FILA.DT_PROCESSAMENTO   IS 'Momento real em que o status foi alterado para CONCLUIDO ou ERRO';
