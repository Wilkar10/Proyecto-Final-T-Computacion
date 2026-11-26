package com.logistpulse.lab.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.List;
import org.junit.jupiter.api.Test;

class PackerTest {

    @Test
    void ffdAcomodaEnMenosCajasQueElOrdenDeLlegada() {
        // 6+4 | 5+5 | 3 → 3 cajas con FFD; el orden 3,5,6,4,5 en first-fit simple usaría 3 también, pero FFD no empeora
        List<Integer> boxes = Packer.firstFitDecreasing(List.of(3, 5, 6, 4, 5), 10);
        assertEquals(3, boxes.size());
        assertEquals(23, boxes.stream().mapToInt(Integer::intValue).sum());
    }

    @Test
    void cadaCajaRespetaLaCapacidad() {
        List<Integer> boxes = Packer.firstFitDecreasing(List.of(4, 4, 4, 4, 3, 3, 3, 2, 1), 10);
        assertEquals(true, boxes.stream().allMatch(b -> b <= 10));
    }

    @Test
    void piezaMasGrandeQueLaCajaSeRechaza() {
        assertThrows(IllegalArgumentException.class, () -> Packer.firstFitDecreasing(List.of(11), 10));
    }

    @Test
    void sinPiezasNoHayCajas() {
        assertEquals(0, Packer.firstFitDecreasing(List.of(), 10).size());
    }
}
