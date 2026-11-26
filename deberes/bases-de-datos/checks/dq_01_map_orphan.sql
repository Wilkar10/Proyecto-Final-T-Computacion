-- DQ-01 · Integridad referencial (consistencia): clientes del lab mapeados a un nombre que NO existe en master.customer.
-- Convención: una consulta que devuelve FILAS = hay violaciones (0 filas = control superado).
SELECT m.lab_customer, m.customer_name
FROM agent.lab_customer_map m
LEFT JOIN master.customer c ON c.name = m.customer_name
WHERE c.customer_id IS NULL;
