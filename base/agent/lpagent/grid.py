"""Plano del almacén y costos de ruta. Replica las reglas de WarehouseGrid.java (lab):
'.' cuesta 1, ',' cuesta 5 (congestión), '#' bloqueado. El costo es el de ENTRAR a cada celda."""
from __future__ import annotations

import heapq

DEFAULT_LAYOUT = [
    "............",
    ".####..####.",
    "............",
    ".#..,,,..#..",
    ".#..,,,..#..",
    "............",
    ".####..####.",
    "............",
]
INF = 10**9


def walkable(rows: list[str], x: int, y: int) -> bool:
    return 0 <= y < len(rows) and 0 <= x < len(rows[0]) and rows[y][x] != "#"


def cell_cost(rows: list[str], x: int, y: int) -> int:
    return 5 if rows[y][x] == "," else 1


def dijkstra(rows: list[str], src: tuple[int, int]) -> dict[tuple[int, int], int]:
    """Costo mínimo desde src a toda celda alcanzable (problema en P: O((V+E) log V))."""
    dist = {src: 0}
    heap = [(0, src)]
    while heap:
        d, (x, y) = heapq.heappop(heap)
        if d != dist[(x, y)]:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if walkable(rows, nx, ny):
                nd = d + cell_cost(rows, nx, ny)
                if nd < dist.get((nx, ny), INF):
                    dist[(nx, ny)] = nd
                    heapq.heappush(heap, (nd, (nx, ny)))
    return dist


def distance_matrix(rows: list[str], points: list[tuple[int, int]]) -> list[list[int]]:
    """Matriz de costos entre puntos[0]=origen y las paradas. Lanza ValueError si alguna es inalcanzable."""
    out: list[list[int]] = []
    for p in points:
        d = dijkstra(rows, p)
        row = []
        for q in points:
            if q not in d:
                raise ValueError(f"destino inalcanzable: {q}")
            row.append(d[q])
        out.append(row)
    return out
