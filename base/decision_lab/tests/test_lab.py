import copy

import pytest

from decision_lab.sim import POLICIES, compare, kpis, load_assumptions, simulate


def a():
    return load_assumptions()


def test_deterministic_for_same_seed():
    r1, r2 = compare(a(), days=4, seed=3), compare(a(), days=4, seed=3)
    assert r1 == r2


def test_same_orders_for_every_policy():
    ms = [simulate(p, a(), days=3, seed=2) for p in POLICIES]
    assert len({m.orders for m in ms}) == 1


def test_validator_never_lets_an_infeasible_system_trip_out():
    for p in POLICIES:
        if p.startswith("sistema"):
            m = simulate(p, a(), days=6, seed=4)
            assert m.failed_trips == 0                      # por construcción: batería validada antes de despachar


def test_manual_failures_come_from_battery_underestimate_and_human_error():
    ass = a()
    ass["manual"].update(cost_underestimate=0.0, error_rate=0.0)
    m = simulate("manual_fifo", ass, days=6, seed=1)
    assert m.failed_orders == 0                              # sin subestimar ni equivocarse, el manual tampoco falla
    ass["manual"].update(cost_underestimate=0.4)
    assert simulate("manual_fifo", ass, days=6, seed=1).failed_orders > 0


def test_kpi_accounting_is_consistent():
    ass = a()
    m = simulate("sistema_plazo", ass, days=5, seed=1)
    assert m.on_time + m.late + m.undelivered == m.orders
    k = kpis(m, ass, 5)
    assert abs(sum(k["componentes_dia_usd"].values()) - k["costo_dia_usd"]) < 1e-9


def test_more_demand_never_improves_manual_sla():
    base = a()
    peak = copy.deepcopy(base)
    peak["orders_per_day"] = 60
    assert kpis(simulate("manual_fifo", peak, 8, 1), peak, 8)["sla_pct"] <= kpis(simulate("manual_fifo", base, 8, 1), base, 8)["sla_pct"]


def test_unknown_policy_is_explicit():
    with pytest.raises(ValueError):
        simulate("magia", a())


# ---------------------------------------------------------------- autonomía (nivel 1 vs nivel 2)
def test_sin_autonomia_el_comportamiento_original_no_cambia():
    """autonomy=None es el camino de siempre: ni aprobaciones ni retrasos."""
    m = simulate("sistema_plazo", a(), days=5, seed=1)
    assert m.approvals == 0 and m.auto_trips == 0


def test_nivel_1_toda_salida_pasa_por_una_persona():
    m = simulate("sistema_plazo", a(), days=5, seed=1, autonomy=1)
    assert m.approvals > 0 and m.auto_trips == 0
    assert m.approvals == m.trips


def test_nivel_2_aprueba_menos_y_usa_menos_horas_persona():
    n1 = simulate("sistema_plazo", a(), days=8, seed=1, autonomy=1)
    n2 = simulate("sistema_plazo", a(), days=8, seed=1, autonomy=2)
    assert n2.auto_trips > 0
    assert n2.approvals < n1.approvals
    assert n2.plan_minutes < n1.plan_minutes


def test_sin_retraso_ni_ayuda_humana_el_nivel_1_equivale_al_original_en_entregas():
    ass = a()
    ass["autonomy"].update(approval_delay_min=0, human_catch_rate=0.0)
    base = kpis(simulate("sistema_plazo", ass, 6, 1), ass, 6)
    n1 = kpis(simulate("sistema_plazo", ass, 6, 1, autonomy=1), ass, 6)
    assert n1["sla_pct"] == base["sla_pct"] and n1["fallidos_pct"] == base["fallidos_pct"]


def test_la_aprobacion_humana_atrapa_errores_pero_cuesta_tiempo():
    ass = a()
    ass["system"]["error_rate"] = 0.05
    ass["autonomy"].update(human_catch_rate=1.0)           # una persona perfecta
    n1 = kpis(simulate("sistema_plazo", ass, 8, 2, autonomy=1), ass, 8)
    n2 = kpis(simulate("sistema_plazo", ass, 8, 2, autonomy=2), ass, 8)
    assert n1["fallidos_error_pct"] == 0.0                  # todo viaje pasó por la persona
    assert n2["fallidos_error_pct"] > 0.0                   # los viajes de bajo riesgo salieron sin revisión


