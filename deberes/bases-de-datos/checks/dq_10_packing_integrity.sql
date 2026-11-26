-- DQ-10 · Validez: ninguna caja excede su capacidad y el volumen de las cajas suma el volumen de las piezas del pedido.
SELECT j.job_id, j.order_code, j.box_capacity, j.piece_volume, count(b.box_no) AS cajas, COALESCE(sum(b.used_volume), 0) AS volumen_cajas
FROM inv.packing_job j LEFT JOIN inv.packing_box b ON b.job_id = j.job_id
GROUP BY j.job_id, j.order_code, j.box_capacity, j.piece_volume, j.box_count
HAVING bool_or(b.used_volume > j.box_capacity) OR count(b.box_no) <> j.box_count OR COALESCE(sum(b.used_volume), 0) <> j.piece_volume;
