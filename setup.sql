-- =============================================================================
-- Robot Platform — run once before starting workers or the orchestrator
-- =============================================================================

-- Tracks which machines are alive (heartbeat updated every 30 s)
CREATE TABLE U_ROBOT_WORKER (
    U_ROBOT_WORKER_ID  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    NOME_COMPUTADOR    VARCHAR2(50)  NOT NULL,
    STATUS             VARCHAR2(20)  DEFAULT 'ONLINE' NOT NULL,
    DT_HEARTBEAT       TIMESTAMP,
    DT_INICIO          TIMESTAMP,
    CONSTRAINT uq_robot_worker_nome UNIQUE (NOME_COMPUTADOR)
);

-- Performance: workers query STATUS constantly — this index is critical
-- (Skip if the index already exists on your environment)
CREATE INDEX IDX_ROBOT_LOG_STATUS ON U_ROBOT_LOG (STATUS);
