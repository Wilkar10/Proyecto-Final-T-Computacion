-- Rol de solo lectura para Grafana / estudiantes (autoservicio)
CREATE ROLE lp_reader LOGIN PASSWORD 'lp_reader';
GRANT CONNECT ON DATABASE logistpulse TO lp_reader;
GRANT USAGE ON SCHEMA master, ods, dw, mart_ops, mart_commercial, semantic, teoria TO lp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA master, ods, dw, mart_ops, mart_commercial, semantic, teoria TO lp_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA master, ods, dw, mart_ops, mart_commercial, semantic, teoria
    GRANT SELECT ON TABLES TO lp_reader;
