-- DQ-02 · Oportunidad (timeliness): propuestas sin decisión humana hace más de 24 h.
SELECT proposal_id, created_at, robot
FROM agent.proposal
WHERE status = 'PENDING_APPROVAL' AND created_at < now() - interval '24 hours';
