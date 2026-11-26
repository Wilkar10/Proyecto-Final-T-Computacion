-- B6 · Inventario → reposición → packing. Tablas de las etapas que antes solo existían en el simulador.
-- Idempotente (IF NOT EXISTS / CREATE OR REPLACE). Mismo modelo que el servicio inventory-replenishment del lab.
CREATE SCHEMA IF NOT EXISTS inv;

CREATE TABLE IF NOT EXISTS inv.sku (
    sku_code        text PRIMARY KEY,
    name            text NOT NULL,
    unit_volume     int  NOT NULL CHECK (unit_volume BETWEEN 1 AND 10),
    min_stock       int  NOT NULL CHECK (min_stock >= 0),
    max_stock       int  NOT NULL,
    lead_time_days  int  NOT NULL CHECK (lead_time_days >= 0),
    CHECK (max_stock > min_stock)
);

-- Saldo vigente. El saldo SIEMPRE debe poder reconstruirse sumando los movimientos (control DQ-08).
CREATE TABLE IF NOT EXISTS inv.stock_level (
    sku_code    text PRIMARY KEY REFERENCES inv.sku (sku_code),
    on_hand     int  NOT NULL CHECK (on_hand >= 0),
    reserved    int  NOT NULL DEFAULT 0 CHECK (reserved >= 0),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    CHECK (reserved <= on_hand)
);

-- Libro de movimientos: solo se inserta (nunca se corrige; un error se compensa con otro movimiento).
CREATE TABLE IF NOT EXISTS inv.stock_movement (
    movement_id      bigserial PRIMARY KEY,
    sku_code         text NOT NULL REFERENCES inv.sku (sku_code),
    kind             text NOT NULL CHECK (kind IN ('OPENING', 'RECEIPT', 'PICK', 'ADJUST')),
    qty              int  NOT NULL CHECK (qty <> 0),            -- con signo: RECEIPT/OPENING > 0, PICK < 0
    ref              text,                                      -- orden de compra o pedido que lo originó
    idempotency_key  text UNIQUE,
    created_at       timestamptz NOT NULL DEFAULT now(),
    CHECK ((kind IN ('OPENING', 'RECEIPT') AND qty > 0) OR (kind = 'PICK' AND qty < 0) OR kind = 'ADJUST')
);
CREATE INDEX IF NOT EXISTS stock_movement_sku_idx ON inv.stock_movement (sku_code, created_at);

CREATE OR REPLACE FUNCTION inv.forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'inv.stock_movement es de solo inserción: compense con un movimiento nuevo';
END $$;
DROP TRIGGER IF EXISTS stock_movement_append_only ON inv.stock_movement;
CREATE TRIGGER stock_movement_append_only BEFORE UPDATE OR DELETE ON inv.stock_movement
    FOR EACH ROW EXECUTE FUNCTION inv.forbid_change();

CREATE TABLE IF NOT EXISTS inv.purchase_order (
    po_id        bigserial PRIMARY KEY,
    sku_code     text NOT NULL REFERENCES inv.sku (sku_code),
    qty          int  NOT NULL CHECK (qty > 0),
    status       text NOT NULL CHECK (status IN ('PROPOSED', 'APPROVED', 'RECEIVED', 'REJECTED')),
    proposed_by  text NOT NULL,
    approved_by  text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    expected_at  timestamptz NOT NULL,
    received_at  timestamptz,
    -- Una compra aprobada o recibida debe tener quién la aprobó; una recibida, cuándo llegó.
    CHECK (status NOT IN ('APPROVED', 'RECEIVED') OR approved_by IS NOT NULL),
    CHECK ((status = 'RECEIVED') = (received_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS purchase_order_status_idx ON inv.purchase_order (status, sku_code);

CREATE TABLE IF NOT EXISTS inv.packing_job (
    job_id        bigserial PRIMARY KEY,
    order_code    text NOT NULL UNIQUE,          -- un pedido se empaca una sola vez
    box_capacity  int  NOT NULL CHECK (box_capacity > 0),
    piece_volume  int  NOT NULL CHECK (piece_volume > 0),
    box_count     int  NOT NULL CHECK (box_count > 0),
    packed_at     timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS inv.packing_box (
    job_id       bigint NOT NULL REFERENCES inv.packing_job (job_id),
    box_no       int    NOT NULL CHECK (box_no >= 1),
    used_volume  int    NOT NULL CHECK (used_volume > 0),
    PRIMARY KEY (job_id, box_no)
);

-- Vistas de lectura para el tablero (mart_ops): cobertura de inventario y eficiencia de empaque.
CREATE OR REPLACE VIEW mart_ops.v_stock_coverage AS
SELECT s.sku_code, s.name, l.on_hand, l.reserved, l.on_hand - l.reserved AS available,
       s.min_stock, s.max_stock, (l.on_hand - l.reserved) < s.min_stock AS below_min,
       COALESCE((SELECT sum(p.qty) FROM inv.purchase_order p WHERE p.sku_code = s.sku_code AND p.status IN ('PROPOSED', 'APPROVED')), 0) AS on_order
FROM inv.sku s JOIN inv.stock_level l USING (sku_code);

CREATE OR REPLACE VIEW mart_ops.v_packing_efficiency AS
SELECT j.job_id, j.order_code, j.box_count, j.piece_volume,
       round(100.0 * j.piece_volume / (j.box_count * j.box_capacity), 1) AS fill_pct
FROM inv.packing_job j;

GRANT USAGE ON SCHEMA inv TO lp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA inv TO lp_reader;
GRANT SELECT ON mart_ops.v_stock_coverage, mart_ops.v_packing_efficiency TO lp_reader;
