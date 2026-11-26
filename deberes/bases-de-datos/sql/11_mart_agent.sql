-- B3 · Data mart de KPIs del agente (alimenta el panel de Grafana). Una fila por día.
CREATE SCHEMA IF NOT EXISTS mart_agent;

CREATE OR REPLACE VIEW mart_agent.kpis AS
SELECT date_trunc('day', created_at)::date                                         AS day,
       count(*)                                                                     AS proposals,
       round(100.0 * count(*) FILTER (WHERE status IN ('APPROVED', 'EXECUTED'))
             / NULLIF(count(*) FILTER (WHERE status <> 'PENDING_APPROVAL'), 0), 1)  AS acceptance_rate,
       round(100.0 * count(*) FILTER (WHERE source = 'fallback') / count(*), 1)     AS fallback_share,
       round(100.0 * avg(cost::numeric / NULLIF(budget, 0)), 1)                     AS avg_budget_use
FROM agent.proposal
GROUP BY 1;

GRANT USAGE ON SCHEMA mart_agent TO lp_reader;
GRANT SELECT ON mart_agent.kpis TO lp_reader;
