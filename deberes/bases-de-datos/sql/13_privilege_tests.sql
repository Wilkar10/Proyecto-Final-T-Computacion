-- B5 · Pruebas de mínimo privilegio: cada intento prohibido DEBE fallar con insufficient_privilege; si no, se lanza excepción.
BEGIN;
SET LOCAL ROLE lp_agent;
DO $$
DECLARE stmt text;
BEGIN
  FOREACH stmt IN ARRAY ARRAY[
      'DELETE FROM agent.audit_event',
      'UPDATE agent.audit_event SET kind = ''x''',
      'DELETE FROM agent.proposal',
      'UPDATE agent.proposal SET robot = ''x''',
      'UPDATE inv.stock_level SET on_hand = 9999',
      'DELETE FROM inv.stock_movement',
      'UPDATE inv.purchase_order SET status = ''APPROVED'''] LOOP
    BEGIN
      EXECUTE stmt;
      RAISE EXCEPTION 'FALLO DE SEGURIDAD: lp_agent pudo ejecutar: %', stmt;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;  -- esperado
    END;
  END LOOP;
END $$;
ROLLBACK;
