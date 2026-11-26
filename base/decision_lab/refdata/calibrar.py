"""Compara los supuestos del laboratorio con datos públicos de referencia (no los reemplaza).
Uso:  python -m refdata.calibrar [--olist CARPETA] [--favorita CARPETA] [--out docs/CONTRASTE_SUPUESTOS.md]"""
from __future__ import annotations

import argparse
import sys

from decision_lab.sim import load_assumptions

from . import favorita, olist


def rows(a: dict, ol: dict | None, fa: dict | None) -> list[tuple[str, str, str, str]]:
    r = []
    pico = a["orders_per_day"] and 60 / a["orders_per_day"]
    if fa:
        r.append(("Pico de demanda (escenario «pico» = ×2)", f"×{pico:.1f} sobre la media",
                  f"p95/media = ×{fa['pico_p95_sobre_media']} (máx ×{fa['max_sobre_media']})",
                  "¿Es ×2 un pico razonable o extremo? Úsese como referencia de forma, no de escala."))
        r.append(("Estacionalidad semanal", "No modelada (uniforme)", ", ".join(f"{k[:3]} {v}" for k, v in fa["indice_por_dia"].items()),
                  "Si el índice varía mucho, el modelo uniforme subestima los días fuertes."))
    if ol:
        r.append(("Error de captura manual (despacho fallido)", f"{a['manual']['error_rate']*100:.1f} %",
                  f"{ol['fallidos_pct']} % de pedidos cancelados/no disponibles",
                  "No son lo mismo (cancelación ≠ error de despacho); sirve como orden de magnitud, no como calibración."))
        r.append(("Error residual del sistema", f"{a['system']['error_rate']*100:.1f} %", "—", "Sin referencia pública: debe medirse en la operación."))
        r.append(("Entregas tardías vs fecha prometida", "El modelo mide SLA en minutos por segmento", f"{ol['tardios_pct']} % tardías (retraso medio {ol['retraso_prom_dias_si_tarde']} días)",
                  "Escala distinta (días, e-commerce). Muestra que un SLA medido contra una promesa puede ser alto o bajo según cómo se prometa."))
        if "flete_prom_por_pedido_brl" in ol:
            r.append(("Costo de transporte", f"{a['money']['cost_per_cost_unit_usd']} USD por unidad de ruta", f"flete {ol['flete_prom_por_pedido_brl']} BRL por pedido ({ol['flete_sobre_precio_pct']} % del precio)",
                      "Útil para discutir peso del flete en el margen; monedas y escalas distintas."))
        if ol.get("tardios_por_estado"):
            ts = ol["tardios_por_estado"]
            lo, hi = min(ts, key=ts.get), max(ts, key=ts.get)
            r.append(("Variación de SLA por región", "No modelada", f"{lo} {ts[lo]} % … {hi} {ts[hi]} % tardías",
                      "Si hay brecha grande, el SLA depende de la región y no solo de la política de despacho."))
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--olist")
    ap.add_argument("--favorita")
    ap.add_argument("--assumptions")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if not (args.olist or args.favorita):
        ap.error("indique --olist y/o --favorita")
    ol = olist.load(args.olist) if args.olist else None
    fa = favorita.load(args.favorita) if args.favorita else None
    a = load_assumptions(args.assumptions)
    md = ["# Contraste de supuestos con datos públicos de referencia", "",
          "> Referencia pública, **no** datos de DANEC. Esta tabla no modifica `assumptions.json`; cada equipo decide qué supuesto cambia y lo justifica.", "",
          "| Parámetro | Supuesto del laboratorio | Referencia pública | Cómo leerlo |", "|---|---|---|---|"]
    md += [f"| {p} | {s} | {ref} | {n} |" for p, s, ref, n in rows(a, ol, fa)]
    text = "\n".join(md)
    print(text)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
