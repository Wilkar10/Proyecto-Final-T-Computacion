-- DQ-08 · Consistencia: el saldo de cada SKU debe ser igual a la suma de sus movimientos (el libro manda).
SELECT l.sku_code, l.on_hand, COALESCE(sum(m.qty), 0) AS suma_movimientos
FROM inv.stock_level l LEFT JOIN inv.stock_movement m ON m.sku_code = l.sku_code
GROUP BY l.sku_code, l.on_hand
HAVING l.on_hand <> COALESCE(sum(m.qty), 0);
