-- Datos mínimos de maestro para que los controles y la vista de prioridad tengan contra qué unirse (CI).
INSERT INTO master.zone (zone_id, name, city) VALUES (1, 'Norte (Carcelén)', 'Quito') ON CONFLICT DO NOTHING;
INSERT INTO master.customer (customer_id, name, segment, zone_id) VALUES
    (1, 'Cliente 001', 'CORPORATE', 1),
    (2, 'Cliente 002', 'PYME', 1),
    (3, 'Cliente 003', 'RETAIL', 1)
ON CONFLICT DO NOTHING;
