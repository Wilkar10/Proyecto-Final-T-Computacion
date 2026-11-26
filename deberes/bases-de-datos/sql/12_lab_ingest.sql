-- B4 · Destino de la ingesta de pedidos del lab. Clave natural = code (por eso el upsert es idempotente).
CREATE TABLE IF NOT EXISTS ods.lab_order (
    code        text PRIMARY KEY,
    lab_id      bigint NOT NULL,
    customer    text   NOT NULL,
    dest_x      int    NOT NULL,
    dest_y      int    NOT NULL,
    status      text   NOT NULL,
    created_at  timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS lab_order_customer_idx ON ods.lab_order (customer);
GRANT SELECT ON ods.lab_order TO lp_reader;