def test_la_politica_manual_no_tiene_nivel_y_los_niveles_se_validan():
    with pytest.raises(ValueError):
        simulate("manual_fifo", a(), days=1, autonomy=1)
    with pytest.raises(ValueError):
        simulate("sistema_plazo", a(), days=1, autonomy=3)


def test_compare_autonomy_entrega_manual_nivel1_nivel2():
    from decision_lab.sim import compare_autonomy
    res = compare_autonomy(a(), days=3, seed=1)
    assert [r["policy"] for r in res["rows"]] == ["manual_fifo", "sistema_plazo · nivel 1", "sistema_plazo · nivel 2"]


# ---------------------------------------------------------------- cadena: inventario → pedidos → reposición → packing
from decision_lab.cadena import first_fit, first_fit_decreasing
from decision_lab.sim import compare_cadena


def test_sin_cadena_no_hay_contadores_de_cadena():
    assert simulate("sistema_plazo", a(), days=3, seed=1).chain == {}


def test_empaque_ffd_nunca_usa_mas_cajas_que_first_fit_y_respeta_capacidad():
    import random
    rng = random.Random(7)
    for _ in range(200):
        items = [rng.randint(1, 4) for _ in range(rng.randint(1, 14))]
        ff, ffd = first_fit(items, 10), first_fit_decreasing(items, 10)
        assert sum(ff) == sum(items) == sum(ffd)
        assert max(ff) <= 10 and max(ffd) <= 10
        assert len(ffd) >= -(-sum(items) // 10)                      # cota inferior: no se puede usar menos que el volumen/capacidad


def test_la_demanda_es_la_misma_para_toda_politica_de_la_cadena():
    ms = [simulate("manual_fifo", a(), 5, 2, chain=c) for c in [("manual", "manual"), ("sistema", "sistema")]]
    assert ms[0].chain["pedidos"] == ms[1].chain["pedidos"]


def test_la_cadena_es_determinista():
    assert compare_cadena(a(), days=4, seed=3) == compare_cadena(a(), days=4, seed=3)


def test_reposicion_sistema_reduce_faltantes_con_pronostico_sesgado():
    m0 = simulate("manual_fifo", a(), 12, 1, chain=("manual", "manual"))
    m1 = simulate("manual_fifo", a(), 12, 1, chain=("sistema", "manual"))
    assert m1.chain["falta_producto"] < m0.chain["falta_producto"]


def test_si_el_pronostico_manual_no_tiene_sesgo_y_revisa_a_diario_la_ventaja_desaparece():
    """Honestidad del modelo: el beneficio de la reposición depende del supuesto de sesgo/frecuencia, no es una ley."""
    ass = a()
    ass["cadena"]["manual"].update(forecast_bias=0.0, review_every_days=1)
    ass["cadena"]["initial_cover_days"] = 20
    m0 = simulate("manual_fifo", ass, 12, 1, chain=("manual", "manual"))
    assert m0.chain["falta_producto"] <= 0.02 * m0.chain["pedidos"]


def test_un_pedido_sin_stock_no_se_entrega_y_cuenta_como_falta_de_producto():
    ass = a()
    ass["cadena"]["initial_cover_days"] = 0.0
    ass["cadena"]["lead_time_days"] = 99
    m = simulate("sistema_plazo", ass, 3, 1, chain=("manual", "sistema"))
    assert m.chain["falta_producto"] == m.orders and m.undelivered == m.orders


def test_contabilidad_de_costos_de_la_cadena_es_coherente():
    ass = a()
    k = kpis(simulate("sistema_plazo", ass, 5, 1, chain=("sistema", "sistema")), ass, 5)
    assert abs(sum(k["componentes_dia_usd"].values()) - k["costo_dia_usd"]) < 1e-9
    assert {"inventario", "compras", "empaque", "quiebres"} <= set(k["componentes_dia_usd"])


def test_escalera_cadena_tiene_cuatro_pasos_y_el_total_mejora_al_manual():
    res = compare_cadena(a(), days=8, seed=1)
    assert [r["policy"][0] for r in res["rows"]] == list("0123")
    assert res["rows"][-1]["costo_dia_usd"] < res["rows"][0]["costo_dia_usd"]
    assert res["rows"][-1]["fallidos_total_pct"] < res["rows"][0]["fallidos_total_pct"]


def test_cadena_valida_sus_opciones():
    with pytest.raises(ValueError):
        simulate("sistema_plazo", a(), 1, chain=("magia", "sistema"))
