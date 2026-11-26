package com.logistpulse.lab.domain;

/** Ciclo de una orden de compra: PROPOSED → APPROVED → RECEIVED (o REJECTED). Solo una persona aprueba. */
public enum PurchaseStatus {
    PROPOSED, APPROVED, RECEIVED, REJECTED
}
