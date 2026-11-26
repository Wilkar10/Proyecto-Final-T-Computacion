-- LOGISTPULSE · resultados de los ejercicios de Teoría de la Computación (notebook 02_teoria_sobre_el_lakehouse)
-- Una fila por corrida de un algoritmo; Grafana las muestra (deberes/teoria-computacion/grafana/teoria_solver.json).
CREATE SCHEMA IF NOT EXISTS teoria;

CREATE TABLE teoria.solver_run (
    run_id     bigserial PRIMARY KEY,
    ts         timestamptz NOT NULL DEFAULT now(),
    problema   text NOT NULL CHECK (problema IN ('tsp', 'mochila', 'empaque', 'cobertura', 'asignacion', 'plazos')),
    algoritmo  text NOT NULL,
    n          int  NOT NULL CHECK (n >= 0),
    exacto     boolean NOT NULL,
    valor      numeric,                       -- costo / valor / nº de viajes obtenido
    optimo     numeric,                       -- referencia exacta si se conoce
    brecha_pct numeric CHECK (brecha_pct IS NULL OR brecha_pct >= 0),
    segundos   numeric NOT NULL CHECK (segundos >= 0),
    fuente     text NOT NULL CHECK (fuente IN ('lakehouse', 'ejemplo'))
);
CREATE INDEX solver_run_idx ON teoria.solver_run (problema, algoritmo, n);
