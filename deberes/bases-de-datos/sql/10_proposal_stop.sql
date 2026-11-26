-- B1 · Normalización: agent.proposal guarda order_codes como arreglo (1FN violada). Se extrae a una tabla de paradas.
-- Idempotente: se puede reaplicar. La tabla se rellena desde el arreglo existente.
CREATE TABLE IF NOT EXISTS agent.proposal_stop (
    proposal_id text NOT NULL REFERENCES agent.proposal (proposal_id),
    stop_seq    int  NOT NULL CHECK (stop_seq >= 1),
    order_code  text NOT NULL,
    PRIMARY KEY (proposal_id, stop_seq)
);
CREATE INDEX IF NOT EXISTS proposal_stop_code_idx ON agent.proposal_stop (order_code);

INSERT INTO agent.proposal_stop (proposal_id, stop_seq, order_code)
SELECT p.proposal_id, u.ord::int, u.code
FROM agent.proposal p, unnest(p.order_codes) WITH ORDINALITY AS u(code, ord)
ON CONFLICT (proposal_id, stop_seq) DO NOTHING;

GRANT SELECT ON agent.proposal_stop TO lp_reader;
