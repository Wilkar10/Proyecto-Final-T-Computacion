-- DQ-07 · Completitud/consistencia: pedidos ingeridos cuyo cliente no está en el mapa de conformación de datos maestros.
SELECT o.code, o.customer
FROM ods.lab_order o
LEFT JOIN agent.lab_customer_map m ON m.lab_customer = o.customer
WHERE m.lab_customer IS NULL;
