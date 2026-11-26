"""Uso:  python -m decision_lab.run [--days 20] [--seed 1] [--scenario normal|pico|flota_reducida|todos] [--assumptions archivo.json] [--autonomia]
--autonomia compara el agente en nivel 1 (una persona aprueba cada viaje) contra el nivel 2 (solo aprueba lo riesgoso).
--cadena recorre inventario → pedidos → reposición → packing → despacho mejorando UNA etapa a la vez."""
from __future__ import annotations

import argparse
import sys

from .sim import compare, compare_autonomy, compare_cadena, load_assumptions

SCENARIOS = {
    "normal": {},
    "pico": {"orders_per_day": 60},
    "flota_reducida": {"robots": 3},
    # Aísla el aporte de OPTIMIZAR y priorizar: el despachador manual no se equivoca ni subestima costos.
    "manual_sin_errores": {"manual": {"error_rate": 0.0, "cost_underestimate": 0.0}},
}


def table(res: dict, title: str) -> str:
    out = [f"### {title}  ({res['days']} días simulados, semilla {res['seed']})", "",
           "| Política | Despachos fallidos | SLA a tiempo | SLA corporativo | Sin entregar | Horas plan./día | Costo/día (USD) | Costo/pedido | Ahorro/mes vs manual | FTE liberados |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        out.append(f"| {r['policy']} | {r['fallidos_pct']:.1f} % ({r['fallidos_bateria_pct']:.1f} bat. + {r['fallidos_error_pct']:.1f} err.) | {r['sla_pct']:.1f} % | {r['sla_corporate_pct']:.1f} % | {r['sin_entregar_pct']:.1f} % | "
                   f"{r['horas_planificacion_dia']:.1f} | {r['costo_dia_usd']:.0f} | {r['costo_por_pedido_usd']:.2f} | "
                   f"{r.get('ahorro_mes_usd', 0):+,.0f} | {r.get('fte_liberados', 0):.2f} |")
    return "\n".join(out)


def table_autonomy(res: dict, title: str) -> str:
    out = [f"### {title}  ({res['days']} días simulados, semilla {res['seed']})", "",
           "| Caso | Despachos fallidos | SLA a tiempo | SLA corporativo | Aprobaciones/día | Viajes sin aprobar | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        out.append(f"| {r['policy']} | {r['fallidos_pct']:.2f} % | {r['sla_pct']:.1f} % | {r['sla_corporate_pct']:.1f} % | {r['aprobaciones_dia']:.1f} | "
                   f"{r['viajes_autonomos_pct']:.0f} % | {r['horas_planificacion_dia']:.2f} | {r['costo_dia_usd']:.0f} | {r['ahorro_mes_usd']:+,.0f} |")
    return "\n".join(out)


def table_cadena(res: dict, title: str) -> str:
    out = [f"### {title}  ({res['days']} días simulados, semilla {res['seed']})", "",
           "| Paso | Falta de producto | Error de empaque | Fallidos de despacho | **Fallidos totales** | SLA a tiempo | Cajas/pedido (llenado) | Cobertura (días) | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        hp = r["horas_planificacion_dia"] + r["horas_persona_cadena_dia"]
        out.append(f"| {r['policy']} | {r['falta_producto_pct']:.1f} % | {r['error_empaque_pct']:.1f} % | {r['fallidos_pct']:.1f} % | **{r['fallidos_total_pct']:.1f} %** | {r['sla_pct']:.1f} % | "
                   f"{r['cajas_por_pedido']:.2f} ({r['llenado_cajas_pct']:.0f} %) | {r['cobertura_dias']:.1f} | {hp:.1f} | {r['costo_dia_usd']:.0f} | {r['ahorro_mes_usd']:+,.0f} |")
    out += ["", "Costo/día por componente (USD): " + " · ".join(f"{k} {v:.1f}" for k, v in res["rows"][-1]["componentes_dia_usd"].items()) + "  (último paso)"]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--scenario", default="todos", choices=[*SCENARIOS, "todos"])
    ap.add_argument("--assumptions")
    ap.add_argument("--autonomia", action="store_true", help="compara nivel 1 vs nivel 2 de autonomía")
    ap.add_argument("--cadena", action="store_true", help="recorre la cadena completa mejorando una etapa a la vez")
    args = ap.parse_args(argv)
    print("> SIMULACIÓN con supuestos explícitos (decision_lab/assumptions.json). Los ahorros NO son reales hasta usar datos de operación.\n")
    for name in (SCENARIOS if args.scenario == "todos" else [args.scenario]):
        a = load_assumptions(args.assumptions, SCENARIOS[name])
        if args.cadena:
            print(table_cadena(compare_cadena(a, days=args.days, seed=args.seed), f"Cadena completa · escenario «{name}»"), "\n")
        elif args.autonomia:
            print(table_autonomy(compare_autonomy(a, days=args.days, seed=args.seed), f"Autonomía · escenario «{name}»"), "\n")
        else:
            print(table(compare(a, days=args.days, seed=args.seed), f"Escenario «{name}»"), "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
