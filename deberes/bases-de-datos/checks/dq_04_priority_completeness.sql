-- DQ-04 · Completitud: clientes del lab sin prioridad calculable (el JOIN con master.customer no los encuentra).
SELECT m.lab_customer
FROM agent.lab_customer_map m
WHERE NOT EXISTS (SELECT 1 FROM agent.v_customer_priority v WHERE v.lab_customer = m.lab_customer);
