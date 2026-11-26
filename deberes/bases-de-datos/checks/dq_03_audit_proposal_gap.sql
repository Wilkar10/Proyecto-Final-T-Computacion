-- DQ-03 · Consistencia auditoría ↔ propuestas: evento proposal_created sin su fila en agent.proposal.
SELECT e.event_id, e.payload -> 'proposal' ->> 'proposal_id' AS proposal_id
FROM agent.audit_event e
WHERE e.kind = 'proposal_created'
  AND NOT EXISTS (SELECT 1 FROM agent.proposal p WHERE p.proposal_id = e.payload -> 'proposal' ->> 'proposal_id');
