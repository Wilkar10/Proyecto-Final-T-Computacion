-- DQ-06 · Unicidad: un mismo pedido del lab asignado a más de una propuesta aún vigente (PENDING_APPROVAL/APPROVED).
SELECT s.order_code, count(DISTINCT s.proposal_id) AS proposals
FROM agent.proposal_stop s
JOIN agent.proposal p ON p.proposal_id = s.proposal_id
WHERE p.status IN ('PENDING_APPROVAL', 'APPROVED')
GROUP BY s.order_code
HAVING count(DISTINCT s.proposal_id) > 1;
