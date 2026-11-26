-- DQ-09 · Trazabilidad: toda orden de compra RECIBIDA debe tener su movimiento de ingreso; y ninguna llega antes de aprobarse.
SELECT p.po_id, p.sku_code, p.status
FROM inv.purchase_order p
WHERE p.status = 'RECEIVED'
  AND NOT EXISTS (SELECT 1 FROM inv.stock_movement m WHERE m.kind = 'RECEIPT' AND m.ref = 'PO-' || p.po_id)
UNION ALL
SELECT p.po_id, p.sku_code, 'RECIBIDA_ANTES_DE_CREARSE'
FROM inv.purchase_order p WHERE p.received_at < p.created_at;
