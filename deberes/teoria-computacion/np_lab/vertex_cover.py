"""Cobertura de vértices: aristas (u, v); ¿existe un conjunto de <= k vértices que toque toda arista?"""
from __future__ import annotations

import itertools


def verify_cover(edges, k: int, cover: set[int]) -> bool:
    """V(G, k, C): O(|E|)."""
    return len(cover) <= k and all(u in cover or v in cover for u, v in edges)


def brute_force(edges, n: int, k: int):
    """Exacto O(C(n,k)·|E|). Devuelve un cubrimiento de tamaño <= k o None."""
    for size in range(k + 1):
        for comb in itertools.combinations(range(n), size):
            if verify_cover(edges, k, set(comb)):
                return set(comb)
    return None


def approx_2(edges) -> set[int]:
    """2-aproximación por emparejamiento maximal: mientras haya una arista (u,v) sin cubrir,
    agregar u y v. Garantía: |C| <= 2·|C óptimo|. Devuelve un cubrimiento válido."""
    cover: set[int] = set()
    for u, v in edges:                 # emparejamiento maximal: las aristas elegidas son disjuntas
        if u not in cover and v not in cover:
            cover |= {u, v}
    return cover
