-- DQ-05 · Validez: propuestas cuyo costo supera el presupuesto o cuya cantidad de pedidos no coincide con sus paradas.
SELECT p.proposal_id, p.cost, p.budget, cardinality(p.order_codes) AS n_codes, count(s.order_code) AS n_stops
FROM agent.proposal p
LEFT JOIN agent.proposal_stop s ON s.proposal_id = p.proposal_id
GROUP BY p.proposal_id, p.cost, p.budget, p.order_codes
HAVING p.cost > p.budget OR cardinality(p.order_codes) <> count(s.order_code);
