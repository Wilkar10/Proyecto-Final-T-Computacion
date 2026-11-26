package com.logistpulse.lab.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** Libro de movimientos: solo se inserta. Un error se compensa con otro movimiento, nunca se edita. */
@Entity
@Table(name = "stock_movement")
public class StockMovement {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 20)
    private String sku;

    /** OPENING, RECEIPT, PICK o ADJUST. */
    @Column(nullable = false, length = 12)
    private String kind;

    /** Con signo: RECEIPT/OPENING > 0, PICK < 0. */
    private int qty;

    @Column(length = 40)
    private String ref;

    @Column(unique = true, length = 64)
    private String idempotencyKey;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    protected StockMovement() {
    }

    public StockMovement(String sku, String kind, int qty, String ref, String idempotencyKey) {
        this.sku = sku;
        this.kind = kind;
        this.qty = qty;
        this.ref = ref;
        this.idempotencyKey = idempotencyKey;
    }

    public Long getId() { return id; }
    public String getSku() { return sku; }
    public String getKind() { return kind; }
    public int getQty() { return qty; }
    public String getRef() { return ref; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public Instant getCreatedAt() { return createdAt; }
}
