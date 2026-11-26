package com.logistpulse.lab.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;

@Entity
@Table(name = "purchase_order")
public class PurchaseOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 20)
    private String sku;

    private int qty;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 12)
    private PurchaseStatus status = PurchaseStatus.PROPOSED;

    @Column(nullable = false, length = 60)
    private String proposedBy;

    @Column(length = 60)
    private String approvedBy;

    @Column(unique = true, length = 64)
    private String idempotencyKey;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    @Column(nullable = false)
    private Instant expectedAt;

    private Instant receivedAt;

    @Version
    private Long version;

    protected PurchaseOrder() {
    }

    public PurchaseOrder(String sku, int qty, String proposedBy, String idempotencyKey, Instant expectedAt) {
        this.sku = sku;
        this.qty = qty;
        this.proposedBy = proposedBy;
        this.idempotencyKey = idempotencyKey;
        this.expectedAt = expectedAt;
    }

    public void approve(String by) {
        this.status = PurchaseStatus.APPROVED;
        this.approvedBy = by;
    }

    public void markReceived() {
        this.status = PurchaseStatus.RECEIVED;
        this.receivedAt = Instant.now();
    }

    public Long getId() { return id; }
    public String getSku() { return sku; }
    public int getQty() { return qty; }
    public PurchaseStatus getStatus() { return status; }
    public String getProposedBy() { return proposedBy; }
    public String getApprovedBy() { return approvedBy; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getExpectedAt() { return expectedAt; }
    public Instant getReceivedAt() { return receivedAt; }
}
