-- Datos SINTÉTICOS de ejemplo (12 SKU, los mismos supuestos que el simulador: volumen por pieza 1..4). Idempotente.
INSERT INTO inv.sku (sku_code, name, unit_volume, min_stock, max_stock, lead_time_days)
SELECT 'SKU-' || lpad(i::text, 2, '0'),
       (ARRAY['Arroz 1 kg','Aceite 1 L','Azúcar 1 kg','Leche 1 L','Atún lata','Fideos 400 g','Harina 1 kg','Sal 500 g',
              'Café 250 g','Galletas pack','Detergente 1 kg','Papel higiénico x4'])[i],
       1 + ((i - 1) * 7) % 4,
       CASE WHEN i <= 3 THEN 30 WHEN i <= 7 THEN 15 ELSE 8 END,
       CASE WHEN i <= 3 THEN 90 WHEN i <= 7 THEN 45 ELSE 24 END,
       2
FROM generate_series(1, 12) AS i
ON CONFLICT (sku_code) DO NOTHING;

INSERT INTO inv.stock_movement (sku_code, kind, qty, ref, idempotency_key)
SELECT sku_code, 'OPENING', (max_stock * 0.8)::int, 'seed', 'seed-opening-' || sku_code FROM inv.sku
ON CONFLICT (idempotency_key) DO NOTHING;

INSERT INTO inv.stock_level (sku_code, on_hand, reserved)
SELECT m.sku_code, sum(m.qty), 0 FROM inv.stock_movement m GROUP BY m.sku_code
ON CONFLICT (sku_code) DO NOTHING;
