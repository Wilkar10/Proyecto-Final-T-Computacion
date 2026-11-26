package com.logistpulse.lab.service;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class ReorderPolicyTest {

    @Test
    void bajoElMinimoSugiereHastaElMaximo() {
        assertEquals(70, ReorderPolicy.suggestedQty(20, 0, 30, 90));
    }

    @Test
    void loYaPedidoCuentaComoPosicion() {
        assertEquals(0, ReorderPolicy.suggestedQty(10, 40, 30, 90));
    }

    @Test
    void enElMinimoExactoNoSugiere() {
        assertEquals(0, ReorderPolicy.suggestedQty(30, 0, 30, 90));
    }
}
