package com.logistpulse.lab.service;

/** Punto de pedido: si lo disponible + lo ya pedido cae bajo el mínimo, sugiere comprar hasta el máximo. Solo SUGIERE. */
public final class ReorderPolicy {

    private ReorderPolicy() {
    }

    public static int suggestedQty(int available, int onOrder, int minStock, int maxStock) {
        int position = available + onOrder;
        return position < minStock ? Math.max(0, maxStock - position) : 0;
    }
}
