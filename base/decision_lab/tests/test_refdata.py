"""Los cargadores se prueban con archivos mínimos que respetan el esquema documentado de Olist y Favorita.
NO se han probado con los archivos reales de Kaggle (no hubo acceso): es la primera tarea al descargarlos."""
import csv
from datetime import date, timedelta

from decision_lab.sim import load_assumptions
from refdata import calibrar, favorita, olist


def _w(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def make_olist(tmp_path):
    h = ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"]
    rows = [
        ["o1", "c1", "delivered", "2017-01-01 10:00:00", "", "", "2017-01-05 10:00:00", "2017-01-10 00:00:00"],   # a tiempo
        ["o2", "c2", "delivered", "2017-01-01 11:00:00", "", "", "2017-01-12 09:00:00", "2017-01-10 00:00:00"],   # tarde 2 días
        ["o3", "c1", "canceled", "2017-01-02 11:00:00", "", "", "", "2017-01-12 00:00:00"],
        ["o4", "c2", "delivered", "2017-01-02 12:00:00", "", "", "2017-01-10 23:00:00", "2017-01-10 00:00:00"],   # mismo día: a tiempo por día? no, 10==10 -> a tiempo
    ]
    _w(tmp_path / "olist_orders_dataset.csv", h, rows)
    _w(tmp_path / "olist_customers_dataset.csv", ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"],
       [["c1", "u1", "1", "x", "SP"], ["c2", "u2", "2", "y", "RJ"]])
    _w(tmp_path / "olist_order_items_dataset.csv", ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"],
       [["o1", 1, "p", "s", "", "100", "10"], ["o2", 1, "p", "s", "", "50", "20"]])
    return tmp_path


def test_olist_kpis(tmp_path):
    r = olist.load(make_olist(tmp_path), min_state_orders=1)
    assert r["pedidos"] == 4 and r["entregados"] == 3
    assert r["fallidos_pct"] == 25.0
    assert r["tardios_pct"] == round(100 / 3, 2)          # solo o2 es tardío (comparación por día)
    assert r["retraso_prom_dias_si_tarde"] == 2.0
    assert r["tardios_por_estado"]["RJ"] == 50.0 and r["tardios_por_estado"]["SP"] == 0.0
    assert r["flete_sobre_precio_pct"] == 20.0


def make_fav(tmp_path):
    rows, d = [], date(2016, 1, 4)  # lunes
    for i in range(28):
        base = 100 + (50 if (d + timedelta(i)).weekday() >= 5 else 0)
        rows += [[(d + timedelta(i)).isoformat(), "1", base], [(d + timedelta(i)).isoformat(), "2", base]]
    _w(tmp_path / "transactions.csv", ["date", "store_nbr", "transactions"], rows)
    return tmp_path


def test_favorita_forma(tmp_path):
    r = favorita.load(make_fav(tmp_path))
    assert r["dias"] == 28 and r["tiendas"] == 2
    assert r["indice_por_dia"]["sábado"] > r["indice_por_dia"]["lunes"]
    assert r["pico_p95_sobre_media"] > 1.0


def test_contraste_no_modifica_supuestos_y_escribe_tabla(tmp_path):
    o, f = tmp_path / "o", tmp_path / "f"
    o.mkdir(); f.mkdir()
    make_olist(o); make_fav(f)
    before = load_assumptions()
    out = tmp_path / "c.md"
    assert calibrar.main(["--olist", str(o), "--favorita", str(f), "--out", str(out)]) == 0
    assert load_assumptions() == before
    txt = out.read_text(encoding="utf-8")
    assert "no** datos de DANEC" in txt and "Pico de demanda" in txt and "Entregas tardías" in txt
