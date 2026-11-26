package com.logistpulse.lab.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** Patrón Outbox: el evento se guarda en la MISMA transacción que el cambio de estado y un relé lo publica después. */
@Entity
@Table(name = "outbox_event")
public class OutboxEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 40)
    private String type;

    @Column(nullable = false, length = 200)
    private String payload;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    private Instant publishedAt;

    protected OutboxEvent() {
    }

    public OutboxEvent(String type, String payload) {
        this.type = type;
        this.payload = payload;
    }

    public Long getId() { return id; }
    public String getType() { return type; }
    public String getPayload() { return payload; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getPublishedAt() { return publishedAt; }
    public void markPublished() { this.publishedAt = Instant.now(); }
}
