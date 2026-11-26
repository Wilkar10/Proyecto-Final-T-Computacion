# Resultados del benchmark (medidos, semilla 1, límite 10 s por llamada)

Comando: `python -m np_lab.bench tsp 6 7 8 9 10 11 12` (instancias `random_tsp(n, 1)`; n = número de paradas sin contar el origen).

| n | fuerza bruta (s) | Held-Karp (s) | vecino más cercano (costo vs óptimo) |
|---|---|---|---|
| 6 | 0,0007 | 0,0002 | 30 vs 28 |
| 8 | 0,043 | 0,001 | 34 vs 32 |
| 9 | 0,42 | 0,003 | 46 vs 36 |
| 10 | 4,44 | 0,006 | 36 vs 36 |
| 11 | timeout (>10) | 0,015 | 36 vs 36 |
| 12 | timeout (>10) | 0,036 | 50 vs 36 |

Held-Karp adicional (misma semilla): n=13 0,08 s; n=14 0,18 s; n=15 0,42 s; n=16 1,0 s (memoria máx. ~36 MB).
2-opt sobre vecino más cercano en n=12: 50 → 36 (alcanza el óptimo en esta instancia; no está garantizado).

## Lectura estratégica
- Fuerza bruta crece como (n-1)!: cada parada adicional multiplica el tiempo por ~10; inviable desde n=11.
- Held-Karp es O(n²·2ⁿ): sigue siendo exponencial, pero con n ≤ 12 (tope del validador del agente) responde en milisegundos. Para el despacho multi-parada real, **el problema NP-completo es práctico** porque n es pequeño.
- La heurística (NN, NN+2-opt) no garantiza óptimo: puede rendir 39 % más costo (n=12, NN). Un «no» de la heurística a la pregunta de decisión (¿existe ciclo ≤ presupuesto?) **no es prueba**; por eso el plugin marca `proven=False`.
- Decisión de producto: ≤ 8 fuerza bruta, ≤ 15 Held-Karp (exacto), > 15 heurística; el validador V verifica el certificado en tiempo polinomial sin importar el solver.
