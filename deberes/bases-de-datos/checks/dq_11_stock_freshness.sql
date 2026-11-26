-- DQ-11 · Oportunidad (actualidad): un SKU con compra abierta cuyo saldo no se actualiza hace más de 48 h indica un flujo detenido.
SELECT l.sku_code, l.updated_at
FROM inv.stock_level l
WHERE l.updated_at < now() - interval '48 hours'
  AND EXISTS (SELECT 1 FROM inv.purchase_order p WHERE p.sku_code = l.sku_code AND p.status IN ('PROPOSED', 'APPROVED'));
