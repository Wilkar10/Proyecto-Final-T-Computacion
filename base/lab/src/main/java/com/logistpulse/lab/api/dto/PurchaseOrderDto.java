package com.logistpulse.lab.api.dto;

import com.logistpulse.lab.domain.PurchaseOrder;
import com.logistpulse.lab.domain.PurchaseStatus;
import java.time.Instant;

public record PurchaseOrderDto(Long id, String sku, int qty, PurchaseStatus status, String proposedBy, String approvedBy,
                               Instant createdAt, Instant expectedAt, Instant receivedAt) {

    public static PurchaseOrderDto from(PurchaseOrder p) {
        return new PurchaseOrderDto(p.getId(), p.getSku(), p.getQty(), p.getStatus(), p.getProposedBy(),
                p.getApprovedBy(), p.getCreatedAt(), p.getExpectedAt(), p.getReceivedAt());
    }
}
