-- LOGISTPULSE · esquema del AGENTE de despacho (base entregada por el docente)
-- El agente lee prioridades del lakehouse y registra propuestas y auditoría. Una persona aprueba.
-- Nota de diseño: NO hay FK hacia master.* porque `lp.seed` hace TRUNCATE de master.customer; una FK lo
-- impediría. La integridad referencial se verifica con un control de calidad (deberes/bases-de-datos/checks).
CREATE SCHEMA IF NOT EXISTS agent;

-- Conformación de datos maestros: nombre del cliente en el lab -> nombre en master.customer
CREATE TABLE agent.lab_customer_map (
    lab_customer  text PRIMARY KEY,
    customer_name text NOT NULL
);
INSERT INTO agent.lab_customer_map VALUES
    ('Supermaxi Cumbayá', 'Cliente 001'),
    ('Farmacia Cruz Azul', 'Cliente 002'),
    ('Ferretería La 10',  'Cliente 003');

-- Prioridad base: segmento (CORPORATE 3, PYME 2, RETAIL 1) + 1 si el cliente cumple < 80 % de OTIF.
CREATE VIEW agent.v_customer_priority AS
SELECT m.lab_customer,
       c.segment,
       s.otif_pct,
       (CASE c.segment WHEN 'CORPORATE' THEN 3 WHEN 'PYME' THEN 2 ELSE 1 END
        + CASE WHEN s.otif_pct IS NOT NULL AND s.otif_pct < 80 THEN 1 ELSE 0 END)::numeric AS priority
FROM agent.lab_customer_map m
JOIN master.customer c ON c.name = m.customer_name
LEFT JOIN mart_commercial.customer_service_level s ON s.customer = c.name;

-- Propuestas del agente. Invariante: una propuesta PENDIENTE no tiene aprobador; las demás sí.
CREATE TABLE agent.proposal (
    proposal_id    text PRIMARY KEY,
    created_at     timestamptz NOT NULL,
    robot          text NOT NULL,
    order_codes    text[] NOT NULL CHECK (cardinality(order_codes) BETWEEN 1 AND 12),
    cost           int  NOT NULL CHECK (cost >= 0),
    budget         int  NOT NULL CHECK (budget >= 0),
    battery_before int  NOT NULL CHECK (battery_before BETWEEN 0 AND 100),
    algorithm      text NOT NULL,
    exact          boolean NOT NULL,
    source         text NOT NULL CHECK (source IN ('rule', 'llm', 'fallback')),
    status         text NOT NULL CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTED', 'FAILED')),
    decided_by     text,
    rationale      text,
    CHECK (cost <= budget),
    CHECK ((status = 'PENDING_APPROVAL') = (decided_by IS NULL))
);
CREATE INDEX proposal_status_idx ON agent.proposal (status, created_at);

-- Auditoría append-only: el rol del agente solo puede INSERTAR.
CREATE TABLE agent.audit_event (
    event_id bigserial PRIMARY KEY,
    ts       timestamptz NOT NULL,
    kind     text NOT NULL,
    payload  jsonb NOT NULL
);
CREATE INDEX audit_event_kind_ts_idx ON agent.audit_event (kind, ts);

-- Rol del agente: mínimo privilegio.
CREATE ROLE lp_agent LOGIN PASSWORD 'lp_agent';
GRANT CONNECT ON DATABASE logistpulse TO lp_agent;
GRANT USAGE ON SCHEMA agent TO lp_agent;
GRANT SELECT ON agent.v_customer_priority TO lp_agent;
GRANT SELECT, INSERT, UPDATE (status, decided_by) ON agent.proposal TO lp_agent;
GRANT INSERT ON agent.audit_event TO lp_agent;
GRANT USAGE ON SEQUENCE agent.audit_event_event_id_seq TO lp_agent;
-- Lectura para autoservicio (Grafana, estudiantes)
GRANT USAGE ON SCHEMA agent TO lp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA agent TO lp_reader;
