package com.logistpulse.lab.service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Empaque en cajas (bin packing): first-fit decreasing. Lógica pura, sin Spring, para poder probarla sola. */
public final class Packer {

    private Packer() {
    }

    /** Devuelve el volumen usado en cada caja. Cada pieza debe caber en una caja vacía. */
    public static List<Integer> firstFitDecreasing(List<Integer> pieces, int capacity) {
        List<Integer> sorted = new ArrayList<>(pieces);
        sorted.sort(Comparator.reverseOrder());
        List<Integer> boxes = new ArrayList<>();
        for (int piece : sorted) {
            if (piece <= 0 || piece > capacity) {
                throw new IllegalArgumentException("pieza de volumen " + piece + " no cabe en una caja de " + capacity);
            }
            boolean placed = false;
            for (int i = 0; i < boxes.size(); i++) {
                if (boxes.get(i) + piece <= capacity) {
                    boxes.set(i, boxes.get(i) + piece);
                    placed = true;
                    break;
                }
            }
            if (!placed) {
                boxes.add(piece);
            }
        }
        return boxes;
    }
}
