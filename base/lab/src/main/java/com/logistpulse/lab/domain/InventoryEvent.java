package com.logistpulse.lab.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** Outbox del contexto de inventario (aparte del de despacho): se guarda en la misma transacción que el cambio. */
@Entity
@Table(name = "inventory_event")
public class InventoryEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 40)
    private String type;

    /** JSON del payload (ver contracts/schemas). */
    @Column(nullable = false, length = 400)
    private String payload;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    private Instant publishedAt;

    protected InventoryEvent() {
    }

    public InventoryEvent(String type, String payload) {
        this.type = type;
        this.payload = payload;
    }

    public void markPublished() {
        this.publishedAt = Instant.now();
    }

    public Long getId() { return id; }
    public String getType() { return type; }
    public String getPayload() { return payload; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getPublishedAt() { return publishedAt; }
}
